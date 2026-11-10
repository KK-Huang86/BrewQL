"""Open-data snapshots loaded at init and readable by the API role (import-open-data D3, D4)."""

import asyncpg
import pytest


@pytest.fixture
async def reader(reader_dsn):
    conn = await asyncpg.connect(reader_dsn)
    yield conn
    await conn.close()


async def test_reader_sees_every_taipei_and_new_taipei_district(reader):
    rows = await reader.fetch("SELECT city, count(*) AS n FROM district_population GROUP BY city ORDER BY city")

    assert [(r["city"], r["n"]) for r in rows] == [("台北市", 12), ("新北市", 29)]


async def test_reader_sees_universities_by_city(reader):
    rows = await reader.fetch("SELECT city, count(*) AS n FROM universities GROUP BY city ORDER BY city")

    assert [(r["city"], r["n"]) for r in rows] == [("台北市", 26), ("新北市", 23)]


async def test_population_rows_keep_their_date_and_area(reader):
    row = await reader.fetchrow(
        "SELECT population, area_km2, as_of FROM district_population WHERE city = '台北市' AND district = '中正區'"
    )

    assert row["population"] > 0
    assert row["area_km2"] > 0
    assert str(row["as_of"]) == "2025-12-31"
