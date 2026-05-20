"""Helper utility functions for embedder and transformer"""

import gzip
import html
import json
import logging
import re
from pathlib import Path
from typing import Generator, Optional

import numpy as np

log = logging.getLogger(__name__)


def fp32_to_fp16(vector: np.ndarray) -> np.ndarray:
    """
    Downcast a float32 embedding to float16 (halfvec precision).
    Used to populate a product_embeddings.embedding_half for HNSW storage
    """

    return vector.astype(np.float16)


def to_pgvector_string(vector: np.ndarray) -> str:
    """Seralise a numpy vector to the string format expected by pgvector"""

    return "[" + ",".join(f"{v:.6f}" for v in vector.tolist()) + "]"


def build_product_text(meta_row: dict, max_chars: int = 512) -> str:
    """Construct the embedding input string from a cleaned metadata row."""

    parts: list[str] = []
    title = meta_row.get("title", "")
    if title:
        parts.append(title)

    for feat in meta_row.get("features", []):
        if feat:
            parts.append(str(feat))

    combined = " ".join(parts).strip()
    return combined[:max_chars] if combined else (meta_row.get("parent_asin") or "")


def clean_text(text: Optional[str]) -> Optional[str]:
    """Full pipeline: strip HTML → decode entities → normalise whitespace"""

    _CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
    _HTML_TAG_RE = re.compile(r"<[^>]+>")
    _WHITESPACE_RE = re.compile(r"\s+")

    if not text:
        return text

    text = _HTML_TAG_RE.sub(" ", text)
    text = html.unescape(text)
    text = _CONTROL_RE.sub("", text)
    return _WHITESPACE_RE.sub(" ", text).strip()


def clean_string_list(lst: Optional[list]) -> list[str]:
    """Clean a list of strings (features, description bullets, etc.)"""

    if not lst:
        return []

    return [cleaned for item in lst if (cleaned := clean_text(str(item)))]


def transform_meta_row(raw: dict) -> dict:
    """
    Clean a single raw metadata row from meta_Gift_Cards.jsonl.
    Returns None if the row has no parent_asin (unusable).
    """

    return {
        "parent_asin": raw.get("parent_asin"),
        "title": clean_text(raw.get("title")),
        "subtitle": clean_text(raw.get("subtitle")),
        "author": clean_text(raw.get("author")),
        "main_category": clean_text(raw.get("main_category")),
        "store": clean_text(raw.get("store")),
        "average_rating": raw.get("average_rating"),
        "rating_number": raw.get("rating_number"),
        "price": raw.get("price"),
        "features": clean_string_list(raw.get("features")),
        "description": clean_string_list(raw.get("description")),
        "categories": raw.get("categories") or [],
        "details": raw.get("details"),
        "images": raw.get("images"),
        "videos": raw.get("videos"),
        "bought_together": raw.get("bought_together"),
    }


def _open_jsonl(path: Path) -> Generator[dict, None, None]:
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                try:
                    yield json.loads(line)
                except json.JSONDecodeError as e:
                    log.warning("Skipping malformed line: %s", e)
