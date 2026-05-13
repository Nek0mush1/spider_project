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
        ("cp01.01.01.00.00.00.html", "标准"),
        ("cp01.01.02.00.00.00.html", "标准"),
        ("cp01.01.03.00.00.00.html", "标准"),
        ("cp01.01.04.00.00.00.html", "标准"),
        ("cp01.01.05.00.00.00.html", "标准"),
        ("cp01.02.01.00.00.00.html", "促销"),
        ("cp01.02.02.00.00.00.html", "促销"),
        ("cp01.02.03.00.00.00.html", "促销"),
        ("cp01.02.04.00.00.00.html", "促销"),
        ("cp01.02.05.00.00.00.html", "促销"),
        ("cp01.02.06.00.00.00.html", "促销"),
        ("cp01.02.07.00.00.00.html", "促销"),
        ("cp01.02.08.00.00.00.html", "促销"),
        ("cp01.02.09.00.00.00.html", "促销"),
        ("cp01.02.10.00.00.00.html", "促销"),
        ("cp01.03.01.00.00.00.html", "促销"),
        ("cp01.03.02.00.00.00.html", "促销"),
        ("cp01.03.04.00.00.00.html", "促销"),
        ("cp01.04.01.00.00.00.html", "促销"),
        ("cp01.04.02.00.00.00.html", "促销"),
        ("cp01.05.01.00.00.00.html", "促销"),
        ("cp01.07.01.00.00.00.html", "促销"),
    ]

    custom_settings = {
        "CONCURRENT_REQUESTS": 3,
        "DOWNLOAD_DELAY": 2.5,
    }

    def start_requests(self):
        for path, layout in self.start_urls:
            url = f"http://category.dangdang.com/{path}"
            cb = self.parse_standard if layout == "标准" else self.parse_promotional
            yield SplashRequest(
                url=url, callback=cb,
                args={"wait": 3, "lua_source": LUA_SCRIPT},
                endpoint="execute",
                meta={"category": "图书", "layout": layout},
            )

    def parse_standard(self, response):
        category = response.meta.get("category", "图书")
        books = response.css("ul.bigimg li")
        self.logger.info(f"[标准] {len(books)} books on {response.url}")

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

        self._follow_next(response, self.parse_standard, category)

    def parse_promotional(self, response):
        category = response.meta.get("category", "图书")
        books = response.css("div.cloth_good_sort li")
        self.logger.info(f"[促销] {len(books)} items on {response.url}")

        for book in books:
            item = BookItem()
            item["name"] = book.css("a.name::text").get("").strip() or None
            raw_url = book.css("a.pic::attr(href)").get()
            if raw_url:
                item["detail_url"] = ("http:" + raw_url) if raw_url.startswith("//") else response.urljoin(raw_url)
            item["author"] = ""
            item["publisher"] = ""
            price_raw = book.css("span.d_price::text").get()
            if price_raw:
                item["price"] = price_raw.replace("¥", "").strip()
            orig_els = book.css("p.price_p i.m_price")
            if len(orig_els) > 1:
                item["original_price"] = orig_els[-1].css("::text").get("").strip()
            item["rating"] = None
            item["rating_people"] = None
            item["sales"] = None
            item["category"] = category
            yield item

        self._follow_next(response, self.parse_promotional, category)

    def _follow_next(self, response, callback, category):
        next_page = response.css("a:contains('\u4e0b\u4e00\u9875')::attr(href)").get()
        if next_page and next_page != "javascript:;":
            next_url = response.urljoin(next_page)
            self.logger.info(f"Following next page: {next_url}")
            yield SplashRequest(
                url=next_url, callback=callback,
                args={"wait": 3, "lua_source": LUA_SCRIPT},
                endpoint="execute",
                meta={"category": category},
            )
