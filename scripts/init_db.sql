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
    want_to_read INTEGER,
    reading INTEGER,
    read INTEGER,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_douban_books_url ON douban_books(url);

CREATE TABLE IF NOT EXISTS reviews (
    id SERIAL PRIMARY KEY,
    book_url VARCHAR(500) NOT NULL,
    review_url VARCHAR(500) NOT NULL,
    title VARCHAR(500),
    content TEXT,
    rating INTEGER,
    useful_count INTEGER,
    useless_count INTEGER,
    useful_ratio DOUBLE PRECISION,
    replies_count INTEGER,
    reviewer_name VARCHAR(255),
    reviewer_url VARCHAR(500),
    published_at VARCHAR(100),
    crawled_at TIMESTAMP DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_reviews_review_url ON reviews(review_url);
CREATE INDEX IF NOT EXISTS idx_reviews_book_url ON reviews(book_url);

CREATE TABLE IF NOT EXISTS rating_distributions (
    id SERIAL PRIMARY KEY,
    book_url VARCHAR(500) NOT NULL,
    source VARCHAR(32) NOT NULL,
    sample_size INTEGER,
    star_5_count INTEGER,
    star_4_count INTEGER,
    star_3_count INTEGER,
    star_2_count INTEGER,
    star_1_count INTEGER,
    star_5_pct DOUBLE PRECISION,
    star_4_pct DOUBLE PRECISION,
    star_3_pct DOUBLE PRECISION,
    star_2_pct DOUBLE PRECISION,
    star_1_pct DOUBLE PRECISION,
    want_to_read INTEGER,
    reading INTEGER,
    read INTEGER,
    crawled_at TIMESTAMP DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_rating_distributions_book_source
ON rating_distributions(book_url, source);

CREATE TABLE IF NOT EXISTS user_profiles (
    id SERIAL PRIMARY KEY,
    reviewer_url VARCHAR(500) NOT NULL,
    display_name VARCHAR(255),
    following_count INTEGER,
    followers_count INTEGER,
    crawled_at TIMESTAMP DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_user_profiles_reviewer_url
ON user_profiles(reviewer_url);

CREATE TABLE IF NOT EXISTS skipped_reviewer_urls (
    id SERIAL PRIMARY KEY,
    reviewer_url VARCHAR(500) NOT NULL,
    reason VARCHAR(64),
    crawled_at TIMESTAMP DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_skipped_reviewer_urls_reviewer_url
ON skipped_reviewer_urls(reviewer_url);
