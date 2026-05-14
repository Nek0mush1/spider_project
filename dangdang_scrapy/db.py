import os, math
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

_engine = None


def get_engine(database_url=None):
    global _engine
    if _engine is None:
        url = database_url or os.environ.get("DATABASE_URL")
        if not url:
            raise RuntimeError("DATABASE_URL 未设置。请复制 .env.example 为 .env 并填入配置")
        _engine = create_engine(url, connect_args={"connect_timeout": 5})
    return _engine


def reset_engine():
    global _engine
    if _engine is not None:
        _engine.dispose()
    _engine = None


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
                    v = row.get(k)
                    if v is None or (isinstance(v, float) and math.isnan(v)):
                        row[k] = None
            conn.execute(stmt, rows)
    return len(df)
