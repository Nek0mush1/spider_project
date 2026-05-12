import subprocess
import sys


def crawl():
    subprocess.run(
        [sys.executable, "-m", "scrapy", "crawl", "dangdang"],
        cwd="/home/reb666/Project/spider_project/dangdang_scrapy",
    )


def analyze():
    subprocess.run(
        [sys.executable, "analysis/visualize.py"],
        cwd="/home/reb666/Project/spider_project/dangdang_scrapy",
    )


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "analyze":
        analyze()
    else:
        crawl()
