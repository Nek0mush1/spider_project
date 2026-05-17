import scrapy

from douban_books.db import fetch_reviewer_urls
from douban_books.items import UserProfileItem
from douban_books.parsers import parse_user_profile
from douban_books.settings import USE_PLAYWRIGHT


class DoubanUserSpider(scrapy.Spider):
    name = "douban_user"
    allowed_domains = ["douban.com", "www.douban.com"]

    custom_settings = {
        "CONCURRENT_REQUESTS": 2,
        "DOWNLOAD_DELAY": 5.0,
    }

    def start_requests(self):
        for reviewer_url in fetch_reviewer_urls():
            meta = {}
            if USE_PLAYWRIGHT:
                meta["playwright"] = True
            yield scrapy.Request(reviewer_url, callback=self.parse, meta=meta)

    def parse(self, response):
        payload = parse_user_profile(response)
        item = UserProfileItem()
        for key, value in payload.items():
            item[key] = value
        yield item
