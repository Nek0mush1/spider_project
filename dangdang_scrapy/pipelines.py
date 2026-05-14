import os
import pandas as pd
from dangdang_scrapy.db import get_engine, init_db, upsert_books
from sqlalchemy import text


class BookCleaningPipeline:
    def process_item(self, item, spider):
        import re
        item["price"] = self._clean_price(item.get("price"))
        item["original_price"] = self._clean_price(item.get("original_price"))
        item["rating"] = self._clean_rating(item.get("rating"))
        item["sales"] = self._clean_number(item.get("sales"))
        item["rating_people"] = self._clean_number(item.get("rating_people"))
        for field in ("name", "author", "publisher"):
            if item.get(field):
                item[field] = item[field].strip()
        return item

    def _clean_price(self, value):
        if not value:
            return None
        import re
        nums = re.findall(r"\d+\.?\d*", str(value))
        return float(nums[0]) if nums else None

    def _clean_rating(self, value):
        if not value:
            return None
        import re
        nums = re.findall(r"(\d+(?:\.\d+)?)", str(value))
        return float(nums[0]) if nums else None

    def _clean_number(self, value):
        if not value:
            return None
        import re
        nums = re.findall(r"\d+", str(value).replace(",", ""))
        return int(nums[0]) if nums else None


class DatabasePipeline:
    BATCH_SIZE = 1000

    def open_spider(self, spider):
        self.items = []
        try:
            self.engine = get_engine()
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            init_db()
            self.db_ok = True
            spider.logger.info("Database connected")
        except Exception as e:
            self.db_ok = False
            spider.logger.error(f"Database unavailable: {e}")
            raise

    def process_item(self, item, spider):
        self.items.append(dict(item))
        if len(self.items) >= self.BATCH_SIZE:
            self._flush(spider)
        return item

    def close_spider(self, spider):
        if self.items:
            self._flush(spider)

    def _flush(self, spider):
        if not self.items:
            return
        df = pd.DataFrame(self.items).drop_duplicates(subset=["detail_url"])
        self.items = []
        before = len(df)
        df = df.dropna(subset=["detail_url"])
        if not df.empty:
            upsert_books(df)
        spider.logger.info(f"Saved {len(df)} books ({before - len(df)} duplicates/empty skipped)")
