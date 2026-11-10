"""Clean the Find Coffee export for real mode (import-real-cafes D4-D7).

Pure functions only: the import script reads the files and writes the database.
"""

import math
import re
from collections.abc import Sequence
from dataclasses import dataclass

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


def distance_m(a: Place, b: Place) -> float:
    """Great-circle (haversine) distance in metres."""
    lat1, lat2 = math.radians(a.lat), math.radians(b.lat)
    dlat, dlng = lat2 - lat1, math.radians(b.lng - a.lng)
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlng / 2) ** 2
    return 2 * _EARTH_RADIUS_M * math.asin(math.sqrt(h))
