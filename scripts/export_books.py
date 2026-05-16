"""Export douban_books table to CSV (8-column reduced schema)."""
import sys
from pathlib import Path

import pandas as pd

# Ensure project root is on sys.path so douban_books package is importable
_project_root = Path(__file__).resolve().parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from douban_books.db import get_engine


def main():
    engine = get_engine()
    df = pd.read_sql("SELECT * FROM douban_books", engine)

    # Exclude id and created_at if present
    for col in ("id", "created_at"):
        if col in df.columns:
            df.drop(columns=[col], inplace=True)

    output_path = _project_root / "data" / "books.csv"
    df.to_csv(output_path, index=False, encoding="utf-8-sig")
    print(f"已导出 {len(df)} 条记录到 {output_path}")


if __name__ == "__main__":
    main()
