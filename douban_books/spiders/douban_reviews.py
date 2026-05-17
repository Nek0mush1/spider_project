import scrapy

from douban_books.db import fetch_pending_review_targets
from douban_books.items import ReviewItem
from douban_books.parsers import parse_review_entries
from douban_books.settings import USE_PLAYWRIGHT


class DoubanReviewsSpider(scrapy.Spider):
    name = "douban_reviews"
    allowed_domains = ["book.douban.com", "douban.com"]

    custom_settings = {
        "CONCURRENT_REQUESTS": 2,
        "DOWNLOAD_DELAY": 5.0,
    }

    def start_requests(self):
        for book_url, remaining in fetch_pending_review_targets(limit_per_book=20):
            if remaining <= 0:
                continue
            reviews_url = book_url.rstrip("/") + "/reviews"
            yield scrapy.Request(
                reviews_url,
                callback=self.parse,
                meta=self._request_meta(book_url, remaining=remaining),
            )

    def parse(self, response):
        book_url = response.meta["book_url"]
        remaining = int(response.meta.get("remaining", 20))
        reviews, next_url = parse_review_entries(response, book_url=book_url, limit=remaining)

        for payload in reviews:
            item = ReviewItem()
            for key, value in payload.items():
                item[key] = value
            yield item

        left = remaining - len(reviews)
        if next_url and left > 0:
            yield scrapy.Request(
                next_url,
                callback=self.parse,
                meta=self._request_meta(book_url, remaining=left),
            )

    def _request_meta(self, book_url, remaining):
        meta = {
            "book_url": book_url,
            "remaining": remaining,
        }
        if USE_PLAYWRIGHT:
            meta["playwright"] = True
        return meta
