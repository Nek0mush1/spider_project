"""Export PostgreSQL books table to CSV."""
import os, pandas as pd
from dangdang_scrapy.db import get_engine

df = pd.read_sql("SELECT * FROM books ORDER BY id", get_engine())
path = os.path.join(os.path.dirname(__file__), "..", "data", "books.csv")
df.to_csv(path, index=False, encoding="utf-8-sig")
print(f"Exported {len(df)} rows to {path}")
