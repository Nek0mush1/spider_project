import scrapy
from scrapy_splash import SplashRequest
from dangdang_scrapy.items import BookItem

LUA_SCRIPT = """
function main(splash, args)
    assert(splash:go(args.url))
    assert(splash:wait(args.wait or 2))
    return splash:html()
end
"""


class DangdangSpider(scrapy.Spider):
    name = "dangdang"
    allowed_domains = [
        "category.dangdang.com", "dangdang.com",
        "product.dangdang.com", "127.0.0.1",
    ]

    start_urls = [
        "http://category.dangdang.com/cp01.01.02.00.00.00.html",
        "http://category.dangdang.com/cp01.01.03.00.00.00.html",
        "http://category.dangdang.com/cp01.01.04.00.00.00.html",
        "http://category.dangdang.com/cp01.01.05.00.00.00.html",
        "http://category.dangdang.com/cp01.01.01.00.00.00.html",
    ]

    custom_settings = {
        "CONCURRENT_REQUESTS": 3,
        "DOWNLOAD_DELAY": 2.5,
    }

    def start_requests(self):
        for url in self.start_urls:
            yield SplashRequest(
                url=url, callback=self.parse,
                args={"wait": 3, "lua_source": LUA_SCRIPT},
                endpoint="execute",
                meta={"category": "图书"},
            )

    def parse(self, response):
        category = response.meta.get("category", "图书")
        books = response.css("ul.bigimg li")
        self.logger.info(f"Found {len(books)} books on {response.url}")

        for book in books:
            item = BookItem()

            item["name"] = book.css("a.pic::attr(title)").get()

            raw_url = book.css("a.pic::attr(href)").get()
            if raw_url:
                if raw_url.startswith("//"):
                    item["detail_url"] = "http:" + raw_url
                else:
                    item["detail_url"] = response.urljoin(raw_url)

            item["author"] = book.css(
                "p.search_book_author a[name='itemlist-author']::text"
            ).get("").strip()

            item["publisher"] = book.css(
                "p.search_book_author a[name='P_cbs']::text"
            ).get("").strip()

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

        next_page = response.css("a:contains('下一页')::attr(href)").get()
        if next_page and next_page != "javascript:;":
            next_url = response.urljoin(next_page)
            self.logger.info(f"Following next page: {next_url}")
            yield SplashRequest(
                url=next_url, callback=self.parse,
                args={"wait": 3, "lua_source": LUA_SCRIPT},
                endpoint="execute",
                meta={"category": category},
            )
