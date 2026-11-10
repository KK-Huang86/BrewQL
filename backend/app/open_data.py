"""Trim official open-data downloads into the snapshots kept in the repo (import-open-data D1, D2).

Pure functions over csv.DictReader rows: keep only the columns the analysis needs, only the
cities in AREA, and the demo spelling of city names (台, not 臺), sorted so a rerun writes the
same file.
"""

import re
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from app.real_cafes import AREA, demo_spelling

Row = dict[str, str]

# 戶政司 site_id joins city and district, e.g. 新北市板橋區.
_DISTRICT = re.compile(r"^.+[區鄉鎮市]$")


@dataclass(frozen=True)
class PopulationRow:
    city: str
    district: str
    population: int
    area_km2: Decimal
    as_of: date  # population counts are taken at the end of the year


def population_rows(rows: Iterable[Row]) -> list[PopulationRow]:
    out = []
    for row in rows:
        year = row["statistic_yyy"]
        if not year.isdigit():  # the official file repeats its header in Chinese on row 2
            continue
        site = demo_spelling(row["site_id"])
        city = next((c for c in AREA if site.startswith(c)), None)
        if city is None:  # other cities, and 東沙群島 / 南沙群島 that name no city
            continue
        district = site.removeprefix(city)
        if not _DISTRICT.match(district):
            raise ValueError(f"population row without a district: {row['site_id']!r}")
        out.append(
            PopulationRow(
                city,
                district,
                int(row["people_total"]),
                Decimal(row["area"]),
                date(int(year) + 1911, 12, 31),  # ROC year to Gregorian
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
            demo_spelling(row["縣市別"]),
            row["第三級\n行政區"],
        )
        for row in rows
    ]
    return sorted((r for r in out if r.city in AREA), key=lambda r: r.code)
