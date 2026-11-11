"""Distance from each cafe to the transit stations (cafe-transit-distance D4).

Known distances are built far from every real station (off the east coast, 25.30 N 122.05 E)
inside a transaction that is always rolled back. 0.001 degree of latitude is about 111.2 m.
"""

import asyncpg
import pytest

from app.real_cafes import distance_m
from tests.integration.points import Point

LAT, LNG = 25.300000, 122.050000
M_PER_DEG_LAT = 111_195  # haversine on a 6,371 km sphere


def north(metres: float) -> float:
    return round(LAT + metres / M_PER_DEG_LAT, 6)


@pytest.fixture
async def scratch(owner_dsn):
    """Owner connection with a test cafe and stations; everything is rolled back afterwards."""
    conn = await asyncpg.connect(owner_dsn)
    tx = conn.transaction()
    await tx.start()
    try:
        cafe_id = await conn.fetchval(
            "INSERT INTO cafes (place_id, name, address, city, district, lat, lng) "
            "VALUES ('test-far', '測試咖啡', '測試地址', '新北市', '貢寮區', $1, $2) RETURNING id",
            LAT,
            LNG,
        )
        await conn.executemany(
            "INSERT INTO mrt_stations (name, city, district, exit_count, lat, lng, as_of) "
            "VALUES ($1, '新北市', '貢寮區', 1, $2, $3, '2026-11-11')",
            [("測試近站", north(500), LNG), ("測試遠站", north(900), LNG)],
        )
        await conn.executemany(
            "INSERT INTO youbike_stations (station_no, name, city, district, docks, lat, lng, as_of) "
            "VALUES ($1, '測試', '新北市', '貢寮區', 10, $2, $3, '2026-11-11')",
            [("test-1", north(100), LNG), ("test-2", north(-250), LNG), ("test-3", north(350), LNG)],
        )
        yield conn, cafe_id
    finally:
        await tx.rollback()
        await conn.close()


async def test_nearest_mrt_station_and_its_distance(scratch):
    conn, cafe_id = scratch

    row = await conn.fetchrow("SELECT * FROM v_cafe_transit WHERE cafe_id = $1", cafe_id)

    assert row["nearest_mrt"] == "測試近站"
    assert row["mrt_distance_m"] == pytest.approx(500, rel=0.01)


async def test_youbike_stations_within_300_m_are_counted(scratch):
    # 100 m and 250 m count; 350 m does not.
    conn, cafe_id = scratch

    assert await conn.fetchval("SELECT youbike_within_300m FROM v_cafe_transit WHERE cafe_id = $1", cafe_id) == 2


async def test_sql_distance_matches_the_python_haversine(reader):
    # 台北車站 to 板橋, about 6 km: the same formula the real import already uses.
    rows = {
        r["name"]: Point(float(r["lat"]), float(r["lng"]))
        for r in await reader.fetch("SELECT name, lat, lng FROM mrt_stations WHERE name IN ('台北車站', '板橋')")
    }
    a, b = rows["台北車站"], rows["板橋"]

    sql = await reader.fetchval("SELECT distance_m($1, $2, $3, $4)", a.lat, a.lng, b.lat, b.lng)

    assert sql == pytest.approx(distance_m(a, b), rel=1e-6)


async def test_reader_sees_one_row_per_demo_cafe(reader):
    rows = await reader.fetch("SELECT cafe_id, nearest_mrt, mrt_distance_m, youbike_within_300m FROM v_cafe_transit")

    assert len(rows) == 200
    assert all(r["nearest_mrt"] and r["mrt_distance_m"] >= 0 and r["youbike_within_300m"] >= 0 for r in rows)
