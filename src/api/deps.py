"""
FastAPI dependency injection providers.

Injects into route handlers via Depends():
  - get_db()          → async SQLAlchemy session
  - get_embedder()    → EmbeddingClient singleton
  - get_generator()   → GenerationClient singleton
  - get_tracker()     → MLTracker singleton
"""

import logging
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from config.read_configs import get_db_configs, get_async_db_url
from src.services.hf_client import (
    EmbeddingClient,
    GenerationClient,
    get_embedding_client,
    get_generation_client,
)
from src.services.ml_tracking import MLTracker

log = logging.getLogger("app.deps")
db_config = get_db_configs()
async_db_url = get_async_db_url()

_AsyncSessionFactory = async_sessionmaker(
    bind=create_async_engine(
        async_db_url,
        pool_size=db_config["pool"]["size"],
        max_overflow=db_config["pool"]["max_overflow"],
        pool_recycle=db_config["pool"]["pool_recycle"],
        pool_pre_ping=db_config["pool"]["pre_ping"],
        echo=False,
    ),
    class_=AsyncSession,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Yield an async database session per request.
    Commits on clean exit; rolls back on exception.

    Inject with:
        db: AsyncSession = Depends(get_db)
    """
    async with _AsyncSessionFactory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


def get_embedder() -> EmbeddingClient:
    """
    Return the process-level EmbeddingClient.
    Model is loaded on first call; subsequent calls return the cached instance.

    Inject with:
        embedder: EmbeddingClient = Depends(get_embedder)
    """
    return get_embedding_client()


def get_generator() -> GenerationClient:
    """
    Return the process-level GenerationClient (Mistral-7B).
    Lazily initialised on first request that needs summarisation.

    Inject with:
        generator: GenerationClient = Depends(get_generator)
    """
    return get_generation_client()


def get_tracker() -> MLTracker:
    """
    Return the process-level MLTracker singleton.

    Inject with:
        tracker: MLTracker = Depends(get_tracker)
    """
    return MLTracker()
