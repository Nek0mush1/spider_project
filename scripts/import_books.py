"""导入 data/books.csv 到 PostgreSQL（首次 setup 使用）。"""
import os, sys, pandas as pd
from dangdang_scrapy.db import get_engine, init_db, upsert_books

path = os.path.join(os.path.dirname(__file__), "..", "data", "books.csv")
if not os.path.exists(path):
    print(f"未找到 {path}，跳过导入")
    sys.exit(0)

df = pd.read_csv(path)
init_db()
upsert_books(df)
print(f"导入 {len(df)} 条完成")
