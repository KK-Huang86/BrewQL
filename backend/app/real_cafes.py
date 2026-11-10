"""Clean the Find Coffee export for real mode (import-real-cafes D4-D7).

Pure functions only: the import script reads the files and writes the database.
"""

import math
import re
import unicodedata
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Protocol

# Every city and county in Taiwan, in the demo spelling ("台", D5).
_CITIES = (
    "台北市", "新北市", "桃園市", "台中市", "台南市", "高雄市", "基隆市", "新竹市", "嘉義市",
    "新竹縣", "苗栗縣", "彰化縣", "南投縣", "雲林縣", "嘉義縣", "屏東縣", "宜蘭縣", "花蓮縣",
    "台東縣", "澎湖縣", "金門縣", "連江縣",
)  # fmt: skip
_CITY = "|".join(c.replace("台", "[台臺]") for c in _CITIES)
# The district follows the city directly: 1-4 characters, then 區/鄉/鎮/市. A road such as
# 中山北路 never ends that way within five characters, so it is not taken for a district.
_ADDRESS = re.compile(rf"({_CITY})\s*([^\s\d]{{1,4}}?[區鄉鎮市])")


def parse_address(address: str) -> tuple[str, str] | None:
    """(city, district) from a Taiwanese address, or None when the address does not say both."""
    match = _ADDRESS.search(address)
    if match is None:
        return None
    return match.group(1).replace("臺", "台"), match.group(2)


Location = tuple[str, str]  # (city, district)

# A cafe this close to one whose address names a district is taken to be in that district (D5).
FILL_RADIUS_M = 1_000.0
_EARTH_RADIUS_M = 6_371_000.0


@dataclass(frozen=True)
class Place:
    address: str
    lat: float
    lng: float


@dataclass(frozen=True)
class Located:
    locations: list[Location | None]  # one per place, in input order
    parsed: int
    filled: int
    unknown: int


def locate(places: Sequence[Place]) -> Located:
    """Each place's (city, district): from its address, else from the nearest parsed place within 1 km."""
    parsed = [parse_address(p.address) for p in places]
    anchors = [(p, loc) for p, loc in zip(places, parsed, strict=True) if loc is not None]
    locations: list[Location | None] = []
    filled = 0
    for place, loc in zip(places, parsed, strict=True):
        if loc is None:
            # Only parsed places are anchors, so a fill never feeds another fill.
            loc = _nearest(place, anchors)
            filled += loc is not None
        locations.append(loc)
    return Located(locations=locations, parsed=len(anchors), filled=filled, unknown=locations.count(None))


def _nearest(place: Place, anchors: list[tuple[Place, Location]]) -> Location | None:
    best: tuple[float, Location] | None = None
    for anchor, loc in anchors:
        d = distance_m(place, anchor)
        if d <= FILL_RADIUS_M and (best is None or d < best[0]):
            best = (d, loc)
    return best[1] if best else None


class HasCoordinates(Protocol):
    @property
    def lat(self) -> float: ...

    @property
    def lng(self) -> float: ...


def distance_m(a: HasCoordinates, b: HasCoordinates) -> float:
    """Great-circle (haversine) distance in metres."""
    lat1, lat2 = math.radians(a.lat), math.radians(b.lat)
    dlat, dlng = lat2 - lat1, math.radians(b.lng - a.lng)
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlng / 2) ** 2
    return 2 * _EARTH_RADIUS_M * math.asin(math.sqrt(h))


# --- export rows ---------------------------------------------------------------------------------

Row = Mapping[str, str]  # one CSV row; pgAdmin writes NULL as the string "NULL"


@dataclass(frozen=True)
class CafeRow:
    """The whitelisted columns of one cafe (D4); anything else in the export is ignored."""

    source_id: int  # Find Coffee's id, only to link votes; the database assigns its own
    place_id: str
    name: str
    address: str
    lat: float  # matching and location fill only; not stored (D4)
    lng: float
    rating: Decimal | None
    user_ratings_total: int
    has_socket: str | None
    limited_time: str | None
    pet_friendly: bool | None
    has_pet: bool | None
    created_at: datetime


@dataclass(frozen=True)
class VoteRow:
    cafe_source_id: int
    attribute: str
    value: str
    source: str
    created_at: datetime


@dataclass(frozen=True)
class CleanVotes:
    kept: list[VoteRow]
    dropped_member_votes: int


# Votes from these sources are imported; "user" votes are real member behaviour (D6).
VOTE_SOURCES = ("google", "cafenomad")


def clean_cafe(row: Row) -> CafeRow:
    rating = _value(row, "rating")
    return CafeRow(
        source_id=int(row["id"]),
        place_id=row["place_id"],
        name=row["name"],
        address=row["address"],
        lat=float(row["lat"]),
        lng=float(row["lng"]),
        rating=Decimal(rating) if rating is not None else None,
        user_ratings_total=int(row["user_ratings_total"]),
        has_socket=_value(row, "has_socket"),
        limited_time=_value(row, "limited_time"),
        pet_friendly=_yes_no(row, "pet_friendly"),
        has_pet=_yes_no(row, "has_pet"),
        created_at=datetime.fromisoformat(row["created_at"]),
    )


def clean_votes(rows: Iterable[Row]) -> CleanVotes:
    kept: list[VoteRow] = []
    dropped = 0
    for row in rows:
        if row["source"] not in VOTE_SOURCES:
            # The whole vote goes, not just user_id: when a member voted is behaviour too.
            dropped += 1
            continue
        kept.append(
            VoteRow(
                cafe_source_id=int(row["cafe_id"]),
                attribute=row["attribute"],
                value=row["value"],
                source=row["source"],
                created_at=datetime.fromisoformat(row["created_at"]),
            )
        )
    return CleanVotes(kept=kept, dropped_member_votes=dropped)


def _value(row: Row, column: str) -> str | None:
    value = row[column]
    return None if value in ("", "NULL") else value


def _yes_no(row: Row, column: str) -> bool | None:
    # Unknown stays unknown: turning it into False would say "no pets" without knowing (D8).
    value = _value(row, column)
    if value is None:
        return None
    if value not in ("yes", "no"):
        raise ValueError(f"{column}: expected yes, no or NULL, got {value!r}")
    return value == "yes"


# --- Cafe Nomad ----------------------------------------------------------------------------------

# A Cafe Nomad row is the same shop when it is this close and the names agree (D7).
MATCH_RADIUS_M = 50.0
_RATINGS = ("wifi", "seat", "quiet", "tasty", "cheap", "music")
_BRACKETS = re.compile(r"[(（][^)）]*[)）]")
_NOT_WORD = re.compile(r"[\W_]+")


@dataclass(frozen=True)
class NomadRow:
    cafe_source_id: int
    cafenomad_id: str
    name: str
    wifi: Decimal | None
    seat: Decimal | None
    quiet: Decimal | None
    tasty: Decimal | None
    cheap: Decimal | None
    music: Decimal | None
    socket: str | None
    limited_time: str | None
    standing_desk: str | None
    mrt: str | None
    synced_at: datetime


@dataclass(frozen=True)
class NomadMatch:
    kept: list[NomadRow]
    unmatched: int  # no cafe close enough with an agreeing name
    duplicates: int  # matched a cafe that a nearer row already took


def match_nomad(cafes: Sequence[CafeRow], rows: Iterable[Row]) -> NomadMatch:
    """Join Cafe Nomad rows to cafes: within 50 m, names agree, one row per cafe (the nearest)."""
    names = [_normalise(c.name) for c in cafes]
    best: dict[int, tuple[float, NomadRow]] = {}  # cafe source id -> nearest matching row
    unmatched = duplicates = 0
    for row in rows:
        here = Place(address="", lat=float(row["lat"]), lng=float(row["lng"]))
        name = _normalise(row["name"])
        found = min(
            (
                (d, cafe)
                for cafe, cafe_name in zip(cafes, names, strict=True)
                if (d := distance_m(here, cafe)) <= MATCH_RADIUS_M and _names_agree(name, cafe_name)
            ),
            key=lambda pair: pair[0],
            default=None,
        )
        if found is None:
            unmatched += 1
            continue
        d, cafe = found
        current = best.get(cafe.source_id)
        if current is not None:
            duplicates += 1
            if current[0] <= d:
                continue
        best[cafe.source_id] = (d, _nomad_row(cafe.source_id, row))
    return NomadMatch(kept=[row for _, row in best.values()], unmatched=unmatched, duplicates=duplicates)


def _normalise(name: str) -> str:
    # Full width to half width, branch names in brackets out, then only letters and digits, lower case.
    name = _BRACKETS.sub("", unicodedata.normalize("NFKC", name))
    return _NOT_WORD.sub("", name).lower()


def _names_agree(a: str, b: str) -> bool:
    return bool(a) and bool(b) and (a in b or b in a)


def _nomad_row(cafe_source_id: int, row: Row) -> NomadRow:
    ratings = {column: _rating(row, column) for column in _RATINGS}
    return NomadRow(
        cafe_source_id=cafe_source_id,
        cafenomad_id=row["cafenomad_id"],
        name=row["name"],
        **ratings,
        socket=_value(row, "socket"),
        limited_time=_value(row, "limited_time"),
        standing_desk=_value(row, "standing_desk"),
        mrt=_value(row, "mrt"),
        synced_at=datetime.fromisoformat(row["synced_at"]),
    )


def _rating(row: Row, column: str) -> Decimal | None:
    # 0 means nobody rated it yet, the same as NULL (D7).
    value = _value(row, column)
    return None if value is None or Decimal(value) == 0 else Decimal(value)
