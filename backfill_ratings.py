import re, time, sys
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from sqlalchemy import create_engine, text

WORKERS = 4
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:126.0) Gecko/20100101 Firefox/126.0",
]

DB_URL = "postgresql+psycopg2://dangdang:dangdang@localhost:5433/dangdang_books"

engine = create_engine(DB_URL, connect_args={"connect_timeout": 10})

def fetch_pending():
    sql = """SELECT id, detail_url FROM books
             WHERE detail_url LIKE '%product.dangdang.com%'
               AND (rating IS NULL OR rating = 0)
             ORDER BY id"""
    with engine.connect() as conn:
        return [(row[0], row[1]) for row in conn.execute(text(sql))]

def extract_rating(html):
    m = re.search(r'<span class="star"[^>]*style="[^"]*width:\s*([\d.]+)%', html)
    rating = float(m.group(1)) if m else None
    m = re.search(r'id="comm_num_down"[^>]*>(\d+)', html)
    people = int(m.group(1)) if m else None
    return rating, people

def process_one(args):
    id_, url, ua = args
    try:
        r = requests.get(url, headers={"User-Agent": ua}, timeout=15)
        if r.status_code != 200:
            return ("fail", id_, url, None, None)
        rating, people = extract_rating(r.text)
        local_engine = create_engine(DB_URL, connect_args={"connect_timeout": 5})
        with local_engine.begin() as conn:
            conn.execute(
                text("UPDATE books SET rating=:r, rating_people=:p WHERE id=:id"),
                {"r": rating, "p": people, "id": id_},
            )
        return ("ok", id_, url, rating, people)
    except Exception as e:
        return ("fail", id_, url, None, str(e))

def main():
    rows = fetch_pending()
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else len(rows)
    rows = rows[:limit]
    print(f"待处理: {len(rows)} 条, 并发: {WORKERS}")

    ok = fail = 0
    t0 = time.time()
    batch = [(id_, url, USER_AGENTS[i % len(USER_AGENTS)]) for i, (id_, url) in enumerate(rows)]

    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        futures = {pool.submit(process_one, item): item[0] for item in batch}
        done = 0
        for f in as_completed(futures):
            status, id_, url, rating, people = f.result()
            if status == "ok":
                ok += 1
            else:
                fail += 1
            done += 1
            if done % 200 == 0:
                elapsed = time.time() - t0
                rate = done / elapsed
                remaining = (len(rows) - done) / rate
                print(f"  {done}/{len(rows)} | ok={ok} fail={fail} | {rate:.0f}条/分 | 剩余{remaining/60:.0f}分")

    elapsed = time.time() - t0
    with engine.connect() as conn:
        r = conn.execute(text("SELECT COUNT(*) FROM books WHERE rating IS NOT NULL AND rating > 0"))
        has = r.scalar()

    print(f"\n{'='*50}")
    print(f"完成: {ok} ok / {fail} fail")
    print(f"耗时: {elapsed:.0f}s ({elapsed/60:.1f}min)")
    print(f"速率: {ok/elapsed*60:.0f} 条/分")
    print(f"有评分: {has} 条")

if __name__ == "__main__":
    main()
