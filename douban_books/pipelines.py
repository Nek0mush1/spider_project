import logging
from datetime import UTC, datetime

import pandas as pd

from douban_books.db import (
    get_engine,
    init_db,
    upsert_books,
    upsert_rating_distributions,
    upsert_reviews,
    upsert_user_profiles,
)

logger = logging.getLogger(__name__)


class BookCleaningPipeline:
    """清洗书籍级字段。"""

    def process_item(self, item, spider):
        if "url" not in item:
            return item
        for field in [
            "url",
            "title",
            "authors",
            "publisher",
            "pubdate",
            "price",
        ]:
            if item.get(field) and isinstance(item[field], str):
                item[field] = item[field].strip()
        if item.get("price") and isinstance(item["price"], str):
            item["price"] = item["price"].replace("元", "").strip()
        return item


class AdvancedItemPipeline:
    """统一批量写入书籍、评论、评分分布和用户数据。"""

    BATCH_SIZE = 100

    def __init__(self):
        self.db_available = True
        self.buffers = {
            "books": [],
            "reviews": [],
            "ratings": [],
            "users": [],
        }

    def open_spider(self, spider):
        try:
            get_engine()
            init_db()
            spider.logger.info("数据库连接成功")
        except Exception as exc:
            self.db_available = False
            spider.logger.warning(f"数据库不可用: {exc}，将跳过数据库写入")

    def process_item(self, item, spider):
        if not self.db_available:
            return item

        payload = dict(item)
        payload.setdefault("crawled_at", datetime.now(UTC).isoformat())

        category = self._categorize(payload)
        self.buffers[category].append(payload)

        if len(self.buffers[category]) >= self.BATCH_SIZE:
            self._flush_category(category, spider)
        return item

    def close_spider(self, spider):
        if not self.db_available:
            return
        for category in list(self.buffers):
            self._flush_category(category, spider)

    def _categorize(self, payload):
        if "review_url" in payload:
            return "reviews"
        if "source" in payload:
            return "ratings"
        if "reviewer_url" in payload and "book_url" not in payload and "url" not in payload:
            return "users"
        return "books"

    def _flush_category(self, category, spider):
        records = self.buffers[category]
        if not records:
            return

        df = pd.DataFrame(records)
        try:
            if category == "books":
                if "url" in df.columns:
                    df = df.drop_duplicates(subset=["url"]).dropna(subset=["url"])
                if not df.empty:
                    upsert_books(df)
            elif category == "reviews":
                if "review_url" in df.columns:
                    df = df.drop_duplicates(subset=["review_url"]).dropna(subset=["review_url"])
                if not df.empty:
                    upsert_reviews(df)
            elif category == "ratings":
                if {"book_url", "source"}.issubset(df.columns):
                    df = df.drop_duplicates(subset=["book_url", "source"]).dropna(subset=["book_url", "source"])
                if not df.empty:
                    upsert_rating_distributions(df)
            elif category == "users":
                if "reviewer_url" in df.columns:
                    df = df.drop_duplicates(subset=["reviewer_url"]).dropna(subset=["reviewer_url"])
                if not df.empty:
                    upsert_user_profiles(df)
            spider.logger.info(f"{category} 已写入 {len(df)} 条记录")
        except Exception as exc:
            spider.logger.error(f"{category} 写入数据库失败: {exc}")

        self.buffers[category] = []


DatabasePipeline = AdvancedItemPipeline
