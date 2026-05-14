export DATABASE_URL ?= $(shell grep ^DATABASE_URL .env 2>/dev/null | cut -d= -f2-)
export DANGDANG_USE_PLAYWRIGHT ?= $(shell grep ^DANGDANG_USE_PLAYWRIGHT .env 2>/dev/null | cut -d= -f2-)
PG_USER   ?= $(shell grep ^PG_USER .env 2>/dev/null | cut -d= -f2-)
PG_USER   ?= dangdang
PG_PASS   ?= $(shell grep ^PG_PASSWORD .env 2>/dev/null | cut -d= -f2-)
PG_PASS   ?= dangdang
PG_DB     ?= $(shell grep ^PG_DB .env 2>/dev/null | cut -d= -f2-)
PG_DB     ?= dangdang_books

define wait_pg
	@echo "等待 PG 就绪..."
	@for i in 1 2 3 4 5 6 7 8; do \
		PGPASSWORD=$(PG_PASS) docker compose exec -T postgres pg_isready -U $(PG_USER) -q 2>/dev/null && break; \
		if [ $$i -eq 8 ]; then echo "PG 启动超时"; exit 1; fi; \
		echo "  等待中... ($$i)"; \
		sleep 2; \
	done
	@sleep 1
endef

.PHONY: setup crawl detail export analyze verify quality test-full reset-db

setup:
	pip install -r requirements.txt
	playwright install chromium 2>/dev/null || true
	[ -f .env ] || cp .env.example .env
	docker compose up -d
	$(call wait_pg)
	python -c "from dangdang_scrapy.db import init_db; init_db()"
	@echo ""
	@echo "环境就绪！"
	@echo "  make crawl    列表抓取"
	@echo "  make detail   评分补抓"
	@echo "  make import   导入旧CSV (可选)"
	@echo "  make export   导出CSV"
	@echo "  make analyze  可视化"
	@echo "  make quality  数据质量报告"
	@echo "  make verify   全链路验证"

import: data/books.csv
	python scripts/import_books.py

crawl:
	python -m scrapy crawl dangdang -s JOBDIR=jobs/crawl

detail:
	python -m scrapy crawl dangdang_detail -s JOBDIR=jobs/detail

export:
	python scripts/export_books.py

analyze:
	python analysis/visualize.py

quality:
	python quality_checks.py

verify: quality
	pytest tests/ -v --tb=short -m "not integration"
	@echo ""
	@echo "=== 导出冒烟 ==="
	python scripts/export_books.py
	@echo ""
	@echo "=== 分析冒烟 ==="
	@if [ -f data/books.csv ]; then \
		python analysis/visualize.py --csv data/books.csv; \
	else \
		echo "data/books.csv 不存在，跳过分析冒烟"; \
	fi
	@echo ""
	@echo "所有验证通过！"

test-full:
	pytest tests/ -v --tb=short

reset-db:
	docker compose down -v
	docker compose up -d
	$(call wait_pg)
	python -c "from dangdang_scrapy.db import init_db; init_db()"

psql:
	docker compose exec postgres psql -U $(PG_USER) -d $(PG_DB)

logs:
	tail -f data/*.log
