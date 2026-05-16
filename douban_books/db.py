import os
import pandas as pd
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

_engine = None
_engine_url = None


def get_engine(database_url=None):
    """获取数据库引擎（单例，URL保护）"""
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
    """重置引擎（测试隔离用）"""
    global _engine, _engine_url
    if _engine is not None:
        _engine.dispose()
    _engine = None
    _engine_url = None


def init_db():
    """创建douban_books表（如果不存在）—— 8列精简schema，url为唯一键"""
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
                created_at TIMESTAMP DEFAULT NOW()
            )
        """))
        conn.execute(text("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_douban_books_url 
            ON douban_books(url)
        """))


def upsert_books(df, batch_size=100):
    """批量插入/更新书籍。

    - 首次插入（列表爬虫）：新行写入，已存在则通过COALESCE保留已有字段。
    - 增量更新（详情爬虫）：用非空字段覆盖已有行，不损坏已填充数据。
    - url 作为唯一键进行冲突处理。
    """
    import math

    engine = get_engine()

    if df.empty:
        return 0

    columns = [c for c in df.columns if c != "id"]
    placeholders = ", ".join([f":{c}" for c in columns])
    cols_str = ", ".join(columns)

    # COALESCE: 仅填充NULL字段（保留已有数据，不覆盖）
    set_clause = ", ".join(
        [f"{c} = COALESCE(douban_books.{c}, EXCLUDED.{c})" for c in columns]
    )

    stmt = text(f"""
        INSERT INTO douban_books ({cols_str})
        VALUES ({placeholders})
        ON CONFLICT (url) DO UPDATE SET {set_clause}
    """)

    inserted = 0
    with engine.begin() as conn:
        for start in range(0, len(df), batch_size):
            batch = df.iloc[start:start + batch_size]
            records = batch.to_dict(orient="records")
            # Convert NaN → None at the record level.
            # pandas float64 columns coerce None back to NaN, so the
            # conversion must happen AFTER to_dict().
            for record in records:
                for k, v in record.items():
                    if isinstance(v, float) and math.isnan(v):
                        record[k] = None
            result = conn.execute(stmt, records)
            inserted += result.rowcount

    return inserted
