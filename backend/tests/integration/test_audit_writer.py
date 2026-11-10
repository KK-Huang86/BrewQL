"""PgAuditWriter against the real ask_audit table (record-audit-log D1, D4), as genbi_audit_writer."""

import uuid

import asyncpg
import pytest

from app.audit import AuditRecord, PgAuditWriter


@pytest.fixture
async def writer(audit_dsn):
    w = PgAuditWriter(audit_dsn)
    yield w
    await w.close()


@pytest.fixture
async def conn(audit_dsn):
    c = await asyncpg.connect(audit_dsn)
    yield c
    await c.close()


def full_record() -> AuditRecord:
    return AuditRecord(
        request_id=uuid.uuid4(),
        visitor="0f1488db",
        question="台北有幾家咖啡店？",
        status="ok",
        sql="SELECT COUNT(*) FROM cafes LIMIT 1000",
        failed_attempts=[{"error_kind": "guardrail", "reason": "只允許 SELECT", "sql": "DELETE FROM cafes"}],
        guardrail_reasons=("prompt_attack",),
        model_id="us.anthropic.claude-haiku-4-5-20251001-v1:0",
        input_tokens=3000,
        output_tokens=120,
        guardrail_units=2,
        estimated_cost_usd=0.00426,
        elapsed_ms=2300,
        row_count=1,
    )


async def test_every_field_is_stored(writer, conn):
    record = full_record()

    await writer.write(record)

    row = await conn.fetchrow("SELECT * FROM ask_audit WHERE request_id = $1", record.request_id)
    assert row["question"] == "台北有幾家咖啡店？"
    assert row["visitor"] == "0f1488db"
    assert (row["status"], row["sql"], row["row_count"]) == ("ok", "SELECT COUNT(*) FROM cafes LIMIT 1000", 1)
    assert (
        row["failed_attempts"] == '[{"sql": "DELETE FROM cafes", "reason": "只允許 SELECT", "error_kind": "guardrail"}]'
    )
    assert row["guardrail_reasons"] == ["prompt_attack"]
    assert (row["input_tokens"], row["output_tokens"], row["guardrail_units"]) == (3000, 120, 2)
    assert float(row["estimated_cost_usd"]) == pytest.approx(0.00426)
    assert row["elapsed_ms"] == 2300
    assert row["created_at"] is not None


async def test_unknown_values_stay_null(writer, conn):
    record = AuditRecord(
        request_id=uuid.uuid4(), visitor=None, question="q", status="error", error_kind="unavailable_db"
    )

    await writer.write(record)

    row = await conn.fetchrow("SELECT * FROM ask_audit WHERE request_id = $1", record.request_id)
    assert (row["visitor"], row["sql"], row["estimated_cost_usd"], row["row_count"]) == (None, None, None, None)
    assert row["failed_attempts"] == "[]"
    assert row["guardrail_reasons"] == []


async def test_writing_the_same_request_twice_keeps_one_row(writer, conn):
    record = full_record()

    await writer.write(record)
    await writer.write(record)

    assert await conn.fetchval("SELECT count(*) FROM ask_audit WHERE request_id = $1", record.request_id) == 1


async def test_unreachable_database_raises_for_the_handler_to_report():
    # The handler counts and logs it (D4); the writer itself must not swallow it.
    w = PgAuditWriter("postgresql://genbi_audit_writer:x@127.0.0.1:1/genbi")

    with pytest.raises(OSError):
        await w.write(full_record())
    await w.close()
