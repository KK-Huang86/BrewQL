"""Turning Taipei Metro exit coordinates into one row per station (import-transit-open-data D3).

Rows mirror the official CSV's columns. Exit names follow the official patterns; coordinates
are made up and placed so distances are easy to reason about (0.001 degree of latitude is about
111 m).
"""

from datetime import date
from decimal import Decimal

import pytest

from app.open_data import MRT_DISTRICT_FIXES, MrtRow, YoubikeRow, mrt_rows

AS_OF = date(2026, 11, 11)


def exit_(name: str, number: str, lat: str, lng: str = "121.500000") -> dict[str, str]:
    return {"項次": "1", "出入口名稱": name, "出入口編號": number, "經度": lng, "緯度": lat, "是否為無障礙用": "否"}


def bike(station_no: str, city: str, district: str, lat: str, lng: str = "121.500000") -> YoubikeRow:
    return YoubikeRow(station_no, "範例站", city, district, 20, Decimal(lat), Decimal(lng), AS_OF)


BIKES = [
    bike("1", "台北市", "中正區", "25.046000"),
    bike("2", "台北市", "大同區", "25.050000"),
    bike("3", "新北市", "板橋區", "25.013000"),
]


def test_exits_of_one_station_become_one_row_at_their_average_position():
    exits = [exit_("板橋站出口1", "1", "25.012000"), exit_("板橋站出口2", "2", "25.014000")]

    assert mrt_rows(exits, BIKES, AS_OF, fixes={}) == [
        MrtRow("板橋", "新北市", "板橋區", 2, Decimal("25.013000"), Decimal("121.500000"), AS_OF)
    ]


def test_an_unnumbered_exit_counts_as_an_exit():
    # Some stations list an accessible exit as 「X站出口」 with number 0.
    exits = [exit_("板橋站出口1", "1", "25.013000"), exit_("板橋站出口", "0", "25.013000")]

    [row] = mrt_rows(exits, BIKES, AS_OF, fixes={})

    assert (row.name, row.exit_count) == ("板橋", 2)


def test_taipei_main_station_keeps_its_official_name():
    # Its exits are 台北車站M1..M8: dropping 站 would leave 台北車.
    exits = [exit_("台北車站M1", "M1", "25.046000"), exit_("台北車站M8", "M8", "25.046000")]

    [row] = mrt_rows(exits, BIKES, AS_OF, fixes={})

    assert (row.name, row.exit_count) == ("台北車站", 2)


def test_district_comes_from_the_nearest_youbike_station():
    # 25.0485 is 278 m from the 中正區 bike and 167 m from the 大同區 bike.
    [row] = mrt_rows([exit_("北門站出口1", "1", "25.048500")], BIKES, AS_OF, fixes={})

    assert (row.city, row.district) == ("台北市", "大同區")


def test_a_fix_overrides_the_nearest_youbike_district():
    fixes = {"北門": ("台北市", "中正區")}

    [row] = mrt_rows([exit_("北門站出口1", "1", "25.048500")], BIKES, AS_OF, fixes=fixes)

    assert (row.city, row.district) == ("台北市", "中正區")


def test_a_fix_for_a_station_not_in_the_file_stops_the_build():
    # A renamed station must not leave a stale fix that silently does nothing.
    with pytest.raises(ValueError, match="不存在站"):
        mrt_rows([exit_("北門站出口1", "1", "25.048500")], BIKES, AS_OF, fixes={"不存在站": ("台北市", "中正區")})


def test_stations_are_sorted_by_name():
    exits = [exit_("北門站出口1", "1", "25.048500"), exit_("板橋站出口1", "1", "25.013000")]

    assert [r.name for r in mrt_rows(exits, BIKES, AS_OF, fixes={})] == sorted(["北門", "板橋"])


def test_an_exit_name_in_an_unknown_format_stops_the_build():
    with pytest.raises(ValueError, match="板橋東門"):
        mrt_rows([exit_("板橋東門", "1", "25.013000")], BIKES, AS_OF, fixes={})


def test_a_station_far_from_every_youbike_station_stops_the_build():
    # About 1.4 km from the nearest bike: no district to borrow, so fail instead of guessing.
    with pytest.raises(ValueError, match="遠方"):
        mrt_rows([exit_("遠方站出口1", "1", "25.063000")], BIKES, AS_OF, fixes={})


def test_no_youbike_stations_stops_the_build():
    with pytest.raises(ValueError, match="YouBike"):
        mrt_rows([exit_("板橋站出口1", "1", "25.013000")], [], AS_OF, fixes={})


def test_unparseable_coordinates_stop_the_build():
    with pytest.raises(ValueError):
        mrt_rows([exit_("板橋站出口1", "1", "not-a-number")], BIKES, AS_OF, fixes={})


def test_no_exits_give_no_stations():
    assert mrt_rows([], BIKES, AS_OF, fixes={}) == []


def test_an_exit_number_with_a_letter_counts_as_an_exit():
    # The official file has 「南港展覽館站出口2A」 next to 「南港展覽館站出口2」.
    exits = [exit_("板橋站出口2", "2", "25.013000"), exit_("板橋站出口2A", "2A", "25.013000")]

    [row] = mrt_rows(exits, BIKES, AS_OF, fixes={})

    assert (row.name, row.exit_count) == ("板橋", 2)


def test_fixes_list_the_stations_whose_nearest_youbike_lies_across_a_district_border():
    # Checked on 2026-11-11 against every station address on the Taipei Metro website
    # (import-transit-open-data task 1.3): these 7 of 119 stations borrow the wrong district.
    assert MRT_DISTRICT_FIXES == {
        "公館": ("台北市", "中正區"),
        "南京復興": ("台北市", "松山區"),
        "台電大樓": ("台北市", "中正區"),
        "國父紀念館": ("台北市", "信義區"),
        "後山埤": ("台北市", "南港區"),
        "忠孝新生": ("台北市", "大安區"),
        "雙連": ("台北市", "大同區"),
    }


def test_a_fix_to_an_unknown_district_stops_the_build():
    # A typo in a fix must fail here, not after the snapshot is written. Known districts are those
    # of the YouBike stations, which youbike_rows already checked against district_population.
    with pytest.raises(ValueError, match="台北市中政區"):
        mrt_rows([exit_("北門站出口1", "1", "25.048500")], BIKES, AS_OF, fixes={"北門": ("台北市", "中政區")})
