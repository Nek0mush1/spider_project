from pathlib import Path

import pandas as pd
from scrapy.http import HtmlResponse, Request

from scripts.backfill_via_proxy import make_response
from douban_books.parsers import parse_detail, parse_list_items


FIXTURES = Path(__file__).parent / "fixtures"


def _fixture_text(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def test_make_response_keeps_url_and_referer():
    response = make_response(
        url="https://book.douban.com/top250?start=0",
        html="<html><body>ok</body></html>",
        referer="https://book.douban.com/",
    )

    assert response.url == "https://book.douban.com/top250?start=0"
    assert response.request.headers[b"Referer"] == b"https://book.douban.com/"


def test_list_fixture_can_be_turned_into_backfill_dataframe():
    response = make_response(
        url="https://book.douban.com/top250?start=0",
        html=_fixture_text("top250_page.html"),
        referer="https://book.douban.com/",
    )

    rows = [
        {
            "url": response.urljoin(item["detail_url"]),
            "title": item["title"],
            "rating": item["rating_avg"],
        }
        for item in parse_list_items(response)
    ]
    df = pd.DataFrame(rows)

    assert not df.empty
    assert "url" in df.columns
    assert df.iloc[0]["url"] == "https://book.douban.com/subject/1000005/"


def test_detail_fixture_still_parses_for_backfill():
    response = make_response(
        url="https://book.douban.com/subject/1000005/",
        html=_fixture_text("detail_page.html"),
        referer="https://book.douban.com/top250",
    )

    item = parse_detail(response)

    assert item["title"] == "百年孤独"
    assert item["authors"] == "加西亚·马尔克斯"
    assert item["votes"] == 280000
