from pydantic import BaseModel, Field
from typing import Any


class ProductSummary(BaseModel):
    parent_asin: str
    title: str | None
    store: str | None
    main_category: str | None
    average_rating: float | None
    price: float | None
    rating_number: int | None


class ReviewOut(BaseModel):
    review_id: int
    user_id: str
    rating: float
    title: str | None
    review_text: str | None
    helpful_vote: int
    verified_purchase: bool
    reviewed_at: str | None
    sentiment_label: str | None
    sentiment_score: float | None


class ProductDetail(ProductSummary):
    subtitle: str | None
    author: str | None
    features: list | None
    description: list | None
    categories: list | None
    details: dict | None
    images: list | None
    reviews: list[ReviewOut] = []


class RatingDistribution(BaseModel):
    rating: float
    review_count: int
    avg_sentiment: float | None


class PriceSummary(BaseModel):
    min_price: float | None
    max_price: float | None
    avg_price: float | None
    median_price: float | None


class MetricsSummary(BaseModel):
    total_products: int
    total_reviews: int
    total_embeddings: int
    avg_rating: float | None
    rating_distribution: list[RatingDistribution]
    price_summary: PriceSummary


class SearchRequest(BaseModel):
    query: str = Field(
        ..., min_length=1, max_length=500, description="Natural language search query"
    )
    top_k: int = Field(
        default=0, ge=1, le=50, description="Number of results to return"
    )
    max_price: float | None = Field(
        default=None, ge=0, description="Hard price filter (≤ max_price)"
    )
    min_rating: float | None = Field(
        default=None, ge=1.0, le=5.0, description="Minimum average rating filter"
    )
    only_in_stock: bool = Field(
        default=False, description="Filter to rating_number > 0 as stock proxy"
    )
    fields: list[str] = Field(
        default_factory=list, description="Columns to return; empty = defaults"
    )
    summarise: bool = Field(default=True, description="Generate LLM pros/cons summary")


class SearchResult(BaseModel):
    products: list[dict[str, Any]]
    summary: str | None
    latency_ms: dict[str, float]
    top_k_returned: int
