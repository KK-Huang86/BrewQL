"""pgvector search as genbi_reader: nearest by cosine distance, one kind at a time, capped by the limit."""

import asyncpg
import pytest

from app.retrieval import PgVectorSearch


def axis(i: int, weight: float = 1.0) -> list[float]:
    vector = [0.0] * 1024
    vector[i] = weight
    vector[(i + 1) % 1024] = 0.1  # never all-zero; cosine distance is undefined for zero vectors
    return vector


def literal(vector: list[float]) -> str:
    return "[" + ",".join(str(x) for x in vector) + "]"


@pytest.fixture
async def docs(knowledge_dsn):
    conn = await asyncpg.connect(knowledge_dsn)
    rows = [
        ("vs-test-near", "glossary", axis(0)),
        ("vs-test-middle", "glossary", [a + b for a, b in zip(axis(0, 0.5), axis(5, 0.5), strict=True)]),
        ("vs-test-far", "glossary", axis(9)),
        ("vs-test-schema", "schema", axis(0)),
    ]
    for doc_id, kind, vector in rows:
        await conn.execute(
            "INSERT INTO knowledge_documents (id, kind, title, content, content_hash, embedding)"
            " VALUES ($1, $2, $1, 'c', 'h', $3::vector)",
            doc_id,
            kind,
            literal(vector),
        )
    yield
    await conn.execute("DELETE FROM knowledge_documents WHERE id LIKE 'vs-test-%'")
    await conn.close()


@pytest.fixture
async def search(reader_dsn):
    s = PgVectorSearch(reader_dsn)
    yield s
    await s.close()


async def test_nearest_documents_of_one_kind_come_first(docs, search):
    found = await search.nearest(axis(0), "glossary", 2)

    assert [d.id for d in found] == ["vs-test-near", "vs-test-middle"]
    assert found[0].distance < found[1].distance
    assert all(d.kind == "glossary" for d in found)


async def test_a_kind_with_no_documents_returns_nothing(docs, search):
    assert await search.nearest(axis(0), "example", 3) == []
