import pandas as pd
import matplotlib.pyplot as plt
import matplotlib
matplotlib.rc("font", family="WenQuanYi Micro Hei", size=10)
matplotlib.rc("axes", unicode_minus=False)

import argparse
from sqlalchemy import create_engine


def load_data(engine_url):
    engine = create_engine(engine_url)
    df = pd.read_sql("SELECT * FROM books", engine)
    return df


def plot_price_distribution(df):
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    df["price"].dropna().plot.hist(bins=30, ax=axes[0], color="steelblue", edgecolor="white")
    axes[0].set_title("图书价格分布")
    axes[0].set_xlabel("价格 (元)")
    axes[0].set_ylabel("数量")

    df["price"].dropna().plot.box(ax=axes[1], vert=False)
    axes[1].set_title("价格箱线图")
    axes[1].set_xlabel("价格 (元)")
    plt.tight_layout()
    plt.savefig("analysis/price_distribution.png", dpi=150)
    plt.close()


def plot_top_publishers(df, top=15):
    pub_counts = df["publisher"].value_counts().head(top)
    fig, ax = plt.subplots(figsize=(12, 6))
    pub_counts.plot.barh(ax=ax, color="coral")
    ax.set_title(f"Top{top} 热门出版社")
    ax.set_xlabel("图书数量")
    ax.invert_yaxis()
    plt.tight_layout()
    plt.savefig("analysis/top_publishers.png", dpi=150)
    plt.close()


def plot_rating_vs_price(df):
    fig, ax = plt.subplots(figsize=(10, 6))
    subset = df[["rating", "price"]].dropna()
    ax.scatter(subset["price"], subset["rating"], alpha=0.4, s=20, c="green")
    ax.set_title("价格 vs 评分")
    ax.set_xlabel("价格 (元)")
    ax.set_ylabel("评分")
    plt.tight_layout()
    plt.savefig("analysis/rating_vs_price.png", dpi=150)
    plt.close()


def plot_sales_distribution(df):
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    col = "rating_people" if df["sales"].isna().all() else "sales"
    title = "评论数分布" if col == "rating_people" else "销量分布"

    data = df[col].dropna()
    data.plot.hist(bins=30, ax=axes[0], color="purple", edgecolor="white")
    axes[0].set_title(title)
    axes[0].set_xlabel(col)
    axes[0].set_ylabel("数量")

    top10 = data.nlargest(10)
    top10.plot.bar(ax=axes[1], color="gold", edgecolor="black")
    axes[1].set_title(f"{title} Top10")
    axes[1].set_xlabel("书籍索引")
    axes[1].set_ylabel(col)
    plt.tight_layout()
    plt.savefig("analysis/sales_distribution.png", dpi=150)
    plt.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mysql", default="postgresql+psycopg2://dangdang:@localhost:5433/dangdang_books")
    parser.add_argument("--csv", help="从 CSV 文件读取")
    args = parser.parse_args()

    if args.csv:
        df = pd.read_csv(args.csv)
    else:
        df = load_data(args.mysql)

    print(f"共加载 {len(df)} 条记录")
    print(df.describe())

    plot_price_distribution(df)
    plot_top_publishers(df)
    plot_rating_vs_price(df)
    plot_sales_distribution(df)
    print("图表已保存到 analysis/ 目录")
