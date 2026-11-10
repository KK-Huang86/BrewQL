"""Postgres knowledge store (rag-knowledge-base D4): one transaction per import, as genbi_knowledge_writer."""

import asyncpg
import pytest

from app.knowledge import KnowledgeDoc
from app.knowledge_sync import EmbeddedDoc, PgKnowledgeStore

DIM = 1024


def embedded(doc_id: str, content: str = "定義", dimension: int = DIM) -> EmbeddedDoc:
    doc = KnowledgeDoc(id=doc_id, kind="glossary", title=doc_id, content=content)
    return EmbeddedDoc(doc, content_hash=f"hash-{content}", embedding=[0.1] * dimension)


@pytest.fixture
async def store(knowledge_dsn):
    store = PgKnowledgeStore(knowledge_dsn)
    yield store
    await store.close()
    conn = await asyncpg.connect(knowledge_dsn)
    await conn.execute("DELETE FROM knowledge_documents WHERE id LIKE 'store-test-%'")
    await conn.close()


async def test_apply_upserts_and_deletes_and_hashes_reflect_it(store):
    await store.apply([embedded("store-test-a"), embedded("store-test-b")], [])
    await store.apply([embedded("store-test-a", content="新定義")], ["store-test-b"])

    hashes = await store.hashes()
    assert hashes["store-test-a"] == "hash-新定義"
    assert "store-test-b" not in hashes


async def test_stored_document_keeps_every_field(store, knowledge_dsn):
    await store.apply([embedded("store-test-a", content="不限時")], [])

    conn = await asyncpg.connect(knowledge_dsn)
    row = await conn.fetchrow(
        "SELECT kind, title, content, vector_dims(embedding) AS dims FROM knowledge_documents WHERE id = $1",
        "store-test-a",
    )
    await conn.close()
    assert dict(row) == {"kind": "glossary", "title": "store-test-a", "content": "不限時", "dims": DIM}


async def test_a_failing_row_rolls_back_the_whole_batch(store):
    await store.apply([embedded("store-test-keep")], [])

    with pytest.raises(asyncpg.PostgresError):
        await store.apply(
            [embedded("store-test-new"), embedded("store-test-bad", dimension=3)],
            ["store-test-keep"],
        )

    hashes = await store.hashes()
    assert "store-test-keep" in hashes  # the delete in the failed batch did not happen
    assert "store-test-new" not in hashes  # nor did the row before the bad one
