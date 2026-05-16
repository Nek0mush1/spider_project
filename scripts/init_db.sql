CREATE TABLE IF NOT EXISTS douban_books (
    id SERIAL PRIMARY KEY,
    url VARCHAR(500) NOT NULL,
    title VARCHAR(500),
    authors TEXT,
    publisher VARCHAR(255),
    pubdate VARCHAR(100),
    price VARCHAR(100),
    rating DOUBLE PRECISION,
    votes INTEGER,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_douban_books_url ON douban_books(url);
