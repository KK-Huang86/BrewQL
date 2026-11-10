"""Trim official open-data downloads into the snapshots kept in the repo (import-open-data D1, D2).

Pure functions over csv.DictReader rows: keep only the columns the analysis needs, only the
cities in AREA, and the demo spelling of city names (台, not 臺), sorted so a rerun writes the
same file.
"""

import re
from collections.abc import Iterable
from dataclasses import dataclass
from decimal import Decimal

from app.real_cafes import AREA

Row = dict[str, str]

# 戶政司 site_id joins city and district, e.g. 新北市板橋區.
_SITE = re.compile(r"^(.{2}[市縣])(.+[區鄉鎮市])$")


def _demo_city(city: str) -> str:
    return city.replace("臺", "台")


@dataclass(frozen=True)
class PopulationRow:
    city: str
    district: str
    population: int
    area_km2: Decimal
    as_of: str  # ISO date: population counts are taken at the end of the year


def population_rows(rows: Iterable[Row]) -> list[PopulationRow]:
    out = []
    for row in rows:
        year = row["statistic_yyy"]
        if not year.isdigit():  # the official file repeats its header in Chinese on row 2
            continue
        match = _SITE.match(row["site_id"])
        if match is None:
            continue
        city = _demo_city(match.group(1))
        if city not in AREA:
            continue
        out.append(
            PopulationRow(
                city,
                match.group(2),
                int(row["people_total"]),
                Decimal(row["area"]),
                f"{int(year) + 1911}-12-31",  # ROC year to Gregorian
            )
        )
    return sorted(out, key=lambda r: (r.city, r.district))


@dataclass(frozen=True)
class UniversityRow:
    code: str
    name: str
    ownership: str  # 公立 or 私立
    level: str  # the official 體制, e.g. 一般大學, 技專校院
    city: str
    district: str


def university_rows(rows: Iterable[Row]) -> list[UniversityRow]:
    """Principal names, phone and fax numbers are dropped: the analysis only needs where schools are."""
    out = [
        UniversityRow(
            row["學校\n代碼"],
            row["學校名稱"],
            row["公私立"],
            row["體制"],
            _demo_city(row["縣市別"]),
            row["第三級\n行政區"],
        )
        for row in rows
    ]
    return sorted((r for r in out if r.city in AREA), key=lambda r: int(r.code))
