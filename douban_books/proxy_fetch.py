from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlparse


USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36"
)

DEFAULT_HEADERS = [
    "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language: zh-CN,zh;q=0.9,en;q=0.8",
    "Cache-Control: no-cache",
    "Pragma: no-cache",
    "Sec-Fetch-Dest: document",
    "Sec-Fetch-Mode: navigate",
    "Sec-Fetch-Site: same-origin",
    "Sec-Fetch-User: ?1",
    "Upgrade-Insecure-Requests: 1",
]


class CurlFetchError(RuntimeError):
    """Raised when proxy curl fetching is blocked or malformed."""


@dataclass(slots=True)
class CurlFetchResult:
    status_code: int
    final_url: str
    body: str


@dataclass(slots=True)
class ProxyConfig:
    scheme: str
    username: str
    password: str
    hostport: str


def parse_proxy_url(proxy_url: str) -> ProxyConfig:
    parsed = urlparse(proxy_url)
    if not parsed.scheme or not parsed.hostname or parsed.port is None:
        raise CurlFetchError(f"invalid proxy url: {proxy_url}")
    if parsed.username is None or parsed.password is None:
        raise CurlFetchError(f"proxy credentials missing in: {proxy_url}")
    return ProxyConfig(
        scheme=parsed.scheme,
        username=parsed.username,
        password=parsed.password,
        hostport=f"{parsed.hostname}:{parsed.port}",
    )


def expand_proxy_candidates(single_url: str, pool: str, ports: str) -> list[str]:
    candidates: list[str] = []
    for raw in pool.split(","):
        value = raw.strip()
        if value:
            candidates.append(value)

    single = single_url.strip()
    if single:
        candidates.append(single)
        if ports.strip():
            base = parse_proxy_url(single)
            for raw_port in ports.split(","):
                port = raw_port.strip()
                if not port:
                    continue
                candidates.append(
                    f"{base.scheme}://{base.username}:{base.password}@"
                    f"{base.hostport.split(':', 1)[0]}:{port}"
                )

    deduped: list[str] = []
    seen: set[str] = set()
    for value in candidates:
        if value not in seen:
            deduped.append(value)
            seen.add(value)
    return deduped


def build_curl_command(url: str, proxy_url: str, referer: str, timeout: int = 25) -> list[str]:
    proxy = parse_proxy_url(proxy_url)
    return [
        "curl",
        "--silent",
        "--show-error",
        "--location",
        "--max-time",
        str(timeout),
        "-x",
        f"{proxy.scheme}://{proxy.hostport}",
        "-U",
        f"{proxy.username}:{proxy.password}",
        "--user-agent",
        USER_AGENT,
        *sum([["--header", header] for header in DEFAULT_HEADERS], []),
        "--referer",
        referer,
        "--write-out",
        "\nCURLMETA:%{http_code} %{url_effective}\n",
        url,
    ]


def parse_curl_output(stdout: str) -> CurlFetchResult:
    marker = "\nCURLMETA:"
    if marker not in stdout:
        raise CurlFetchError("curl output missing CURLMETA marker")

    body, meta = stdout.rsplit(marker, 1)
    meta = meta.strip()
    parts = meta.split(" ", 1)
    if len(parts) != 2:
        raise CurlFetchError(f"invalid curl metadata line: {meta}")

    status_raw, final_url = parts
    return CurlFetchResult(
        status_code=int(status_raw),
        final_url=final_url.strip(),
        body=body.rstrip(),
    )


def raise_for_blocked_response(result: CurlFetchResult, source_url: str) -> None:
    final_url = result.final_url.lower()
    body = result.body.lower()
    if "sec.douban.com" in final_url:
        raise CurlFetchError(
            f"blocked by douban security redirect for {source_url}: {result.final_url}"
        )
    if result.status_code >= 400:
        raise CurlFetchError(
            f"unexpected status {result.status_code} for {source_url}: {result.final_url}"
        )
    if "登录跳转页" in result.body or "sec.douban.com" in body:
        raise CurlFetchError(
            f"blocked content returned for {source_url}: {result.final_url}"
        )
