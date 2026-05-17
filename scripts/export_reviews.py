"""Export advanced tables to CSV files."""
import sys
from pathlib import Path

import pandas as pd

_project_root = Path(__file__).resolve().parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from douban_books.db import get_engine


def _export_table(table_name, filename):
    engine = get_engine()
    df = pd.read_sql(f"SELECT * FROM {table_name}", engine)
    output_path = _project_root / "data" / filename
    df.to_csv(output_path, index=False, encoding="utf-8-sig")
    print(f"{table_name}: {len(df)} -> {output_path}")


def main():
    _export_table("reviews", "reviews.csv")
    _export_table("rating_distributions", "rating_distributions.csv")
    _export_table("user_profiles", "user_profiles.csv")


if __name__ == "__main__":
    main()
