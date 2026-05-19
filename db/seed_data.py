"""
Populates a local PostgreSQL instance with a small, realistic Gift Cards
dataset for development and integration testing.

Usage
-----
    # Apply schema first
    cd db && alembic upgrade head && cd ..

    # Seed
    python db/seed_data.py --db-url "postgresql://postgres:postgres@localhost/amazon_reviews"

    # Or with a .env file
    python db/seed_data.py

What it creates
---------------
  - 10 products     (realistic Gift Cards metadata)
  - 30 reviews      (~3 per product, varied ratings and sentiment)
  - 10 embeddings   (random unit vectors at 384-dim — no model required)

The random embeddings let you test vector similarity queries without
downloading the full embedding model.
"""

import logging

from sqlalchemy import create_engine, text

from config.read_configs import get_db_url
from consts import (
    PRODUCTS,
    SEED_EMBEDDINGS_STR,
    SEED_PRODUCTS_STR,
    SEED_REVIEWS_STR,
)
from seed_helpers import (
    get_embedding_rows,
    get_product_rows,
    get_reviews_rows,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger(__name__)


def seed_products(conn) -> None:
    log.info("Seeding %d products...", len(PRODUCTS))
    stmt = text(SEED_PRODUCTS_STR)
    rows = get_product_rows()
    conn.execute(stmt, rows)
    log.info("Products seeded")


def seed_reviews(conn) -> None:
    log.info("Seeding reviews (~3 per product)...")
    stmt = text(SEED_REVIEWS_STR)
    rows = get_reviews_rows()
    conn.execute(stmt, rows)
    log.info("Reviews seeded: %d rows", len(rows))


def seed_product_embeddings(conn) -> None:
    log.info("Seeding random unit-norm embeddings (384-dim)...")
    stmt = text(SEED_EMBEDDINGS_STR)
    rows = get_embedding_rows()
    conn.execute(stmt, rows)
    log.info("Embeddings seeded: %d rows", len(rows))


def run_seed():

    db_url = get_db_url()
    engine = create_engine(db_url, pool_pre_ping=True)
    with engine.begin() as conn:

        seed_products(conn)
        seed_reviews(conn)
        seed_product_embeddings(conn)

    log.info("Seed complete")
