from __future__ import annotations

import argparse
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import pandas as pd
from scrapy.http import HtmlResponse, Request

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from douban_books.db import (
    fetch_pending_rating_urls,
    fetch_pending_review_targets,
    fetch_reviewer_urls,
    fetch_reviews_for_book,
    get_engine,
    init_db,
    upsert_books,
    upsert_rating_distributions,
    upsert_reviews,
    upsert_skipped_reviewers,
    upsert_user_profiles,
)
from douban_books.parsers import (
    build_derived_rating_distribution,
    parse_official_rating_distribution,
    parse_reading_state,
    parse_review_entries,
    parse_user_profile,
)
from douban_books.proxy_fetch import (
    CurlFetchError,
    build_curl_command,
    expand_proxy_candidates,
    parse_curl_output,
    raise_for_blocked_response,
)

VALID_STAGES = ("reviews", "ratings", "users")
DEFAULT_USER_CONCURRENCY = 3
DEFAULT_USER_TIMEOUT = 10
DEFAULT_USER_MIN_REVIEW_COUNT = 2
DEFAULT_USER_MAX_PROXY_ATTEMPTS = 2


def get_proxy_candidates() -> list[str]:
    single = os.environ.get("DOUBAN_PROXY_URL", "").strip()
    pool = os.environ.get("DOUBAN_PROXY_POOL", "").strip()
    ports = os.environ.get("DOUBAN_PROXY_PORTS", "").strip()
    candidates = expand_proxy_candidates(single_url=single, pool=pool, ports=ports)
    if not candidates:
        raise RuntimeError("未配置任何可用代理")
    return candidates


def fetch_html(
    url: str,
    referer: str,
    timeout: int = 25,
    max_proxy_attempts: int | None = None,
) -> str:
    last_error: Exception | None = None
    for index, proxy_url in enumerate(get_proxy_candidates(), start=1):
        if max_proxy_attempts is not None and index > max_proxy_attempts:
            break
        command = build_curl_command(url=url, proxy_url=proxy_url, referer=referer, timeout=timeout)
        completed = subprocess.run(command, check=False, capture_output=True, text=True)
        if completed.returncode != 0:
            last_error = RuntimeError(completed.stderr.strip() or f"curl failed for {url} via {proxy_url}")
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


def make_response(url: str, html: str, referer: str) -> HtmlResponse:
    request = Request(
        url=url,
        headers={b"Referer": referer.encode("utf-8")},
    )
    return HtmlResponse(url=url, body=html.encode("utf-8"), encoding="utf-8", request=request)


def parse_stage_names(raw: str | None) -> tuple[str, ...]:
    if not raw:
        return VALID_STAGES
    requested = {part.strip().lower() for part in raw.split(",") if part.strip()}
    normalized = tuple(stage for stage in VALID_STAGES if stage in requested)
    return normalized or VALID_STAGES


def select_book_targets(
    targets: list[tuple[str, int]],
    requested_urls: set[str] | None = None,
) -> list[tuple[str, int]]:
    if not requested_urls:
        return targets
    return [target for target in targets if target[0] in requested_urls]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Backfill advanced Douban data via proxy curl")
    parser.add_argument(
        "--book-url",
        action="append",
        dest="book_urls",
        default=[],
        help="Limit processing to one or more Douban subject URLs",
    )
    parser.add_argument(
        "--stages",
        default="reviews,ratings,users",
        help="Comma-separated subset of stages: reviews,ratings,users",
    )
    parser.add_argument(
        "--user-limit",
        type=int,
        default=None,
        help="Optional cap for user profile backfill",
    )
    parser.add_argument(
        "--user-concurrency",
        type=int,
        default=DEFAULT_USER_CONCURRENCY,
        help="Small parallelism for user profile backfill",
    )
    parser.add_argument(
        "--user-timeout",
        type=int,
        default=DEFAULT_USER_TIMEOUT,
        help="Per-request timeout in seconds for user profile fetches",
    )
    parser.add_argument(
        "--user-min-review-count",
        type=int,
        default=DEFAULT_USER_MIN_REVIEW_COUNT,
        help="Only crawl reviewers who appear at least this many times in reviews",
    )
    parser.add_argument(
        "--user-max-proxy-attempts",
        type=int,
        default=DEFAULT_USER_MAX_PROXY_ATTEMPTS,
        help="Maximum proxy candidates to try per user profile request",
    )
    return parser.parse_args()


def should_skip_user_fetch_error(exc: Exception) -> bool:
    message = str(exc)
    return "unexpected status 404" in message and "/people/" in message


def should_record_user_skip(exc: Exception) -> str | None:
    if should_skip_user_fetch_error(exc):
        return "http_404"
    return None


def backfill_reviews(book_urls: set[str] | None = None) -> int:
    targets = select_book_targets(
        fetch_pending_review_targets(limit_per_book=20),
        requested_urls=book_urls,
    )
    total_written = 0
    for book_url, remaining in targets:
        if remaining <= 0:
            continue
        next_url = book_url.rstrip("/") + "/reviews"
        left = remaining
        fetched_count = 0
        payloads: list[dict] = []
        while next_url and left > 0:
            html = fetch_html(next_url, referer="https://book.douban.com/")
            response = make_response(next_url, html, referer="https://book.douban.com/")
            reviews, next_url = parse_review_entries(response, book_url=book_url, limit=left)
            payloads.extend(reviews)
            left -= len(reviews)
            fetched_count += len(reviews)
            if len(reviews) == 0:
                break
        print(f"[reviews] book={book_url} fetched={fetched_count} remaining={left}")
        if payloads:
            df = pd.DataFrame(payloads).drop_duplicates(subset=["review_url"]).dropna(subset=["review_url"])
            total_written += upsert_reviews(df)
    return total_written


def backfill_ratings(book_urls: set[str] | None = None) -> tuple[int, int]:
    targets = fetch_pending_rating_urls()
    if book_urls:
        targets = [book_url for book_url in targets if book_url in book_urls]

    ratings_written = 0
    books_written = 0
    for book_url in targets:
        html = fetch_html(book_url, referer="https://book.douban.com/")
        response = make_response(book_url, html, referer="https://book.douban.com/")
        distribution = parse_official_rating_distribution(response)
        reading_state = parse_reading_state(response)
        books_df = pd.DataFrame(
            [
                {
                    "url": book_url,
                    "want_to_read": reading_state["want_to_read"],
                    "reading": reading_state["reading"],
                    "read": reading_state["read"],
                }
            ]
        ).drop_duplicates(subset=["url"]).dropna(subset=["url"])
        books_written += upsert_books(books_df)

        official_df = pd.DataFrame(
            [
                {
                    "book_url": book_url,
                    "source": "official",
                    "sample_size": None,
                    "star_5_count": None,
                    "star_4_count": None,
                    "star_3_count": None,
                    "star_2_count": None,
                    "star_1_count": None,
                    **distribution,
                    **reading_state,
                }
            ]
        ).drop_duplicates(subset=["book_url", "source"])
        ratings_written += upsert_rating_distributions(official_df)

        derived = build_derived_rating_distribution(fetch_reviews_for_book(book_url))
        derived_df = pd.DataFrame(
            [
                {
                    "book_url": book_url,
                    "source": "derived",
                    **derived,
                    **reading_state,
                }
            ]
        ).drop_duplicates(subset=["book_url", "source"])
        ratings_written += upsert_rating_distributions(derived_df)
        print(
            f"[ratings] book={book_url} official5={distribution['star_5_pct']} "
            f"derived_sample={derived['sample_size']} read={reading_state['read']}"
        )
    return ratings_written, books_written


def _fetch_one_user_profile(
    reviewer_url: str,
    timeout: int,
    max_proxy_attempts: int,
) -> tuple[str, dict | None]:
    try:
        html = fetch_html(
            reviewer_url,
            referer="https://book.douban.com/",
            timeout=timeout,
            max_proxy_attempts=max_proxy_attempts,
        )
    except Exception as exc:
        reason = should_record_user_skip(exc)
        if reason is not None:
            upsert_skipped_reviewers(
                pd.DataFrame(
                    [
                        {
                            "reviewer_url": reviewer_url,
                            "reason": reason,
                        }
                    ]
                )
            )
            return reviewer_url, None
        raise
    response = make_response(reviewer_url, html, referer="https://book.douban.com/")
    return reviewer_url, parse_user_profile(response)


def backfill_users(
    limit: int | None = None,
    concurrency: int = DEFAULT_USER_CONCURRENCY,
    timeout: int = DEFAULT_USER_TIMEOUT,
    min_review_count: int = DEFAULT_USER_MIN_REVIEW_COUNT,
    max_proxy_attempts: int = DEFAULT_USER_MAX_PROXY_ATTEMPTS,
) -> int:
    urls = fetch_reviewer_urls(limit=limit, min_review_count=min_review_count)
    total_written = 0
    if not urls:
        return 0

    with ThreadPoolExecutor(max_workers=max(1, concurrency)) as executor:
        futures = {
            executor.submit(
                _fetch_one_user_profile,
                reviewer_url,
                timeout,
                max_proxy_attempts,
            ): reviewer_url
            for reviewer_url in urls
        }
        for future in as_completed(futures):
            reviewer_url = futures[future]
            reviewer_url, payload = future.result()
            if payload is None:
                print(f"[users] skip_404 reviewer={reviewer_url}", flush=True)
                continue
            df = pd.DataFrame([payload]).drop_duplicates(subset=["reviewer_url"]).dropna(subset=["reviewer_url"])
            written = upsert_user_profiles(df)
            total_written += written
            print(
                f"[users] reviewer={reviewer_url} written={written} "
                f"followers={payload.get('followers_count')} following={payload.get('following_count')}",
                flush=True,
            )
    return total_written


def main() -> None:
    args = parse_args()
    selected_stages = parse_stage_names(args.stages)
    book_urls = {url.strip() for url in args.book_urls if url.strip()} or None
    init_db()

    reviews_written = 0
    ratings_written = 0
    books_written = 0
    users_written = 0

    if "reviews" in selected_stages:
        reviews_written = backfill_reviews(book_urls=book_urls)
    if "ratings" in selected_stages:
        ratings_written, books_written = backfill_ratings(book_urls=book_urls)
    if "users" in selected_stages:
        users_written = backfill_users(
            limit=args.user_limit,
            concurrency=args.user_concurrency,
            timeout=args.user_timeout,
            min_review_count=args.user_min_review_count,
            max_proxy_attempts=args.user_max_proxy_attempts,
        )

    print(f"reviews_written={reviews_written}", flush=True)
    print(f"ratings_written={ratings_written}", flush=True)
    print(f"books_written={books_written}", flush=True)
    print(f"users_written={users_written}", flush=True)


if __name__ == "__main__":
    main()
