from prometheus_client import Counter, Histogram, Gauge, Summary

UPSERT_PRODUCT_TEMPLATE = """
    INSERT INTO products (
        parent_asin, title, subtitle, author, main_category, store,
        average_rating, rating_number, price_raw, price,
        features, description, categories, details,
        images, videos, bought_together
    ) VALUES (
        :parent_asin, :title, :subtitle, :author, :main_category, :store,
        :average_rating, :rating_number, :price_raw, :price,
        :features::jsonb, :description::jsonb, :categories::jsonb,
        :details::jsonb, :images::jsonb, :videos::jsonb,
        :bought_together::jsonb
    )
    ON CONFLICT (parent_asin) DO UPDATE SET
        title           = EXCLUDED.title,
        average_rating  = EXCLUDED.average_rating,
        rating_number   = EXCLUDED.rating_number,
        price_raw       = EXCLUDED.price_raw,
        price           = EXCLUDED.price,
        features        = EXCLUDED.features,
        description     = EXCLUDED.description,
        categories      = EXCLUDED.categories,
        details         = EXCLUDED.details,
        images          = EXCLUDED.images,
        videos          = EXCLUDED.videos,
        bought_together = EXCLUDED.bought_together,
        ingested_at     = NOW()
""".strip()


INSERT_REVIEWS_TEMPLATE = """
    INSERT INTO reviews (
        parent_asin, asin, user_id, rating, title, review_text,
        helpful_vote, verified_purchase, timestamp_raw, reviewed_at,
        sentiment_label, sentiment_score
    ) VALUES (
        :parent_asin, :asin, :user_id, :rating, :title, :review_text,
        :helpful_vote, :verified_purchase, :timestamp_raw, :reviewed_at,
        :sentiment_label, :sentiment_score
    )
    ON CONFLICT DO NOTHING
""".strip()

UPSERT_EMBED_TEMPLATE = """
    INSERT INTO product_embeddings (
        parent_asin, embedding, embedding_half, model_name, mlflow_run_id
    ) VALUES (
        :parent_asin,
        :embedding::vector,
        :embedding_half::halfvec,
        :model_name,
        :mlflow_run_id
    )
    ON CONFLICT (parent_asin) DO UPDATE SET
        embedding      = EXCLUDED.embedding,
        embedding_half = EXCLUDED.embedding_half,
        model_name     = EXCLUDED.model_name,
        mlflow_run_id  = EXCLUDED.mlflow_run_id,
        ingested_at    = NOW()
""".strip()

SELECT_PARENT_ASINS = "SELECT parent_asin FROM products"

PRODUCTS: list[dict] = [
    {
        "parent_asin": "SEED_GC_0001",
        "title": "Amazon eGift Card — Happy Birthday Balloons",
        "main_category": "Gift Cards",
        "store": "Amazon",
        "average_rating": 4.8,
        "rating_number": 3210,
        "price_raw": "$25.00",
        "price": 25.00,
        "features": [
            "Redeemable toward millions of items",
            "No expiry date",
            "Email delivery",
        ],
        "description": ["Send a birthday surprise instantly with an Amazon Gift Card."],
        "categories": ["Gift Cards", "eGift Cards"],
    },
    {
        "parent_asin": "SEED_GC_0002",
        "title": "Amazon Physical Gift Card — Classic Black",
        "main_category": "Gift Cards",
        "store": "Amazon",
        "average_rating": 4.7,
        "rating_number": 1845,
        "price_raw": "$50.00",
        "price": 50.00,
        "features": [
            "Physical card in elegant black",
            "Free standard shipping",
            "No fees",
        ],
        "description": ["A sleek physical card delivered to your door."],
        "categories": ["Gift Cards", "Physical Gift Cards"],
    },
    {
        "parent_asin": "SEED_GC_0003",
        "title": "Amazon Gift Card — Holiday Wreath",
        "main_category": "Gift Cards",
        "store": "Amazon",
        "average_rating": 4.9,
        "rating_number": 987,
        "price_raw": "$100.00",
        "price": 100.00,
        "features": ["Holiday design", "Choose any amount", "Instant delivery"],
        "description": ["Perfect holiday gift for everyone on your list."],
        "categories": ["Gift Cards", "eGift Cards", "Holiday"],
    },
    {
        "parent_asin": "SEED_GC_0004",
        "title": "Amazon Gift Card Box — Smile",
        "main_category": "Gift Cards",
        "store": "Amazon",
        "average_rating": 4.6,
        "rating_number": 512,
        "price_raw": "$25.00",
        "price": 25.00,
        "features": ["Gift box included", "Blue ribbon packaging", "No expiry"],
        "description": ["Give the gift of choice in a beautiful box."],
        "categories": ["Gift Cards", "Physical Gift Cards"],
    },
    {
        "parent_asin": "SEED_GC_0005",
        "title": "Amazon eGift Card — Thank You Stars",
        "main_category": "Gift Cards",
        "store": "Amazon",
        "average_rating": 4.7,
        "rating_number": 2341,
        "price_raw": "$10.00",
        "price": 10.00,
        "features": ["Customisable message", "Scheduled delivery", "No fees"],
        "description": ["Say thank you with a personalised eGift Card."],
        "categories": ["Gift Cards", "eGift Cards"],
    },
    {
        "parent_asin": "SEED_GC_0006",
        "title": "Amazon Gift Card — Wedding Cake",
        "main_category": "Gift Cards",
        "store": "Amazon",
        "average_rating": 4.5,
        "rating_number": 678,
        "price_raw": "$75.00",
        "price": 75.00,
        "features": ["Wedding design", "Email delivery", "Millions of items"],
        "description": ["Celebrate their big day with the perfect gift."],
        "categories": ["Gift Cards", "eGift Cards", "Wedding"],
    },
    {
        "parent_asin": "SEED_GC_0007",
        "title": "Amazon Gift Card — Graduation Cap",
        "main_category": "Gift Cards",
        "store": "Amazon",
        "average_rating": 4.8,
        "rating_number": 1120,
        "price_raw": "$50.00",
        "price": 50.00,
        "features": ["Graduation design", "Instant email delivery", "No expiry"],
        "description": ["Reward their achievement with a flexible Amazon Gift Card."],
        "categories": ["Gift Cards", "eGift Cards", "Graduation"],
    },
    {
        "parent_asin": "SEED_GC_0008",
        "title": "Amazon Gift Card Tin — Happy Birthday Cupcake",
        "main_category": "Gift Cards",
        "store": "Amazon",
        "average_rating": 4.4,
        "rating_number": 334,
        "price_raw": "$30.00",
        "price": 30.00,
        "features": ["Reusable tin packaging", "No fees", "No expiry date"],
        "description": ["A fun birthday gift in a reusable cupcake tin."],
        "categories": ["Gift Cards", "Physical Gift Cards"],
    },
    {
        "parent_asin": "SEED_GC_0009",
        "title": "Amazon eGift Card — Just Because",
        "main_category": "Gift Cards",
        "store": "Amazon",
        "average_rating": 4.6,
        "rating_number": 890,
        "price_raw": "$15.00",
        "price": 15.00,
        "features": [
            "Casual everyday design",
            "Instant delivery",
            "Customisable amount",
        ],
        "description": ["No occasion needed — just spread some joy."],
        "categories": ["Gift Cards", "eGift Cards"],
    },
    {
        "parent_asin": "SEED_GC_0010",
        "title": "Amazon Gift Card — Baby Shower",
        "main_category": "Gift Cards",
        "store": "Amazon",
        "average_rating": 4.9,
        "rating_number": 445,
        "price_raw": "$50.00",
        "price": 50.00,
        "features": ["Baby shower design", "Email delivery", "No expiry"],
        "description": ["Help new parents get exactly what they need."],
        "categories": ["Gift Cards", "eGift Cards", "Baby"],
    },
]

REVIEW_TEMPLATES: list[dict] = [
    {
        "rating": 5.0,
        "title": "Perfect gift!",
        "text": "Sent this as a birthday present. The recipient loved it. Delivery was instant.",
        "sentiment_label": "positive",
        "sentiment_score": 0.9987,
    },
    {
        "rating": 5.0,
        "title": "Always a great choice",
        "text": "You can never go wrong with an Amazon gift card. Everyone loves them.",
        "sentiment_label": "positive",
        "sentiment_score": 0.9972,
    },
    {
        "rating": 4.0,
        "title": "Good but slow delivery",
        "text": "Great value but the physical card took longer than expected to arrive.",
        "sentiment_label": "positive",
        "sentiment_score": 0.8341,
    },
    {
        "rating": 3.0,
        "title": "Fine, nothing special",
        "text": "It's just a gift card. Does what it says. Packaging was a bit flimsy.",
        "sentiment_label": "negative",
        "sentiment_score": 0.6120,
    },
    {
        "rating": 5.0,
        "title": "Excellent!",
        "text": "Super easy to redeem and the design is beautiful. Would buy again.",
        "sentiment_label": "positive",
        "sentiment_score": 0.9991,
    },
    {
        "rating": 2.0,
        "title": "Card arrived damaged",
        "text": "The physical card was bent in the envelope. Very disappointed.",
        "sentiment_label": "negative",
        "sentiment_score": 0.9843,
    },
    {
        "rating": 5.0,
        "title": "Instant and reliable",
        "text": "Arrived in seconds via email. No issues at all. My go-to gift.",
        "sentiment_label": "positive",
        "sentiment_score": 0.9965,
    },
    {
        "rating": 4.0,
        "title": "Great value",
        "text": "Solid gift option. Recipient was happy and redeemed it straight away.",
        "sentiment_label": "positive",
        "sentiment_score": 0.9120,
    },
    {
        "rating": 1.0,
        "title": "Code did not work",
        "text": "Tried to redeem and the code was already used. Had to contact support.",
        "sentiment_label": "negative",
        "sentiment_score": 0.9981,
    },
    {
        "rating": 5.0,
        "title": "Wonderful gift idea",
        "text": "Bought this for a graduation and the recipient was thrilled. Highly recommend.",
        "sentiment_label": "positive",
        "sentiment_score": 0.9978,
    },
]

SEED_PRODUCTS_STR = """
INSERT INTO products (
    parent_asin, title, main_category, store,
    average_rating, rating_number, price_raw, price,
    features, description, categories
) VALUES (
    :parent_asin, :title, :main_category, :store,
    :average_rating, :rating_number, :price_raw, :price,
    :features::jsonb, :description::jsonb, :categories::jsonb
)
ON CONFLICT (parent_asin) DO NOTHING
""".strip()

SEED_REVIEWS_STR = """
INSERT INTO reviews (
    parent_asin, asin, user_id, rating, title, review_text,
    helpful_vote, verified_purchase, reviewed_at,
    sentiment_label, sentiment_score
) VALUES (
    :parent_asin, :asin, :user_id, :rating, :title, :review_text,
    :helpful_vote, :verified_purchase, :reviewed_at,
    :sentiment_label, :sentiment_score
)
""".strip()

SEED_EMBEDDINGS_STR = """
INSERT INTO product_embeddings (
    parent_asin, embedding, embedding_half, model_name, mlflow_run_id
) VALUES (
    :parent_asin,
    :embedding::vector,
    :embedding_half::halfvec,
    :model_name,
    :mlflow_run_id
)
ON CONFLICT (parent_asin) DO NOTHING
""".strip()

_SUMMARISE_PROMPT_TEMPLATE = """You are a concise product review analyst.
Given the following customer reviews for a product, write a short pros/cons summary.
 
Reviews:
{reviews}
 
Respond in this format:
Pros:
- <point>
Cons:
- <point>
 
Summary:""".strip()


HTTP_REQUEST_DURATION = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration for all FastAPI endpoints",
    labelnames=["method", "endpoint", "status_code"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
)

HTTP_REQUESTS_TOTAL = Counter(
    "http_requests_total",
    "Total HTTP requests received",
    labelnames=["method", "endpoint", "status_code"],
)

HNSW_STAGE1_LATENCY = Histogram(
    "hnsw_stage1_scan_seconds",
    "Time spent traversing the binary-quantised HNSW index (Stage 1 Hamming scan)",
    labelnames=["top_k"],
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0),
)

HNSW_STAGE2_LATENCY = Histogram(
    "hnsw_stage2_rerank_seconds",
    "Time spent on full FP32 cosine re-ranking (Stage 2)",
    labelnames=["top_k"],
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0),
)

DB_QUERY_LATENCY = Histogram(
    "db_query_seconds",
    "End-to-end PostgreSQL query round-trip time",
    labelnames=["query_type"],  # "vector_search" | "keyword" | "reviews" | "products"
    buckets=(0.001, 0.005, 0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5),
)

HNSW_RECALL_RATE = Gauge(
    "hnsw_recall_rate",
    "Fraction of true nearest neighbours returned by binary-quantised HNSW "
    "(updated by periodic Airflow evaluation task)",
    labelnames=["k"],  # evaluated at different k values
)

PG_BUFFER_HIT_RATIO = Gauge(
    "pg_buffer_hit_ratio",
    "PostgreSQL shared_buffers cache hit ratio for product_embeddings table "
    "(updated by periodic Airflow stats task)",
)

PG_INDEX_SIZE_BYTES = Gauge(
    "pg_index_size_bytes",
    "On-disk size of the HNSW index in bytes",
    labelnames=["index_name"],
)

LLM_TTFT = Histogram(
    "llm_time_to_first_token_seconds",
    "Time to First Token (TTFT) — latency from prompt submission to first generated token",
    labelnames=["model_name"],
    buckets=(0.1, 0.25, 0.5, 1.0, 2.0, 4.0, 8.0, 15.0, 30.0),
)

LLM_GENERATION_LATENCY = Histogram(
    "llm_generation_seconds",
    "Total wall-clock time for a complete LLM generation (pros/cons summary)",
    labelnames=["model_name"],
    buckets=(0.5, 1.0, 2.0, 4.0, 8.0, 15.0, 30.0, 60.0),
)

LLM_TOKEN_COUNT = Counter(
    "llm_tokens_total",
    "Total input and output tokens consumed via Hugging Face",
    labelnames=["model_name", "token_type"],  # token_type: "input" | "output"
)

LLM_FAITHFULNESS = Histogram(
    "llm_faithfulness_score",
    "Ragas faithfulness score for LLM-generated summaries (0–1)",
    labelnames=["model_name"],
    buckets=(0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0),
)

LLM_ANSWER_RELEVANCE = Histogram(
    "llm_answer_relevance_score",
    "Ragas answer relevance score for LLM-generated summaries (0–1)",
    labelnames=["model_name"],
    buckets=(0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0),
)

LLM_ERRORS = Counter(
    "llm_errors_total",
    "Number of generation failures (timeouts, OOM, truncation errors)",
    labelnames=["model_name", "error_type"],
)

SEARCH_LATENCY = Histogram(
    "search_execution_seconds",
    "Time spent executing the full hybrid search workflow",
    labelnames=["has_vector", "category_filter"],
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
)

EMBEDDING_LATENCY = Histogram(
    "embedding_encode_seconds",
    "Time to encode a query string into a 384-dim sentence embedding",
    labelnames=["model_name"],
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25),
)

SEARCH_REQUESTS_TOTAL = Counter(
    "search_requests_total",
    "Total number of search requests received",
    labelnames=["search_type"],  # "semantic" | "keyword"
)

SEARCH_ERRORS_TOTAL = Counter(
    "search_errors_total",
    "Number of search requests that resulted in an error",
    labelnames=["search_type", "error_type"],
)

SEARCH_RESULTS_RETURNED = Histogram(
    "search_results_returned",
    "Number of results returned per search request",
    labelnames=["search_type"],
    buckets=(0, 1, 2, 3, 5, 10, 20, 50),
)

EMBEDDING_DRIFT_SCORE = Gauge(
    "embedding_drift_score",
    "Jensen–Shannon divergence of current embedding distribution vs baseline "
    "(updated by Airflow drift monitoring task; higher = more drift)",
    labelnames=["category"],
)

_ALLOWED_COLUMNS: frozenset[str] = frozenset(
    {
        "parent_asin",
        "title",
        "subtitle",
        "author",
        "main_category",
        "store",
        "average_rating",
        "rating_number",
        "price_raw",
        "price",
        "features",
        "description",
        "categories",
        "details",
        "images",
        "bought_together",
        "ingested_at",
    }
)

_DEFAULT_COLUMNS: list[str] = [
    "parent_asin",
    "title",
    "store",
    "average_rating",
    "price",
    "main_category",
]

SQL_SEARCH_QUERY = """
    SET LOCAL hnsw.ef_search = :ef_search;

    WITH candidates AS (
        SELECT
            pe.parent_asin,
            (binary_quantize(pe.embedding)::bit(384))
                <~> (binary_quantize(:query_vector::vector(384))::bit(384))
                AS hamming_dist
        FROM product_embeddings pe
        ORDER BY hamming_dist
        LIMIT :candidate_k
    ),
    reranked AS (
        SELECT
            c.parent_asin,
            pe.embedding <=> :query_vector::vector(384) AS cosine_dist
        FROM candidates c
        JOIN product_embeddings pe ON pe.parent_asin = c.parent_asin
        ORDER BY cosine_dist
        LIMIT :final_k
    )
    SELECT
        {select_cols},
        r.cosine_dist AS _distance
    FROM reranked r
    JOIN products p ON p.parent_asin = r.parent_asin
    WHERE {where_sql}
    ORDER BY r.cosine_dist;
""".strip()

REVIEWS_SQL_QUERY = """
    SELECT review_text
    FROM reviews
    WHERE parent_asin = ANY(:asins)
        AND review_text IS NOT NULL
    ORDER BY helpful_vote DESC
    LIMIT 15
""".strip()

SQL_KEYWORD_SEARCH = """
    SELECT {select_cols}
    FROM products
    WHERE {" AND ".join(where)}
    ORDER BY average_rating DESC NULLS LAST
    LIMIT :limit
""".strip()
