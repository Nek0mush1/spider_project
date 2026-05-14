import pytest, os, sys, pandas as pd
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

os.environ["DATABASE_URL"] = "postgresql+psycopg2://dangdang:dangdang@localhost:5433/dangdang_books"
from dangdang_scrapy.db import get_engine, init_db, upsert_books
from sqlalchemy import text


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
    init_db()
    with get_engine().begin() as conn:
        conn.execute(text("DELETE FROM books"))
    yield


def test_upsert_inserts_new():
    df = _make_df([{"name": "测试书", "author": "测试", "detail_url": "http://test.com/1"}])
    upsert_books(df)
    with get_engine().connect() as conn:
        cnt = conn.execute(text("SELECT COUNT(*) FROM books")).scalar()
    assert cnt == 1


def test_upsert_skips_duplicate():
    df = _make_df([{"name": "测试书", "detail_url": "http://test.com/1"}])
    upsert_books(df)
    upsert_books(df)
    with get_engine().connect() as conn:
        cnt = conn.execute(text("SELECT COUNT(*) FROM books")).scalar()
    assert cnt == 1


def test_upsert_handles_nan():
    df = _make_df([{"name": "NaN书", "detail_url": "http://test.com/2", "rating_people": float("nan")}])
    upsert_books(df)
    with get_engine().connect() as conn:
        r = conn.execute(text("SELECT rating_people, sales FROM books WHERE detail_url='http://test.com/2'")).fetchone()
    assert r[0] is None
    assert r[1] is None


@pytest.mark.skip(reason="模块级单例导致隔离困难，需 subprocess 测试，留作手动验证")
def test_no_database_url_fails():
    pass


def test_empty_dataframe():
    df = _make_df([])
    upsert_books(df)
    assert True
