"""Integration tests need a real Postgres seeded by db/init, reached as genbi_reader.

Set TEST_DATABASE_URL (e.g. postgresql://genbi_reader:...@127.0.0.1:5432/genbi)
to run them; without it they are skipped so unit tests never need a database.
"""

import os
from pathlib import Path

import asyncpg
import pytest

from app.db import PgExecutor


@pytest.fixture
def reader_dsn() -> str:
    dsn = os.environ.get("TEST_DATABASE_URL")
    if not dsn:
        pytest.skip("TEST_DATABASE_URL not set")
    return dsn


@pytest.fixture
async def reader(reader_dsn):
    """A plain genbi_reader connection; tests that need a writable session override it."""
    conn = await asyncpg.connect(reader_dsn)
    yield conn
    await conn.close()


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


@pytest.fixture
def owner_dsn() -> str:
    """The database owner's DSN, for tests of what only the owner writes (import-real-cafes D3)."""
    dsn = os.environ.get("TEST_OWNER_DATABASE_URL")
    if not dsn:
        pytest.skip("TEST_OWNER_DATABASE_URL not set")
    return dsn


@pytest.fixture
def knowledge_dsn() -> str:
    """genbi_knowledge_writer's DSN (rag-knowledge-base D5); db/test-db.sh prints it next to the others."""
    dsn = os.environ.get("TEST_KNOWLEDGE_DATABASE_URL")
    if not dsn:
        pytest.skip("TEST_KNOWLEDGE_DATABASE_URL not set")
    return dsn


SCHEMA = Path(__file__).resolve().parents[3] / "db" / "init" / "01_schema.sql"
SCRATCH = "genbi_real_import_test"


@pytest.fixture
async def empty_db(owner_dsn):
    """A scratch database with db/init/01_schema.sql only: no seed, no roles (import-real-cafes)."""
    admin = await asyncpg.connect(owner_dsn)
    await admin.execute(f"DROP DATABASE IF EXISTS {SCRATCH} WITH (FORCE)")
    await admin.execute(f"CREATE DATABASE {SCRATCH}")
    dsn = owner_dsn.rsplit("/", 1)[0] + f"/{SCRATCH}"
    conn = await asyncpg.connect(dsn)
    await conn.execute(SCHEMA.read_text(encoding="utf-8"))
    await conn.close()
    yield dsn
    await admin.execute(f"DROP DATABASE IF EXISTS {SCRATCH} WITH (FORCE)")
    await admin.close()
