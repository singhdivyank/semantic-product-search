"""
Text cleaning and preprocessing helpers consumed by the Airflow transform task.

Responsibilities
----------------
1. Strip HTML / malformed markup from Amazon crawl data
2. Normalise whitespace and Unicode
3. Run lightweight sentiment scoring (DistilBERT) on review text
4. Produce clean dicts ready for the embed and load tasks
"""

import json
import logging
from pathlib import Path
from typing import Iterator, Generator, Optional

from transformers import pipeline

from config.read_configs import get_sentiment_model_conf
from dags.src.helpers import _open_jsonl, clean_text, transform_meta_row

log = logging.getLogger("pipeline.transformer")


def transform_meta_stream(rows: Iterator[dict]) -> Generator[dict, None, None]:
    """Yield cleaned metadata dicts, skipping invalid rows"""

    skipped = 0

    for _, raw in enumerate(rows, 1):
        asin = raw.get("parent_asin")
        if not asin:
            log.debug("Skipping meta row with no parent_asin")
            skipped += 1
            continue
        yield transform_meta_row(raw)

    if skipped:
        log.warning("Skipped %d meta rows (missing parent_asin)", skipped)


class ReviewTransformer:
    """
    Stateful transformer that holds the loaded sentiment model and processes
    review rows in batches for efficient GPU/CPU utilisation.
    """

    def __init__(self):
        self._initialised = False
        self.model = None
        self.get_configs()
        self._init_model()

    def get_configs(self):
        configs = get_sentiment_model_conf()
        self.model_name = configs.get("model_name")
        self.batch_size = configs.get("batch_size", 256)
        self.max_length = configs.get("max_length", 512)
        self.truncation = configs.get("truncation", True)

    def _init_model(self):
        """Initialise Sentiment Model"""

        if self._initialised:
            return

        log.info("Getting sentiment model ..")
        try:
            self.model = pipeline(  # type: ignore
                task="sentiment-analysis",
                model=self.model_name,
            )
            self._initialised = True
            log.info("Loaded Sentiment Model %s", self.model_name)
        except Exception as e:
            log.error(
                "Unable to load sentiment model %s, error: %s", self.model_name, str(e)
            )
            raise

    def transform_stream(self, rows: Iterator[dict]) -> Generator[dict, None, None]:
        """
        Yield cleaned + sentiment-scored review dicts.
        Buffers rows to run sentiment inference in batches.
        """

        buffer: list[dict] = []
        skipped: int = 0

        self._init_model()

        for raw in rows:
            cleaned = self._clean_review_row(raw)
            if cleaned is None:
                skipped += 1
                continue

            buffer.append(cleaned)

            if len(buffer) >= self.batch_size:
                yield from self._score_and_flush(buffer)
                buffer.clear()

        if buffer:
            yield from self._score_and_flush(buffer)

        if skipped:
            log.warning("Skipped %d review rows (missing mandatory fields)", skipped)

    def _score_and_flush(self, buffer: list[dict]) -> list[dict]:
        """Run sentiment inference on a batch and attach scores"""

        if self.model is None:
            raise RuntimeError("Sentiment model not initialised")

        texts = [r.get("text", "") for r in buffer]
        results = self.model(
            texts,
            batch_size=self.batch_size,
            truncation=self.truncation,
            max_length=self.max_length,
        )

        for row, score in zip(buffer, results):
            row["sentiment_label"] = score["label"].lower()
            row["sentiment_score"] = round(score["score"], 4)

        log.debug("Sentiment scored batch of %d reviews", len(buffer))
        return buffer

    @staticmethod
    def _clean_review_row(raw: dict) -> Optional[dict]:
        """
        Validate and clean a single review row.
        Returns None if mandatory fields (parent_asin, user_id, rating) are absent.
        """

        parent_asin = raw.get("parent_asin")
        user_id = raw.get("user_id")
        rating = raw.get("rating")

        if not parent_asin or not user_id or rating is None:
            return None

        return {
            "parent_asin": parent_asin,
            "asin": raw.get("asin"),
            "user_id": user_id,
            "rating": float(rating or 0),
            "title": clean_text(raw.get("title")),
            "text": clean_text(raw.get("text")),
            "helpful_vote": int(raw.get("helpful_vote") or 0),
            "verified_purchase": bool(raw.get("verified_purchase", False)),
            "timestamp": raw.get("timestamp"),
        }


def _clean_meta_file(clean_meta_path: Path, meta_path: Path):
    try:
        log.info("Transforming metadata %s -> %s", meta_path, clean_meta_path)
        with open(clean_meta_path, "w", encoding="utf-8") as fh:
            for row in transform_meta_stream(_open_jsonl(meta_path)):
                fh.write(json.dumps(row) + "\n")
        log.info("Metadata transform complete")
    except Exception as e:
        log.error("Error while cleaning metadata file: %s", e)
        raise


def _clean_reviews_file(clean_reviews_path: Path, reviews_path: Path):
    try:
        log.info(
            "Transforming reviews %s -> %s (with sentiment)",
            reviews_path,
            clean_reviews_path,
        )
        rt = ReviewTransformer()
        with open(clean_reviews_path, "w", encoding="utf-8") as fh:
            for row in rt.transform_stream(_open_jsonl(reviews_path)):
                fh.write(json.dumps(row, default=str) + "\n")
        log.info("Reviews transform complete")
    except Exception as e:
        log.error("Error while cleaning reviews file: %s", e)
        raise
