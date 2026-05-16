import scrapy
from sqlalchemy import text
from douban_books.db import get_engine
from douban_books.parsers import parse_detail
import logging

logger = logging.getLogger(__name__)


class DoubanDetailSpider(scrapy.Spider):
    """DB-driven spider: reads URLs from the database and scrapes book
    detail pages, yielding 8-field parsed dicts for persistence via DatabasePipeline."""

    name = "douban_detail"
    allowed_domains = ["book.douban.com", "douban.com"]

    custom_settings = {
        "CONCURRENT_REQUESTS": 2,
        "DOWNLOAD_DELAY": 4.0,
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.http_errors = 0
        self.processed_count = 0

    def start_requests(self):
        engine = get_engine()
        with engine.connect() as conn:
            result = conn.execute(text(
                "SELECT url FROM douban_books "
                "WHERE url IS NOT NULL "
                "AND (authors IS NULL OR publisher IS NULL "
                "OR pubdate IS NULL OR price IS NULL OR votes IS NULL)"
            ))
            urls = [row[0] for row in result]

        self.logger.info(f"从数据库加载了 {len(urls)} 个待抓取的详情页URL")

        for url in urls:
            yield scrapy.Request(
                url=url,
                callback=self.parse,
                errback=self.on_error,
            )

    def parse(self, response):
        """Parse a single book detail page and yield the 8-field result dict."""
        item = parse_detail(response)
        self.processed_count += 1
        yield item

    def on_error(self, failure):
        """Log failed requests and track error count."""
        self.http_errors += 1
        self.logger.error(
            f"请求失败 [{failure.request.url}]: {failure.value}"
        )

    def closed(self, reason):
        """Log a summary of the spider run."""
        self.logger.info(
            f"爬虫关闭 (reason={reason}) | "
            f"已处理: {self.processed_count} 条 | "
            f"HTTP错误: {self.http_errors} 次"
        )
