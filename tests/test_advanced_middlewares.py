import os

from scrapy import Request

from douban_books.middlewares import (
    AnonymousCookieSessionMiddleware,
    ProxyRotationMiddleware,
    RandomizedRequestMiddleware,
)


class DummySpider:
    name = "dummy"


def test_proxy_rotation_uses_pool(monkeypatch):
    monkeypatch.setenv("DOUBAN_PROXY_POOL", "http://proxy-a,http://proxy-b")
    middleware = ProxyRotationMiddleware()

    request_one = Request("https://book.douban.com/subject/1007305/")
    request_two = Request("https://book.douban.com/subject/1007305/reviews")

    middleware.process_request(request_one, DummySpider())
    middleware.process_request(request_two, DummySpider())

    assert request_one.meta["proxy"] == "http://proxy-a"
    assert request_two.meta["proxy"] == "http://proxy-b"


def test_anonymous_cookie_session_rotates_cookiejar(monkeypatch):
    monkeypatch.setenv("DOUBAN_COOKIE_SESSION_MAX_REQUESTS", "1")
    middleware = AnonymousCookieSessionMiddleware()

    first = Request("https://book.douban.com/subject/1007305/")
    second = Request("https://book.douban.com/subject/1007305/reviews")

    middleware.process_request(first, DummySpider())
    middleware.process_request(second, DummySpider())

    assert first.meta["cookiejar"] != second.meta["cookiejar"]
    assert first.meta["anonymous_session"] is True
    assert second.meta["anonymous_session"] is True


def test_randomized_request_sets_headers():
    middleware = RandomizedRequestMiddleware()
    request = Request("https://book.douban.com/subject/1007305/")

    middleware.process_request(request, DummySpider())

    assert request.headers.get("Accept-Language")
    assert request.headers.get("Referer")
    assert request.headers.get("Sec-Fetch-Mode")
