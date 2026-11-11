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


# import-transit-open-data D1, D4: snapshots downloaded on 2026-11-11.


async def test_reader_sees_youbike_stations_by_city(reader):
    rows = await reader.fetch("SELECT city, count(*) AS n FROM youbike_stations GROUP BY city ORDER BY city")

    assert [(r["city"], r["n"]) for r in rows] == [("台北市", 1803), ("新北市", 1595)]


async def test_reader_sees_mrt_stations_by_city(reader):
    rows = await reader.fetch("SELECT city, count(*) AS n FROM mrt_stations GROUP BY city ORDER BY city")

    assert [(r["city"], r["n"]) for r in rows] == [("台北市", 74), ("新北市", 45)]


async def test_transit_rows_keep_coordinates_and_download_day(reader):
    station = await reader.fetchrow(
        "SELECT district, exit_count, lat, lng, as_of FROM mrt_stations WHERE name = '台北車站'"
    )
    bike = await reader.fetchrow("SELECT docks, lat, lng, as_of FROM youbike_stations WHERE station_no = '500101001'")

    assert (station["district"], station["exit_count"]) == ("中正區", 8)
    assert (str(station["lat"]), str(station["lng"])) == ("25.046778", "121.517707")
    assert (bike["docks"], str(bike["lat"]), str(bike["lng"])) == (28, "25.026050", "121.543600")
    assert str(station["as_of"]) == str(bike["as_of"]) == "2026-11-11"


async def test_districts_without_an_mrt_station_count_zero_instead_of_vanishing(reader):
    # Spec scenario 各區交通站數, written the way glossary-transit teaches: start from
    # district_population and LEFT JOIN the per-district station count.
    rows = await reader.fetch(
        "WITH m AS (SELECT district, count(*) AS n FROM mrt_stations GROUP BY district) "
        "SELECT p.district, coalesce(m.n, 0) AS mrt_stations FROM district_population p LEFT JOIN m USING (district)"
    )

    assert len(rows) == 41
    assert sum(r["mrt_stations"] == 0 for r in rows) == 20  # all in 新北市, e.g. 林口區 (Airport MRT only)
    assert sum(r["mrt_stations"] for r in rows) == 119
