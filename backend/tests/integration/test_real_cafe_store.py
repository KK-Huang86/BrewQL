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


async def test_members_and_their_behaviour_are_simulated_for_the_real_cafes(empty_db):
    store = PgRealCafeStore(empty_db)
    try:
        await store.write(batch())
    finally:
        await store.close()

    [counts] = await fetch(
        empty_db,
        """
        SELECT (SELECT count(*) FROM users) AS users,
               (SELECT count(*) FROM search_logs) AS searches,
               (SELECT count(*) FROM cafe_views) AS views,
               (SELECT count(*) FROM favorites) AS favorites,
               -- searches only name districts that have real cafes
               (SELECT count(*) FROM search_logs s
                WHERE NOT EXISTS (SELECT 1 FROM cafes c WHERE c.city = s.city AND c.district = s.district))
                 AS searches_elsewhere,
               -- the counters on cafes equal the detail rows, as in demo
               (SELECT count(*) FROM cafes c
                WHERE c.view_count <> (SELECT count(*) FROM cafe_views v WHERE v.cafe_id = c.id)
                   OR c.favorite_count <> (SELECT count(*) FROM favorites f WHERE f.cafe_id = c.id))
                 AS counters_off,
               -- nobody searches or views before joining
               (SELECT count(*) FROM search_logs s JOIN users u ON u.id = s.user_id
                WHERE s.created_at < u.created_at) AS before_joining,
               -- the real votes stay as imported: no member votes appear
               (SELECT count(*) FROM cafe_attribute_votes WHERE source = 'user') AS member_votes
        """,
    )
    assert counts["users"] == 2000
    assert counts["searches"] > 40_000 and counts["views"] > 150_000 and counts["favorites"] > 0
    assert (counts["searches_elsewhere"], counts["counters_off"], counts["before_joining"]) == (0, 0, 0)
    assert counts["member_votes"] == 0


async def test_no_view_or_favorite_comes_before_the_cafe_was_listed(empty_db):
    # Real cafes keep their listing date; one listed three days ago must not have months of views.
    from datetime import UTC, datetime, timedelta

    listed = (datetime.now(UTC) - timedelta(days=3)).isoformat(sep=" ")
    cafes = [
        {**EXPORT_ROW, "id": "1", "place_id": "p1", "address": "台北市信義區信義路五段 7 號"},
        {**EXPORT_ROW, "id": "2", "place_id": "p2", "address": "台北市信義區松仁路 1 號", "created_at": listed},
    ]
    store = PgRealCafeStore(empty_db)
    try:
        await store.write(prepare(cafes, [], []))
    finally:
        await store.close()

    [early] = await fetch(
        empty_db,
        """
        SELECT (SELECT count(*) FROM cafe_views v JOIN cafes c ON c.id = v.cafe_id
                WHERE v.created_at < c.created_at) AS views,
               (SELECT count(*) FROM favorites f JOIN cafes c ON c.id = f.cafe_id
                WHERE f.created_at < c.created_at) AS favorites,
               (SELECT count(*) FROM cafe_views v JOIN cafes c ON c.id = v.cafe_id
                WHERE c.place_id = 'p2') AS new_cafe_views
        """,
    )
    assert (early["views"], early["favorites"]) == (0, 0)
    assert early["new_cafe_views"] > 0  # still visited, just not before it existed
