"""Cleaning the Find Coffee export for real mode (import-real-cafes). Every address here is made up."""

import pytest

from app.real_cafes import parse_address


@pytest.mark.parametrize(
    ("address", "expected"),
    [
        ("臺北市大安區復興南路一段 1 號", ("台北市", "大安區")),
        ("台北市中山區南京東路二段 2 號", ("台北市", "中山區")),
        ("106臺北市大安區忠孝東路四段 3 號", ("台北市", "大安區")),
        ("臺中市西屯區台灣大道三段 4 號", ("台中市", "西屯區")),
        ("新竹市東區光復路 5 號", ("新竹市", "東區")),
        ("宜蘭縣礁溪鄉中山路 6 號", ("宜蘭縣", "礁溪鄉")),
        ("新竹縣竹北市光明六路 7 號", ("新竹縣", "竹北市")),
    ],
)
def test_city_and_district_come_from_the_address_in_the_demo_spelling(address, expected):
    assert parse_address(address) == expected


@pytest.mark.parametrize(
    "address",
    [
        "大安區復興南路一段 1 號",  # no city: 2.2 fills it from nearby cafes
        "台北市中山北路二段 8 號",  # a road, not a district
        "No. 9, Section 1, Fuxing S Rd, Taipei",
        "",
    ],
)
def test_address_without_city_and_district_gives_none(address):
    assert parse_address(address) is None
