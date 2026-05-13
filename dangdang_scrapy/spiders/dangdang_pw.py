import scrapy
from dangdang_scrapy.items import BookItem

LUA_SCRIPT = """
function main(splash, args)
    assert(splash:go(args.url))
    assert(splash:wait(args.wait or 2))
    return splash:html()
end
"""


class DangdangPlaywrightSpider(scrapy.Spider):
    name = "dangdang_pw"
    allowed_domains = ["category.dangdang.com", "dangdang.com", "product.dangdang.com"]

    start_urls = ["http://category.dangdang.com/cp01.01.02.00.00.00.html"]

    custom_settings = {
        "CONCURRENT_REQUESTS": 3,
        "DOWNLOAD_DELAY": 2.5,
        "DOWNLOAD_HANDLERS": {
            "http": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
            "https": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
        },
        "TWISTED_REACTOR": "twisted.internet.asyncioreactor.AsyncioSelectorReactor",
        "PLAYWRIGHT_LAUNCH_OPTIONS": {
            "headless": True,
            "timeout": 30000,
        },
        "PLAYWRIGHT_DEFAULT_NAVIGATION_TIMEOUT": 30000,
        "RETRY_TIMES": 2,
        "RETRY_HTTP_CODES": [504, 502, 500, 403],
        "ROBOTSTXT_OBEY": False,
        "DUPEFILTER_CLASS": "scrapy.dupefilters.BaseDupeFilter",
        "ITEM_PIPELINES": {
            "dangdang_scrapy.pipelines.BookCleaningPipeline": 200,
            "dangdang_scrapy.pipelines.MySQLPipeline": 300,
        },
    }

    def start_requests(self):
        for url in self.start_urls:
            yield scrapy.Request(
                url=url,
                callback=self.parse,
                meta={"playwright": True, "playwright_include_page": False},
            )

    def parse(self, response):
        category = "图书"
        books = response.css("ul.bigimg li")
        self.logger.info(f"[Playwright] {len(books)} books on {response.url}")

        for book in books:
            item = BookItem()
            item["name"] = book.css("a.pic::attr(title)").get()
            raw_url = book.css("a.pic::attr(href)").get()
            if raw_url:
                item["detail_url"] = ("http:" + raw_url) if raw_url.startswith("//") else response.urljoin(raw_url)
            item["author"] = book.css("p.search_book_author a[name='itemlist-author']::text").get("").strip()
            item["publisher"] = book.css("p.search_book_author a[name='P_cbs']::text").get("").strip()
            price_text = book.css("span.search_now_price::text").get()
            item["price"] = price_text.strip() if price_text else None
            orig_text = book.css("span.search_pre_price::text").get()
            item["original_price"] = orig_text.strip() if orig_text else None
            rating_style = book.css("span.search_star_black span::attr(style)").get()
            item["rating"] = rating_style
            comment_text = book.css("a.search_comment_num::text").re_first(r"(\d+)")
            item["rating_people"] = int(comment_text) if comment_text else None
            item["sales"] = None
            item["category"] = category
            yield item

        next_page = response.css("a:contains('\u4e0b\u4e00\u9875')::attr(href)").get()
        if next_page and next_page != "javascript:;":
            next_url = response.urljoin(next_page)
            self.logger.info(f"[Playwright] Following next page: {next_url}")
            yield scrapy.Request(
                url=next_url,
                callback=self.parse,
                meta={"playwright": True, "playwright_include_page": False},
            )
