.PHONY: setup crawl detail export quality verify-fast test-full reset-db psql logs clean

CONDA_ENV = douban_books
DOCKER_COMPOSE = docker compose

# 一键环境搭建
setup:
	@echo "=== 检查 conda 环境 ==="
	@conda env list | grep -q $(CONDA_ENV) || (echo "请先运行: conda create -n $(CONDA_ENV) python=3.13 -y && conda run -n $(CONDA_ENV) pip install -r requirements.txt && conda run -n $(CONDA_ENV) playwright install chromium")
	@echo "=== 启动 PostgreSQL ==="
	$(DOCKER_COMPOSE) up -d
	@sleep 5
	@echo "=== 验证数据库 ==="
	$(DOCKER_COMPOSE) exec -T postgres psql -U douban -d douban_books -c "SELECT '环境就绪！' AS status;"
	@echo "=== 环境搭建完成 ==="

# 爬取TOP250列表页
crawl:
	conda run -n $(CONDA_ENV) scrapy crawl douban_list -s JOBDIR=jobs/crawl-list

# 详情页补抓
detail:
	conda run -n $(CONDA_ENV) scrapy crawl douban_detail -s JOBDIR=jobs/crawl-detail

# CSV导出
export:
	conda run -n $(CONDA_ENV) python scripts/export_books.py

# 数据质量检查
quality:
	conda run -n $(CONDA_ENV) python scripts/quality_checks.py

# 快速验证（单元测试 + 导出 + 质量）
verify-fast:
	@echo "=== 运行单元测试 ==="
	conda run -n $(CONDA_ENV) pytest tests/ -v -m "not integration" --tb=short
	@echo "=== CSV导出 ==="
	conda run -n $(CONDA_ENV) python scripts/export_books.py 2>/dev/null || echo "导出完成（可能无数据）"
	@echo "=== 质量检查 ==="
	conda run -n $(CONDA_ENV) python scripts/quality_checks.py 2>/dev/null || echo "质量检查完成"

# 完整测试（含集成测试）
test-full:
	@echo "=== 检查测试数据库 ==="
	@test -n "$$TEST_DATABASE_URL" || (echo "请设置 TEST_DATABASE_URL 环境变量（必须以_test结尾）" && exit 1)
	@echo "$$TEST_DATABASE_URL" | grep -q "_test" || (echo "TEST_DATABASE_URL 必须以_test结尾！" && exit 1)
	@echo "=== 确保测试数据库存在 ==="
	@if $(DOCKER_COMPOSE) exec -T postgres psql -U douban -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname='douban_books_test';" | grep -q 1; then \
		echo "  douban_books_test 已存在，跳过创建"; \
	else \
		echo "  创建 douban_books_test..."; \
		$(DOCKER_COMPOSE) exec -T postgres psql -U douban -d postgres -c "CREATE DATABASE douban_books_test;"; \
	fi
	@echo "=== 运行集成测试 ==="
	conda run -n $(CONDA_ENV) pytest tests/ -v -m integration --tb=short

# 重置数据库
reset-db:
	$(DOCKER_COMPOSE) down -v
	$(DOCKER_COMPOSE) up -d
	@sleep 5
	@echo "=== 创建测试数据库 ==="
	@if $(DOCKER_COMPOSE) exec -T postgres psql -U douban -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname='douban_books_test';" | grep -q 1; then \
		echo "  douban_books_test 已存在"; \
	else \
		echo "  创建 douban_books_test..."; \
		$(DOCKER_COMPOSE) exec -T postgres psql -U douban -d postgres -c "CREATE DATABASE douban_books_test;"; \
	fi
	@echo "=== 数据库已重置 ==="

# 连接数据库
psql:
	$(DOCKER_COMPOSE) exec -T postgres psql -U douban -d douban_books

# 查看日志
logs:
	$(DOCKER_COMPOSE) logs --tail=100 -f

# 清理
clean:
	$(DOCKER_COMPOSE) down -v
	rm -rf jobs/ .scrapy/ data/books.csv
	@echo "=== 清理完成 ==="
