export DATABASE_URL ?= $(shell grep ^DATABASE_URL .env 2>/dev/null | cut -d= -f2-)
export DANGDANG_USE_PLAYWRIGHT ?= $(shell grep ^DANGDANG_USE_PLAYWRIGHT .env 2>/dev/null | cut -d= -f2-)
PG_USER   ?= $(shell grep ^PG_USER .env 2>/dev/null | cut -d= -f2-)
PG_USER   ?= dangdang
PG_DB     ?= $(shell grep ^PG_DB .env 2>/dev/null | cut -d= -f2-)
PG_DB     ?= dangdang_books

define wait_pg
	@echo "等待 PG 就绪..."
	@for i in 1 2 3 4 5 6 7 8; do \
		docker compose exec -T postgres pg_isready -U $(PG_USER) -q 2>/dev/null && break; \
		echo "  等待中... ($$i)"; \
		sleep 2; \
	done
	@sleep 1
endef

.PHONY: setup crawl detail analyze export reset-db

setup:
	pip install -r requirements.txt
	playwright install chromium 2>/dev/null || true
	[ -f .env ] || cp .env.example .env
	docker compose up -d
	$(call wait_pg)
	python -c "from dangdang_scrapy.db import init_db; init_db()"
	@echo "环境就绪！运行: make crawl  (需要旧数据? make import)"


import: $(wildcard data/books.csv)
	python scripts/import_books.py

crawl:
	python -m scrapy crawl dangdang -s JOBDIR=jobs/crawl

detail:
	python -m scrapy crawl dangdang_detail -s JOBDIR=jobs/detail

export:
	python scripts/export_books.py

analyze:
	python analysis/visualize.py

reset-db:
	docker compose down -v
	docker compose up -d
	$(call wait_pg)
	python -c "from dangdang_scrapy.db import init_db; init_db()"

psql:
	docker compose exec postgres psql -U $(PG_USER) -d $(PG_DB)

logs:
	tail -f data/*.log
