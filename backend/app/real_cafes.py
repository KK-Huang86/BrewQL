"""Clean the Find Coffee export for real mode (import-real-cafes D4-D7).

Pure functions only: the import script reads the files and writes the database.
"""

import re

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
