import os, sys
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()


def get_engine():
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL 未设置")
    return create_engine(url)


def run():
    engine = get_engine()
    with engine.connect() as conn:
        total = conn.execute(text("SELECT COUNT(*) FROM books")).scalar()

        unique_urls = conn.execute(
            text("SELECT COUNT(*) FROM (SELECT detail_url FROM books GROUP BY detail_url) sub")
        ).scalar()

        product_urls = conn.execute(
            text("SELECT COUNT(*) FROM books WHERE detail_url LIKE '%product.dangdang.com%'")
        ).scalar()

        jump_urls = conn.execute(
            text("SELECT COUNT(*) FROM books WHERE detail_url LIKE '%jump.php%'")
        ).scalar()

        has_rating = conn.execute(
            text("SELECT COUNT(*) FROM books WHERE rating IS NOT NULL AND rating > 0")
        ).scalar()

        has_price = conn.execute(
            text("SELECT COUNT(*) FROM books WHERE price IS NOT NULL AND price > 0")
        ).scalar()

        has_name = conn.execute(
            text("SELECT COUNT(*) FROM books WHERE name IS NOT NULL AND name != ''")
        ).scalar()

        publishers = conn.execute(
            text("SELECT COUNT(DISTINCT publisher) FROM books WHERE publisher != ''")
        ).scalar()

        avg_price = conn.execute(
            text("SELECT ROUND(AVG(price)::numeric, 2) FROM books WHERE price > 0")
        ).scalar()

        avg_rating = conn.execute(
            text("SELECT ROUND(AVG(rating)::numeric, 1) FROM books WHERE rating > 0")
        ).scalar()

    print("=" * 50)
    print("数据质量报告")
    print("=" * 50)
    print(f"  采集总条数:              {total}")
    print(f"  唯一商品(detail_url):    {unique_urls}")
    print(f"  可用详情页(product URL): {product_urls} ({product_urls/total*100:.1f}%)")
    print(f"  脏链接(jump.php):        {jump_urls} ({jump_urls/total*100:.1f}%)")
    print(f"  评分补全率:               {has_rating}/{total} ({has_rating/total*100:.1f}%)")
    print(f"  价格可解析率:             {has_price}/{total} ({has_price/total*100:.1f}%)")
    print(f"  书名非空率:               {has_name}/{total} ({has_name/total*100:.1f}%)")
    print(f"  出版社数:                {publishers}")
    print(f"  平均价格:                ¥{avg_price}")
    print(f"  平均评分:                {avg_rating}/100")
    print("=" * 50)


if __name__ == "__main__":
    run()
