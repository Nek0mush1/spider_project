import random
from scrapy.downloadermiddlewares.useragent import UserAgentMiddleware


class RandomUserAgentMiddleware(UserAgentMiddleware):
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:126.0) Gecko/20100101 Firefox/126.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Safari/605.1.15",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36 Edg/125.0.0.0",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    ]

    def process_request(self, request, spider):
        request.headers["User-Agent"] = random.choice(self.user_agents)


class SplashRoundRobinMiddleware:
    instances = [
        "http://127.0.0.1:8051",
        "http://127.0.0.1:8052",
        "http://127.0.0.1:8053",
    ]
    counter = 0

    @classmethod
    def from_crawler(cls, crawler):
        m = cls()
        urls = crawler.settings.getlist("SPLASH_URLS")
        if urls:
            m.instances = urls
        return m

    def process_request(self, request, spider):
        if "splash" in request.meta:
            idx = self.counter % len(self.instances)
            self.counter += 1
            endpoint = self.instances[idx]
            request.meta["splash"]["endpoint"] = endpoint + "/execute"
