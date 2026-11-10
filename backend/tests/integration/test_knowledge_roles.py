"""Knowledge base permissions (rag-knowledge-base D5): only the importer writes it, the API only reads it."""

import uuid

import asyncpg
import pytest

VECTOR = "[" + ",".join(["0.1"] * 1024) + "]"


@pytest.fixture
async def writer(knowledge_dsn):
    conn = await asyncpg.connect(knowledge_dsn)
    yield conn
    await conn.execute("DELETE FROM knowledge_documents WHERE id LIKE 'test-%'")
    await conn.close()


@pytest.fixture
async def reader(reader_dsn):
    conn = await asyncpg.connect(reader_dsn)
    # Lift the role's read-only default so the missing grant, not read-only mode, is what refuses.
    await conn.execute("SET SESSION CHARACTERISTICS AS TRANSACTION READ WRITE")
    yield conn
    await conn.close()


async def insert_one(conn, embedding: str = VECTOR) -> str:
    doc_id = f"test-{uuid.uuid4()}"
    await conn.execute(
        "INSERT INTO knowledge_documents (id, kind, title, content, content_hash, embedding)"
        " VALUES ($1, 'glossary', '工作友善', '定義', 'hash', $2::vector)",
        doc_id,
        embedding,
    )
    return doc_id


async def test_writer_inserts_updates_and_deletes_documents(writer):
    doc_id = await insert_one(writer)
    await writer.execute("UPDATE knowledge_documents SET content = '新定義' WHERE id = $1", doc_id)
    assert await writer.fetchval("SELECT content FROM knowledge_documents WHERE id = $1", doc_id) == "新定義"

    await writer.execute("DELETE FROM knowledge_documents WHERE id = $1", doc_id)
    assert await writer.fetchval("SELECT count(*) FROM knowledge_documents WHERE id = $1", doc_id) == 0


@pytest.mark.parametrize(
    "sql",
    [
        "SELECT * FROM cafes LIMIT 1",
        "INSERT INTO cafes (name, address) VALUES ('x', 'y')",
        "SELECT * FROM ask_audit LIMIT 1",
    ],
)
async def test_writer_cannot_touch_other_tables(writer, sql):
    with pytest.raises(asyncpg.InsufficientPrivilegeError):
        await writer.execute(sql)


async def test_embedding_must_have_1024_dimensions(writer):
    # A different embedding model or dimension must fail loudly, not mix incomparable vectors.
    with pytest.raises(asyncpg.DataError):
        await insert_one(writer, embedding="[0.1,0.2,0.3]")


async def test_reader_can_read_documents_for_retrieval(reader, writer):
    doc_id = await insert_one(writer)

    assert await reader.fetchval("SELECT title FROM knowledge_documents WHERE id = $1", doc_id) == "工作友善"


@pytest.mark.parametrize(
    "sql",
    ["UPDATE knowledge_documents SET content = 'x'", "DELETE FROM knowledge_documents", "TRUNCATE knowledge_documents"],
)
async def test_reader_cannot_change_documents(reader, sql):
    with pytest.raises(asyncpg.InsufficientPrivilegeError):
        await reader.execute(sql)
