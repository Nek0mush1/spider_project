from pathlib import Path

import scrapy
from scrapy.http import HtmlResponse, Request

from douban_books.spiders.douban_rating_dist import DoubanRatingDistributionSpider
from douban_books.spiders.douban_reviews import DoubanReviewsSpider
from douban_books.spiders.douban_user import DoubanUserSpider


FIXTURES = Path(__file__).parent / "fixtures"


def _response(path: str, url: str, request: Request | None = None) -> HtmlResponse:
    body = (FIXTURES / path).read_bytes()
    if request is None:
        request = Request(url=url)
    return HtmlResponse(url=url, body=body, encoding="utf-8", request=request)


def test_reviews_spider_parse_page_yields_items_and_next_request():
    spider = DoubanReviewsSpider()
    request = Request(
        url="https://book.douban.com/subject/1007305/reviews",
        meta={
            "book_url": "https://book.douban.com/subject/1007305/",
            "remaining": 20,
        },
    )
    response = _response(
        "reviews_page.html",
        "https://book.douban.com/subject/1007305/reviews",
        request=request,
    )

    results = list(spider.parse(response))

    items = [item for item in results if isinstance(item, scrapy.Item)]
    requests = [item for item in results if isinstance(item, scrapy.Request)]

    assert len(items) == 2
    assert len(requests) == 1
    assert requests[0].meta["remaining"] == 18


def test_rating_distribution_spider_parse_yields_book_and_distribution():
    spider = DoubanRatingDistributionSpider()
    spider.get_review_ratings = lambda book_url: [{"rating": 5}, {"rating": 4}]
    request = Request(
        url="https://book.douban.com/subject/1007305/",
        meta={"book_url": "https://book.douban.com/subject/1007305/"},
    )
    response = _response(
        "detail_advanced.html",
        "https://book.douban.com/subject/1007305/",
        request=request,
    )

    results = list(spider.parse(response))

    assert len(results) == 3
    distribution = next(item for item in results if item.get("source") == "official")
    derived = next(item for item in results if item.get("source") == "derived")
    book = next(item for item in results if item.get("url"))

    assert distribution["book_url"] == "https://book.douban.com/subject/1007305/"
    assert distribution["star_5_pct"] == 50.0
    assert derived["sample_size"] == 2
    assert book["want_to_read"] == 12345
    assert book["reading"] == 678
    assert book["read"] == 9012


def test_user_spider_parse_yields_profile_item():
    spider = DoubanUserSpider()
    response = _response(
        "user_profile.html",
        "https://www.douban.com/people/reviewer-a/",
    )

    results = list(spider.parse(response))

    assert len(results) == 1
    item = results[0]
    assert item["reviewer_url"] == "https://www.douban.com/people/reviewer-a/"
    assert item["following_count"] == 42
    assert item["followers_count"] == 128
