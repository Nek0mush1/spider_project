import pytest, os, sys, pandas as pd
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

pytestmark = [pytest.mark.integration]

# 集成测试只在 TEST_DATABASE_URL 指向 _test 库时才运行
_url = os.environ.get("TEST_DATABASE_URL")
if not _url:
    pytest.skip("TEST_DATABASE_URL 未设置", allow_module_level=True)
elif not _url.endswith("_test"):
    raise RuntimeError(f"拒绝在非测试库上运行集成测试: {_url}")

from sqlalchemy import create_engine, text
from dangdang_scrapy.db import upsert_books

_test_engine = create_engine(_url, connect_args={"connect_timeout": 5})

# 初始化测试库表结构
with _test_engine.begin() as conn:
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS books (
            id SERIAL PRIMARY KEY,
            name VARCHAR(500), author VARCHAR(500), publisher VARCHAR(300),
            price DOUBLE PRECISION, original_price DOUBLE PRECISION,
            rating DOUBLE PRECISION, rating_people BIGINT, sales BIGINT,
            detail_url VARCHAR(1000), category VARCHAR(200),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """))
    conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS idx_books_url ON books (detail_url)"))


def _make_df(rows):
    cols = ["name", "author", "publisher", "price", "original_price",
            "rating", "rating_people", "sales", "detail_url", "category"]
    records = []
    for r in rows:
        row = {c: None for c in cols}
        row.update(r)
        records.append(row)
    return pd.DataFrame(records)


@pytest.fixture(autouse=True)
def clean_db():
    with _test_engine.begin() as conn:
        conn.execute(text("TRUNCATE TABLE books RESTART IDENTITY"))


def test_upsert_inserts_new():
    df = _make_df([{"name": "测试书", "author": "测试", "detail_url": "http://test.com/1"}])
    upsert_books(df)
    with _test_engine.connect() as conn:
        cnt = conn.execute(text("SELECT COUNT(*) FROM books")).scalar()
    assert cnt == 1


def test_upsert_skips_duplicate():
    df = _make_df([{"name": "测试书", "detail_url": "http://test.com/1"}])
    upsert_books(df)
    upsert_books(df)
    with _test_engine.connect() as conn:
        cnt = conn.execute(text("SELECT COUNT(*) FROM books")).scalar()
    assert cnt == 1


def test_upsert_handles_nan():
    df = _make_df([{"name": "NaN书", "detail_url": "http://test.com/2", "rating_people": float("nan")}])
    upsert_books(df)
    with _test_engine.connect() as conn:
        r = conn.execute(
            text("SELECT rating_people, sales FROM books WHERE detail_url='http://test.com/2'")
        ).fetchone()
    assert r[0] is None
    assert r[1] is None


def test_empty_dataframe():
    df = _make_df([])
    upsert_books(df)
    assert True


def test_upsert_batch_size():
    rows = [{"name": f"书{i}", "detail_url": f"http://test.com/{i}"} for i in range(250)]
    df = _make_df(rows)
    upsert_books(df, batch_size=100)
    with _test_engine.connect() as conn:
        cnt = conn.execute(text("SELECT COUNT(*) FROM books")).scalar()
    assert cnt == 250
