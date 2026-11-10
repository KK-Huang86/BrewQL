"""Cleaning the Find Coffee export for real mode (import-real-cafes). Every address here is made up."""

from dataclasses import asdict
from datetime import UTC, datetime
from decimal import Decimal

import pytest

from app.real_cafes import (
    CafeRow,
    Place,
    clean_cafe,
    clean_votes,
    locate,
    match_nomad,
    parse_address,
    prepare,
)


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


def cafe(source_id, name, north_m=0.0):
    return clean_cafe({**EXPORT_ROW, "id": str(source_id), "name": name, "lat": str(LAT + north_m / 111_000)})


def nomad(cafenomad_id, name, north_m=0.0, **override):
    row = {
        "id": "1", "cafenomad_id": cafenomad_id, "name": name, "city": "taipei", "address": "台北市測試路 1 號",
        "lat": str(LAT + north_m / 111_000), "lng": str(LNG), "socket": "yes", "limited_time": "NULL",
        "standing_desk": "no", "wifi": "4.5", "seat": "0", "quiet": "NULL", "tasty": "5.0", "cheap": "3.0",
        "music": "4.0", "url": "https://example.com", "mrt": "NULL", "open_time": "NULL",
        "synced_at": "2026-04-16 03:36:42.864021+00", "created_at": "2026-04-16 03:36:42.864021+00",
    }  # fmt: skip
    return {**row, **override}


def test_nomad_row_within_50_m_with_a_matching_name_joins_that_cafe():
    matched = match_nomad([cafe(1, "測試咖啡")], [nomad("n1", "測試咖啡", north_m=30, mrt="忠孝復興站")])

    [row] = matched.kept
    assert (row.cafe_source_id, row.cafenomad_id, row.mrt) == (1, "n1", "忠孝復興站")
    # 0 means nobody rated it, like NULL (D7).
    assert (row.wifi, row.seat, row.quiet, row.tasty) == (Decimal("4.5"), None, None, Decimal("5.0"))
    assert (row.socket, row.limited_time, row.standing_desk) == ("yes", None, "no")
    assert (matched.unmatched, matched.duplicates) == (0, 0)


@pytest.mark.parametrize(
    ("cafe_name", "nomad_name"),
    [
        ("Simple Kaffa 華山店", "ｓｉｍｐｌｅ　ｋａｆｆａ"),  # full width, spaces, case
        ("晨光咖啡", "晨光咖啡（信義店）"),  # branch in brackets
        ("晨光咖啡 信義店", "晨光咖啡"),  # one name contains the other
    ],
)
def test_names_match_after_normalising(cafe_name, nomad_name):
    assert len(match_nomad([cafe(1, cafe_name)], [nomad("n1", nomad_name)]).kept) == 1


@pytest.mark.parametrize(
    ("north_m", "nomad_name"),
    [(80, "測試咖啡"), (10, "隔壁茶館")],  # too far / a different shop next door
)
def test_nomad_row_that_is_too_far_or_differently_named_is_dropped(north_m, nomad_name):
    matched = match_nomad([cafe(1, "測試咖啡")], [nomad("n1", nomad_name, north_m=north_m)])

    assert matched.kept == []
    assert matched.unmatched == 1


def test_a_cafe_takes_only_its_nearest_nomad_row():
    matched = match_nomad(
        [cafe(1, "測試咖啡")], [nomad("far", "測試咖啡", north_m=40), nomad("near", "測試咖啡", north_m=5)]
    )

    assert [r.cafenomad_id for r in matched.kept] == ["near"]
    assert matched.duplicates == 1


@pytest.mark.parametrize(
    ("cafe_name", "nomad_name"),
    [
        ("NOTCH咖啡 內湖店", "NOTCH內湖店"),
        ("JokeR coffee", "joker咖啡"),
        ("小巷 Café", "小巷咖啡館"),
    ],
)
def test_generic_words_like_coffee_do_not_stop_a_match(cafe_name, nomad_name):
    assert len(match_nomad([cafe(1, cafe_name)], [nomad("n1", nomad_name)]).kept) == 1


@pytest.mark.parametrize(
    ("cafe_name", "nomad_name"),
    [
        ("好食紀", "好咖啡"),  # only 好 is left of 好咖啡: one character proves nothing
        ("Pinot Coffee", "IN Cafe"),  # two Latin letters, in is inside pinot
    ],
)
def test_a_name_left_too_short_after_removing_generic_words_never_matches(cafe_name, nomad_name):
    assert match_nomad([cafe(1, cafe_name)], [nomad("n1", nomad_name)]).kept == []


def test_prepare_joins_the_three_exports_into_one_batch_with_a_report():
    cafes = [
        {**EXPORT_ROW, "id": "1", "name": "晨光咖啡", "address": "台北市信義區信義路五段 7 號"},
        {**EXPORT_ROW, "id": "2", "name": "午後咖啡", "address": "信義路五段 9 號", "lat": str(LAT + 300 / 111_000)},
    ]
    votes = [vote("google", cafe_id="1"), vote("user", user_id="99", cafe_id="2")]

    batch = prepare(cafes, votes, [nomad("n1", "晨光咖啡"), nomad("n2", "沒有這家店", north_m=5_000)])

    assert [(c.source_id, loc) for c, loc in batch.cafes] == [(1, ("台北市", "信義區")), (2, ("台北市", "信義區"))]
    assert [v.cafe_source_id for v in batch.votes] == [1]
    assert [n.cafenomad_id for n in batch.nomad] == ["n1"]
    assert batch.report == {
        "cafes": 2, "parsed": 1, "filled": 1, "unknown": 0, "outside_area": 0,
        "votes": 1, "member_votes_dropped": 1,
        "nomad_matched": 1, "nomad_unmatched": 1, "nomad_duplicates": 0,
    }  # fmt: skip


def test_prepare_refuses_a_vote_for_a_cafe_not_in_the_export():
    with pytest.raises(ValueError, match="vote for unknown cafe 404"):
        prepare([EXPORT_ROW], [vote("google", cafe_id="404")], [])
