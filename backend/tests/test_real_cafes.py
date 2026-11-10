"""Cleaning the Find Coffee export for real mode (import-real-cafes). Every address here is made up."""

import pytest

from app.real_cafes import Place, locate, parse_address


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


# Near Taipei 101: 0.001 degree of latitude is about 111 m.
LAT, LNG = 25.0330, 121.5654


def place(address, north_m=0.0):
    return Place(address=address, lat=LAT + north_m / 111_000, lng=LNG)


def test_unparsed_address_takes_the_nearest_parsed_cafe_within_one_kilometre():
    located = locate(
        [
            place("台北市信義區信義路五段 7 號"),
            place("台北市大安區基隆路 1 號", north_m=900),
            place("信義路五段 9 號", north_m=300),  # 300 m from 信義區, 600 m from 大安區
        ]
    )

    assert located.locations == [("台北市", "信義區"), ("台北市", "大安區"), ("台北市", "信義區")]
    assert (located.parsed, located.filled, located.unknown) == (2, 1, 0)


def test_unparsed_address_with_no_parsed_cafe_within_one_kilometre_stays_unknown():
    located = locate([place("台北市信義區信義路五段 7 號"), place("某條路 1 號", north_m=1_200)])

    assert located.locations == [("台北市", "信義區"), None]
    assert (located.parsed, located.filled, located.unknown) == (1, 0, 1)


def test_a_filled_location_is_not_passed_on_to_another_cafe():
    # Only addresses vouch for a district; chaining fills could walk across a district border.
    located = locate(
        [
            place("台北市信義區信義路五段 7 號"),
            place("某條路 1 號", north_m=800),
            place("某條路 2 號", north_m=1_600),  # 800 m from the filled cafe, 1.6 km from the parsed one
        ]
    )

    assert located.locations == [("台北市", "信義區"), ("台北市", "信義區"), None]
