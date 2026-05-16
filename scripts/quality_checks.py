"""Quality checks for douban_books table (8-column reduced schema)."""
import sys
from pathlib import Path

from sqlalchemy import text

# Ensure project root is on sys.path so douban_books package is importable
_project_root = Path(__file__).resolve().parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from douban_books.db import get_engine

CORE_FIELDS = ["title", "authors", "publisher", "pubdate", "price"]


def main():
    engine = get_engine()

    with engine.connect() as conn:
        total = conn.execute(text("SELECT COUNT(*) FROM douban_books")).scalar()

    if total == 0:
        print("=== 数据质量报告 ===")
        print("总记录数: 0")
        print("数据为空，跳过检查")
        sys.exit(0)

    # Compute fill rates for core fields
    fill_rates = {}
    with engine.connect() as conn:
        for field in CORE_FIELDS:
            filled = conn.execute(
                text(
                    f"SELECT COUNT(*) FROM douban_books "
                    f"WHERE {field} IS NOT NULL AND {field} != ''"
                )
            ).scalar()
            fill_rates[field] = filled / total

    # Print report
    print("=== 数据质量报告 ===")
    print(f"总记录数: {total}")
    print()
    print("核心字段填充率:")
    for field, rate in fill_rates.items():
        print(f"  {field}: {rate:.2%}")

    # Rating stats if any data exists
    with engine.connect() as conn:
        rating_count = conn.execute(
            text("SELECT COUNT(*) FROM douban_books WHERE rating IS NOT NULL")
        ).scalar()

    if rating_count > 0:
        with engine.connect() as conn:
            row = conn.execute(
                text(
                    "SELECT AVG(rating)::numeric(10,2), MIN(rating), MAX(rating) "
                    "FROM douban_books WHERE rating IS NOT NULL"
                )
            ).fetchone()
        print()
        print(f"评分统计 (共 {rating_count} 条有评分):")
        print(f"  平均分: {row[0]}")
        print(f"  最低分: {row[1]}")
        print(f"  最高分: {row[2]}")

    # Determine exit code
    all_ok = all(rate > 0.9 for rate in fill_rates.values())
    print()
    if all_ok:
        print("所有核心字段填充率 > 90%，检查通过")
        sys.exit(0)
    else:
        print("存在填充率 <= 90% 的核心字段，检查未通过")
        sys.exit(1)


if __name__ == "__main__":
    main()
