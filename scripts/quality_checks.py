"""Basic quality checks for douban_books advanced crawler."""
import sys
from pathlib import Path

from sqlalchemy import text

_project_root = Path(__file__).resolve().parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from douban_books.db import get_engine


def _scalar(conn, sql):
    return conn.execute(text(sql)).scalar() or 0


def main():
    engine = get_engine()

    with engine.connect() as conn:
        books = _scalar(conn, "SELECT COUNT(*) FROM douban_books")
        reviews = _scalar(conn, "SELECT COUNT(*) FROM reviews")
        ratings = _scalar(conn, "SELECT COUNT(*) FROM rating_distributions")
        users = _scalar(conn, "SELECT COUNT(*) FROM user_profiles")
        duplicate_users = _scalar(
            conn,
            """
            SELECT COUNT(*) FROM (
                SELECT reviewer_url, COUNT(*) AS c
                FROM user_profiles
                GROUP BY reviewer_url
                HAVING COUNT(*) > 1
            ) dup
            """,
        )

    print("=== 进阶质量检查 ===")
    print(f"douban_books: {books}")
    print(f"reviews: {reviews}")
    print(f"rating_distributions: {ratings}")
    print(f"user_profiles: {users}")
    print(f"user_profiles duplicates: {duplicate_users}")

    if duplicate_users > 0:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
