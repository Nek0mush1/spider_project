from pathlib import Path

from scrapy.http import HtmlResponse

from douban_books.parsers import (
    build_derived_rating_distribution,
    parse_official_rating_distribution,
    parse_reading_state,
    parse_review_entries,
    parse_user_profile,
)


FIXTURES = Path(__file__).parent / "fixtures"


def _html_response(fixture_name: str, url: str) -> HtmlResponse:
    body = (FIXTURES / fixture_name).read_bytes()
    return HtmlResponse(url=url, body=body, encoding="utf-8")


def test_parse_review_entries_extracts_core_fields():
    response = _html_response(
        "reviews_page.html",
        "https://book.douban.com/subject/1007305/reviews",
    )

    reviews, next_url = parse_review_entries(
        response,
        book_url="https://book.douban.com/subject/1007305/",
        limit=20,
    )

    assert len(reviews) == 2
    assert next_url == "https://book.douban.com/subject/1007305/reviews?start=20"

    first = reviews[0]
    assert first["book_url"] == "https://book.douban.com/subject/1007305/"
    assert first["review_url"] == "https://book.douban.com/review/111/"
    assert first["title"] == "魔幻与现实的边界"
    assert first["content"] == "布恩迪亚家族的宿命循环令人震撼。"
    assert first["rating"] == 5
    assert first["useful_count"] == 120
    assert first["useless_count"] == 30
    assert first["useful_ratio"] == 0.8
    assert first["replies_count"] == 6
    assert first["reviewer_name"] == "读者甲"
    assert first["reviewer_url"] == "https://www.douban.com/people/reviewer-a/"
    assert first["published_at"] == "2024-01-02 03:04:05"


def test_parse_official_rating_distribution_and_reading_state():
    response = _html_response(
        "detail_advanced.html",
        "https://book.douban.com/subject/1007305/",
    )

    distribution = parse_official_rating_distribution(response)
    reading_state = parse_reading_state(response)

    assert distribution == {
        "star_5_pct": 50.0,
        "star_4_pct": 30.0,
        "star_3_pct": 15.0,
        "star_2_pct": 3.0,
        "star_1_pct": 2.0,
    }
    assert reading_state == {
        "want_to_read": 12345,
        "reading": 678,
        "read": 9012,
    }


def test_build_derived_rating_distribution_from_reviews():
    reviews = [
        {"rating": 5},
        {"rating": 5},
        {"rating": 4},
        {"rating": 3},
        {"rating": None},
    ]

    derived = build_derived_rating_distribution(reviews)

    assert derived["sample_size"] == 4
    assert derived["star_5_count"] == 2
    assert derived["star_4_count"] == 1
    assert derived["star_3_count"] == 1
    assert derived["star_2_count"] == 0
    assert derived["star_1_count"] == 0
    assert derived["star_5_pct"] == 50.0
    assert derived["star_4_pct"] == 25.0


def test_parse_user_profile_counts():
    response = _html_response(
        "user_profile.html",
        "https://www.douban.com/people/reviewer-a/",
    )

    profile = parse_user_profile(response)

    assert profile["reviewer_url"] == "https://www.douban.com/people/reviewer-a/"
    assert profile["display_name"] == "读者甲"
    assert profile["following_count"] == 42
    assert profile["followers_count"] == 128
