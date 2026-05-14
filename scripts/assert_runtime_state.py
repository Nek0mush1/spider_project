"""断言运行时数据库状态：表存在、有数据、有有效商品链接。"""
import sys
from sqlalchemy import text
from dangdang_scrapy.db import get_engine


def check():
    engine = get_engine()
    with engine.connect() as conn:
        total = conn.execute(text("SELECT COUNT(*) FROM books")).scalar()
        product = conn.execute(
            text("SELECT COUNT(*) FROM books WHERE detail_url LIKE '%product.dangdang.com%'")
        ).scalar()

    errors = []
    if total is None or total <= 0:
        errors.append(f"books 表为空 ({total})，请先运行 make crawl 或 make import")
    if product is None or product <= 0:
        errors.append(f"有效商品详情链接为 0，爬取质量检查不通过")

    if errors:
        print("运行时状态检查失败:")
        for e in errors:
            print(f"  ✗ {e}")
        print(f"\n当前状态: {total or 0} 条记录, {product or 0} 个有效详情链接")
        sys.exit(1)

    print(f"运行时状态检查通过: {total} 条记录, {product} 个有效详情链接")


if __name__ == "__main__":
    check()
