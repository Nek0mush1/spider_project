from pathlib import Path

from scripts.backfill_advanced_via_proxy import (
    DEFAULT_USER_CONCURRENCY,
    DEFAULT_USER_MAX_PROXY_ATTEMPTS,
    DEFAULT_USER_MIN_REVIEW_COUNT,
    DEFAULT_USER_TIMEOUT,
    make_response,
    parse_args,
    parse_stage_names,
    select_book_targets,
    should_record_user_skip,
    should_skip_user_fetch_error,
)
from douban_books.parsers import (
    build_derived_rating_distribution,
    parse_official_rating_distribution,
    parse_reading_state,
    parse_review_entries,
    parse_user_profile,
)


FIXTURES = Path(__file__).parent / "fixtures"


def _fixture_text(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def test_live_style_review_response_still_parses():
    response = make_response(
        "https://book.douban.com/subject/1007305/reviews",
        _fixture_text("reviews_page.html"),
        "https://book.douban.com/",
    )
    reviews, next_url = parse_review_entries(
        response,
        book_url="https://book.douban.com/subject/1007305/",
        limit=20,
    )
    assert len(reviews) == 2
    assert next_url.endswith("start=20")


def test_live_style_detail_response_parses_rating_and_state():
    response = make_response(
        "https://book.douban.com/subject/1007305/",
        _fixture_text("detail_advanced.html"),
        "https://book.douban.com/",
    )
    distribution = parse_official_rating_distribution(response)
    reading = parse_reading_state(response)
    assert distribution["star_5_pct"] == 50.0
    assert reading["want_to_read"] == 12345


def test_user_profile_fixture_parses():
    response = make_response(
        "https://www.douban.com/people/reviewer-a/",
        _fixture_text("user_profile.html"),
        "https://book.douban.com/",
    )
    profile = parse_user_profile(response)
    assert profile["reviewer_url"].endswith("/reviewer-a/")
    assert profile["followers_count"] == 128


def test_derived_distribution_uses_review_ratings():
    derived = build_derived_rating_distribution(
        [{"rating": 5}, {"rating": 4}, {"rating": 4}, {"rating": None}]
    )
    assert derived["sample_size"] == 3
    assert derived["star_4_count"] == 2


def test_parse_stage_names_defaults_to_all_stages():
    assert parse_stage_names("") == ("reviews", "ratings", "users")


def test_parse_stage_names_normalizes_and_filters_invalid_values():
    assert parse_stage_names(" ratings, reviews ,ignored ") == ("reviews", "ratings")


def test_select_book_targets_filters_by_requested_book_urls():
    targets = [
        ("https://book.douban.com/subject/1007305/", 20),
        ("https://book.douban.com/subject/1000005/", 18),
    ]

    filtered = select_book_targets(
        targets,
        requested_urls={"https://book.douban.com/subject/1007305/"},
    )

    assert filtered == [("https://book.douban.com/subject/1007305/", 20)]


def test_select_book_targets_keeps_original_order_when_unfiltered():
    targets = [
        ("https://book.douban.com/subject/1007305/", 20),
        ("https://book.douban.com/subject/1000005/", 18),
    ]

    assert select_book_targets(targets, requested_urls=None) == targets


def test_should_skip_user_fetch_error_on_404_profile():
    assert should_skip_user_fetch_error(
        RuntimeError(
            "unexpected status 404 for https://www.douban.com/people/1000638/: "
            "https://www.douban.com/people/1000638/"
        )
    )


def test_should_record_user_skip_for_404_profile():
    assert should_record_user_skip(
        RuntimeError(
            "unexpected status 404 for https://www.douban.com/people/1000638/: "
            "https://www.douban.com/people/1000638/"
        )
    ) == "http_404"


def test_parse_args_uses_faster_user_defaults(monkeypatch):
    monkeypatch.setattr("sys.argv", ["backfill_advanced_via_proxy.py"])

    args = parse_args()

    assert args.user_concurrency == DEFAULT_USER_CONCURRENCY
    assert args.user_timeout == DEFAULT_USER_TIMEOUT
    assert args.user_min_review_count == DEFAULT_USER_MIN_REVIEW_COUNT
    assert args.user_max_proxy_attempts == DEFAULT_USER_MAX_PROXY_ATTEMPTS


def test_parse_args_accepts_user_tuning(monkeypatch):
    monkeypatch.setattr(
        "sys.argv",
        [
            "backfill_advanced_via_proxy.py",
            "--user-concurrency", "4",
            "--user-timeout", "8",
            "--user-min-review-count", "3",
            "--user-max-proxy-attempts", "2",
        ],
    )

    args = parse_args()

    assert args.user_concurrency == 4
    assert args.user_timeout == 8
    assert args.user_min_review_count == 3
    assert args.user_max_proxy_attempts == 2
