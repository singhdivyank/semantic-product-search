import json
import logging
import re
from datetime import datetime, timezone
from typing import Any, Optional

from config.read_configs import get_embedding_conf, read_ingestion_configs
from dags.src.helpers import _open_jsonl
from dags.tasks.alchemy_helpers import (
    _get_engine,
    _embed_buf_res,
    insert_review_sql,
    upsert_product_sql,
    upsert_embed_sql,
    select_asins,
)

log = logging.getLogger("pipeline.dag")


def _parse_price(raw: Any) -> float | None:
    if raw is None or str(raw).strip().lower() in ("none", ""):
        return None
    cleaned = re.sub(r"[,$]", "", str(raw))
    m = re.search(r"\d+(?:\.\d+)?", cleaned)
    return float(m.group()) if m else None


def _buf_res(row: dict) -> dict:

    def _parse_ts(ts: Any) -> Optional[datetime]:
        if ts is None:
            return None
        try:
            return datetime.fromtimestamp(int(ts) / 1000, tz=timezone.utc)
        except Exception:
            try:
                return datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
            except Exception:
                return None

    ts_raw = row.get("timestamp")

    return {
        "parent_asin": row["parent_asin"],
        "asin": row.get("asin"),
        "user_id": row.get("user_id"),
        "rating": float(row.get("rating", 0)),
        "title": row.get("title"),
        "review_text": row.get("text"),
        "helpful_vote": int(row.get("helpful_vote") or 0),
        "verified_purchase": bool(row.get("verified_purchase", False)),
        "timestamp_raw": int(ts_raw) if ts_raw is not None else None,
        "reviewed_at": _parse_ts(ts_raw),
        "sentiment_label": row.get("sentiment_label"),
        "sentiment_score": row.get("sentiment_score"),
    }


def _get_buf_res(row: dict):
    price_raw = row.get("price")

    return {
        "parent_asin": row.get("parent_asin"),
        "title": row.get("title"),
        "subtitle": row.get("subtitle"),
        "author": row.get("author"),
        "main_category": row.get("main_category"),
        "store": row.get("store"),
        "average_rating": row.get("average_rating"),
        "rating_number": row.get("rating_number"),
        "price_raw": str(price_raw) if price_raw is not None else None,
        "price": _parse_price(price_raw),
        **{
            k: json.dumps(row.get(k)) if row.get(k) is not None else None
            for k in (
                "features",
                "description",
                "categories",
                "details",
                "images",
                "videos",
                "bought_together",
            )
        },
    }


def task_load(**context) -> None:
    """Bulk UPSERT products, reviews (+ sentiment), and embeddings into Cloud SQL"""

    buf: list[dict] = []
    products_loaded: int = 0

    ingestion_configs = read_ingestion_configs()
    embedding_config = get_embedding_conf()

    clean_meta_path = ingestion_configs["clean_meta_path"]
    clean_reviews_path = ingestion_configs["clean_reviews_path"]
    chunk_size = embedding_config["chunk_size"]
    embeddings_path = embedding_config["embeddings_path"]

    log.info("Loading products from %s", clean_meta_path)

    engine = _get_engine()
    with engine.begin() as conn:
        for row in _open_jsonl(clean_meta_path):
            buf.append(_get_buf_res(row))
            if len(buf) >= chunk_size:
                conn.execute(upsert_product_sql, buf)
                products_loaded += len(buf)
                buf.clear()
        if buf:
            conn.execute(upsert_product_sql, buf)
            products_loaded += len(buf)

    log.info("Products loaded: %d", products_loaded)
    log.info("Loading reviews from %s", clean_reviews_path)

    with engine.connect() as conn:
        buf = []
        reviews_loaded = 0

        valid_asins = {r[0] for r in conn.execute(select_asins)}
        with engine.begin() as conn:
            for row in _open_jsonl(clean_reviews_path):
                if row.get("parent_asin") not in valid_asins:
                    continue
                buf.append(_buf_res(row=row))
                if len(buf) >= chunk_size:
                    conn.execute(insert_review_sql, buf)
                    reviews_loaded += len(buf)
                    buf.clear()
            if buf:
                conn.execute(insert_review_sql, buf)
                reviews_loaded += len(buf)

    log.info("Reviews loaded: %d", reviews_loaded)
    log.info("Loading embeddings from %s", embeddings_path)

    embeddings_loaded = 0
    buf = []
    with engine.begin() as conn:
        for row in _open_jsonl(embeddings_path):
            if row.get("parent_asin") not in valid_asins:
                continue
            buf.append(_embed_buf_res(row=row))
            if len(buf) >= chunk_size:
                conn.execute(upsert_embed_sql, buf)
                embeddings_loaded += len(buf)
                buf.clear()
        if buf:
            conn.execute(upsert_embed_sql, buf)
            embeddings_loaded += len(buf)

    log.info("Embeddings loaded: %d", embeddings_loaded)
    log.info(
        "Load complete — products: %d | reviews: %d | embeddings: %d",
        products_loaded,
        reviews_loaded,
        embeddings_loaded,
    )
