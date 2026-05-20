"""
Singleton client for all-MiniLM-L6-v2 Hugging Face model
(384-dim sentence embeddings) used at inference time:

Lazily initialised on first use and cached for the lifetime of the
FastAPI process.  The FastAPI dependency `get_embedding_client` and
in src/api/deps.py inject this into route handlers.

Design notes
------------
- Model is loaded once; concurrent async requests reuse the same instance.
- Embedding runs synchronously (SentenceTransformer is CPU/GPU thread-safe).
"""

import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import List

import numpy as np
from sentence_transformers import SentenceTransformer

from config.read_configs import get_embedding_conf

log = logging.getLogger("app.hf_client")


class EmbeddingClient:
    """Wraps SentenceTransformer for real-time query embedding at search time"""

    def __init__(self) -> None:
        self._initialized = False
        self.thread_pool = ThreadPoolExecutor(
            max_workers=2, thread_name_prefix="hf-interface"
        )
        self._init_embeddings()

    def _init_embeddings(self):
        try:
            embedding_configs = get_embedding_conf()
            model_name = embedding_configs["model_name"]
            self.model = SentenceTransformer(model_name)
            self.dimension = embedding_configs["dim"]
            self.normalise = embedding_configs["normalize"]
            self.batch_size = embedding_configs["batch_size"]
            self._initialized = True
            log.info("Embedding model ready (dim = %d)", self.dimension)
        except Exception as error:
            log.error("Error initialising embeddings model %s", str(error))
            raise

    def embed(self, text: str) -> np.ndarray:
        """Encode a single query string into a normalised float32 vector"""

        if not self._initialized:
            return np.empty(0)

        return self.model.encode(
            text, normalize_embeddings=self.normalise, convert_to_numpy=True
        )

    def embed_batch(self, texts: List[str]) -> np.ndarray:
        """
        Encode a list of strings. Returns shape (N, 384).
        Used for batch re-ranking scenarios.
        """

        if not self._initialized:
            return np.empty(0)

        return self.model.encode(
            texts,
            batch_size=self.batch_size,
            normalize_embeddings=self.normalise,
            convert_to_numpy=True,
            show_progress_bar=False,
        )

    async def embed_async(self, text: str) -> np.ndarray:
        """
        Non-blocking version for use in async FastAPI route handlers.
        Offloads to thread pool so the event loop is not blocked.
        """

        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(self.thread_pool, self.embed, text)

    def to_pgvector_string(self, vector: np.ndarray) -> str:
        """Serialise vector to '[0.1, -0.2, ...]' for pgvector SQL parameters"""

        return "[" + ",".join(f"{v:.6f}" for v in vector.tolist()) + "]"
