"""Retrieve knowledge for a question (rag-knowledge-base D3): embed once, search three kinds concurrently."""

import asyncio
from dataclasses import dataclass
from typing import Protocol

import asyncpg

from app.knowledge import KnowledgeKind
from app.knowledge_sync import Embedder


class RetrievalUnavailable(Exception):
    """Embedding or search failed; the question cannot go on in rag mode (D9: never fall back to static)."""


@dataclass(frozen=True)
class Retrieved:
    id: str
    kind: KnowledgeKind
    title: str
    content: str
    # Cosine distance to the question: 0 is identical, larger is less related.
    distance: float


@dataclass(frozen=True)
class RetrievalResult:
    schema: tuple[Retrieved, ...] = ()
    glossary: tuple[Retrieved, ...] = ()
    example: tuple[Retrieved, ...] = ()

    def all(self) -> tuple[Retrieved, ...]:
        return self.schema + self.glossary + self.example


@dataclass(frozen=True)
class TopN:
    schema: int = 4
    glossary: int = 3
    example: int = 3

    def __post_init__(self) -> None:
        for kind in ("schema", "glossary", "example"):
            if getattr(self, kind) < 1:
                raise ValueError(f"top-N for {kind} must be at least 1")


DEFAULT_TOP_N = TopN()


class VectorSearch(Protocol):
    async def nearest(self, vector: list[float], kind: KnowledgeKind, limit: int) -> list[Retrieved]: ...


class Retriever:
    def __init__(self, embedder: Embedder, search: VectorSearch, *, top_n: TopN = DEFAULT_TOP_N):
        self._embedder = embedder
        self._search = search
        self._top_n = top_n

    async def retrieve(self, question: str) -> RetrievalResult:
        try:
            # The slowest call, so once per question; the three searches share its vector.
            vector = await self._embedder.embed(question)
            schema, glossary, example = await asyncio.gather(
                self._search.nearest(vector, "schema", self._top_n.schema),
                self._search.nearest(vector, "glossary", self._top_n.glossary),
                self._search.nearest(vector, "example", self._top_n.example),
            )
        except Exception as e:
            raise RetrievalUnavailable(f"{type(e).__name__}: {e}") from e
        return RetrievalResult(schema=tuple(schema), glossary=tuple(glossary), example=tuple(example))


_NEAREST = """
SELECT id, kind, title, content, embedding <=> $1::vector AS distance
FROM knowledge_documents WHERE kind = $2
ORDER BY distance, id LIMIT $3
"""


class PgVectorSearch:
    """Cosine search on knowledge_documents as genbi_reader (D5, D7: no index, a full scan of tens of rows)."""

    def __init__(self, dsn: str, *, statement_timeout_ms: int = 2000):
        if statement_timeout_ms <= 0:
            raise ValueError(f"statement_timeout_ms must be positive, got {statement_timeout_ms}")
        self._dsn = dsn
        self._statement_timeout_ms = statement_timeout_ms
        self._pool: asyncpg.Pool | None = None
        self._lock = asyncio.Lock()

    async def _get_pool(self) -> asyncpg.Pool:
        async with self._lock:
            if self._pool is None:
                # Three connections: one per kind, so the searches really run at the same time.
                self._pool = await asyncpg.create_pool(self._dsn, min_size=1, max_size=3)
        return self._pool

    async def nearest(self, vector: list[float], kind: KnowledgeKind, limit: int) -> list[Retrieved]:
        pool = await self._get_pool()
        literal = "[" + ",".join(repr(float(x)) for x in vector) + "]"
        async with pool.acquire() as conn, conn.transaction(readonly=True):
            await conn.execute(f"SET LOCAL statement_timeout = {int(self._statement_timeout_ms)}")
            rows = await conn.fetch(_NEAREST, literal, kind, limit)
        return [Retrieved(r["id"], r["kind"], r["title"], r["content"], float(r["distance"])) for r in rows]

    async def close(self) -> None:
        if self._pool is not None:
            await self._pool.close()
