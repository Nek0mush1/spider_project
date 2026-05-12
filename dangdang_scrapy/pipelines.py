import os
import pandas as pd
from sqlalchemy import create_engine, text


class BookCleaningPipeline:
    def process_item(self, item, spider):
        item["price"] = self._clean_price(item.get("price"))
        item["original_price"] = self._clean_price(item.get("original_price"))
        item["rating"] = self._clean_rating(item.get("rating"))
        item["sales"] = self._clean_sales(item.get("sales"))
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
        nums = re.findall(r"\d+\.?\d*", str(value))
        return float(nums[0]) if nums else None

    def _clean_sales(self, value):
        if not value:
            return None
        import re
        nums = re.findall(r"\d+", str(value).replace(",", ""))
        return int(nums[0]) if nums else None

    def _clean_number(self, value):
        if not value:
            return None
        import re
        nums = re.findall(r"\d+", str(value).replace(",", ""))
        return int(nums[0]) if nums else None


class MySQLPipeline:
    def open_spider(self, spider):
        self.items = []
        self.csv_path = os.path.join(os.path.dirname(__file__), "..", "data", "books.csv")
        host = spider.settings.get("MYSQL_HOST")
        try:
            self.engine = create_engine(
                f"mysql+pymysql://{spider.settings.get('MYSQL_USER')}:"
                f"{spider.settings.get('MYSQL_PASSWORD')}@{host}:"
                f"{spider.settings.get('MYSQL_PORT')}/"
                f"{spider.settings.get('MYSQL_DATABASE')}?charset=utf8mb4",
                connect_args={"connect_timeout": 5},
            )
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            self._create_table()
            self.mysql_ok = True
            spider.logger.info(f"MySQL connected via {host}")
        except Exception as e:
            self.mysql_ok = False
            spider.logger.warning(f"MySQL unavailable ({e}), falling back to CSV")

    def _create_table(self):
        ddl = text("""
            CREATE TABLE IF NOT EXISTS books (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(500),
                author VARCHAR(500),
                publisher VARCHAR(300),
                price FLOAT,
                original_price FLOAT,
                rating FLOAT,
                rating_people INT,
                sales INT,
                detail_url VARCHAR(1000),
                category VARCHAR(200),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE KEY uk_url (detail_url(255))
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)
        with self.engine.begin() as conn:
            conn.execute(ddl)

    def process_item(self, item, spider):
        self.items.append(dict(item))
        return item

    def close_spider(self, spider):
        if not self.items:
            return
        df = pd.DataFrame(self.items).drop_duplicates(subset=["detail_url"])
        if self.mysql_ok:
            spider.logger.info(f"Saving {len(df)} books to MySQL")
            df.to_sql("books", self.engine, if_exists="append", index=False, method="multi", chunksize=100)
            spider.logger.info("MySQL save done")
        os.makedirs(os.path.dirname(self.csv_path), exist_ok=True)
        df.to_csv(self.csv_path, index=False, encoding="utf-8-sig")
        spider.logger.info(f"CSV saved to {self.csv_path}")
