"""Integration tests need a real Postgres seeded by db/init, reached as genbi_reader.

Set TEST_DATABASE_URL (e.g. postgresql://genbi_reader:...@127.0.0.1:5432/genbi)
to run them; without it they are skipped so unit tests never need a database.
"""

import os

import pytest

from app.db import PgExecutor


@pytest.fixture
def reader_dsn() -> str:
    dsn = os.environ.get("TEST_DATABASE_URL")
    if not dsn:
        pytest.skip("TEST_DATABASE_URL not set")
    return dsn


@pytest.fixture
async def executor(reader_dsn):
    ex = PgExecutor(reader_dsn)
    yield ex
    await ex.close()


@pytest.fixture
def audit_dsn() -> str:
    """genbi_audit_writer's DSN (record-audit-log); db/test-db.sh prints it next to TEST_DATABASE_URL."""
    dsn = os.environ.get("TEST_AUDIT_DATABASE_URL")
    if not dsn:
        pytest.skip("TEST_AUDIT_DATABASE_URL not set")
    return dsn
