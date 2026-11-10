"""Writing a real cafe batch (import-real-cafes D3) into a scratch database built from db/init/01_schema.sql."""

from pathlib import Path

import asyncpg
import pytest

from app.real_cafes import prepare
from app.real_cafes_store import PgRealCafeStore
from tests.test_real_cafes import EXPORT_ROW, LAT, nomad, vote

SCHEMA = Path(__file__).resolve().parents[3] / "db" / "init" / "01_schema.sql"
SCRATCH = "genbi_real_import_test"


@pytest.fixture
async def empty_db(owner_dsn):
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


def batch(nomad_override=None):
    cafes = [
        {**EXPORT_ROW, "id": "1", "place_id": "p1", "name": "晨光咖啡", "address": "台北市信義區信義路五段 7 號"},
        {**EXPORT_ROW, "id": "2", "place_id": "p2", "name": "午後咖啡", "address": "某條路 9 號",
         "lat": str(LAT + 300 / 111_000)},
    ]  # fmt: skip
    votes = [vote("google", cafe_id="2"), vote("cafenomad", cafe_id="1")]
    return prepare(cafes, votes, [nomad("n1", "午後咖啡", north_m=300, **(nomad_override or {}))])


async def fetch(dsn, sql):
    conn = await asyncpg.connect(dsn)
    try:
        return await conn.fetch(sql)
    finally:
        await conn.close()


async def test_batch_lands_with_votes_and_nomad_linked_to_the_new_cafe_ids(empty_db):
    store = PgRealCafeStore(empty_db)
    try:
        assert await store.has_cafes() is False
        await store.write(batch())
        assert await store.has_cafes() is True
    finally:
        await store.close()

    cafes = await fetch(empty_db, "SELECT place_id, city, district, pet_friendly FROM cafes ORDER BY place_id")
    assert [tuple(r) for r in cafes] == [("p1", "台北市", "信義區", None), ("p2", "台北市", "信義區", None)]
    links = await fetch(
        empty_db,
        "SELECT c.place_id, v.source FROM cafe_attribute_votes v JOIN cafes c ON c.id = v.cafe_id ORDER BY 1",
    )
    assert [tuple(r) for r in links] == [("p1", "cafenomad"), ("p2", "google")]
    nomad_rows = await fetch(
        empty_db, "SELECT c.place_id, n.wifi FROM cafe_nomad_cache n JOIN cafes c ON c.id = n.cafe_id"
    )
    assert [(r["place_id"], float(r["wifi"])) for r in nomad_rows] == [("p2", 4.5)]


async def test_a_failure_after_the_cafes_leaves_the_database_empty(empty_db):
    store = PgRealCafeStore(empty_db)
    try:
        # The CHECK on cafe_nomad_cache.socket fails after cafes and votes were inserted.
        with pytest.raises(asyncpg.CheckViolationError):
            await store.write(batch({"socket": "sometimes"}))
        assert await store.has_cafes() is False
    finally:
        await store.close()
    assert await fetch(empty_db, "SELECT 1 FROM cafe_attribute_votes") == []
