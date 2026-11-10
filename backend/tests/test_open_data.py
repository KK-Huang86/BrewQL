"""Trimming the official open-data downloads into repo snapshots (import-open-data D1, D2).

Rows mirror the official files' columns; the numbers are made up.
"""

from datetime import date
from decimal import Decimal

import pytest

from app.open_data import PopulationRow, UniversityRow, population_rows, university_rows

POPULATION_HEADER = {"statistic_yyy": "統計年", "site_id": "區域別", "people_total": "年底人口數", "area": "土地面積"}


def population(site_id: str, people: str = "100000", area: str = "10.5", year: str = "114") -> dict[str, str]:
    return {"statistic_yyy": year, "site_id": site_id, "people_total": people, "area": area}


def test_population_keeps_taipei_and_new_taipei_districts_in_the_demo_spelling():
    rows = [
        POPULATION_HEADER,
        population("新北市板橋區", "549762", "23.1373"),
        population("臺北市大安區", "290000", "11.3614"),
        population("臺中市西屯區"),
        population("宜蘭縣礁溪鄉"),
    ]

    assert population_rows(rows) == [
        PopulationRow("台北市", "大安區", 290000, Decimal("11.3614"), date(2025, 12, 31)),
        PopulationRow("新北市", "板橋區", 549762, Decimal("23.1373"), date(2025, 12, 31)),
    ]


def test_population_as_of_is_the_end_of_the_roc_year():
    [row] = population_rows([population("臺北市中正區", year="113")])

    assert row.as_of == date(2024, 12, 31)


def university(code: str, name: str, city: str, district: str, ownership: str = "私立") -> dict[str, str]:
    # The official header keeps line breaks inside some column names.
    return {
        "序號": "1",
        "學校\n代碼": code,
        "公私立": ownership,
        "體制": "一般大學",
        "學校名稱": name,
        "學校英文名稱": "Example University",
        "職稱": "校長",
        "姓名": "王小明",
        "縣市別": city,
        "第三級\n行政區": district,
        "郵遞\n區號": "106",
        "學校地址": f"{city}{district}範例路 1 號",
        "學校總機": "(02)1234-5678",
        "學校傳真": "(02)1234-5679",
        "網址": "https://example.edu.tw",
    }


def test_universities_keep_taipei_and_new_taipei_schools_without_personal_details():
    rows = [
        university("0002", "範例科技大學", "新北市", "板橋區"),
        university("0001", "範例大學", "臺北市", "大安區", ownership="公立"),
        university("0003", "台中範例大學", "臺中市", "西屯區"),
    ]

    assert university_rows(rows) == [
        UniversityRow("0001", "範例大學", "公立", "一般大學", "台北市", "大安區"),
        UniversityRow("0002", "範例科技大學", "私立", "一般大學", "新北市", "板橋區"),
    ]


def test_population_row_without_city_and_district_stops_the_trim():
    # A format change in the official file must fail loudly, not shrink the snapshot.
    with pytest.raises(ValueError, match="臺北市"):
        population_rows([population("臺北市")])


def test_population_rows_outside_the_area_need_not_name_a_district():
    # The official file lists 東沙群島 and 南沙群島 without a city; they are outside the area anyway.
    rows = [population("東沙群島"), population("臺北市中正區")]

    assert [r.district for r in population_rows(rows)] == ["中正區"]
