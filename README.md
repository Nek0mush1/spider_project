# dangdang_scrapy — 当当图书爬虫项目

基于 Scrapy + PostgreSQL 的当当网图书数据采集与分析系统。支持**原生 HTTP**（默认）和 **Playwright**（可选）双模式渲染引擎。

## 目录结构

```
dangdang_scrapy/
├── docker-compose.yml       # PostgreSQL 容器
├── Makefile                  # 一键命令入口 (自动识别 Conda 环境)
├── requirements.txt          # Python 依赖
├── .env.example              # 环境变量模板
├── README.md
├── data/                     # CSV 导出产物
│   ├── books.csv             # 初始样本数据 (git 跟踪)
├── scripts/
│   ├── init_db.sql           # 建表 DDL (容器首次启动自动执行)
│   ├── export_books.py       # 数据库 → CSV
│   └── import_books.py       # CSV → 数据库
├── tests/
│   ├── test_parsers.py
│   ├── test_spiders.py
│   ├── test_db_pipeline.py
│   └── fixtures/             # 本地 HTML 样本
├── analysis/
│   └── visualize.py          # matplotlib 可视化
├── quality_checks.py         # 数据质量检查
└── dangdang_scrapy/
    ├── settings.py
    ├── items.py
    ├── pipelines.py
    ├── middlewares.py
    ├── db.py                 # 统一数据库连接 + upsert
    ├── parsers.py            # 集中解析函数
    └── spiders/
        ├── dangdang.py       # 列表爬虫 (标准页 + 促销页)
        └── dangdang_detail.py # 详情页评分补抓
```

## 快速开始

### 前置：Conda 环境

项目依赖统一通过 Conda 环境管理（`dangdang_scrapy`），所有 `make` 命令自动使用该环境。

```bash
# 创建 Conda 环境（首次）
conda create -n dangdang_scrapy python=3.13 -y

# 激活环境后手动操作，或直接用 make（自动识别环境）
conda activate dangdang_scrapy
```

### 一键初始化

```bash
# 1. 环境变量
cp .env.example .env

# 2. 一键初始化 (Docker + Python 依赖 + 建库)
make setup

# 3. 数据采集
make crawl      # 列表页抓取
make detail     # 详情页评分补抓

# 4. 导出与分析
make export     # 数据库 → CSV
make analyze    # 可视化图表
make quality    # 数据质量报告
make verify-fast  # 快速验证（依赖数据库可连接）
make verify-e2e   # 端到端验证（需数据库已有有效数据）
```

## 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `DATABASE_URL` | 必填 | PostgreSQL 连接串 |
| `DANGDANG_USE_PLAYWRIGHT` | `false` | `true` 时启用 Playwright 渲染 |
| `PG_USER` / `PG_PASSWORD` / `PG_DB` | dangdang | Docker Compose 变量 |

## 双模式渲染

| 模式 | 速度 | 抗反爬 | 设置 |
|------|------|--------|------|
| 原生 HTTP | ~0.3s/页 | 中等 | `DANGDANG_USE_PLAYWRIGHT=false` (默认) |
| Playwright | ~3s/页 | 最强 | `DANGDANG_USE_PLAYWRIGHT=true` |

## 字段语义

| 字段 | 类型 | 说明 |
|------|------|------|
| `rating` | DOUBLE (0–100) | **百分比值**，90 = 4.5 星，非 5 分制 |
| `rating_people` | BIGINT | 评论人数，可为空 |
| `price` | DOUBLE | 当前售价，可为空 |
| `sales` | BIGINT | 销量（当前未采集），保留字段 |

## 整改对照

| 问题 | 修复 |
|------|------|
| 明文凭证 | 全部移入 `.env`，`gitignore` |
| 分页失效 | `self._follow_next()` → `yield from` |
| 全表去重 | 移除 `SELECT detail_url` → `ON CONFLICT DO NOTHING` |
| 多路径补抓 | 统一为 `scrapy crawl dangdang_detail` |
| CSV 主存储 | PostgreSQL 唯一事实源，CSV 仅导出产物 |
| 配置漂移 | 删除 MySQL 残留，统一 PostgreSQL |

## 质量指标

`make quality` 输出示例：

```
采集总条数: 8599
唯一商品(去重): 8599
可用详情页(product.dangdang.com): 7541 (87.7%)
评分补全率: 989/8599 (11.5%)
脏链接过滤(jump.php): 1058 (12.3%)
价格可解析率: 8175/8599 (95.1%)
name 非空率: 7694/8599 (89.5%)
```

## 验证命令

| 命令 | 说明 |
|------|------|
| `make verify-fast` | fixture测试 + 导出 + 分析冒烟（依赖数据库可连接） |
| `make verify-e2e` | verify-fast + 运行时断言（需数据库有数据） |
| `make test-full` | 在独立 `_test` 库运行全部集成测试 |
| `pytest -m "not integration"` | 只跑单元测试 |

## 开发者指南

### 新增解析函数
1. 在 `parsers.py` 实现，补类型标注
2. 在 `tests/test_parsers.py` 补测试（正常值 / 空值 / 异常值）
3. 在 `pipelines.py` 或 `spiders/` 中复用

### 新增爬虫 / Fixture / 集成测试
1. 爬虫放在 `spiders/`，数据库测试打 `@pytest.mark.integration`
2. 本地 HTML fixture 放在 `tests/fixtures/`，测试不依赖外网
3. 集成测试使用 `TEST_DATABASE_URL`（必须以 `_test` 结尾），与生产库隔离

### 数据语义
| 字段 | 说明 |
|------|------|
| `rating` | 百分比 0-100，90 = 4.5 星 |
| `rating_people` | 评论数，可为空 |
| `sales` | 预留字段，当前未采集 |
| `price` | 当前售价，可为空 |

### 数据流
```
当当网 → Scrapy spider → BookCleaningPipeline → DatabasePipeline(upsert) → PostgreSQL
                                                                              ↓
                                                                       CSV(显式导出)
                                                                              ↓
                                                                   matplotlib(可视化)
```

## 技术栈

Python 3.13 · Scrapy 2.15 · Playwright · PostgreSQL 16 · Docker · Conda · pandas · matplotlib
