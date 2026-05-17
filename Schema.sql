-- PostgreSQL 15+ with pgvector extension
-- Tables: products, product_embeddings, reviews

-- Enable pgvector for embedding storage
CREATE EXTENSION IF NOT EXISTS vector;

-- PRODUCTS (from meta_Gift_Cards.jsonl)
-- Fields: parent_asin, title, main_category, store, average_rating,
--         rating_number, price, features, description, categories,
--         details, images, videos, bought_together, subtitle, author

CREATE TABLE IF NOT EXISTS products (
    parent_asin         TEXT            PRIMARY KEY,
    title               TEXT,
    subtitle            TEXT,
    author              TEXT,
    main_category       TEXT,
    store               TEXT,
    average_rating      NUMERIC(3, 1),
    rating_number       INTEGER,
    price_raw           TEXT,
    price               NUMERIC(10, 2),
    features            JSONB,
    description         JSONB,
    categories          JSONB,
    details             JSONB,
    images              JSONB,
    videos              JSONB,
    bought_together     JSONB,
    ingested_at         TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);
 
-- Indexes for common filter predicates (from scoping doc)
CREATE INDEX IF NOT EXISTS idx_products_main_category  ON products (main_category);
CREATE INDEX IF NOT EXISTS idx_products_price          ON products (price);
CREATE INDEX IF NOT EXISTS idx_products_average_rating ON products (average_rating);
CREATE INDEX IF NOT EXISTS idx_products_store          ON products (store);
 
-- GIN indexes for JSONB search
CREATE INDEX IF NOT EXISTS idx_products_features_gin    ON products USING GIN (features);
CREATE INDEX IF NOT EXISTS idx_products_categories_gin  ON products USING GIN (categories);

-- PRODUCT EMBEDDINGS (populated by the Embed Task in Airflow)
-- Stores all-MiniLM-L6-v2 vectors (384 dims) for semantic search.
-- Binary-quantised halfvec stored alongside for HNSW fast pre-selection.
CREATE TABLE IF NOT EXISTS product_embeddings (
    parent_asin         TEXT            PRIMARY KEY
                                        REFERENCES products (parent_asin)
                                        ON DELETE CASCADE,
    embedding           vector(384)     NOT NULL,
    embedding_half      halfvec(384),
    model_name          TEXT            NOT NULL DEFAULT 'sentence-transformers/all-MiniLM-L6-v2',
    model_version       TEXT,
    mlflow_run_id       TEXT,
    ingested_at         TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

-- HNSW index on binary-quantised vectors for fast candidate pre-selection
CREATE INDEX IF NOT EXISTS idx_product_embeddings_hnsw_binary
    ON product_embeddings
    USING hnsw ((binary_quantize(embedding)::bit(384)) bit_hamming_ops)
    WITH (m = 16, ef_construction = 64);
 
-- IVFFlat index on full vectors for fallback / smaller datasets
CREATE INDEX IF NOT EXISTS idx_product_embeddings_ivfflat
    ON product_embeddings
    USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 50);

-- REVIEWS (from Gift_Cards.jsonl)
-- Fields: rating, title, text, parent_asin, user_id, asin,
--         helpful_vote, verified_purchase, timestamp

CREATE TABLE IF NOT EXISTS reviews (
    -- Surrogate PK (dataset has no native review ID)
    review_id           BIGSERIAL       PRIMARY KEY,
    -- Foreign key to products (asin is the child/variant ASIN; parent_asin links up)
    parent_asin         TEXT            NOT NULL
                                        REFERENCES products (parent_asin)
                                        ON DELETE CASCADE,
    asin                TEXT,
    user_id             TEXT            NOT NULL,
    rating              NUMERIC(2, 1)   NOT NULL CHECK (rating BETWEEN 1 AND 5),
    title               TEXT,
    review_text         TEXT,
    helpful_vote        INTEGER         NOT NULL DEFAULT 0,
    verified_purchase   BOOLEAN         NOT NULL DEFAULT FALSE,
    timestamp_raw       BIGINT,
    reviewed_at         TIMESTAMPTZ,
    ingested_at         TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

-- Indexes for common access patterns
CREATE INDEX IF NOT EXISTS idx_reviews_parent_asin      ON reviews (parent_asin);
CREATE INDEX IF NOT EXISTS idx_reviews_user_id          ON reviews (user_id);
CREATE INDEX IF NOT EXISTS idx_reviews_rating           ON reviews (rating);
CREATE INDEX IF NOT EXISTS idx_reviews_reviewed_at      ON reviews (reviewed_at);
CREATE INDEX IF NOT EXISTS idx_reviews_verified         ON reviews (verified_purchase);

-- Full-text search index on review body (for LLM context retrieval)
CREATE INDEX IF NOT EXISTS idx_reviews_fts
    ON reviews
    USING GIN (to_tsvector('english', COALESCE(review_text, '')));