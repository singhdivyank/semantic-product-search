"""
SQLAlchemy ORM class for the products table.
Consumed by Alembic (db/alembic/), FastAPI (src/), and Airflow load task.

Table
------
  products           — product metadata (meta_Gift_Cards.jsonl)

pgvector types
--------------
  Vector(384)    — full-precision cosine re-ranking (Stage 2)
  HalfVector(384)— FP16 downcast stored for HNSW binary quantisation (Stage 1)
  Falls back to Text if pgvector-python is not installed (DDL in Alembic
  migration handles the real column type).
"""

from sqlalchemy import Column, Text, Numeric, Integer, func
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP
from sqlalchemy.orm import relationship

from db.tables.base import Base


class Product(Base):
    """One row per unique Amazon product identified by parent_asin."""

    __tablename__ = "products"

    parent_asin = Column(Text, primary_key=True)
    title = Column(Text)
    subtitle = Column(Text)
    author = Column(Text)
    main_category = Column(Text, index=True)
    store = Column(Text, index=True)
    average_rating = Column(Numeric(3, 1), index=True)
    rating_number = Column(Integer)
    price_raw = Column(Text)
    price = Column(Numeric(10, 2), index=True)
    features = Column(JSONB)
    description = Column(JSONB)
    categories = Column(JSONB)
    details = Column(JSONB)
    images = Column(JSONB)
    videos = Column(JSONB)
    bought_together = Column(JSONB)
    ingested_at = Column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now()
    )

    embedding = relationship(
        "ProductEmbedding",
        back_populates="product",
        uselist=False,
        cascade="all, delete-orphan",
    )
    reviews = relationship(
        "Review",
        back_populates="product",
        cascade="all, delete-orphan",
    )

    __table_args__ = ()

    def __repr__(self) -> str:
        return f"<Product asin={self.parent_asin!r} title={self.title!r}>"
