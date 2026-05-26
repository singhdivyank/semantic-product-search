"""
SQLAlchemy ORM class for the reviews table.
Consumed by Alembic (db/alembic/), FastAPI (src/), and Airflow load task.

Table
------
  reviews            — user reviews with sentiment (Gift_Cards.jsonl)

pgvector types
--------------
  Vector(384)    — full-precision cosine re-ranking (Stage 2)
  HalfVector(384)— FP16 downcast stored for HNSW binary quantisation (Stage 1)
  Falls back to Text if pgvector-python is not installed (DDL in Alembic
  migration handles the real column type).
"""

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Column,
    ForeignKey,
    Integer,
    Numeric,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlalchemy.orm import relationship

from db.tables.base import Base


class Reviews(Base):
    """
    One row per user review.
    Source: Gift_Cards.jsonl, enriched with sentiment by dags/src/transformer.py
    """

    __tablename__ = "reviews"

    review_id = Column(BigInteger, primary_key=True, autoincrement=True)
    parent_asin = Column(
        Text,
        ForeignKey("products.parent_asin", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    asin = Column(Text)
    user_id = Column(Text, nullable=False, index=True)
    rating = Column(Numeric(2, 1), nullable=False)
    title = Column(Text)
    review_text = Column(Text)  # renamed from 'text' (SQL reserved word)
    helpful_vote = Column(Integer, nullable=False, default=0)
    verified_purchase = Column(Boolean, nullable=False, default=False, index=True)
    timestamp_raw = Column(BigInteger)  # original Unix ms from dataset
    reviewed_at = Column(TIMESTAMP(timezone=True), index=True)
    sentiment_label = Column(Text)  # 'positive' | 'negative'
    sentiment_score = Column(Numeric(6, 4))
    ingested_at = Column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now()
    )

    product = relationship("Product", back_populates="reviews")

    __table_args__ = (
        CheckConstraint("rating BETWEEN 1 AND 5", name="ck_reviews_rating"),
    )

    def __repr__(self) -> str:
        return f"<Review id={self.review_id} asin={self.parent_asin!r} rating={self.rating}>"
