import os
from sqlalchemy import create_engine, text

_engine = None


def get_engine():
    global _engine
    if _engine is None:
        url = os.environ.get(
            "DATABASE_URL",
            "postgresql+psycopg2://dangdang:dangdang@localhost:5433/dangdang_books",
        )
        _engine = create_engine(url, connect_args={"connect_timeout": 5})
    return _engine


def init_db():
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS books (
                id SERIAL PRIMARY KEY,
                name VARCHAR(500),
                author VARCHAR(500),
                publisher VARCHAR(300),
                price DOUBLE PRECISION,
                original_price DOUBLE PRECISION,
                rating DOUBLE PRECISION,
    rating_people BIGINT,
    sales BIGINT,
                detail_url VARCHAR(1000),
                category VARCHAR(200),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
        conn.execute(text("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_books_url
            ON books (detail_url)
        """))


def upsert_books(df, batch_size=100):
    import math
    engine = get_engine()
    stmt = text("""
        INSERT INTO books (name, author, publisher, price, original_price,
                           rating, rating_people, sales, detail_url, category)
        VALUES (:name, :author, :publisher, :price, :original_price,
                :rating, :rating_people, :sales, :detail_url, :category)
        ON CONFLICT (detail_url) DO NOTHING
    """)
    with engine.begin() as conn:
        for start in range(0, len(df), batch_size):
            batch = df.iloc[start:start + batch_size]
            rows = batch.to_dict(orient="records")
            for row in rows:
                for k in ("rating_people", "sales"):
                    if k in row and (row[k] is None or (isinstance(row[k], float) and math.isnan(row[k]))):
                        row[k] = None
                conn.execute(stmt, row)
    return len(df)
