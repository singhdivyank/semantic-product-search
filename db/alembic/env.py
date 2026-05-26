"""
db/alembic/env.py
=================
Alembic migration environment.
Reads the database URL from environment variables and wires in the
ORM Base for autogenerate support.

Run migrations
--------------
    alembic -c db/alembic.ini upgrade head
    alembic -c db/alembic.ini revision --autogenerate -m "add column x"
    alembic -c db/alembic.ini downgrade -1
"""

from __future__ import annotations

import os
import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import engine_from_config, pool

PROJECT_ROOT = str(Path(__file__).resolve().parents[2])
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from db.tables.base import Base

config = context.config

_db_url = (
    f"postgresql+psycopg2://"
    f"{os.environ.get('DB_USER', 'postgres')}:"
    f"{os.environ.get('DB_PASSWORD', 'postgres')}@"
    f"{os.environ.get('DB_HOST', 'localhost')}:"
    f"{os.environ.get('DB_PORT', '5432')}/"
    f"{os.environ.get('DB_NAME', 'amazon_reviews')}"
)
config.set_main_option("sqlalchemy.url", _db_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

_EXCLUDED_INDEXES = {
    "idx_product_embeddings_hnsw_binary",
    "idx_product_embeddings_ivfflat",
    "idx_reviews_fts",
    "idx_products_features_gin",
    "idx_products_categories_gin",
    "idx_products_average_rating",
    "idx_products_main_category",
    "idx_products_price",
    "idx_products_store",
    "idx_reviews_parent_asin",
    "idx_reviews_rating",
    "idx_reviews_reviewed_at",
    "idx_reviews_user_id",
    "idx_reviews_verified",
}


def _include_object(object, name, type_, reflected, compare_to):
    """
    Called by Alembic autogenerate for every DB object it considers.
    Return False to exclude an object from migration generation.
    """
    if type_ == "index" and name in _EXCLUDED_INDEXES:
        return False
    return True


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        include_object=_include_object,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            include_object=_include_object,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
