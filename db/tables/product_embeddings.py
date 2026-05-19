"""
SQLAlchemy ORM class for the product_embeddings table.
Consumed by Alembic (db/alembic/), FastAPI (src/), and Airflow load task.

Table
------
  product_embeddings — 384-dim FP32 vectors + FP16 halfvec

pgvector types
--------------
  Vector(384)    — full-precision cosine re-ranking (Stage 2)
  HalfVector(384)— FP16 downcast stored for HNSW binary quantisation (Stage 1)
  Falls back to Text if pgvector-python is not installed (DDL in Alembic
  migration handles the real column type).
"""

from pgvector.sqlalchemy import Vector, HALFVEC
from sqlalchemy import Column, ForeignKey, Text, func
from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlalchemy.orm import relationship

from base import Base

_VECTOR_TYPE = Vector(384)
_HALFVECTOR_TYPE = HALFVEC(384)


class ProductEmbedding(Base):
    """
    384-dim sentence embedding per product.
    Populated by the Airflow embed task using all-MiniLM-L6-v2.

    Two-stage hybrid query support (from scoping doc):
      Stage 1 — HNSW index on binary_quantize(embedding)  → fast Hamming scan
      Stage 2 — Cosine rerank on full embedding            → precise top-k
    """

    __tablename__ = "product_embeddings"

    parent_asin = Column(
        Text,
        ForeignKey("products.parent_asin", ondelete="CASCADE"),
        primary_key=True,
    )
    # FP32, 384-dim
    embedding = Column(_VECTOR_TYPE, nullable=False)
    # FP16, 384-dim
    embedding_half = Column(_HALFVECTOR_TYPE)
    model_name = Column(
        Text,
        nullable=False,
        default="sentence-transformers/all-MiniLM-L6-v2",
    )
    model_version = Column(Text)
    mlflow_run_id = Column(Text)
    ingested_at = Column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now()
    )

    product = relationship("Product", back_populates="embedding")

    def __repr__(self) -> str:
        return f"<ProductEmbedding asin={self.parent_asin!r} model={self.model_name!r}>"
