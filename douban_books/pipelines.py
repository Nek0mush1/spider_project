import pandas as pd
from douban_books.db import get_engine, init_db, upsert_books
import logging

logger = logging.getLogger(__name__)


class BookCleaningPipeline:
    """清洗管道：解析和标准化字段（8列精简schema）"""

    def process_item(self, item, spider):
        # Strip string fields
        for field in ["url", "title", "authors", "publisher", "pubdate", "price"]:
            if item.get(field) and isinstance(item[field], str):
                item[field] = item[field].strip()

        # Parse price: strip "元" suffix
        if item.get("price") and isinstance(item["price"], str):
            item["price"] = item["price"].replace("元", "").strip()

        return item


class DatabasePipeline:
    """数据库管道：批量写入PostgreSQL（url为唯一键）"""

    BATCH_SIZE = 100

    def __init__(self):
        self.items = []
        self.db_available = True

    def open_spider(self, spider):
        try:
            engine = get_engine()
            init_db()
            spider.logger.info("数据库连接成功")
        except Exception as e:
            self.db_available = False
            spider.logger.warning(f"数据库不可用: {e}，将跳过数据库写入")

    def process_item(self, item, spider):
        if not self.db_available:
            return item

        self.items.append(dict(item))
        if len(self.items) >= self.BATCH_SIZE:
            self._flush(spider)
        return item

    def _flush(self, spider):
        if not self.items:
            return

        df = pd.DataFrame(self.items)
        if "url" in df.columns:
            df = df.drop_duplicates(subset=["url"])
            df = df.dropna(subset=["url"])

        if not df.empty:
            try:
                upsert_books(df)
                spider.logger.info(f"已写入 {len(df)} 条记录")
            except Exception as e:
                spider.logger.error(f"写入数据库失败: {e}")

        self.items = []

    def close_spider(self, spider):
        if self.db_available and self.items:
            self._flush(spider)
