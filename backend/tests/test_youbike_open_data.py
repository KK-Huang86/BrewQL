"""Trimming the YouBike 2.0 station feeds into a repo snapshot (import-transit-open-data D1, D2).

Rows mirror the two official JSON feeds: Taipei sends numbers, New Taipei sends strings and
names its city. Station names and numbers are made up.
"""

from datetime import date
from decimal import Decimal

import pytest

from app.open_data import YoubikeRow, youbike_rows

AS_OF = date(2026, 11, 11)
DISTRICTS = {("台北市", "大安區"), ("台北市", "中正區"), ("新北市", "板橋區")}


def taipei(sno: str, sarea: str = "大安區", act: str = "1", quantity: int = 28) -> dict:
    return {
        "sno": sno,
        "sna": f"YouBike2.0_範例站{sno[-2:]}",
        "sarea": sarea,
        "ar": "範例路 1 號",
        "act": act,
        "Quantity": quantity,
        "available_rent_bikes": 17,
        "available_return_bikes": 11,
        "latitude": 25.02605,
        "longitude": 121.5436,
        "mday": "2026-11-11 00:15:04",
    }


def new_taipei(sno: str, sarea: str = "板橋區", act: str = "1", scity: str = "新北市") -> dict:
    return {
        "sno": sno,
        "sna": f"YouBike2.0_新北範例{sno[-2:]}",
        "scity": scity,
        "sarea": sarea,
        "ar": "範例路 2 號",
        "act": act,
        "tot_quantity": "20",
        "sbi_quantity": "9",
        "bemp": "11",
        "lat": "25.14678",
        "lng": "121.3999",
        "mday": "20261111T001403",
    }


def test_both_feeds_become_one_snapshot_sorted_by_station_number():
    rows = youbike_rows([taipei("500101002")], [new_taipei("500201001")], DISTRICTS, AS_OF)

    assert rows == [
        YoubikeRow("500101002", "範例站02", "台北市", "大安區", 28, Decimal("25.026050"), Decimal("121.543600"), AS_OF),
        YoubikeRow(
            "500201001", "新北範例01", "新北市", "板橋區", 20, Decimal("25.146780"), Decimal("121.399900"), AS_OF
        ),
    ]


def test_live_counts_are_not_kept():
    [row] = youbike_rows([taipei("500101001")], [], DISTRICTS, AS_OF)

    assert set(vars(row)) == {"station_no", "name", "city", "district", "docks", "lat", "lng", "as_of"}


def test_stations_out_of_service_are_dropped():
    rows = youbike_rows([taipei("500101001", act="0")], [new_taipei("500201001", act="0")], DISTRICTS, AS_OF)

    assert rows == []


def test_ntu_campus_area_counts_as_daan_district():
    [row] = youbike_rows([taipei("500119001", sarea="臺大公館校區")], [], DISTRICTS, AS_OF)

    assert (row.city, row.district) == ("台北市", "大安區")


def test_stations_outside_taipei_and_new_taipei_are_dropped():
    rows = youbike_rows(
        [], [new_taipei("500201001", scity="新北市"), new_taipei("500301001", scity="桃園市")], DISTRICTS, AS_OF
    )

    assert [r.station_no for r in rows] == ["500201001"]


def test_unknown_district_stops_the_trim():
    # A district missing from district_population would silently drop out of per-district joins.
    with pytest.raises(ValueError, match="台北市信義區"):
        youbike_rows([taipei("500101001", sarea="信義區")], [], DISTRICTS, AS_OF)


def test_duplicate_station_number_stops_the_trim():
    with pytest.raises(ValueError, match="500101001"):
        youbike_rows([taipei("500101001"), taipei("500101001")], [], DISTRICTS, AS_OF)


def test_missing_column_stops_the_trim():
    station = taipei("500101001")
    del station["Quantity"]

    with pytest.raises(KeyError, match="Quantity"):
        youbike_rows([station], [], DISTRICTS, AS_OF)


def test_empty_feeds_give_an_empty_snapshot():
    assert youbike_rows([], [], DISTRICTS, AS_OF) == []
