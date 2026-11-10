"""Trimming the official open-data downloads into repo snapshots (import-open-data D1, D2).

Rows mirror the official files' columns; the numbers are made up.
"""

from decimal import Decimal

from app.open_data import PopulationRow, population_rows

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
        PopulationRow("台北市", "大安區", 290000, Decimal("11.3614"), "2025-12-31"),
        PopulationRow("新北市", "板橋區", 549762, Decimal("23.1373"), "2025-12-31"),
    ]


def test_population_as_of_is_the_end_of_the_roc_year():
    [row] = population_rows([population("臺北市中正區", year="113")])

    assert row.as_of == "2024-12-31"
