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
    BATCH_SIZE = 1000

    def open_spider(self, spider):
        self.items = []
        self.csv_path = os.path.join(os.path.dirname(__file__), "..", "data", "books.csv")
        db_url = spider.settings.get("DATABASE_URL",
            f"postgresql+psycopg2://dangdang:@localhost:5433/dangdang_books")
        try:
            self.engine = create_engine(db_url, connect_args={"connect_timeout": 5})
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            self._create_table()
            self.db_ok = True
            spider.logger.info("PostgreSQL connected")
        except Exception as e:
            self.db_ok = False
            spider.logger.warning(f"Database unavailable ({e}), falling back to CSV")

    def _create_table(self):
        ddl = text("""
            CREATE TABLE IF NOT EXISTS books (
                id SERIAL PRIMARY KEY,
                name VARCHAR(500),
                author VARCHAR(500),
                publisher VARCHAR(300),
                price DOUBLE PRECISION,
                original_price DOUBLE PRECISION,
                rating DOUBLE PRECISION,
                rating_people INTEGER,
                sales INTEGER,
                detail_url VARCHAR(1000),
                category VARCHAR(200),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        with self.engine.begin() as conn:
            conn.execute(ddl)
            conn.execute(text("""
                CREATE UNIQUE INDEX IF NOT EXISTS idx_books_url
                ON books (detail_url)
            """))

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
        if self.db_ok:
            try:
                existing = pd.read_sql("SELECT detail_url FROM books", self.engine)
                known = set(existing["detail_url"].dropna().tolist())
                before = len(df)
                df = df[~df["detail_url"].isin(known)]
                spider.logger.info(f"Saving {len(df)} books to DB ({before - len(df)} duplicates skipped)")
                if not df.empty:
                    df.to_sql("books", self.engine, if_exists="append", index=False, method="multi", chunksize=100)
                spider.logger.info(f"DB batch saved, {len(self.items)} pending in memory")
            except Exception as e:
                spider.logger.warning(f"DB save failed ({e}), CSV saved anyway")
        os.makedirs(os.path.dirname(self.csv_path), exist_ok=True)
        df.to_csv(self.csv_path, index=False, encoding="utf-8-sig",
                  mode="a", header=not os.path.exists(self.csv_path))
        spider.logger.info(f"CSV batch appended ({len(df)} rows)")
