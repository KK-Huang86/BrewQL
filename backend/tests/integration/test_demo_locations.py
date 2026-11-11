"""Generated demo cafe coordinates (cafe-transit-distance D3), on the demo test database."""

from dataclasses import dataclass

import asyncpg
import pytest

from app.real_cafes import distance_m


@dataclass(frozen=True)
class Point:
    lat: float
    lng: float


@pytest.fixture
async def reader(reader_dsn):
    conn = await asyncpg.connect(reader_dsn)
    yield conn
    await conn.close()


async def test_every_demo_cafe_has_coordinates(reader):
    row = await reader.fetchrow("SELECT count(*) AS cafes, count(lat) AS lat, count(lng) AS lng FROM cafes")

    assert (row["cafes"], row["lat"], row["lng"]) == (200, 200, 200)


async def test_each_cafe_sits_within_250_m_of_a_youbike_station_in_its_own_district(reader):
    cafes = await reader.fetch("SELECT place_id, city, district, lat, lng FROM cafes")
    bikes = await reader.fetch("SELECT city, district, lat, lng FROM youbike_stations")
    by_district: dict[tuple[str, str], list[Point]] = {}
    for b in bikes:
        by_district.setdefault((b["city"], b["district"]), []).append(Point(float(b["lat"]), float(b["lng"])))

    # 1 m of slack for rounding the coordinates to 6 decimals (about 0.1 m each).
    far = [
        c["place_id"]
        for c in cafes
        if min(distance_m(Point(float(c["lat"]), float(c["lng"])), b) for b in by_district[(c["city"], c["district"])])
        > 251
    ]
    assert far == []


async def test_cafes_are_spread_over_many_anchors(reader):
    # The anchor is picked per cafe, not one per district: 大安區 alone has 40 cafes.
    row = await reader.fetchrow(
        "SELECT count(DISTINCT (round(lat, 3), round(lng, 3))) AS spots FROM cafes WHERE district = '大安區'"
    )

    assert row["spots"] >= 30
