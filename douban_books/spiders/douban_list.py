import re

import scrapy

from douban_books.items import DoubanBookItem
from douban_books.parsers import parse_list_items
from douban_books.settings import USE_PLAYWRIGHT


class DoubanListSpider(scrapy.Spider):
    name = "douban_list"
    allowed_domains = ["book.douban.com", "douban.com"]
    start_urls = ["https://book.douban.com/top250?start=0"]

    def parse(self, response):
        """Parse a list page: extract books then follow next pagination."""
        items = parse_list_items(response)

        for item_dict in items:
            book = DoubanBookItem()
            detail_url = response.urljoin(item_dict.get("detail_url", ""))
            book["url"] = detail_url
            book["title"] = item_dict.get("title")
            book["rating"] = item_dict.get("rating_avg")
            # Fields to be enriched by detail spider
            book["authors"] = None
            book["publisher"] = None
            book["pubdate"] = None
            book["price"] = None
            book["votes"] = None
            yield book

        yield from self._follow_next(response)

    def _follow_next(self, response):
        """Yield a Request for the next list page, or nothing if none found."""
        next_url = None

        # 1. <link rel="next"> in <head>
        next_url = response.css('link[rel="next"]::attr(href)').get()

        # 2. Paginator "后页>" link
        if not next_url:
            next_url = response.css(".paginator .next a::attr(href)").get()

        # 3. Any paginator link whose start offset exceeds the current one
        if not next_url:
            m = re.search(r"[?&]start=(\d+)", response.url)
            current_start = int(m.group(1)) if m else 0
            for href in response.css(".paginator a::attr(href)").getall():
                m2 = re.search(r"[?&]start=(\d+)", href)
                if m2 and int(m2.group(1)) > current_start:
                    next_url = href
                    break

        if not next_url:
            return

        next_url = response.urljoin(next_url)
        yield scrapy.Request(
            url=next_url,
            callback=self.parse,
            meta=self._request_meta(),
        )

    def _request_meta(self):
        """Request metadata; Playwright enabled only when setting says so."""
        if USE_PLAYWRIGHT:
            return {"playwright": True}
        return {}
