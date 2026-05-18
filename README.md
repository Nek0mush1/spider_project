# 豆瓣读书 TOP250 爬虫与进阶数据回填

这是一个围绕豆瓣读书 Top250 构建的 Scrapy 项目，目标不是只抓书目基础字段，而是把书籍、长评、评分分布、阅读状态和部分用户画像落到 PostgreSQL，并支持 CSV 导出与质量检查。

当前这条分支已经不是“只跑列表页”的初版，而是两条链路并存：

- 基础链路：`Scrapy spiders -> pipeline -> PostgreSQL`
- 进阶链路：`proxy curl fetch -> parser -> DB upsert`

之所以保留第二条链路，是因为进阶页面在真实抓取中更容易受到反爬、跳转、代理协议和重试成本影响。对这部分，项目已经收敛到“先小批验证，再分阶段回填”的策略。

## 当前能力

已覆盖的数据层：

- `douban_books`
  - Top250 书籍基础信息
  - 阅读状态字段 `want_to_read / reading / read`
- `reviews`
  - 书评链接、标题、正文、评分、互动计数、评论者信息
- `rating_distributions`
  - 官方评分分布
  - 基于评论样本推导的评分分布
- `user_profiles`
  - 评论者主页的昵称、关注数、粉丝数
- `skipped_reviewer_urls`
  - 已确认无效或应跳过的评论者主页

截至 2026-05-18 的阶段性实库结果见 [`ADVANCED_CRAWLER_STAGE_REPORT_2026-05-18.md`](./ADVANCED_CRAWLER_STAGE_REPORT_2026-05-18.md)。

## 技术栈

- Python 3.11+
- Scrapy
- Playwright，可选
- PostgreSQL 16
- pandas
- SQLAlchemy
- pytest
- `curl`，用于代理回填脚本

## 项目结构

```text
douban_books/
├── README.md
├── Makefile
├── docker-compose.yml
├── requirements.txt
├── pyproject.toml
├── scrapy.cfg
├── data/
├── scripts/
│   ├── init_db.sql
│   ├── export_books.py
│   ├── export_reviews.py
│   ├── quality_checks.py
│   ├── backfill_via_proxy.py
│   ├── backfill_advanced_via_proxy.py
│   ├── playwright_probe.py
│   └── playwright_top250_probe.py
├── tests/
└── douban_books/
    ├── db.py
    ├── items.py
    ├── middlewares.py
    ├── parsers.py
    ├── pipelines.py
    ├── proxy_fetch.py
    ├── settings.py
    └── spiders/
        ├── douban_list.py
        ├── douban_detail.py
        ├── douban_reviews.py
        ├── douban_rating_dist.py
        └── douban_user.py
```

## 快速开始

### 1. 创建环境

```bash
conda create -n douban_books python=3.13 -y
conda activate douban_books
pip install -r requirements.txt
playwright install chromium
```

如果你只跑代理回填脚本而不使用 Playwright，最后一步可以暂时不执行。

### 2. 配置环境变量

复制 `.env.example`，至少补齐数据库连接。常用变量如下：

```bash
DATABASE_URL=postgresql+psycopg2://douban:douban@localhost:5434/douban_books
DOUBAN_USE_PLAYWRIGHT=false
DOUBAN_PLAYWRIGHT_HEADLESS=false

# 二选一：单个代理，或多个代理 URL 组成的池
DOUBAN_PROXY_URL=
DOUBAN_PROXY_POOL=

# 可选：基于单个代理自动扩展端口池
DOUBAN_PROXY_PORTS=

TEST_DATABASE_URL=postgresql+psycopg2://douban:douban@localhost:5434/douban_books_test
```

说明：

- `DATABASE_URL` 必填。
- `DOUBAN_PROXY_URL` / `DOUBAN_PROXY_POOL` 用于代理回填脚本。
- 如果代理提供商对协议敏感，必须让这里的 scheme 与真实可用配置一致，例如 `https://...`。
- `TEST_DATABASE_URL` 仅用于集成测试，且库名必须以 `_test` 结尾。

### 3. 启动数据库

```bash
docker compose up -d
```

PostgreSQL 默认映射到本机 `5434` 端口。初始化 SQL 会自动创建：

- `douban_books`
- `reviews`
- `rating_distributions`
- `user_profiles`
- `skipped_reviewer_urls`

### 4. 验证环境

```bash
make setup
```

## 基础抓取链路

基础链路适合先把 Top250 书籍和项目骨架跑通。

### 常用命令

```bash
make crawl
make detail
make reviews
make ratings
make social
make export
make export-advanced
make quality
```

对应含义：

- `make crawl`：抓 Top250 列表页
- `make detail`：补抓书籍详情
- `make reviews`：抓书评 spider
- `make ratings`：抓评分分布与阅读状态 spider
- `make social`：抓用户 spider
- `make export`：导出 `data/books.csv`
- `make export-advanced`：导出 `reviews / rating_distributions / user_profiles`
- `make quality`：跑基础质量检查

### Scrapy 设置摘要

当前默认设置偏保守：

- `ROBOTSTXT_OBEY = True`
- `DOWNLOAD_DELAY = 3.0`
- `CONCURRENT_REQUESTS = 4`
- `AUTOTHROTTLE_ENABLED = True`
- 启用 cookie、随机 UA、请求扰动和代理中间件

如果设置：

```bash
DOUBAN_USE_PLAYWRIGHT=true
```

则 Scrapy 下载层会切换到 Playwright。

## 进阶数据回填链路

当基础 spider 难以稳定拿到目标页面，或者你要更可控地跑实库回填时，使用代理回填脚本。

核心脚本：

- `scripts/backfill_via_proxy.py`
- `scripts/backfill_advanced_via_proxy.py`

其中当前主要使用的是：

```bash
conda run -n douban_books python scripts/backfill_advanced_via_proxy.py
```

### 设计思路

进阶回填不直接依赖 Scrapy downloader，而是走：

1. 用 `curl` 通过代理抓取真实页面
2. 复用项目内 parser 解析 HTML
3. 直接 upsert 到 PostgreSQL

这样做的目的是把问题拆开：

- 代理是否真实可用
- 目标站是否被拦截
- 页面是否能解析
- 数据是否真的写入数据库

### 支持的阶段

```bash
--stages reviews,ratings,users
```

建议顺序也是：

1. `reviews`
2. `ratings`
3. `users`

原因很直接：`users` 最贵、最脆弱、最容易烧代理流量。

### 小批量验证示例

先验证单本书：

```bash
conda run -n douban_books python scripts/backfill_advanced_via_proxy.py \
  --book-url https://book.douban.com/subject/1007305/ \
  --stages reviews,ratings
```

再验证 users 小批量：

```bash
conda run -n douban_books python scripts/backfill_advanced_via_proxy.py \
  --stages users \
  --user-limit 20 \
  --user-concurrency 3 \
  --user-timeout 10 \
  --user-min-review-count 2 \
  --user-max-proxy-attempts 2
```

### users 阶段已做的止损措施

- 小并发，默认 `3`
- 用户页超时收紧，默认 `10s`
- reviewer 预过滤，默认评论出现次数 `>= 2`
- 每个 reviewer 的代理尝试次数上限，默认 `2`
- `404 reviewer` 持久化写入 `skipped_reviewer_urls`
- 后续抓取自动排除 skip 表中的无效主页

这部分是为了避免“代理流量在烧，但 `user_profiles` 不增长”。

## 导出与质量检查

### 导出

```bash
make export
make export-advanced
```

输出文件位于 `data/`：

- `books.csv`
- `reviews.csv`
- `rating_distributions.csv`
- `user_profiles.csv`

### 质量检查

```bash
make quality
make verify-fast
make verify-advanced
```

当前质量检查至少会关注：

- 各表总行数
- `user_profiles` 是否存在重复 `reviewer_url`

## 测试

### 非集成测试

```bash
make verify-fast
```

或：

```bash
conda run -n douban_books pytest tests/ -v -m "not integration" --tb=short
```

### 集成测试

```bash
make test-full
```

前提：

- `TEST_DATABASE_URL` 已设置
- 数据库名以 `_test` 结尾
- 本地 Docker PostgreSQL 正常运行

## 常见问题

### 1. 代理能查到出口 IP，但豆瓣页面还是不通

先不要把这类问题判断成“代理可用”。真正应该验证的是：

- 代理能否打开真实豆瓣页面
- 返回的是不是被拦截页或安全跳转页
- parser 能否从 HTML 中提取到目标字段
- 数据库是否真的产生了新增行

只有 `ip.decodo.com` 之类的探活成功，不代表目标站路径成功。

### 2. 代理流量持续消耗，但数据库没有增长

优先检查：

- 剩余候选 URL 是否大量为 `404`
- parser 是否因页面变化失效
- DB 是否可写
- 重试链路是否过长
- users 阶段是否在反复请求同一批失效 reviewer

当前项目已经通过 `skipped_reviewer_urls` 解决了一部分“反复撞 404”的问题。

### 3. 是否应该一上来就跑全量 users

不建议。

更稳妥的顺序是：

1. 先确认 `reviews` 能写入
2. 再确认 `ratings` 和阅读状态能写入
3. 最后才用小并发推进 `users`

## 当前分支说明

这条 worktree 分支重点不是“重新实现一个基础豆瓣 spider”，而是把进阶数据链路做成可恢复、可验证、可止损的实库回填流程。

如果你想知道本阶段已经实际落了多少数据，直接看：

- [`ADVANCED_CRAWLER_STAGE_REPORT_2026-05-18.md`](./ADVANCED_CRAWLER_STAGE_REPORT_2026-05-18.md)

如果你想继续扩展用户画像，建议先从小批量 users 回填命令开始，而不是直接全量重跑。
