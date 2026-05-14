import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# ── 集成测试隔离保护 ──────────────────────────────────
#   upsert_books() 内部调用 get_engine() 读取 DATABASE_URL。
#   测试必须把 DATABASE_URL 覆盖到测试库，确保读写同一目标。
_test_url = os.environ.get("TEST_DATABASE_URL")
if not _test_url:
    import pytest
    pytest.skip("TEST_DATABASE_URL 未设置", allow_module_level=True)
if not _test_url.endswith("_test"):
    raise RuntimeError(f"拒绝在非测试库上运行集成测试: {_test_url}")

os.environ["DATABASE_URL"] = _test_url
from dangdang_scrapy import db
db.reset_engine()          # 清除可能缓存的旧连接
# ─────────────────────────────────────────────────────

import pytest
import pandas as pd
from sqlalchemy import text

pytestmark = [pytest.mark.integration]
engine = db.get_engine()

# 初始化测试库表结构
db.init_db()


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
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE TABLE books RESTART IDENTITY"))


def test_upsert_inserts_new():
    df = _make_df([{"name": "测试书", "author": "测试", "detail_url": "http://test.com/1"}])
    db.upsert_books(df)
    with engine.connect() as conn:
        cnt = conn.execute(text("SELECT COUNT(*) FROM books")).scalar()
    assert cnt == 1


def test_upsert_skips_duplicate():
    df = _make_df([{"name": "测试书", "detail_url": "http://test.com/1"}])
    db.upsert_books(df)
    db.upsert_books(df)
    with engine.connect() as conn:
        cnt = conn.execute(text("SELECT COUNT(*) FROM books")).scalar()
    assert cnt == 1


def test_upsert_handles_nan():
    df = _make_df([{"name": "NaN书", "detail_url": "http://test.com/2", "rating_people": float("nan")}])
    db.upsert_books(df)
    with engine.connect() as conn:
        r = conn.execute(
            text("SELECT rating_people, sales FROM books WHERE detail_url='http://test.com/2'")
        ).fetchone()
    assert r[0] is None
    assert r[1] is None


def test_empty_dataframe():
    df = _make_df([])
    db.upsert_books(df)
    assert True


def test_upsert_batch_size():
    rows = [{"name": f"书{i}", "detail_url": f"http://test.com/{i}"} for i in range(250)]
    df = _make_df(rows)
    db.upsert_books(df, batch_size=100)
    with engine.connect() as conn:
        cnt = conn.execute(text("SELECT COUNT(*) FROM books")).scalar()
    assert cnt == 250
