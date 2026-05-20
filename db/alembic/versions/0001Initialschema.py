"""Initial schema: products, reviews, product_embeddings with pgvector

Revision ID: 0001_initial_schema
Revises:
Create Date: 2024-01-01 00:00:00.000000

Creates
-------
  - pgvector extension
  - products table + scalar and GIN indexes
  - reviews table + FTS GIN index + sentiment columns
  - product_embeddings table + HNSW (binary-quantised) + IVFFlat indexes

Apply
-----
    alembic -c db/alembic.ini upgrade head

Rollback
--------
    alembic -c db/alembic.ini downgrade base
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # pgvector extension
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # products
    op.create_table(
        "products",
        sa.Column("parent_asin", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column("subtitle", sa.Text(), nullable=True),
        sa.Column("author", sa.Text(), nullable=True),
        sa.Column("main_category", sa.Text(), nullable=True),
        sa.Column("store", sa.Text(), nullable=True),
        sa.Column("average_rating", sa.Numeric(3, 1), nullable=True),
        sa.Column("rating_number", sa.Integer(), nullable=True),
        sa.Column("price_raw", sa.Text(), nullable=True),
        sa.Column("price", sa.Numeric(10, 2), nullable=True),
        sa.Column("features", postgresql.JSONB(), nullable=True),
        sa.Column("description", postgresql.JSONB(), nullable=True),
        sa.Column("categories", postgresql.JSONB(), nullable=True),
        sa.Column("details", postgresql.JSONB(), nullable=True),
        sa.Column("images", postgresql.JSONB(), nullable=True),
        sa.Column("videos", postgresql.JSONB(), nullable=True),
        sa.Column("bought_together", postgresql.JSONB(), nullable=True),
        sa.Column(
            "ingested_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.PrimaryKeyConstraint("parent_asin"),
    )
    op.create_index("idx_products_main_category", "products", ["main_category"])
    op.create_index("idx_products_price", "products", ["price"])
    op.create_index("idx_products_average_rating", "products", ["average_rating"])
    op.create_index("idx_products_store", "products", ["store"])
    op.create_index(
        "idx_products_features_gin",
        "products",
        ["features"],
        postgresql_using="gin",
    )
    op.create_index(
        "idx_products_categories_gin",
        "products",
        ["categories"],
        postgresql_using="gin",
    )

    # reviews
    op.create_table(
        "reviews",
        sa.Column("review_id", sa.BigInteger(), nullable=False, autoincrement=True),
        sa.Column("parent_asin", sa.Text(), nullable=False),
        sa.Column("asin", sa.Text(), nullable=True),
        sa.Column("user_id", sa.Text(), nullable=False),
        sa.Column("rating", sa.Numeric(2, 1), nullable=False),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column("review_text", sa.Text(), nullable=True),
        sa.Column("helpful_vote", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "verified_purchase", sa.Boolean(), nullable=False, server_default="false"
        ),
        sa.Column("timestamp_raw", sa.BigInteger(), nullable=True),
        sa.Column("reviewed_at", sa.TIMESTAMP(timezone=True), nullable=True),
        # Sentiment columns added by transform task
        sa.Column("sentiment_label", sa.Text(), nullable=True),
        sa.Column("sentiment_score", sa.Numeric(6, 4), nullable=True),
        sa.Column(
            "ingested_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.PrimaryKeyConstraint("review_id"),
        sa.ForeignKeyConstraint(
            ["parent_asin"], ["products.parent_asin"], ondelete="CASCADE"
        ),
        sa.CheckConstraint("rating BETWEEN 1 AND 5", name="ck_reviews_rating"),
    )
    op.create_index("idx_reviews_parent_asin", "reviews", ["parent_asin"])
    op.create_index("idx_reviews_user_id", "reviews", ["user_id"])
    op.create_index("idx_reviews_rating", "reviews", ["rating"])
    op.create_index("idx_reviews_reviewed_at", "reviews", ["reviewed_at"])
    op.create_index("idx_reviews_verified", "reviews", ["verified_purchase"])
    # Full-text search index on review body
    op.execute("""
        CREATE INDEX idx_reviews_fts
            ON reviews
            USING GIN (to_tsvector('english', COALESCE(review_text, '')))
    """)

    # product_embeddings
    # Declare as Text first, then ALTER to vector/halfvec types
    # (Alembic's create_table doesn't know these dialect types)
    op.create_table(
        "product_embeddings",
        sa.Column("parent_asin", sa.Text(), nullable=False),
        sa.Column("embedding", sa.Text(), nullable=False),
        sa.Column("embedding_half", sa.Text(), nullable=True),
        sa.Column(
            "model_name",
            sa.Text(),
            nullable=False,
            server_default="sentence-transformers/all-MiniLM-L6-v2",
        ),
        sa.Column("model_version", sa.Text(), nullable=True),
        sa.Column("mlflow_run_id", sa.Text(), nullable=True),
        sa.Column(
            "ingested_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.PrimaryKeyConstraint("parent_asin"),
        sa.ForeignKeyConstraint(
            ["parent_asin"], ["products.parent_asin"], ondelete="CASCADE"
        ),
    )

    # Alter to pgvector column types
    op.execute(
        "ALTER TABLE product_embeddings "
        "ALTER COLUMN embedding      TYPE vector(384)   USING embedding::vector(384)"
    )
    op.execute(
        "ALTER TABLE product_embeddings "
        "ALTER COLUMN embedding_half TYPE halfvec(384)  USING embedding_half::halfvec(384)"
    )

    # HNSW index — binary-quantised for Stage 1 fast Hamming pre-selection
    op.execute("""
        CREATE INDEX idx_product_embeddings_hnsw_binary
            ON product_embeddings
            USING hnsw ((binary_quantize(embedding)::bit(384)) bit_hamming_ops)
            WITH (m = 16, ef_construction = 64)
    """)

    # IVFFlat index on full FP32 vectors — Stage 2 cosine re-ranking
    op.execute("""
        CREATE INDEX idx_product_embeddings_ivfflat
            ON product_embeddings
            USING ivfflat (embedding vector_cosine_ops)
            WITH (lists = 50)
    """)


def downgrade() -> None:
    op.drop_table("product_embeddings")
    op.drop_table("reviews")
    op.drop_table("products")
    op.execute("DROP EXTENSION IF EXISTS vector")
