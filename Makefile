.PHONY: setup crawl detail reviews ratings social full export export-advanced quality verify-fast verify-advanced test-full reset-db psql logs clean

CONDA_ENV = douban_books
DOCKER_COMPOSE = docker compose

setup:
	@echo "=== 检查 conda 环境 ==="
	@conda env list | grep -q $(CONDA_ENV) || (echo "请先创建环境并安装依赖" && exit 1)
	@echo "=== 启动 PostgreSQL ==="
	$(DOCKER_COMPOSE) up -d
	@sleep 5
	@echo "=== 验证数据库 ==="
	$(DOCKER_COMPOSE) exec -T postgres psql -U douban -d douban_books -c "SELECT '环境就绪！' AS status;"

crawl:
	conda run -n $(CONDA_ENV) scrapy crawl douban_list -s JOBDIR=jobs/crawl-list

detail:
	conda run -n $(CONDA_ENV) scrapy crawl douban_detail -s JOBDIR=jobs/crawl-detail

reviews:
	conda run -n $(CONDA_ENV) scrapy crawl douban_reviews -s JOBDIR=jobs/crawl-reviews

ratings:
	conda run -n $(CONDA_ENV) scrapy crawl douban_rating_dist -s JOBDIR=jobs/crawl-ratings

social:
	conda run -n $(CONDA_ENV) scrapy crawl douban_user -s JOBDIR=jobs/crawl-user

full: setup crawl detail reviews ratings social

export:
	conda run -n $(CONDA_ENV) python scripts/export_books.py

export-advanced:
	conda run -n $(CONDA_ENV) python scripts/export_reviews.py

quality:
	conda run -n $(CONDA_ENV) python scripts/quality_checks.py

verify-fast:
	conda run -n $(CONDA_ENV) pytest tests/ -v -m "not integration" --tb=short

verify-advanced:
	conda run -n $(CONDA_ENV) pytest tests/ -v -m "not integration" --tb=short
	conda run -n $(CONDA_ENV) python scripts/quality_checks.py

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
	conda run -n $(CONDA_ENV) pytest tests/ -v -m integration --tb=short

reset-db:
	$(DOCKER_COMPOSE) down -v
	$(DOCKER_COMPOSE) up -d
	@sleep 5

psql:
	$(DOCKER_COMPOSE) exec -T postgres psql -U douban -d douban_books

logs:
	$(DOCKER_COMPOSE) logs --tail=100 -f

clean:
	$(DOCKER_COMPOSE) down -v
	rm -rf jobs/ .scrapy/ data/books.csv data/reviews.csv data/rating_distributions.csv data/user_profiles.csv
