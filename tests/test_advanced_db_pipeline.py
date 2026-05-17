import os

import pandas as pd
import pytest
from sqlalchemy import text

from douban_books.db import (
    get_engine,
    init_db,
    reset_engine,
    upsert_rating_distributions,
    upsert_reviews,
    upsert_user_profiles,
)


@pytest.fixture(autouse=True)
def _integration_db():
    test_url = os.environ.get("TEST_DATABASE_URL")
    if not test_url:
        pytest.skip("TEST_DATABASE_URL not set")
    assert test_url.endswith("_test")

    reset_engine()
    old_url = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = test_url

    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(text("DROP TABLE IF EXISTS rating_distributions CASCADE"))
        conn.execute(text("DROP TABLE IF EXISTS reviews CASCADE"))
        conn.execute(text("DROP TABLE IF EXISTS user_profiles CASCADE"))
        conn.execute(text("DROP TABLE IF EXISTS douban_books CASCADE"))
    init_db()

    yield

    reset_engine()
    if old_url is not None:
        os.environ["DATABASE_URL"] = old_url
    else:
        os.environ.pop("DATABASE_URL", None)


@pytest.mark.integration
def test_init_db_creates_advanced_tables():
    engine = get_engine()
    with engine.connect() as conn:
        review_exists = conn.execute(
            text("SELECT to_regclass('public.reviews')")
        ).scalar()
        rating_exists = conn.execute(
            text("SELECT to_regclass('public.rating_distributions')")
        ).scalar()
        user_exists = conn.execute(
            text("SELECT to_regclass('public.user_profiles')")
        ).scalar()

    assert review_exists == "reviews"
    assert rating_exists == "rating_distributions"
    assert user_exists == "user_profiles"


@pytest.mark.integration
def test_upsert_reviews_and_users_and_ratings():
    reviews = pd.DataFrame(
        [
            {
                "book_url": "https://book.douban.com/subject/1007305/",
                "review_url": "https://book.douban.com/review/111/",
                "title": "标题A",
                "content": "内容A",
                "rating": 5,
                "useful_count": 12,
                "useless_count": 3,
                "useful_ratio": 0.8,
                "replies_count": 2,
                "reviewer_name": "读者甲",
                "reviewer_url": "https://www.douban.com/people/reviewer-a/",
                "published_at": "2024-01-02",
            }
        ]
    )
    ratings = pd.DataFrame(
        [
            {
                "book_url": "https://book.douban.com/subject/1007305/",
                "source": "official",
                "star_5_pct": 50.0,
                "star_4_pct": 30.0,
                "star_3_pct": 15.0,
                "star_2_pct": 3.0,
                "star_1_pct": 2.0,
                "want_to_read": 12345,
                "reading": 678,
                "read": 9012,
            }
        ]
    )
    users = pd.DataFrame(
        [
            {
                "reviewer_url": "https://www.douban.com/people/reviewer-a/",
                "display_name": "读者甲",
                "following_count": 42,
                "followers_count": 128,
            }
        ]
    )

    assert upsert_reviews(reviews) == 1
    assert upsert_rating_distributions(ratings) == 1
    assert upsert_user_profiles(users) == 1

    engine = get_engine()
    with engine.connect() as conn:
        review_count = conn.execute(text("SELECT COUNT(*) FROM reviews")).scalar()
        rating_count = conn.execute(text("SELECT COUNT(*) FROM rating_distributions")).scalar()
        user_count = conn.execute(text("SELECT COUNT(*) FROM user_profiles")).scalar()

    assert review_count == 1
    assert rating_count == 1
    assert user_count == 1
