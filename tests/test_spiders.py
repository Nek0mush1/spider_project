"""Spider tests — tightly scoped, no network requests. 8-column schema."""

from pathlib import Path

import scrapy
from scrapy.http import HtmlResponse

from douban_books.spiders.douban_detail import DoubanDetailSpider
from douban_books.spiders.douban_list import DoubanListSpider

# ---------------------------------------------------------------------------
# Fixture helper
# ---------------------------------------------------------------------------

FIXTURES = Path(__file__).parent / "fixtures"


def _make_response(path, url):
    """Load a fixture HTML file and wrap it in a Scrapy HtmlResponse."""
    body = (FIXTURES / path).read_bytes()
    return HtmlResponse(url=url, body=body, encoding="utf-8")


# ============================================================================
# List Spider — 3 tests
# ============================================================================


def test_list_spider_parse():
    """Parse top250_page.html → yields DoubanBookItem objects with 8-field data."""
    spider = DoubanListSpider()
    response = _make_response(
        "top250_page.html", "https://book.douban.com/top250?start=0"
    )
    results = list(spider.parse(response))

    # Separate items from any pagination Requests (fixture has no paginator, but be safe)
    items = [r for r in results if isinstance(r, scrapy.Item)]
    assert len(items) >= 2, f"Expected at least 2 items, got {len(items)}"

    first = items[0]
    assert first["url"] == "https://book.douban.com/subject/1000005/"
    assert "百年孤独" in first["title"]
    assert first["rating"] == 9.2
    # Fields not available from list page should be None
    assert first["authors"] is None
    assert first["publisher"] is None
    assert first["pubdate"] is None
    assert first["price"] is None
    assert first["votes"] is None


def test_list_spider_pagination():
    """Inline HTML with paginator .next link → _follow_next yields correct Request."""
    spider = DoubanListSpider()
    html = (
        "<html><body>"
        '<div class="paginator">'
        '<span class="next"><a href="?start=25">后页&gt;</a></span>'
        "</div>"
        "</body></html>"
    )
    response = HtmlResponse(
        url="https://book.douban.com/top250?start=0",
        body=html.encode(),
        encoding="utf-8",
    )
    results = list(spider._follow_next(response))

    assert len(results) == 1
    req = results[0]
    assert isinstance(req, scrapy.Request)
    assert "start=25" in req.url


def test_list_spider_no_next():
    """Response without any paginator → _follow_next yields nothing."""
    spider = DoubanListSpider()
    html = "<html><body><p>No paginator here.</p></body></html>"
    response = HtmlResponse(
        url="https://book.douban.com/top250?start=225",
        body=html.encode(),
        encoding="utf-8",
    )
    results = list(spider._follow_next(response))
    assert results == []


# ============================================================================
# Detail Spider — 2 tests
# ============================================================================


def test_detail_spider_parse():
    """Parse detail_page.html fixture → yields 8-field dict and increments counter."""
    spider = DoubanDetailSpider()
    response = _make_response(
        "detail_page.html", "https://book.douban.com/subject/1000005/"
    )

    assert spider.processed_count == 0
    results = list(spider.parse(response))

    assert len(results) == 1
    item = results[0]
    assert isinstance(item, dict)
    assert item["url"] == "https://book.douban.com/subject/1000005/"
    assert item["title"] == "百年孤独"
    assert item["authors"] == "加西亚·马尔克斯"
    assert item["publisher"] == "南海出版公司"
    assert item["pubdate"] == "2011-6"
    assert item["price"] == "39.50元"
    assert item["rating"] == 9.2
    assert item["votes"] == 280000
    assert spider.processed_count == 1


def test_detail_spider_error_handling():
    """on_error() increments http_errors using a lightweight fake failure object."""
    spider = DoubanDetailSpider()

    class FakeFailure:
        def __init__(self, url):
            self.request = type("FakeRequest", (), {"url": url})()
            self.value = Exception("Simulated connection error")

    assert spider.http_errors == 0

    spider.on_error(FakeFailure("https://book.douban.com/subject/9999999/"))
    assert spider.http_errors == 1

    spider.on_error(FakeFailure("https://book.douban.com/subject/8888888/"))
    assert spider.http_errors == 2
