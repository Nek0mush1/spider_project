.PHONY: setup crawl detail analyze export reset-db

setup: ## 一键初始化 (cp .env.example .env 后首次运行)
	pip install -r requirements.txt
	playwright install chromium 2>/dev/null || true
	docker compose up -d
	@sleep 4
	python -c "from dangdang_scrapy.db import init_db; init_db()"
	@echo "环境就绪！运行: make crawl"

crawl: ## 列表爬虫
	python -m scrapy crawl dangdang -s JOBDIR=jobs/crawl

detail: ## 详情页评分补抓
	python -m scrapy crawl dangdang_detail -s JOBDIR=jobs/detail

export: ## 导出 CSV
	python scripts/export_books.py

analyze: ## 可视化分析
	python analysis/visualize.py

reset-db: ## 重建数据库
	docker compose down -v
	docker compose up -d
	@sleep 4
	python -c "from dangdang_scrapy.db import init_db; init_db()"

psql: ## 连接数据库
	docker compose exec postgres psql -U dangdang -d dangdang_books

logs: ## 查看爬虫日志
	tail -f data/*.log
