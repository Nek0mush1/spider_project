"""Integration tests for db.py and pipelines.py — 8-column reduced schema.

Requires TEST_DATABASE_URL env var ending in '_test'.
"""

import os
import numpy as np
import pandas as pd
import pytest
from sqlalchemy import text

from douban_books.db import get_engine, init_db, reset_engine, upsert_books
from douban_books.pipelines import DatabasePipeline

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _integration_db():
    """Auto-use fixture: validate TEST_DATABASE_URL & wire engine.

    - Skips if TEST_DATABASE_URL is missing
    - Asserts URL ends with '_test' for safety
    - Calls reset_engine() to discard any prior singleton
    - Sets DATABASE_URL so get_engine() picks up the test DB
    - Creates the douban_books table
    - Cleans up after each test (DELETE + reset)
    """
    test_url = os.environ.get("TEST_DATABASE_URL")
    if not test_url:
        pytest.skip("TEST_DATABASE_URL not set")

    assert test_url.endswith("_test"), (
        f"TEST_DATABASE_URL must end with '_test', got: {test_url}"
    )

    # ---- setup ----
    reset_engine()

    old_url = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = test_url

    # Drop old table (schema may have changed) then recreate
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(text("DROP TABLE IF EXISTS douban_books CASCADE"))
    init_db()

    yield

    # ---- teardown ----
    try:
        engine = get_engine()
        with engine.begin() as conn:
            conn.execute(text("DELETE FROM douban_books"))
    except Exception:
        pass

    reset_engine()

    if old_url is not None:
        os.environ["DATABASE_URL"] = old_url
    else:
        os.environ.pop("DATABASE_URL", None)


def _make_minimal_record(url: str) -> dict:
    """Return a minimal valid dict matching the 8-field schema."""
    return {
        "url": url,
        "title": "测试书名",
        "authors": "张三, 李四",
        "publisher": "测试出版社",
        "pubdate": "2024-06",
        "price": "68.00",
        "rating": 8.5,
        "votes": 1000,
    }


def _count_books():
    """Return total row count in douban_books."""
    engine = get_engine()
    with engine.connect() as conn:
        return conn.execute(text("SELECT COUNT(*) FROM douban_books")).scalar()


def _fetch_row(url: str) -> dict | None:
    """Return the first matching row as a dict, or None."""
    engine = get_engine()
    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT * FROM douban_books WHERE url = :url"),
            {"url": url},
        ).mappings().first()
    return dict(row) if row else None


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_db_engine_creation():
    """Verify engine is created and connected to the correct test database."""
    test_url = os.environ["DATABASE_URL"]
    assert test_url.endswith("_test")

    engine = get_engine()
    assert engine is not None
    # Compare database name (str(engine.url) masks the password as ***)
    assert engine.url.database.endswith("_test")

    # Sanity: can actually query
    with engine.connect() as conn:
        result = conn.execute(text("SELECT 1")).scalar()
        assert result == 1


@pytest.mark.integration
def test_upsert_single_book():
    """Insert a single book and verify it lands in the database."""
    url = "https://book.douban.com/subject/36090832/"
    record = _make_minimal_record(url)

    df = pd.DataFrame([record])
    inserted = upsert_books(df)
    assert inserted == 1
    assert _count_books() == 1

    row = _fetch_row(url)
    assert row is not None
    assert row["title"] == "测试书名"
    assert row["rating"] == 8.5
    assert row["url"] == url


@pytest.mark.integration
def test_upsert_duplicate_prevention():
    """Upserting the same url twice must not create duplicates."""
    url = "https://book.douban.com/subject/36090833/"
    record = _make_minimal_record(url)

    # First insert
    assert upsert_books(pd.DataFrame([record])) == 1
    assert _count_books() == 1

    # Second insert with same url → COALESCE preserves existing data
    # PostgreSQL ON CONFLICT DO UPDATE always returns rowcount ≥ 1
    record2 = _make_minimal_record(url)
    record2["title"] = "不同的书名"  # different data, same key
    assert upsert_books(pd.DataFrame([record2])) >= 1
    assert _count_books() == 1

    # The original title is preserved
    row = _fetch_row(url)
    assert row["title"] == "测试书名"


@pytest.mark.integration
def test_batch_upsert_100():
    """Insert 100 books in a single call and verify all make it in."""
    records = []
    for i in range(100):
        url = f"https://book.douban.com/subject/batch_{i:04d}/"
        rec = _make_minimal_record(url)
        records.append(rec)

    df = pd.DataFrame(records)
    inserted = upsert_books(df)

    assert inserted == 100
    assert _count_books() == 100


@pytest.mark.integration
def test_nan_conversion():
    """NaN in the 'votes' column must be converted to NULL in the database."""
    url = "https://book.douban.com/subject/36090834/"
    record = _make_minimal_record(url)
    record["votes"] = np.nan

    df = pd.DataFrame([record])
    assert upsert_books(df) == 1

    row = _fetch_row(url)
    assert row["votes"] is None


@pytest.mark.integration
def test_pipeline_flush():
    """Feed items through DatabasePipeline and verify they are flushed to DB."""
    pipeline = DatabasePipeline()

    # open_spider needs a spider-like object with a logger
    class FakeSpider:
        class logger:
            @staticmethod
            def info(msg):
                pass

            @staticmethod
            def warning(msg):
                pass

            @staticmethod
            def error(msg):
                pass

    spider = FakeSpider()
    pipeline.open_spider(spider)

    # Feed BATCH_SIZE items to trigger auto-flush
    for i in range(DatabasePipeline.BATCH_SIZE):
        url = f"https://book.douban.com/subject/flush_{i:04d}/"
        item = _make_minimal_record(url)
        pipeline.process_item(item, spider)

    # After BATCH_SIZE items, flush should have been triggered
    assert _count_books() == DatabasePipeline.BATCH_SIZE

    # Feed a few more then close_spider → remaining flushed
    extra = 7
    for i in range(extra):
        url = f"https://book.douban.com/subject/flush_extra_{i:04d}/"
        item = _make_minimal_record(url)
        pipeline.process_item(item, spider)

    pipeline.close_spider(spider)
    assert _count_books() == DatabasePipeline.BATCH_SIZE + extra
