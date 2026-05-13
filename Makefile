.PHONY: setup crawl analyze clean

setup: ## 一键初始化环境
	pip install -r requirements.txt
	playwright install chromium 2>/dev/null || true
	docker compose up -d
	@echo "等待 PG 就绪..."
	@sleep 5
	@echo "环境就绪！运行: make crawl"

crawl: ## 运行爬虫
	python -m scrapy crawl dangdang -s JOBDIR=jobs/crawl

detail: ## 补爬详情页评分
	python backfill_ratings.py

analyze: ## 可视化分析
	python analysis/visualize.py

clean: ## 清理数据
	docker compose down -v
	rm -rf jobs/

logs: ## 查看爬虫日志
	tail -f data/crawl.log

psql: ## 连接数据库
	docker compose exec postgres psql -U dangdang -d dangdang_books
