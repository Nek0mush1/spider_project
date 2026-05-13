import scrapy
import re
from scrapy_playwright.page import PageMethod
from sqlalchemy import create_engine, text


class DangdangDetailSpider(scrapy.Spider):
    name = "dangdang_detail"
    allowed_domains = ["product.dangdang.com", "dangdang.com"]

    custom_settings = {
        "CONCURRENT_REQUESTS": 6,
        "DOWNLOAD_DELAY": 2.0,
        "DOWNLOAD_TIMEOUT": 60,
        "RETRY_TIMES": 3,
        "RETRY_HTTP_CODES": [504, 502, 500, 403, 429],
        "ITEM_PIPELINES": {},
        "DOWNLOAD_HANDLERS": {
            "http": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
            "https": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
        },
        "TWISTED_REACTOR": "twisted.internet.asyncioreactor.AsyncioSelectorReactor",
        "PLAYWRIGHT_LAUNCH_OPTIONS": {"headless": True},
        "PLAYWRIGHT_DEFAULT_NAVIGATION_TIMEOUT": 30000,
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.engine = create_engine(
            "mysql+pymysql://root:su_yuan19820409@172.27.80.1:3306/"
            "dangdang_books?charset=utf8mb4",
            connect_args={"connect_timeout": 5},
        )
        self.updated = 0
        self.skipped = 0

    def start_requests(self):
        urls = self._fetch_pending()
        self.logger.info(f"Fetched {len(urls)} URLs to scrape for ratings")
        for detail_url in urls:
            yield scrapy.Request(
                url=detail_url,
                callback=self.parse,
                meta={"detail_url": detail_url, "playwright": True,
                "playwright_page_methods": [
                    PageMethod("wait_for_selector", "span.star_box, #comm_num_down", timeout=15000),
                ],},
                errback=self.on_error,
            )

    def _fetch_pending(self, limit=200):
        sql = """
            SELECT detail_url FROM books
            WHERE detail_url LIKE '%product.dangdang.com%'
              AND (rating IS NULL OR rating = 0 OR rating_people IS NULL OR rating_people = 0)
            ORDER BY id
            LIMIT :lim
        """
        with self.engine.connect() as conn:
            result = conn.execute(text(sql), {"lim": limit})
            return [row[0] for row in result]

    def parse(self, response):
        detail_url = response.meta["detail_url"]
        rating = None
        rating_people = None

        m = re.search(r'<span class="star"[^>]*style="[^"]*width:\s*([\d.]+)%', response.text)
        if m:
            rating = float(m.group(1))

        m = re.search(r'id="comm_num_down"[^>]*>(\d+)', response.text)
        if m:
            rating_people = int(m.group(1))

        self._update_db(detail_url, rating, rating_people)

    def on_error(self, failure):
        self.logger.warning(f"Failed: {failure.request.meta.get('detail_url','?')}")

    def _update_db(self, detail_url, rating, rating_people):
        sql = "UPDATE books SET rating = :r, rating_people = :p WHERE detail_url = :u"
        with self.engine.begin() as conn:
            result = conn.execute(text(sql), {"r": rating, "p": rating_people, "u": detail_url})
            if result.rowcount > 0:
                self.updated += 1
            else:
                self.skipped += 1

    def closed(self, reason):
        self.logger.info(f"Done: {self.updated} updated, {self.skipped} skipped")
