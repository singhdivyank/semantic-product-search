""""""

from functools import lru_cache

from services.clients.embedding_client import EmbeddingClient
from services.clients.generator_client import GenerationClient


@lru_cache(maxsize=1)
def get_embedding_client() -> EmbeddingClient:
    """Return the process-level EmbeddingClient singleton"""

    return EmbeddingClient()


@lru_cache(maxsize=1)
def get_generation_client() -> GenerationClient:
    """Return the process-level GenerationClient singleton"""

    return GenerationClient()
