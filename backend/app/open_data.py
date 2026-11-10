"""Trim official open-data downloads into the snapshots kept in the repo (import-open-data D1, D2).

Pure functions over csv.DictReader rows: keep only the columns the analysis needs, only the
cities in AREA, and the demo spelling of city names (台, not 臺), sorted so a rerun writes the
same file.
"""

import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation

from app.real_cafes import AREA, demo_spelling, distance_m

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


@dataclass(frozen=True)
class YoubikeRow:
    station_no: str
    name: str
    city: str
    district: str
    docks: int
    lat: Decimal
    lng: Decimal
    as_of: date  # the download day: the feeds are live and carry no version


# 臺大公館校區 is a campus, not a district; the campus lies in 大安區 (import-transit-open-data D2).
_YOUBIKE_AREAS = {"臺大公館校區": "大安區"}
_YOUBIKE_PREFIX = "YouBike2.0_"
_COORD = Decimal("0.000001")


def _coord(value: float | str) -> Decimal:
    # str() first: Taipei sends floats, and Decimal(float) would keep binary noise.
    try:
        return Decimal(str(value)).quantize(_COORD)
    except InvalidOperation:
        raise ValueError(f"not a coordinate: {value!r}") from None


def youbike_rows(
    taipei: Iterable[dict], new_taipei: Iterable[dict], districts: set[tuple[str, str]], as_of: date
) -> list[YoubikeRow]:
    """Stations in service, without live bike counts. districts are the (city, district) pairs of
    district_population: a station anywhere else stops the trim instead of joining nothing."""
    feeds = [("台北市", row, row["Quantity"], row["latitude"], row["longitude"]) for row in taipei] + [
        (demo_spelling(row["scity"]), row, row["tot_quantity"], row["lat"], row["lng"]) for row in new_taipei
    ]
    out: dict[str, YoubikeRow] = {}
    for city, row, docks, lat, lng in feeds:
        if city not in AREA or row["act"] != "1":
            continue
        district = _YOUBIKE_AREAS.get(row["sarea"], row["sarea"])
        if (city, district) not in districts:
            raise ValueError(f"YouBike station {row['sno']} in an unknown district: {city}{district}")
        if row["sno"] in out:
            raise ValueError(f"duplicate YouBike station number: {row['sno']}")
        out[row["sno"]] = YoubikeRow(
            row["sno"],
            row["sna"].removeprefix(_YOUBIKE_PREFIX),
            city,
            district,
            int(docks),
            _coord(lat),
            _coord(lng),
            as_of,
        )
    return sorted(out.values(), key=lambda r: r.station_no)


@dataclass(frozen=True)
class MrtRow:
    name: str
    city: str
    district: str
    exit_count: int
    lat: Decimal  # average of the station's exits
    lng: Decimal
    as_of: date  # the download day: the exit file carries no version


# Exits are 「板橋站出口1」, 「南港展覽館站出口2A」, 「板橋站出口」 (an unnumbered accessible exit) or
# 「台北車站M1」, whose station is officially called 台北車站 (import-transit-open-data D3).
_MRT_EXIT = re.compile(r"^(?:(?P<main>台北車站)M\d+|(?P<station>.+?)站出口(?:\d+[A-Z]?)?)$")
# Farther than this from every YouBike station, the nearest one says nothing about the district.
_MRT_MAX_BIKE_M = 1000

# Stations whose nearest YouBike station lies across a district border: every station was
# checked against its address on the Taipei Metro website on 2026-11-11 (task 1.3).
MRT_DISTRICT_FIXES: dict[str, tuple[str, str]] = {
    "公館": ("台北市", "中正區"),
    "南京復興": ("台北市", "松山區"),
    "台電大樓": ("台北市", "中正區"),
    "國父紀念館": ("台北市", "信義區"),
    "後山埤": ("台北市", "南港區"),
    "忠孝新生": ("台北市", "大安區"),
    "雙連": ("台北市", "大同區"),
}


@dataclass(frozen=True)
class _Point:
    lat: Decimal
    lng: Decimal


def mrt_rows(
    exits: Iterable[Row],
    youbike: list[YoubikeRow],
    as_of: date,
    fixes: Mapping[str, tuple[str, str]] = MRT_DISTRICT_FIXES,
) -> list[MrtRow]:
    """One row per station. The exit file has no district, so a station borrows the district of
    its nearest YouBike station, unless fixes names it; no boundary map needed."""
    stations: dict[str, list[_Point]] = {}
    for row in exits:
        match = _MRT_EXIT.match(row["出入口名稱"])
        if match is None:
            raise ValueError(f"MRT exit name in an unknown format: {row['出入口名稱']!r}")
        name = match["main"] or match["station"]
        stations.setdefault(name, []).append(_Point(_coord(row["緯度"]), _coord(row["經度"])))
    if stations and not youbike:
        raise ValueError("no YouBike stations to take MRT districts from")
    if stale := set(fixes) - set(stations):
        raise ValueError(f"MRT district fixes for stations not in the file: {sorted(stale)}")
    out = []
    for name, points in stations.items():
        where = _Point(_mean([p.lat for p in points]), _mean([p.lng for p in points]))
        if name in fixes:
            city, district = fixes[name]
        else:
            nearest = min(youbike, key=lambda bike: distance_m(where, bike))
            if distance_m(where, nearest) > _MRT_MAX_BIKE_M:
                raise ValueError(f"MRT station {name} has no YouBike station within {_MRT_MAX_BIKE_M} m")
            city, district = nearest.city, nearest.district
        out.append(MrtRow(name, city, district, len(points), where.lat, where.lng, as_of))
    return sorted(out, key=lambda r: r.name)


def _mean(values: list[Decimal]) -> Decimal:
    return (sum(values) / len(values)).quantize(_COORD)
