from prometheus_client import Counter, Gauge, Histogram

DB_QUERY_LATENCY = Histogram(
    "db_query_seconds",
    "End-to-end PostgreSQL query round-trip time",
    labelnames=["query_type"],
    buckets=(0.001, 0.005, 0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5),
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

HNSW_RECALL_RATE = Gauge(
    "hnsw_recall_rate",
    "Fraction of true nearest neighbours returned by binary-quantised HNSW",
    labelnames=["k"],
)

PG_BUFFER_HIT_RATIO = Gauge(
    "pg_buffer_hit_ratio",
    "PostgreSQL shared_buffers cache hit ratio for product_embeddings table",
)

PG_INDEX_SIZE_BYTES = Gauge(
    "pg_index_size_bytes",
    "On-disk size of the HNSW index in bytes",
    labelnames=["index_name"],
)

LLM_TTFT = Histogram(
    "llm_time_to_first_token_seconds",
    "Time to First Token (TTFT)",
    labelnames=["model_name"],
    buckets=(0.1, 0.25, 0.5, 1.0, 2.0, 4.0, 8.0, 15.0, 30.0),
)

LLM_GENERATION_LATENCY = Histogram(
    "llm_generation_seconds",
    "Total wall-clock time for a complete LLM generation",
    labelnames=["model_name"],
    buckets=(0.5, 1.0, 2.0, 4.0, 8.0, 15.0, 30.0, 60.0),
)

LLM_TOKEN_COUNT = Counter(
    "llm_tokens_total",
    "Total input and output tokens consumed via Hugging Face",
    labelnames=["model_name", "token_type"],
)

LLM_FAITHFULNESS = Histogram(
    "llm_faithfulness_score",
    "Ragas faithfulness score for LLM-generated summaries (0-1)",
    labelnames=["model_name"],
    buckets=(0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0),
)

LLM_ANSWER_RELEVANCE = Histogram(
    "llm_answer_relevance_score",
    "Ragas answer relevance score for LLM-generated summaries (0-1)",
    labelnames=["model_name"],
    buckets=(0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0),
)

LLM_ERRORS = Counter(
    "llm_errors_total",
    "Number of generation failures",
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
    labelnames=["search_type"],
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
    "Jensen-Shannon divergence of current embedding distribution vs baseline",
    labelnames=["category"],
)

REVIEWS_SQL_QUERY = """
    SELECT review_text
    FROM reviews
    WHERE parent_asin = ANY(:asins)
        AND review_text IS NOT NULL
    ORDER BY helpful_vote DESC
    LIMIT 15
""".strip()

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

SQL_KEYWORD_SEARCH = """
    SELECT {select_cols}
    FROM products
    WHERE {" AND ".join(where)}
    ORDER BY average_rating DESC NULLS LAST
    LIMIT :limit
""".strip()

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
