CREATE TABLE IF NOT EXISTS books (
    id SERIAL PRIMARY KEY,
    name VARCHAR(500),
    author VARCHAR(500),
    publisher VARCHAR(300),
    price DOUBLE PRECISION,
    original_price DOUBLE PRECISION,
    rating DOUBLE PRECISION,
    rating_people BIGINT,
    sales BIGINT,
    detail_url VARCHAR(1000),
    category VARCHAR(200),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_books_url ON books (detail_url);
