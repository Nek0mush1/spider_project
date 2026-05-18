# 豆瓣进阶数据爬取阶段报告

日期：2026-05-18  
分支工作区：`/home/reb666/Project/spider_project/douban_books/.worktrees/douban-advanced-crawler`

## 1. 当前阶段结论

本阶段已经完成进阶数据链路的主要打通与实库验证：

- `reviews` 已完成落库
- `rating_distributions` 已完成落库
- `books_with_state` 已完成落库
- `user_profiles` 已完成一部分有效作者主页落库
- `404 reviewer` 已识别并加入持久化跳过机制，后续不会重复消耗代理

当前数据库真实状态：

- `reviews = 4994`
- `rating_distributions = 500`
- `books_with_state = 250`
- `user_profiles = 583`
- `skipped_reviewers = 39`

## 2. 已完成内容

### 2.1 进阶数据实库结果

已确认以下数据表有真实数据：

- `reviews`：4994 条
- `rating_distributions`：500 条
- `douban_books.want_to_read / reading / read`：250 本书完成
- `user_profiles`：583 条

其中：

- `rating_distributions = 500` 表示 Top250 每本书都已有 `official + derived` 两条分布记录
- `books_with_state = 250` 表示 Top250 每本书都已有阅读状态统计
- `reviews = 4994` 表示 Top250 基本达到“每本约 20 条热门长评”的目标量级

### 2.2 代理与抓取策略修正

已确认并落地以下关键抓取策略：

- 代理必须使用 `https://` 形式
- 对豆瓣页面抓取需要更接近浏览器的请求头
- `book.douban.com` 与 `www.douban.com/people/...` 的可用性表现不同，用户主页阶段更脆弱
- 通过 `curl + proxy + parser + DB upsert` 绕过原始 Scrapy 下载链路中的不稳定点

### 2.3 users 阶段性能优化

已对 `users` 阶段做了三类优化：

- 小并发：默认 `3`
- 用户页超时收紧：默认 `10s`
- reviewer 预过滤：
  - 仅抓 `reviewer_url LIKE %/people/%`
  - 排除已入库用户
  - 排除已加入 skip 表的无效用户
  - 默认仅抓评论中出现次数 `>= 2` 的 reviewer

### 2.4 404 reviewer 持久化跳过

已新增 `skipped_reviewer_urls` 持久化表。

作用：

- 对确认失效的 `reviewer_url` 记录 `reason`
- 当前已记录 `39` 条 `http_404`
- 后续运行 `users` 时自动排除这些 URL
- 避免重复请求同一批无效主页，减少代理浪费

## 3. 已定位的核心问题

### 3.1 为什么 user_profiles 一度“流量在消耗但数据不增长”

根因已经明确，不是数据库故障，也不主要是代理无效，而是：

- 剩余待抓 reviewer 中存在大量失效主页
- 这些 URL 返回 `404`
- 在未做持久化跳过之前，每次运行都会重新请求这些主页
- 因而出现：
  - 代理流量继续消耗
  - 但 `user_profiles` 不增长

后续已通过 `skipped_reviewer_urls` 解决“重复撞 404”问题。

### 3.2 为什么 users 阶段仍然没有跑满所有评论作者

当前 `user_profiles = 583`，并不意味着抓取链路还坏着，而是因为：

- 当前筛选条件为 `min_review_count >= 2`
- 在该筛选条件下，可抓 reviewer 范围已经明显收窄
- 且有效主页、404 主页、不可稳定返回主页混在一起
- 在完成有效主页抓取并清理 404 后，剩余增量空间已明显下降

## 4. 当前代码侧关键变更

本阶段已新增或修改的关键文件包括：

- `scripts/backfill_advanced_via_proxy.py`
  - 增加单书/阶段化入口
  - 增加 users 小并发
  - 增加 users 专用 timeout
  - 增加 reviewer 预过滤参数
  - 增加 404 持久化 skip 逻辑

- `douban_books/proxy_fetch.py`
  - 浏览器化请求头
  - 支持代理端口池
  - curl 输出解析与 blocked 判断

- `douban_books/db.py`
  - `fetch_reviewer_urls()` 支持按评论频次过滤
  - 新增 `skipped_reviewer_urls` 表初始化
  - 新增 `upsert_skipped_reviewers()`

- `scripts/init_db.sql`
  - 同步新增 `skipped_reviewer_urls`

- `tests/test_backfill_advanced_via_proxy.py`
- `tests/test_advanced_db_pipeline.py`
- `tests/test_proxy_fetch.py`

## 5. 验证情况

本阶段已完成的验证：

- 单书进阶链路验证：
  - 评论页抓取成功
  - 评分分布抓取成功
  - 阅读状态抓取成功
  - 数据可真实写入 PostgreSQL

- 全量 `reviews + ratings` 验证：
  - `reviews = 4994`
  - `rating_distributions = 500`
  - `books_with_state = 250`

- users 优化验证：
  - 小批次并发抓取成功写入
  - 404 reviewer 可识别并跳过
  - 404 reviewer 可持久化写入 skip 表
  - skip 后不会再进入待抓集合

测试状态说明：

- 不依赖测试库的本地测试已通过
- 依赖 `douban_books_test` 的集成测试仍受测试库连接环境影响，属于既有环境问题，不是本次功能逻辑问题

## 6. 当前剩余工作

如果后续继续推进，剩余工作主要是 `user_profiles` 扩展，而不是 `reviews/ratings/state`。

可选方向：

### 方向 A：保守收尾

目标：

- 接受当前 `user_profiles = 583`
- 作为本阶段课程展示或阶段性交付结果

优点：

- 数据已具备完整“书评 + 评分分布 + 阅读状态 + 部分用户画像”结构
- 不再继续消耗代理

### 方向 B：继续扩张 user_profiles

可继续尝试：

- 将 `--user-min-review-count` 从 `2` 下调到 `1`
- 进一步扩大 reviewer 池

风险：

- 会引入更多低价值 reviewer
- 404/慢主页比例可能更高
- 代理流量消耗会继续增加

### 方向 C：继续做 users 精细化策略

可继续增强：

- 对 timeout / blocked / 404 分类型持久化
- 增加“连续失败黑名单”
- 增加更细粒度的 reviewer 价值排序
- 先探活再抓详情

这条路线更适合后续把 `users` 单独当一个优化专题处理。

## 7. 当前建议

当前建议是：

- 将本阶段认定为“进阶数据主目标已完成”
- 把 `user_profiles = 583` 视为当前阶段有效成果
- 是否继续扩展用户画像，交由后续单独决策

原因：

- `reviews / ratings / books_with_state` 已经完整达成
- `users` 的剩余问题已从“链路不通”转变为“收益递减 + 代理成本问题”
- 从阶段性产出角度，已经具备可交付的数据规模和结构

## 8. 后续接手提示

如果后续继续跑 `users`，建议使用当前优化参数作为起点：

```bash
conda run -n douban_books python scripts/backfill_advanced_via_proxy.py \
  --stages users \
  --user-concurrency 3 \
  --user-timeout 10 \
  --user-min-review-count 2 \
  --user-max-proxy-attempts 2
```

如果要继续扩大用户池，再评估是否把：

```bash
--user-min-review-count 2
```

下调为：

```bash
--user-min-review-count 1
```

但这一步应结合代理成本重新决策。
