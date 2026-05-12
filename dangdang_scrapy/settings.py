BOT_NAME = "dangdang_scrapy"

SPIDER_MODULES = ["dangdang_scrapy.spiders"]
NEWSPIDER_MODULE = "dangdang_scrapy.spiders"

ROBOTSTXT_OBEY = False

SPLASH_URL = "http://127.0.0.1:8050"

DUPEFILTER_CLASS = "scrapy_splash.SplashAwareDupeFilter"
HTTPCACHE_STORAGE = "scrapy_splash.SplashAwareFSCacheStorage"

SPLASH_COOKIES_DEBUG = False

HTTPCACHE_ENABLED = True
HTTPCACHE_EXPIRATION_SECS = 3600

DOWNLOAD_TIMEOUT = 60
RETRY_TIMES = 3
RETRY_HTTP_CODES = [504, 502, 500, 403, 429]

SCHEDULER_PERSIST = True

DOWNLOADER_MIDDLEWARES = {
    "scrapy_splash.SplashCookiesMiddleware": 723,
    "scrapy_splash.SplashMiddleware": 725,
    "scrapy.downloadermiddlewares.httpcompression.HttpCompressionMiddleware": 810,
    "dangdang_scrapy.middlewares.RandomUserAgentMiddleware": 400,
}

SPIDER_MIDDLEWARES = {
    "scrapy_splash.SplashDeduplicateArgsMiddleware": 100,
}

ITEM_PIPELINES = {
    "dangdang_scrapy.pipelines.BookCleaningPipeline": 200,
    "dangdang_scrapy.pipelines.MySQLPipeline": 300,
}

CONCURRENT_REQUESTS = 4
CONCURRENT_REQUESTS_PER_DOMAIN = 2
DOWNLOAD_DELAY = 2.0
RANDOMIZE_DOWNLOAD_DELAY = True

AUTOTHROTTLE_ENABLED = True
AUTOTHROTTLE_START_DELAY = 2.0
AUTOTHROTTLE_MAX_DELAY = 10.0
AUTOTHROTTLE_TARGET_CONCURRENCY = 1.0

COOKIES_ENABLED = True

DEFAULT_REQUEST_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
}

FEED_EXPORT_ENCODING = "utf-8"
FEED_EXPORT_INDENT = 2

MYSQL_HOST = "172.27.80.1"
MYSQL_PORT = 3306
MYSQL_USER = "root"
MYSQL_PASSWORD = "su_yuan19820409"
MYSQL_DATABASE = "dangdang_books"
