import math
import os

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

_engine = None
_engine_url = None


BOOK_COLUMNS = [
    "url",
    "title",
    "authors",
    "publisher",
    "pubdate",
    "price",
    "rating",
    "votes",
    "want_to_read",
    "reading",
    "read",
]

REVIEW_COLUMNS = [
    "book_url",
    "review_url",
    "title",
    "content",
    "rating",
    "useful_count",
    "useless_count",
    "useful_ratio",
    "replies_count",
    "reviewer_name",
    "reviewer_url",
    "published_at",
    "crawled_at",
]

RATING_DISTRIBUTION_COLUMNS = [
    "book_url",
    "source",
    "sample_size",
    "star_5_count",
    "star_4_count",
    "star_3_count",
    "star_2_count",
    "star_1_count",
    "star_5_pct",
    "star_4_pct",
    "star_3_pct",
    "star_2_pct",
    "star_1_pct",
    "want_to_read",
    "reading",
    "read",
    "crawled_at",
]

USER_PROFILE_COLUMNS = [
    "reviewer_url",
    "display_name",
    "following_count",
    "followers_count",
    "crawled_at",
]


def get_engine(database_url=None):
    global _engine, _engine_url
    requested = database_url or os.environ.get("DATABASE_URL")
    if not requested:
        raise RuntimeError("DATABASE_URL 未设置，请检查 .env 文件")
    if _engine is not None and requested != _engine_url:
        raise RuntimeError(f"engine 已用 {_engine_url} 初始化，无法切换到 {requested}")
    if _engine is None:
        _engine_url = requested
        _engine = create_engine(requested)
    return _engine


def reset_engine():
    global _engine, _engine_url
    if _engine is not None:
        _engine.dispose()
    _engine = None
    _engine_url = None


def init_db():
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS douban_books (
                id SERIAL PRIMARY KEY,
                url VARCHAR(500) NOT NULL,
                title VARCHAR(500),
                authors TEXT,
                publisher VARCHAR(255),
                pubdate VARCHAR(100),
                price VARCHAR(100),
                rating DOUBLE PRECISION,
                votes INTEGER,
                want_to_read INTEGER,
                reading INTEGER,
                read INTEGER,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """))
        conn.execute(text("""
            ALTER TABLE douban_books
            ADD COLUMN IF NOT EXISTS want_to_read INTEGER,
            ADD COLUMN IF NOT EXISTS reading INTEGER,
            ADD COLUMN IF NOT EXISTS read INTEGER
        """))
        conn.execute(text("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_douban_books_url
            ON douban_books(url)
        """))

        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS reviews (
                id SERIAL PRIMARY KEY,
                book_url VARCHAR(500) NOT NULL,
                review_url VARCHAR(500) NOT NULL,
                title VARCHAR(500),
                content TEXT,
                rating INTEGER,
                useful_count INTEGER,
                useless_count INTEGER,
                useful_ratio DOUBLE PRECISION,
                replies_count INTEGER,
                reviewer_name VARCHAR(255),
                reviewer_url VARCHAR(500),
                published_at VARCHAR(100),
                crawled_at TIMESTAMP DEFAULT NOW()
            )
        """))
        conn.execute(text("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_reviews_review_url
            ON reviews(review_url)
        """))
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_reviews_book_url
            ON reviews(book_url)
        """))

        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS rating_distributions (
                id SERIAL PRIMARY KEY,
                book_url VARCHAR(500) NOT NULL,
                source VARCHAR(32) NOT NULL,
                sample_size INTEGER,
                star_5_count INTEGER,
                star_4_count INTEGER,
                star_3_count INTEGER,
                star_2_count INTEGER,
                star_1_count INTEGER,
                star_5_pct DOUBLE PRECISION,
                star_4_pct DOUBLE PRECISION,
                star_3_pct DOUBLE PRECISION,
                star_2_pct DOUBLE PRECISION,
                star_1_pct DOUBLE PRECISION,
                want_to_read INTEGER,
                reading INTEGER,
                read INTEGER,
                crawled_at TIMESTAMP DEFAULT NOW()
            )
        """))
        conn.execute(text("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_rating_distributions_book_source
            ON rating_distributions(book_url, source)
        """))

        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS user_profiles (
                id SERIAL PRIMARY KEY,
                reviewer_url VARCHAR(500) NOT NULL,
                display_name VARCHAR(255),
                following_count INTEGER,
                followers_count INTEGER,
                crawled_at TIMESTAMP DEFAULT NOW()
            )
        """))
        conn.execute(text("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_user_profiles_reviewer_url
            ON user_profiles(reviewer_url)
        """))


def _records_from_df(df, columns):
    normalized = df.copy()
    for column in columns:
        if column not in normalized.columns:
            normalized[column] = None
    normalized = normalized[columns]
    records = normalized.to_dict(orient="records")
    for record in records:
        for key, value in record.items():
            if isinstance(value, float) and math.isnan(value):
                record[key] = None
    return records


def _upsert_dataframe(table_name, conflict_columns, update_columns, df, batch_size=100):
    engine = get_engine()
    if df.empty:
        return 0

    columns = list(df.columns)
    placeholders = ", ".join([f":{column}" for column in columns])
    cols_str = ", ".join(columns)
    conflict_str = ", ".join(conflict_columns)
    set_clause = ", ".join(
        [f"{column} = COALESCE(EXCLUDED.{column}, {table_name}.{column})" for column in update_columns]
    )
    stmt = text(f"""
        INSERT INTO {table_name} ({cols_str})
        VALUES ({placeholders})
        ON CONFLICT ({conflict_str}) DO UPDATE SET {set_clause}
    """)

    written = 0
    with engine.begin() as conn:
        for start in range(0, len(df), batch_size):
            batch = df.iloc[start:start + batch_size]
            records = batch.to_dict(orient="records")
            for record in records:
                for key, value in record.items():
                    if isinstance(value, float) and math.isnan(value):
                        record[key] = None
            result = conn.execute(stmt, records)
            written += result.rowcount
    return written


def upsert_books(df, batch_size=100):
    if df.empty:
        return 0
    normalized = df.copy()
    for column in BOOK_COLUMNS:
        if column not in normalized.columns:
            normalized[column] = None
    normalized = normalized[BOOK_COLUMNS]
    engine = get_engine()
    columns = list(normalized.columns)
    placeholders = ", ".join([f":{column}" for column in columns])
    cols_str = ", ".join(columns)
    set_clause = ", ".join(
        [f"{column} = COALESCE(douban_books.{column}, EXCLUDED.{column})" for column in columns if column != "url"]
    )
    stmt = text(f"""
        INSERT INTO douban_books ({cols_str})
        VALUES ({placeholders})
        ON CONFLICT (url) DO UPDATE SET {set_clause}
    """)
    written = 0
    with engine.begin() as conn:
        for start in range(0, len(normalized), batch_size):
            batch = normalized.iloc[start:start + batch_size]
            records = batch.to_dict(orient="records")
            for record in records:
                for key, value in record.items():
                    if isinstance(value, float) and math.isnan(value):
                        record[key] = None
            result = conn.execute(stmt, records)
            written += result.rowcount
    return written


def upsert_reviews(df, batch_size=100):
    if df.empty:
        return 0
    normalized = df.copy()
    for column in REVIEW_COLUMNS:
        if column not in normalized.columns:
            normalized[column] = None
    normalized = normalized[REVIEW_COLUMNS]
    return _upsert_dataframe(
        "reviews",
        ["review_url"],
        [column for column in REVIEW_COLUMNS if column != "review_url"],
        normalized,
        batch_size=batch_size,
    )


def upsert_rating_distributions(df, batch_size=100):
    if df.empty:
        return 0
    normalized = df.copy()
    for column in RATING_DISTRIBUTION_COLUMNS:
        if column not in normalized.columns:
            normalized[column] = None
    normalized = normalized[RATING_DISTRIBUTION_COLUMNS]
    return _upsert_dataframe(
        "rating_distributions",
        ["book_url", "source"],
        [column for column in RATING_DISTRIBUTION_COLUMNS if column not in {"book_url", "source"}],
        normalized,
        batch_size=batch_size,
    )


def upsert_user_profiles(df, batch_size=100):
    if df.empty:
        return 0
    normalized = df.copy()
    for column in USER_PROFILE_COLUMNS:
        if column not in normalized.columns:
            normalized[column] = None
    normalized = normalized[USER_PROFILE_COLUMNS]
    return _upsert_dataframe(
        "user_profiles",
        ["reviewer_url"],
        [column for column in USER_PROFILE_COLUMNS if column != "reviewer_url"],
        normalized,
        batch_size=batch_size,
    )


def fetch_book_urls():
    engine = get_engine()
    with engine.connect() as conn:
        rows = conn.execute(text("SELECT url FROM douban_books WHERE url IS NOT NULL ORDER BY id")).fetchall()
    return [row[0] for row in rows]


def fetch_pending_review_targets(limit_per_book=20):
    engine = get_engine()
    sql = text("""
        SELECT b.url, COUNT(r.id) AS review_count
        FROM douban_books b
        LEFT JOIN reviews r ON r.book_url = b.url
        WHERE b.url IS NOT NULL
        GROUP BY b.url
        HAVING COUNT(r.id) < :limit_per_book
        ORDER BY b.url
    """)
    with engine.connect() as conn:
        rows = conn.execute(sql, {"limit_per_book": limit_per_book}).fetchall()
    return [(row[0], max(limit_per_book - int(row[1]), 0)) for row in rows]


def fetch_pending_rating_urls():
    engine = get_engine()
    sql = text("""
        SELECT b.url
        FROM douban_books b
        LEFT JOIN rating_distributions rd
          ON rd.book_url = b.url AND rd.source = 'official'
        WHERE b.url IS NOT NULL
          AND rd.id IS NULL
        ORDER BY b.url
    """)
    with engine.connect() as conn:
        rows = conn.execute(sql).fetchall()
    return [row[0] for row in rows]


def fetch_reviews_for_book(book_url):
    engine = get_engine()
    sql = text("""
        SELECT rating
        FROM reviews
        WHERE book_url = :book_url
    """)
    with engine.connect() as conn:
        rows = conn.execute(sql, {"book_url": book_url}).mappings().all()
    return [dict(row) for row in rows]


def fetch_reviewer_urls(limit=None):
    engine = get_engine()
    sql = """
        SELECT DISTINCT reviewer_url
        FROM reviews
        WHERE reviewer_url IS NOT NULL
          AND reviewer_url <> ''
          AND reviewer_url NOT IN (
            SELECT reviewer_url FROM user_profiles WHERE reviewer_url IS NOT NULL
          )
        ORDER BY reviewer_url
    """
    if limit:
        sql += f" LIMIT {int(limit)}"
    with engine.connect() as conn:
        rows = conn.execute(text(sql)).fetchall()
    return [row[0] for row in rows]
