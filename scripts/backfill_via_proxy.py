from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pandas as pd
from scrapy.http import HtmlResponse, Request
from sqlalchemy import text

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from douban_books.db import get_engine, init_db, upsert_books
from douban_books.parsers import parse_detail, parse_list_items
from douban_books.proxy_fetch import (
    CurlFetchError,
    build_curl_command,
    expand_proxy_candidates,
    parse_curl_output,
    raise_for_blocked_response,
)


LIST_STARTS = tuple(range(0, 250, 25))


def get_proxy_url() -> str:
    proxy_url = os.environ.get("DOUBAN_PROXY_URL", "").strip()
    if proxy_url:
        return proxy_url
    raise RuntimeError("DOUBAN_PROXY_URL 未设置")


def get_proxy_candidates() -> list[str]:
    single = os.environ.get("DOUBAN_PROXY_URL", "").strip()
    pool = os.environ.get("DOUBAN_PROXY_POOL", "").strip()
    ports = os.environ.get("DOUBAN_PROXY_PORTS", "").strip()
    if single.startswith("http://"):
        single = "https://" + single[len("http://") :]
    candidates = expand_proxy_candidates(
        single_url=single,
        pool=pool,
        ports=ports,
    )
    if not candidates:
        raise RuntimeError("未配置任何可用代理")
    return candidates


def fetch_html(url: str, referer: str) -> str:
    last_error: Exception | None = None
    for proxy_url in get_proxy_candidates():
        command = build_curl_command(
            url=url,
            proxy_url=proxy_url,
            referer=referer,
        )
        completed = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
        )
        if completed.returncode != 0:
            last_error = RuntimeError(
                completed.stderr.strip() or f"curl failed for {url} via {proxy_url}"
            )
            continue
        try:
            result = parse_curl_output(completed.stdout)
            raise_for_blocked_response(result, url)
        except CurlFetchError as exc:
            last_error = exc
            continue
        return result.body

    assert last_error is not None
    raise last_error


def make_response(url: str, html: str, referer: str | None = None) -> HtmlResponse:
    headers = {}
    if referer:
        headers[b"Referer"] = referer.encode("utf-8")
    request = Request(url=url, headers=headers)
    return HtmlResponse(url=url, body=html.encode("utf-8"), encoding="utf-8", request=request)


def backfill_list_pages() -> int:
    records: list[dict] = []
    for start in LIST_STARTS:
        url = f"https://book.douban.com/top250?start={start}"
        html = fetch_html(url, referer="https://book.douban.com/")
        response = make_response(url, html, referer="https://book.douban.com/")
        for item_dict in parse_list_items(response):
            records.append(
                {
                    "url": response.urljoin(item_dict.get("detail_url", "")),
                    "title": item_dict.get("title"),
                    "rating": item_dict.get("rating_avg"),
                }
            )

    if not records:
        return 0

    df = pd.DataFrame(records).drop_duplicates(subset=["url"]).dropna(subset=["url"])
    return upsert_books(df)


def fetch_pending_detail_urls(limit: int | None = None) -> list[str]:
    engine = get_engine()
    sql = """
        SELECT url FROM douban_books
        WHERE url IS NOT NULL
          AND (authors IS NULL OR publisher IS NULL OR pubdate IS NULL OR price IS NULL OR votes IS NULL)
        ORDER BY url
    """
    if limit is not None:
        sql += " LIMIT :limit"
    with engine.connect() as conn:
        if limit is None:
            rows = conn.execute(text(sql)).fetchall()
        else:
            rows = conn.execute(text(sql), {"limit": limit}).fetchall()
    return [row[0] for row in rows]


def backfill_detail_pages(limit: int | None = None) -> int:
    records: list[dict] = []
    for url in fetch_pending_detail_urls(limit=limit):
        html = fetch_html(url, referer="https://book.douban.com/top250")
        response = make_response(url, html, referer="https://book.douban.com/top250")
        records.append(parse_detail(response))

    if not records:
        return 0

    df = pd.DataFrame(records).drop_duplicates(subset=["url"]).dropna(subset=["url"])
    return upsert_books(df)


def main() -> None:
    init_db()
    list_written = backfill_list_pages()
    detail_written = backfill_detail_pages()
    print(f"list_rows_written={list_written}")
    print(f"detail_rows_written={detail_written}")


if __name__ == "__main__":
    main()
