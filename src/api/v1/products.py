"""
CRUD and analytics routes for products and reviews.

Endpoints
---------
  GET  /products/                  List products with optional filters
  GET  /products/{parent_asin}     Fetch a single product with reviews
  GET  /products/{parent_asin}/reviews  Paginated review list
  GET  /products/metrics/summary   Aggregate stats: rating dist, price stats
  GET  /products/metrics/latency   Rolling search latency summary from MLTracker
"""

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_db, get_tracker
from src.services.ml_tracking import MLTracker
from src.api.v1.pydantic_classes import (
    ProductSummary,
    ProductDetail,
    ReviewOut,
    MetricsSummary,
)

log = logging.getLogger("app.products")
router = APIRouter(prefix="/products", tags=["products"])


@router.get("/", response_model=list[ProductSummary], summary="List products")
async def list_products(
    main_category: str | None = Query(default=None, description="Filter by category"),
    store: str | None = Query(default=None, description="Filter by store name"),
    min_price: float | None = Query(default=None, ge=0),
    max_price: float | None = Query(default=None, ge=0),
    min_rating: float | None = Query(default=None, ge=1.0, le=5.0),
    limit: int = Query(default=20, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    """
    List products with optional scalar filters.
    Supports pagination via limit/offset.
    """
    where = ["TRUE"]
    params: dict[str, Any] = {"limit": limit, "offset": offset}

    if main_category:
        where.append("main_category ILIKE :category")
        params["category"] = f"%{main_category}%"
    if store:
        where.append("store ILIKE :store")
        params["store"] = f"%{store}%"
    if min_price is not None:
        where.append("price >= :min_price")
        params["min_price"] = min_price
    if max_price is not None:
        where.append("price <= :max_price")
        params["max_price"] = max_price
    if min_rating is not None:
        where.append("average_rating >= :min_rating")
        params["min_rating"] = min_rating

    sql = text(f"""
        SELECT
            parent_asin, title, store, main_category,
            average_rating, price, rating_number
        FROM products
        WHERE {" AND ".join(where)}
        ORDER BY average_rating DESC NULLS LAST
        LIMIT :limit OFFSET :offset
    """)

    result = await db.execute(sql, params)
    return [dict(row) for row in result.mappings().all()]


@router.get(
    "/{parent_asin}", response_model=ProductDetail, summary="Get product detail"
)
async def get_product(
    parent_asin: str,
    include_reviews: bool = Query(default=True, description="Attach recent reviews"),
    review_limit: int = Query(default=5, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Fetch full product metadata and optionally a sample of its reviews.
    """
    product_sql = text("""
        SELECT
            parent_asin, title, subtitle, author,
            main_category, store,
            average_rating, rating_number,
            price, price_raw,
            features, description, categories, details, images
        FROM products
        WHERE parent_asin = :asin
    """)
    result = await db.execute(product_sql, {"asin": parent_asin})
    row = result.mappings().first()

    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product '{parent_asin}' not found.",
        )

    product = dict(row)
    product["reviews"] = []

    if include_reviews:
        reviews_sql = text("""
            SELECT
                review_id, user_id, rating, title, review_text,
                helpful_vote, verified_purchase,
                reviewed_at::text AS reviewed_at,
                sentiment_label, sentiment_score
            FROM reviews
            WHERE parent_asin = :asin
            ORDER BY helpful_vote DESC, reviewed_at DESC
            LIMIT :limit
        """)
        rev_result = await db.execute(
            reviews_sql, {"asin": parent_asin, "limit": review_limit}
        )
        product["reviews"] = [dict(r) for r in rev_result.mappings().all()]

    return product


@router.get(
    "/{parent_asin}/reviews",
    response_model=list[ReviewOut],
    summary="Paginated reviews for a product",
)
async def list_reviews(
    parent_asin: str,
    verified_only: bool = Query(default=False),
    min_rating: float | None = Query(default=None, ge=1.0, le=5.0),
    sentiment: str | None = Query(default=None, pattern="^(positive|negative)$"),
    limit: int = Query(default=20, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    """
    Paginated, filterable review list for a single product.
    """
    where = ["parent_asin = :asin"]
    params: dict[str, Any] = {
        "asin": parent_asin,
        "limit": limit,
        "offset": offset,
    }

    if verified_only:
        where.append("verified_purchase = TRUE")
    if min_rating is not None:
        where.append("rating >= :min_rating")
        params["min_rating"] = min_rating
    if sentiment:
        where.append("sentiment_label = :sentiment")
        params["sentiment"] = sentiment

    sql = text(f"""
        SELECT
            review_id, user_id, rating, title, review_text,
            helpful_vote, verified_purchase,
            reviewed_at::text AS reviewed_at,
            sentiment_label, sentiment_score
        FROM reviews
        WHERE {" AND ".join(where)}
        ORDER BY helpful_vote DESC, reviewed_at DESC
        LIMIT :limit OFFSET :offset
    """)

    result = await db.execute(sql, params)
    return [dict(r) for r in result.mappings().all()]


@router.get(
    "/metrics/summary",
    response_model=MetricsSummary,
    summary="Catalogue-level aggregate metrics",
)
async def metrics_summary(db: AsyncSession = Depends(get_db)) -> dict:
    """
    Returns catalogue-wide statistics:
      - total product / review / embedding counts
      - overall average rating
      - rating distribution (1–5 stars) with average sentiment per bucket
      - price min / max / avg / median
    """
    counts_sql = text("""
        SELECT
            (SELECT COUNT(*) FROM products)         AS total_products,
            (SELECT COUNT(*) FROM reviews)          AS total_reviews,
            (SELECT COUNT(*) FROM product_embeddings) AS total_embeddings,
            (SELECT ROUND(AVG(average_rating)::numeric, 2) FROM products) AS avg_rating
    """)
    counts = dict((await db.execute(counts_sql)).mappings().first())

    rating_dist_sql = text("""
        SELECT
            FLOOR(rating) AS rating,
            COUNT(*)      AS review_count,
            ROUND(AVG(sentiment_score)::numeric, 4) AS avg_sentiment
        FROM reviews
        GROUP BY FLOOR(rating)
        ORDER BY rating
    """)
    rating_rows = [
        dict(r) for r in (await db.execute(rating_dist_sql)).mappings().all()
    ]

    price_sql = text("""
        SELECT
            ROUND(MIN(price)::numeric, 2)    AS min_price,
            ROUND(MAX(price)::numeric, 2)    AS max_price,
            ROUND(AVG(price)::numeric, 2)    AS avg_price,
            ROUND(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY price)::numeric, 2)
                                             AS median_price
        FROM products
        WHERE price IS NOT NULL
    """)
    price_row = dict((await db.execute(price_sql)).mappings().first())

    return {
        **counts,
        "rating_distribution": rating_rows,
        "price_summary": price_row,
    }


@router.get(
    "/metrics/latency",
    summary="Rolling search latency stats",
)
async def metrics_latency(tracker: MLTracker = Depends(get_tracker)) -> dict:
    """
    Returns rolling p50/p95/mean latency for each pipeline stage:
      embedding → stage1 (binary scan) → stage2 (cosine rerank) → generation → e2e
    Populated in-process from the last 200 requests.
    """
    return tracker.latency_summary()
