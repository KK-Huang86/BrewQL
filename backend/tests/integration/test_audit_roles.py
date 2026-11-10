"""Audit table permissions (record-audit-log D2): the writer appends, nobody in the API edits."""

import uuid

import asyncpg
import pytest


@pytest.fixture
async def writer(audit_dsn):
    conn = await asyncpg.connect(audit_dsn)
    yield conn
    await conn.close()


@pytest.fixture
async def reader(reader_dsn):
    conn = await asyncpg.connect(reader_dsn)
    # Lift the role's read-only default so the missing grant, not read-only mode, is what refuses.
    await conn.execute("SET SESSION CHARACTERISTICS AS TRANSACTION READ WRITE")
    yield conn
    await conn.close()


async def insert_one(conn) -> uuid.UUID:
    request_id = uuid.uuid4()
    await conn.execute(
        "INSERT INTO ask_audit (request_id, question, status) VALUES ($1, $2, $3)", request_id, "台北有幾家？", "ok"
    )
    return request_id


async def test_writer_appends_and_reads_back_its_record(writer):
    request_id = await insert_one(writer)

    row = await writer.fetchrow("SELECT question, status FROM ask_audit WHERE request_id = $1", request_id)
    assert (row["question"], row["status"]) == ("台北有幾家？", "ok")


async def test_writer_cannot_read_business_tables(writer):
    with pytest.raises(asyncpg.InsufficientPrivilegeError):
        await writer.fetch("SELECT * FROM cafes LIMIT 1")


@pytest.mark.parametrize(
    "sql",
    [
        "UPDATE ask_audit SET question = 'edited' WHERE request_id = $1",
        "DELETE FROM ask_audit WHERE request_id = $1",
    ],
)
async def test_writer_cannot_change_a_record(writer, sql):
    request_id = await insert_one(writer)

    with pytest.raises(asyncpg.InsufficientPrivilegeError):
        await writer.execute(sql, request_id)


async def test_writer_cannot_empty_the_table(writer):
    with pytest.raises(asyncpg.InsufficientPrivilegeError):
        await writer.execute("TRUNCATE ask_audit")


@pytest.mark.parametrize("sql", ["SELECT * FROM ask_audit LIMIT 1", "DELETE FROM ask_audit"])
async def test_reader_cannot_touch_audit_records(reader, writer, sql):
    # Even SQL that slipped past the guard must not see other visitors' questions.
    await insert_one(writer)

    with pytest.raises(asyncpg.InsufficientPrivilegeError):
        await reader.execute(sql)
