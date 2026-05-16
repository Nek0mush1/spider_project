import os
from dotenv import load_dotenv

load_dotenv()

BOT_NAME = "douban_books"
SPIDER_MODULES = ["douban_books.spiders"]
NEWSPIDER_MODULE = "douban_books.spiders"

# robots.txt 遵守（豆瓣专用，与dangdang_scrapy不同）
ROBOTSTXT_OBEY = True

# Cookie禁用（豆瓣使用Cookie绑定反爬，与dangdang_scrapy不同）
COOKIES_ENABLED = False

# 爬取礼貌性（豆瓣比当当更严格）
DOWNLOAD_DELAY = 3.0
RANDOMIZE_DOWNLOAD_DELAY = True
CONCURRENT_REQUESTS = 4
CONCURRENT_REQUESTS_PER_DOMAIN = 4

# 自动限速
AUTOTHROTTLE_ENABLED = True
AUTOTHROTTLE_START_DELAY = 3.0
AUTOTHROTTLE_MAX_DELAY = 60.0
AUTOTHROTTLE_TARGET_CONCURRENCY = 1.0

# 重试配置（包含豆瓣418/429/403）
RETRY_ENABLED = True
RETRY_TIMES = 5
RETRY_HTTP_CODES = [500, 502, 503, 504, 408, 429, 403, 418]

# Referer伪装（反检测）
REFERER_ENABLED = True

# 默认请求头（中文）
DEFAULT_REQUEST_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}

# 中间件
DOWNLOADER_MIDDLEWARES = {
    "douban_books.middlewares.RandomUserAgentMiddleware": 400,
}

# 管道（两阶段：清洗 → 数据库）
ITEM_PIPELINES = {
    "douban_books.pipelines.BookCleaningPipeline": 200,
    "douban_books.pipelines.DatabasePipeline": 300,
}

# Playwright双模式渲染（通过环境变量切换，与dangdang_scrapy模式一致）
USE_PLAYWRIGHT = os.environ.get("DOUBAN_USE_PLAYWRIGHT", "").lower() in ("1", "true")
if USE_PLAYWRIGHT:
    DOWNLOAD_HANDLERS = {
        "http": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
        "https": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
    }
    TWISTED_REACTOR = "twisted.internet.asyncioreactor.AsyncioSelectorReactor"
