import pytest, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from pathlib import Path
from scrapy.http import HtmlResponse, Request

FIXTURES = Path(__file__).parent / "fixtures"


def _make_response(name, url, meta=None):
    html = (FIXTURES / name).read_text(encoding="utf-8")
    req = Request(url=url, meta=meta or {})
    return HtmlResponse(url=url, body=html.encode(), request=req)


class TestStandardPageParsing:
    def test_book_count(self):
        from dangdang_scrapy.spiders.dangdang import DangdangSpider
        resp = _make_response("standard_page.html",
            "http://category.dangdang.com/cp01.01.02.00.00.00.html",
            {"category": "图书"})
        spider = DangdangSpider()
        items = list(spider._parse_standard_items(resp))
        assert len(items) == 60
        assert all(i["name"] for i in items)
        assert all(i["detail_url"] for i in items)

    def test_skips_tracking_links(self):
        from dangdang_scrapy.spiders.dangdang import DangdangSpider
        resp = _make_response("standard_page.html",
            "http://category.dangdang.com/cp01.01.02.00.00.00.html",
            {"category": "图书"})
        spider = DangdangSpider()
        items = list(spider._parse_standard_items(resp))
        # No jump.php links should survive
        assert not any("jump.php" in (i["detail_url"] or "") for i in items)

    def test_pagination_yielded(self):
        from dangdang_scrapy.spiders.dangdang import DangdangSpider
        resp = _make_response("standard_page.html",
            "http://category.dangdang.com/cp01.01.02.00.00.00.html",
            {"category": "图书"})
        spider = DangdangSpider()
        results = list(spider.parse_standard(resp))
        items = [r for r in results if hasattr(r, "fields")]
        requests = [r for r in results if hasattr(r, "url")]
        assert len(items) > 0
        assert len(requests) > 0  # yield from works


class TestPromoPageParsing:
    def test_book_count(self):
        from dangdang_scrapy.spiders.dangdang import DangdangSpider
        resp = _make_response("promo_page.html",
            "http://category.dangdang.com/cp01.02.01.00.00.00.html",
            {"category": "图书"})
        spider = DangdangSpider()
        items = list(spider._parse_promo_items(resp))
        assert len(items) > 50
        assert all(i["name"] for i in items)

    def test_skips_tracking_links(self):
        from dangdang_scrapy.spiders.dangdang import DangdangSpider
        resp = _make_response("promo_page.html",
            "http://category.dangdang.com/cp01.02.01.00.00.00.html",
            {"category": "图书"})
        spider = DangdangSpider()
        items = list(spider._parse_promo_items(resp))
        assert not any("jump.php" in (i["detail_url"] or "") for i in items)


class TestDetailPage:
    def test_rating_extraction(self):
        from dangdang_scrapy.parsers import parse_detail_rating
        html = (FIXTURES / "detail_with_rating.html").read_text(encoding="utf-8")
        rating, people = parse_detail_rating(html)
        assert rating is not None
        assert people is not None
        assert 0 <= rating <= 100

    def test_missing_rating_returns_none(self):
        from dangdang_scrapy.parsers import parse_detail_rating
        html = "<html><body>no rating info</body></html>"
        rating, people = parse_detail_rating(html)
        assert rating is None
        assert people is None
