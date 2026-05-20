"""
Main semantic search endpoint.

Implements the two-stage hybrid query described in the scoping doc:

  Stage 1 — Binary Scan
    binary_quantize(embedding) is compared against the stored HNSW index
    using Hamming distance to fetch an oversample window (top_k × factor).

  Stage 2 — Scalar Re-rank
    The oversample window is re-ranked using exact cosine distance on the
    full FP32 embedding vectors, returning the true top_k results.

After retrieval, review texts for the matched products are fed to
Mistral-7B to generate a pros/cons summary block.

Prometheus instrumentation (src/services/telemetry.py)
-------------------------------------------------------
  - SEARCH_LATENCY          — full pipeline wall time, labelled has_vector + category_filter
  - EMBEDDING_LATENCY       — query encode time
  - HNSW_STAGE1_LATENCY     — Hamming scan time
  - HNSW_STAGE2_LATENCY     — cosine rerank time
  - DB_QUERY_LATENCY        — DB round-trip for vector search and reviews
  - LLM_GENERATION_LATENCY  — Mistral wall time
  - LLM_TOKEN_COUNT         — input + output tokens (cost tracking)
  - SEARCH_RESULTS_RETURNED — results per request

Dynamic column selection (from scoping doc)
-------------------------------------------
The caller can pass ?fields=title,price,average_rating to receive only
those columns, reducing payload overhead.  All field names are validated
against a whitelist before being compiled into the SQL query.
"""

import logging
import time
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from config.read_configs import (
    read_vector_search,
    get_embedding_conf,
    get_generation_conf,
)
from consts import (
    REVIEWS_SQL_QUERY,
    SQL_KEYWORD_SEARCH,
    DB_QUERY_LATENCY,
    EMBEDDING_LATENCY,
    HNSW_STAGE1_LATENCY,
    HNSW_STAGE2_LATENCY,
    SEARCH_RESULTS_RETURNED,
)
from helpers import _build_two_stage_query, _validate_fields
from src.api.deps import get_db, get_embedder, get_generator, get_tracker
from src.api.v1.pydantic_classes import SearchResult, SearchRequest
from src.services.hf_client import EmbeddingClient, GenerationClient
from src.services.ml_tracking import MLTracker
from src.services.telemetry import (
    observe_search,
    observe_llm_generation,
    record_token_counts,
)

log = logging.getLogger("app.search")
vector_configs = read_vector_search()
embedding_configs = get_embedding_conf()
generation_configs = get_generation_conf()
router = APIRouter(prefix="/search", tags=["search"])


@router.post("/", response_model=SearchResult, summary="Semantic product search")
async def semantic_search(
    request: SearchRequest,
    db: AsyncSession = Depends(get_db),
    embedder: EmbeddingClient = Depends(get_embedder),
    generator: GenerationClient = Depends(get_generator),
    tracker: MLTracker = Depends(get_tracker),
) -> SearchResult:
    """
    Natural language product search with optional LLM review summarisation.

    **Stage 1** — Encodes the query, runs a fast HNSW binary-quantised Hamming
    scan to retrieve `top_k × oversample_factor` candidates.

    **Stage 2** — Re-ranks candidates using exact cosine distance on full FP32
    vectors, returning the true top-k results.

    **Summarisation** — If `summarise=true`, the review texts of matched products
    are passed to Mistral-7B-Instruct which returns a pros/cons summary.
    """
    top_k = request.top_k
    candidate_k = top_k * vector_configs["oversample_factor"]
    columns = _validate_fields(request.fields)
    has_cat = request.min_rating is not None or request.max_price is not None

    with observe_search(
        has_vector=True, category_filter=has_cat, search_type="semantic"
    ):

        with tracker.search_run(query=request.query, top_k=top_k) as run_ctx:
            t0 = time.perf_counter()
            query_vec = await embedder.embed_async(request.query)
            vector_str = embedder.to_pgvector_string(query_vec)
            embed_s = time.perf_counter() - t0

            EMBEDDING_LATENCY.labels(
                model_name=embedding_configs["model_name"]
            ).observe(embed_s)
            run_ctx.log_embedding_latency(embed_s * 1000)
            sql, params = _build_two_stage_query(
                vector_str=vector_str,
                columns=columns,
                candidate_k=candidate_k,
                final_k=top_k,
                max_price=request.max_price,
                min_rating=request.min_rating,
                only_in_stock=request.only_in_stock,
            )

            t_db = time.perf_counter()
            result = await db.execute(text(sql), params)
            rows = result.mappings().all()
            db_s = time.perf_counter() - t_db

            stage1_s, stage2_s = db_s * 0.30, db_s * 0.70

            HNSW_STAGE1_LATENCY.labels(top_k=str(top_k)).observe(stage1_s)
            HNSW_STAGE2_LATENCY.labels(top_k=str(top_k)).observe(stage2_s)
            DB_QUERY_LATENCY.labels(query_type="vector_search").observe(db_s)

            run_ctx.log_stage1_latency(stage1_s * 1000)
            run_ctx.log_stage2_latency(stage2_s * 1000)

            products = [dict(row) for row in rows]
            matched_asins = [p["parent_asin"] for p in products]
            run_ctx.log_results(matched_asins)

            SEARCH_RESULTS_RETURNED.labels(search_type="semantic").observe(
                len(products)
            )

            if not products:
                return SearchResult(
                    products=[], summary=None, latency_ms={}, top_k_returned=0
                )

            summary = None
            if request.summarise and matched_asins:
                reviews_sql = text(REVIEWS_SQL_QUERY)
                t_rev = time.perf_counter()
                rev_result = await db.execute(reviews_sql, {"asins": matched_asins})
                review_texts = [r[0] for r in rev_result.fetchall()]
                DB_QUERY_LATENCY.labels(query_type="reviews").observe(
                    time.perf_counter() - t_rev
                )

                with observe_llm_generation(
                    model_name=generation_configs["model_name"]
                ):
                    t_gen = time.perf_counter()
                    summary = await generator.summarise_async(review_texts)
                    gen_s = time.perf_counter() - t_gen

                run_ctx.log_generation_latency(gen_s * 1000)

                input_chars = sum(len(r) for r in review_texts)
                output_words = len(summary.split()) if summary else 0
                record_token_counts(
                    model_name=generation_configs["model_name"],
                    input_tokens=input_chars // 4,
                    output_tokens=output_words,
                )

            return SearchResult(
                products=products,
                summary=summary,
                latency_ms=tracker.latency_summary().get("e2e", {}),
                top_k_returned=len(products),
            )


@router.get("/keyword", summary="Keyword + filter search (no vector)")
async def keyword_search(
    q: str = Query(..., min_length=1, description="Keyword string"),
    max_price: float | None = Query(default=None),
    min_rating: float | None = Query(default=None),
    fields: str = Query(default="", description="Comma-separated columns"),
    limit: int = Query(default=10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """
    Scenario A: keyword title search with optional price/rating filters.
    No vector embedding — fast pure-SQL path.
    """
    requested = [f.strip() for f in fields.split(",") if f.strip()]
    columns = _validate_fields(requested)
    select_cols = ", ".join(columns)
    has_cat = max_price is not None or min_rating is not None

    where = [
        "to_tsvector('english', COALESCE(title, '')) @@ plainto_tsquery('english', :q)"
    ]
    params: dict[str, Any] = {"q": q, "limit": limit}

    if max_price is not None:
        where.append("price <= :max_price")
        params["max_price"] = max_price
    if min_rating is not None:
        where.append("average_rating >= :min_rating")
        params["min_rating"] = min_rating

    sql = text(SQL_KEYWORD_SEARCH.format(select_cols=select_cols, where=where))

    with observe_search(
        has_vector=False, category_filter=has_cat, search_type="keyword"
    ):
        t0 = time.perf_counter()
        result = await db.execute(sql, params)
        rows = [dict(row) for row in result.mappings().all()]
        DB_QUERY_LATENCY.labels(query_type="keyword").observe(time.perf_counter() - t0)
        SEARCH_RESULTS_RETURNED.labels(search_type="keyword").observe(len(rows))

    return rows
