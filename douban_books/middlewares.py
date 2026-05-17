import random
import os

from scrapy.downloadermiddlewares.useragent import UserAgentMiddleware


class RandomUserAgentMiddleware(UserAgentMiddleware):
    """每个请求随机选择一个现代浏览器User-Agent"""

    USER_AGENTS = [
        # Chrome on Windows 11
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        # Chrome on macOS
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        # Firefox on Windows
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:133.0) Gecko/20100101 Firefox/133.0",
        # Firefox on macOS
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 14.7; rv:133.0) Gecko/20100101 Firefox/133.0",
        # Edge on Windows
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.0",
        # Safari on macOS
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.2 Safari/605.1.15",
        # Chrome on Linux
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    ]

    def process_request(self, request, spider):
        ua = random.choice(self.USER_AGENTS)
        if ua:
            request.headers.setdefault("User-Agent", ua)


class RandomizedRequestMiddleware:
    """补充随机化请求头，降低固定模式特征。"""

    ACCEPT_LANGUAGES = [
        "zh-CN,zh;q=0.9,en;q=0.8",
        "zh-CN,zh;q=0.8,en-US;q=0.7,en;q=0.6",
    ]

    def process_request(self, request, spider):
        request.headers.setdefault(
            "Accept",
            "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        )
        request.headers.setdefault(
            "Accept-Language",
            random.choice(self.ACCEPT_LANGUAGES),
        )
        request.headers.setdefault("Cache-Control", "no-cache")
        request.headers.setdefault("Pragma", "no-cache")
        request.headers.setdefault("Sec-Fetch-Dest", "document")
        request.headers.setdefault("Sec-Fetch-Mode", "navigate")
        request.headers.setdefault("Sec-Fetch-Site", "same-site")
        request.headers.setdefault("Upgrade-Insecure-Requests", "1")
        request.headers.setdefault(
            "Referer",
            request.meta.get("referer_override", "https://book.douban.com/"),
        )


class ProxyRotationMiddleware:
    """按顺序轮转付费代理。"""

    def __init__(self):
        pool = os.environ.get("DOUBAN_PROXY_POOL", "").strip()
        single = os.environ.get("DOUBAN_PROXY_URL", "").strip()
        proxies = [p.strip() for p in pool.split(",") if p.strip()]
        if single:
            proxies.append(single)
        self.proxies = proxies
        self._index = 0

    def process_request(self, request, spider):
        if not self.proxies:
            return
        proxy = self.proxies[self._index % len(self.proxies)]
        self._index += 1
        request.meta["proxy"] = proxy
        request.meta["proxy_enabled"] = True


class AnonymousCookieSessionMiddleware:
    """使用匿名 cookiejar，并按请求数轮转会话。"""

    def __init__(self):
        self.max_requests = int(os.environ.get("DOUBAN_COOKIE_SESSION_MAX_REQUESTS", "20"))
        self._request_count = 0
        self._cookiejar_id = 0

    def process_request(self, request, spider):
        if self._request_count >= self.max_requests:
            self._cookiejar_id += 1
            self._request_count = 0
        request.meta["cookiejar"] = f"anon-{self._cookiejar_id}"
        request.meta["anonymous_session"] = True
        self._request_count += 1
