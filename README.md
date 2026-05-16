# 豆瓣读书 TOP250 元数据爬虫

基于 Scrapy 的豆瓣读书 TOP250 元数据采集项目，支持列表页抓取、详情页补抓、数据清洗、入库和 CSV 导出。默认走原生 HTTP，必要时可切换 Playwright。

## 技术栈

- Scrapy
- Playwright, 可选
- PostgreSQL
- pytest

## 目录结构

```text
douban_books/
├── docker-compose.yml
├── Makefile
├── requirements.txt
├── .env.example
├── data/
├── scripts/
├── tests/
├── scrapy.cfg
└── douban_books/
    ├── settings.py
    ├── items.py
    ├── pipelines.py
    ├── db.py
    └── spiders/
        ├── douban_list.py
        └── douban_detail.py
```

## 快速开始

### 1) 创建 conda 环境

```bash
conda create -n douban_books python=3.13 -y
conda activate douban_books
```

### 2) 安装依赖

```bash
pip install -r requirements.txt
playwright install chromium
```

### 3) 启动数据库

```bash
docker compose up -d
```

### 4) 常用命令

```bash
make setup
make crawl
make detail
make export
make quality
make verify-fast
make test-full
```

## 环境变量

- `DATABASE_URL`，生产或本地入库连接串
- `DOUBAN_USE_PLAYWRIGHT`，`true` 时启用 Playwright
- `TEST_DATABASE_URL`，测试库连接串，需用于 `_test` 库

示例：

```bash
DATABASE_URL=postgresql+psycopg2://douban:douban@localhost:5434/douban_books
DOUBAN_USE_PLAYWRIGHT=false
TEST_DATABASE_URL=postgresql+psycopg2://douban:douban@localhost:5434/douban_books_test
```

## 数据流

```text
列表爬虫 -> 详情爬虫 -> Pipeline -> PostgreSQL -> CSV
```

## 字段说明

精简为 8 个字段（url 为唯一键）：

`url`, `title`, `authors`, `publisher`, `pubdate`, `price`, `rating`, `votes`

## 反爬策略

- `ROBOTSTXT_OBEY = True`
- `COOKIES_ENABLED = False`
- `DOWNLOAD_DELAY = 3s`
- `AUTOTHROTTLE_ENABLED = True`

## 与 dangdang_scrapy 的主要差异

- 数据库端口改为 `5434`
- 不采集 `cover_url`
- 更严格的礼貌性策略，延迟更大，自动限速更保守

## 常用命令说明

- `make setup`，检查 conda 环境并启动 PostgreSQL
- `make crawl`，抓取 TOP250 列表页
- `make detail`，补抓详情页
- `make export`，导出 CSV
- `make quality`，执行数据质量检查
- `make verify-fast`，单元测试 + 导出 + 质量检查
- `make test-full`，使用 `TEST_DATABASE_URL` 跑完整集成测试
