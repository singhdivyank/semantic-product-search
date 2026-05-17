"""
Utility functions involving SQLAlchemy for DAGs
"""

from sqlalchemy import create_engine, text

from consts import (
    INSERT_REVIEWS_TEMPLATE,
    SELECT_PARENT_ASINS,
    UPSERT_PRODUCT_TEMPLATE,
    UPSERT_EMBED_TEMPLATE,
)
from config.read_configs import get_db_configs


def _get_engine():
    """Define SQLAlchemy db engine"""

    db = get_db_configs()
    url = (
        f"postgresql+psycopg2://{db['user']}:{db['password']}"
        f"@{db['host']}:{db['port']}/{db['name']}"
    )
    pool = db.get("pool", [])
    return create_engine(
        url,
        pool_size=pool.get("size", 10),
        max_overflow=pool.get("max_overflow", 5),
        pool_recycle=pool.get("pool_recycle", 3600),
        pool_pre_ping=pool.get("pre_ping", True),
    )


def _embed_buf_res(row: dict) -> dict:
***REMOVED***
        "parent_asin": row["parent_asin"],
        "embedding": row.get("embedding_str"),
        "embedding_half": row.get("embedding_half_str"),
        "model_name": row.get("model_name"),
        "mlflow_run_id": row.get("mlflow_run_id"),
***REMOVED***


select_asins = text(SELECT_PARENT_ASINS)
upsert_product_sql = text(UPSERT_PRODUCT_TEMPLATE)
insert_review_sql = text(INSERT_REVIEWS_TEMPLATE)
upsert_embed_sql = text(UPSERT_EMBED_TEMPLATE)
