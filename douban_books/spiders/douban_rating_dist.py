import scrapy

from douban_books.db import fetch_pending_rating_urls, fetch_reviews_for_book
from douban_books.items import DoubanBookItem, RatingDistributionItem
from douban_books.parsers import (
    build_derived_rating_distribution,
    parse_official_rating_distribution,
    parse_reading_state,
)
from douban_books.settings import USE_PLAYWRIGHT


class DoubanRatingDistributionSpider(scrapy.Spider):
    name = "douban_rating_dist"
    allowed_domains = ["book.douban.com", "douban.com"]

    custom_settings = {
        "CONCURRENT_REQUESTS": 2,
        "DOWNLOAD_DELAY": 4.0,
    }

    def get_review_ratings(self, book_url):
        return fetch_reviews_for_book(book_url)

    def start_requests(self):
        for book_url in fetch_pending_rating_urls():
            meta = {"book_url": book_url}
            if USE_PLAYWRIGHT:
                meta["playwright"] = True
            yield scrapy.Request(book_url, callback=self.parse, meta=meta)

    def parse(self, response):
        book_url = response.meta["book_url"]
        distribution = parse_official_rating_distribution(response)
        reading_state = parse_reading_state(response)

        book = DoubanBookItem()
        book["url"] = book_url
        book["want_to_read"] = reading_state["want_to_read"]
        book["reading"] = reading_state["reading"]
        book["read"] = reading_state["read"]
        yield book

        dist_item = RatingDistributionItem()
        dist_item["book_url"] = book_url
        dist_item["source"] = "official"
        dist_item["sample_size"] = None
        dist_item["star_5_count"] = None
        dist_item["star_4_count"] = None
        dist_item["star_3_count"] = None
        dist_item["star_2_count"] = None
        dist_item["star_1_count"] = None
        for key, value in distribution.items():
            dist_item[key] = value
        dist_item["want_to_read"] = reading_state["want_to_read"]
        dist_item["reading"] = reading_state["reading"]
        dist_item["read"] = reading_state["read"]
        yield dist_item

        derived = build_derived_rating_distribution(self.get_review_ratings(book_url))
        derived_item = RatingDistributionItem()
        derived_item["book_url"] = book_url
        derived_item["source"] = "derived"
        for key, value in derived.items():
            derived_item[key] = value
        derived_item["want_to_read"] = reading_state["want_to_read"]
        derived_item["reading"] = reading_state["reading"]
        derived_item["read"] = reading_state["read"]
        yield derived_item
