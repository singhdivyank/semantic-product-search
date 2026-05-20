import json
import random
import string
from datetime import datetime, timezone

import numpy as np

from consts import PRODUCTS, REVIEW_TEMPLATES


def get_embedding_rows() -> list[dict]:

    def _random_unit_vector(dim: int = 384) -> str:
        """Generate a random unit-norm vector in pgvector string format."""
        vec = np.random.randn(dim).astype(np.float32)
        vec /= np.linalg.norm(vec)
        return "[" + ",".join(f"{v:.6f}" for v in vec.tolist()) + "]"

    return [
        {
            "parent_asin": p["parent_asin"],
            "embedding": _random_unit_vector(384),
            "embedding_half": _random_unit_vector(384),
            "model_name": "sentence-transformers/all-MiniLM-L6-v2",
            "mlflow_run_id": "seed-run-local",
        }
        for p in PRODUCTS
    ]


def get_product_rows() -> list[dict]:
    rows = []
    for product in PRODUCTS:
        rows.append(
            {
                **product,
                "features": json.dumps(product.get("features", [])),
                "description": json.dumps(product.get("description", [])),
                "categories": json.dumps(product.get("categories", [])),
            }
        )

    return rows


def get_reviews_rows() -> list[dict]:

    def _random_asin(prefix: str = "TEST") -> str:
        return prefix + "".join(
            random.choices(string.ascii_uppercase + string.digits, k=8)
        )

    rows = []
    for product in PRODUCTS:
        for _ in range(3):
            tmpl = random.choice(REVIEW_TEMPLATES)
            rows.append(
                {
                    "parent_asin": product["parent_asin"],
                    "asin": _random_asin("VAR"),
                    "user_id": _random_asin("USR"),
                    "rating": tmpl["rating"],
                    "title": tmpl["title"],
                    "review_text": tmpl["text"],
                    "helpful_vote": random.randint(0, 50),
                    "verified_purchase": random.choice([True, False]),
                    "reviewed_at": datetime.now(tz=timezone.utc),
                    "sentiment_label": tmpl["sentiment_label"],
                    "sentiment_score": tmpl["sentiment_score"],
                }
            )

    return rows
