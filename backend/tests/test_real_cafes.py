"""Cleaning the Find Coffee export for real mode (import-real-cafes). Every address here is made up."""

from dataclasses import asdict
from datetime import UTC, datetime
from decimal import Decimal

import pytest

from app.real_cafes import CafeRow, Place, clean_cafe, clean_votes, locate, parse_address


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


# A made-up row shaped like the pgAdmin export: every column, NULL written as the string "NULL".
EXPORT_ROW = {
    "id": "42", "place_id": "ChIJ-made-up", "name": "測試咖啡", "address": "台北市大安區測試路 1 號",
    "phone": "02 1234 5678", "lat": "25.0330", "lng": "121.5654", "rating": "4.6",
    "user_ratings_total": "321", "opening_hours": "{}", "website": "https://example.com",
    "google_maps": "https://maps.example.com", "favorite_count": "7", "last_refreshed": "NULL",
    "created_at": "2026-04-06 17:34:53.840986+00", "updated_at": "NULL",
    "attributes_last_calculated_at": "NULL", "has_socket": "yes", "limited_time": "NULL",
    "photo_reference": "ref", "photo_s3_url": "https://s3.example.com/p.jpg", "view_count": "0",
    "photo_updated_at": "NULL", "has_pet": "no", "pet_friendly": "NULL", "reviews": "[]",
    "ai_summary": "摘要", "brand_new_column": "anything",
}  # fmt: skip


def test_cafe_keeps_only_the_whitelisted_public_columns():
    cafe = clean_cafe(EXPORT_ROW)

    assert cafe == CafeRow(
        source_id=42,
        place_id="ChIJ-made-up",
        name="測試咖啡",
        address="台北市大安區測試路 1 號",
        lat=25.0330,
        lng=121.5654,
        rating=Decimal("4.6"),
        user_ratings_total=321,
        has_socket="yes",
        limited_time=None,
        pet_friendly=None,
        has_pet=False,
        created_at=datetime(2026, 4, 6, 17, 34, 53, 840986, tzinfo=UTC),
    )
    # Member aggregates, Google content and unknown new columns never come through (D4).
    for dropped in ("favorite_count", "view_count", "reviews", "ai_summary", "phone", "brand_new_column"):
        assert dropped not in asdict(cafe)


def test_pet_columns_map_yes_and_no_to_booleans_and_keep_unknown_as_none():
    assert clean_cafe({**EXPORT_ROW, "pet_friendly": "yes", "has_pet": "NULL"}).pet_friendly is True
    assert clean_cafe({**EXPORT_ROW, "pet_friendly": "yes", "has_pet": "NULL"}).has_pet is None


def vote(source, user_id="NULL", cafe_id="42"):
    return {
        "id": "1", "attribute": "socket", "value": "yes", "source": source,
        "created_at": "2026-04-07 16:42:20.149889+00", "cafe_id": cafe_id, "user_id": user_id,
    }  # fmt: skip


def test_votes_from_members_are_dropped_whole_and_no_user_id_survives():
    votes = clean_votes([vote("google"), vote("cafenomad"), vote("user", user_id="99")])

    assert [v.source for v in votes.kept] == ["google", "cafenomad"]
    assert votes.dropped_member_votes == 1
    assert all("user_id" not in asdict(v) for v in votes.kept)
    assert votes.kept[0].cafe_source_id == 42
