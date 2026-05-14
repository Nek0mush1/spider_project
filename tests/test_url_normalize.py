import pytest, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from scrapy.http import HtmlResponse, Request
from dangdang_scrapy.spiders.dangdang import _normalize_url


def _resp(url="http://category.dangdang.com/cp01.01.02.00.00.00.html"):
    return HtmlResponse(url=url, body=b"", request=Request(url=url))


@pytest.mark.parametrize("raw,expected", [
    ("//product.dangdang.com/29680848.html", "http://product.dangdang.com/29680848.html"),
    ("//product.dangdang.com/29680848.html?foo=1#bar", "http://product.dangdang.com/29680848.html"),
    ("http://product.dangdang.com/29680848.html", "http://product.dangdang.com/29680848.html"),
    (None, None),
    ("", None),
    ("javascript:;", None),
    ("javascript:void(0)", None),
    ("mailto:test@example.com", None),
    ("#", None),
])
def test_normalize_url_valid(raw, expected):
    assert _normalize_url(raw, _resp()) == expected


@pytest.mark.parametrize("raw", [
    "//a.dangdang.com/jump.php?q=abc123",
    "http://a.dangdang.com/jump.php?q=abc123",
    "//img3.ddimg.cn/upload_img/00782/home/ic_close.png",
])
def test_normalize_url_rejects_non_product(raw):
    assert _normalize_url(raw, _resp()) is None
