"""Import knowledge documents into pgvector (rag-knowledge-base D4).

Embed only what changed (content hash), compute every vector first, then write the whole batch in one
transaction: a failure anywhere leaves the knowledge base exactly as it was.
"""

import asyncio
import hashlib
import logging
from dataclasses import dataclass
from typing import Protocol

import asyncpg

from app.knowledge import KnowledgeDoc

log = logging.getLogger(__name__)


class Embedder(Protocol):
    async def embed(self, text: str) -> list[float]: ...


@dataclass(frozen=True)
class EmbeddedDoc:
    doc: KnowledgeDoc
    content_hash: str
    embedding: list[float]


class KnowledgeStore(Protocol):
    async def hashes(self) -> dict[str, str]: ...

    async def apply(self, upserts: list[EmbeddedDoc], deletes: list[str]) -> None: ...


@dataclass(frozen=True)
class SyncReport:
    added: int
    updated: int
    unchanged: int
    deleted: int


class ImportFailed(Exception):
    """The import stopped and wrote nothing; the message names the document or step at fault."""


def embedding_text(doc: KnowledgeDoc) -> str:
    # Users ask questions, so an example matches on its question rather than on SQL keywords.
    if doc.kind == "example":
        return doc.title
    return f"{doc.title}\n{doc.content}"


def content_hash(doc: KnowledgeDoc, model_id: str) -> str:
    # The model is part of the hash: vectors from two models are not comparable.
    payload = "\n".join([model_id, doc.kind, doc.title, doc.content])
    return hashlib.sha256(payload.encode()).hexdigest()


async def sync_knowledge(
    docs: list[KnowledgeDoc], *, embedder: Embedder, store: KnowledgeStore, model_id: str, dimension: int
) -> SyncReport:
    stored = await store.hashes()
    upserts: list[EmbeddedDoc] = []
    unchanged = 0
    for doc in docs:
        digest = content_hash(doc, model_id)
        if stored.get(doc.id) == digest:
            unchanged += 1
            continue
        upserts.append(EmbeddedDoc(doc, digest, await _embed(embedder, doc, dimension)))
    deletes = sorted(set(stored) - {doc.id for doc in docs})
    added = sum(1 for e in upserts if e.doc.id not in stored)
    report = SyncReport(added=added, updated=len(upserts) - added, unchanged=unchanged, deleted=len(deletes))

    if upserts or deletes:
        try:
            await store.apply(upserts, deletes)
        except Exception as e:
            log.error("knowledge import write failed", extra={"error": type(e).__name__})
            raise ImportFailed(f"write failed, knowledge base unchanged: {type(e).__name__}: {e}") from e
    log.info("knowledge import done", extra={"event": "knowledge_import", **report.__dict__})
    return report


async def _embed(embedder: Embedder, doc: KnowledgeDoc, dimension: int) -> list[float]:
    try:
        vector = await embedder.embed(embedding_text(doc))
    except Exception as e:
        # Nothing has been written yet; stopping here is the rollback.
        log.error("knowledge embedding failed", extra={"doc_id": doc.id, "error": type(e).__name__})
        raise ImportFailed(f"{doc.id}: embedding failed, knowledge base unchanged: {type(e).__name__}: {e}") from e
    if len(vector) != dimension:
        raise ImportFailed(f"{doc.id}: embedding has {len(vector)} dimensions, expected {dimension}")
    return vector


# Serialises concurrent imports; the key is arbitrary but fixed.
_IMPORT_LOCK_KEY = 0x4B4E4F57  # "KNOW"

_UPSERT = """
INSERT INTO knowledge_documents (id, kind, title, content, content_hash, embedding, updated_at)
VALUES ($1, $2, $3, $4, $5, $6::vector, now())
ON CONFLICT (id) DO UPDATE SET
    kind = EXCLUDED.kind, title = EXCLUDED.title, content = EXCLUDED.content,
    content_hash = EXCLUDED.content_hash, embedding = EXCLUDED.embedding, updated_at = now()
"""


class PgKnowledgeStore:
    """knowledge_documents as genbi_knowledge_writer (D5)."""

    def __init__(self, dsn: str) -> None:
        self._dsn = dsn
        self._pool: asyncpg.Pool | None = None
        self._lock = asyncio.Lock()

    async def _get_pool(self) -> asyncpg.Pool:
        async with self._lock:
            if self._pool is None:
                self._pool = await asyncpg.create_pool(self._dsn, min_size=1, max_size=1)
        return self._pool

    async def hashes(self) -> dict[str, str]:
        pool = await self._get_pool()
        rows = await pool.fetch("SELECT id, content_hash FROM knowledge_documents")
        return {r["id"]: r["content_hash"] for r in rows}

    async def apply(self, upserts: list[EmbeddedDoc], deletes: list[str]) -> None:
        pool = await self._get_pool()
        async with pool.acquire() as conn, conn.transaction():
            # Two imports at once apply one after the other; both write the same repo state.
            await conn.execute("SELECT pg_advisory_xact_lock($1)", _IMPORT_LOCK_KEY)
            # Deletes first: a failing upsert after them must undo them, which only the transaction does.
            if deletes:
                await conn.execute("DELETE FROM knowledge_documents WHERE id = ANY($1::text[])", deletes)
            await conn.executemany(_UPSERT, [_row(e) for e in upserts])

    async def close(self) -> None:
        if self._pool is not None:
            await self._pool.close()


def _row(e: EmbeddedDoc) -> tuple:
    vector = "[" + ",".join(repr(float(x)) for x in e.embedding) + "]"
    return (e.doc.id, e.doc.kind, e.doc.title, e.doc.content, e.content_hash, vector)
