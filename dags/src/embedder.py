"""
Generates sentence embeddings and manages FP32 → FP16 precision scaling.

Responsibilities
----------------
1. Load all-MiniLM-L6-v2 via sentence-transformers
2. Encode product text (title + features) in configurable batches
3. Scale full-precision float32 vectors to float16 (halfvec) for
   storage efficiency — mirrors the binary_quantize / halfvec pattern
   from the scoping doc's "Embedding Quantization" section
4. Return dicts ready for the DB load task and MLflow logging
"""

import json
import logging
import time
from pathlib import Path
from typing import Generator, List, Iterator, Optional

import numpy as np
from sentence_transformers import SentenceTransformer

from config.read_configs import get_embedding_conf
from helpers import _open_jsonl, build_product_text, fp32_to_fp16, to_pgvector_string

log = logging.getLogger("pipeline.embedder")


class ProductEmbedder:
    """Batch-encodes product text and emits FP32/FP16 embedding payloads"""

    def __init__(self) -> None:
        self._initialised = False
        self.get_configs()

    def get_configs(self):
        configs = get_embedding_conf()
        self.model_name = configs.get("model_name", "")
        self.batch_size = configs.get("batch_size", 64)
        self.normalize = configs.get("normalize", True)

    def _init_model(self):
        """Initialise Embedding Model"""

        if self._initialised:
            return

        log.info("Loading Embedding model")
        try:
            self.model = SentenceTransformer(self.model_name)

            log.info(
                "Model %s loaded. Embedding dim: %d",
                self.model_name,
                self.model.get_embedding_dimension(),
            )
            self._initialised = True
        except ValueError as e:
            log.error("Unable to load model %s, error: %s", self.model_name, str(e))
            raise

    def _encode_batch(self, texts: list[str]) -> np.ndarray:
        """Encode a list of texts and return an (N, dim) float32 ndarray."""

        if self.model is None:
            raise RuntimeError("Model not initialised")

        return self.model.encode(
            texts,
            batch_size=self.batch_size,
            show_progress_bar=False,
            normalize_embeddings=self.normalize,
            convert_to_numpy=True,
        )

    def embed_stream(
        self,
        meta_rows: Iterator[dict],
        mlflow_run_id: Optional[str],
        chunk_size: int = 500,
    ) -> Generator[dict, None, None]:
        """
        Consume an iterator of cleaned metadata dicts, yield embedding records.
        """

        buffer_asins: list[str] = []
        buffer_texts: list[str] = []

        total = 0
        total_s = 0.0

        self._init_model()

        def flush() -> Generator[dict, None, None]:
            nonlocal total, total_s
            if not buffer_texts:
                return

            t0 = time.perf_counter()
            vectors = self._encode_batch(buffer_texts)
            elapsed = time.perf_counter() - t0
            total_s += elapsed
            total += len(buffer_texts)

            log.debug(
                "Encoded %d vectors in %.2f s (%.1f ms/item)",
                len(buffer_texts),
                elapsed,
                elapsed / len(buffer_texts) * 1000,
            )

            for asin, fp32_vec in zip(buffer_asins, vectors):
                fp16_vec = fp32_to_fp16(fp32_vec)
                yield {
                    "parent_asin": asin,
                    "embedding_str": to_pgvector_string(fp32_vec),
                    "embedding_half_str": to_pgvector_string(fp16_vec),
                    "model_name": self.model_name,
                    "mlflow_run_id": mlflow_run_id,
                }

            buffer_asins.clear()
            buffer_texts.clear()

        for row in meta_rows:
            asin = row.get("parent_asin")
            if not asin:
                continue

            buffer_asins.append(asin)
            buffer_texts.append(build_product_text(row))

            if len(buffer_texts) >= chunk_size:
                yield from flush()

        if buffer_texts:
            yield from flush()

        if total:
            log.info(
                "Embedding complete: %d products | total %.2f s | avg %.2f ms/item",
                total,
                total_s,
                total_s / total * 1000,
            )

    def get_metrics(self, total_items: int, elapsed_s: float) -> dict:
        """Return a dict of MLflow-compatible metrics"""

        return {
            "total_embed": total_items,
            "total_embeddings_time_ms": round(elapsed_s * 1000, 2),
            "avg_embedding_time_ms": round(elapsed_s / max(total_items, 1) * 1000, 4),
            "embedding_dim": self.model.get_embedding_dimension(),
        }

    def encode_batch(self, texts: List[str]) -> np.ndarray:
        """Encode a list of texts and return an (N, dim) float32 ndarray"""

        return self.model.encode(
            texts,
            batch_size=self.batch_size,
            show_progress_bar=False,
            normalize_embeddings=self.normalize,
            convert_to_numpy=True,
        )


def _write_embeddings(
    embeddings_path: Path, clean_meta_path: Path, chunk_size: int, run_id: str
) -> Optional[dict]:
    total = 0

    try:
        embedder = ProductEmbedder()

        with open(embeddings_path, "w", encoding="utf-8") as fh:
            for record in embedder.embed_stream(
                _open_jsonl(clean_meta_path),
                chunk_size=chunk_size,
                mlflow_run_id=run_id,
            ):
                fh.write(json.dumps(record) + "\n")
                total += 1

        elapsed = time.perf_counter()
        metrics = embedder.get_metrics(total, elapsed)
        log.info(
            "Embeddings written: %d records → %s",
            total,
            embeddings_path,
        )
        return metrics
    except Exception as e:
        log.error("Write embeddings failed: %s", e)
        return None
