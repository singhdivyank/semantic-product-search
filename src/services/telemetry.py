"""
src/services/telemetry.py
=========================
Helper functions for recording Prometheus metrics.
All metric OBJECTS are defined in src/api/v1/consts.py — this file
only contains context managers and convenience recording functions.
No metrics are instantiated here to avoid duplicate registration errors.
"""

import time
from contextlib import contextmanager
from typing import Generator

from src.api.v1.consts import (
    HNSW_RECALL_RATE,
    PG_BUFFER_HIT_RATIO,
    LLM_GENERATION_LATENCY,
    LLM_FAITHFULNESS,
    LLM_ANSWER_RELEVANCE,
    LLM_ERRORS,
    LLM_TOKEN_COUNT,
    SEARCH_LATENCY,
    SEARCH_REQUESTS_TOTAL,
    SEARCH_ERRORS_TOTAL,
    EMBEDDING_DRIFT_SCORE,
)


@contextmanager
def observe_search(
    has_vector: bool,
    category_filter: bool,
    search_type: str = "semantic",
) -> Generator[None, None, None]:
    """Times the full search block and records SEARCH_LATENCY."""
    SEARCH_REQUESTS_TOTAL.labels(search_type=search_type).inc()
    start = time.perf_counter()
    try:
        yield
    except Exception as exc:
        SEARCH_ERRORS_TOTAL.labels(
            search_type=search_type,
            error_type=type(exc).__name__,
        ).inc()
        raise
    finally:
        SEARCH_LATENCY.labels(
            has_vector=str(has_vector),
            category_filter=str(category_filter),
        ).observe(time.perf_counter() - start)


@contextmanager
def observe_llm_generation(model_name: str) -> Generator[None, None, None]:
    """Times LLM generation and records LLM_GENERATION_LATENCY."""
    start = time.perf_counter()
    try:
        yield
    except Exception as exc:
        LLM_ERRORS.labels(model_name=model_name, error_type=type(exc).__name__).inc()
        raise
    finally:
        LLM_GENERATION_LATENCY.labels(model_name=model_name).observe(
            time.perf_counter() - start
        )


def record_token_counts(model_name: str, input_tokens: int, output_tokens: int) -> None:
    LLM_TOKEN_COUNT.labels(model_name=model_name, token_type="input").inc(input_tokens)
    LLM_TOKEN_COUNT.labels(model_name=model_name, token_type="output").inc(
        output_tokens
    )


def record_faithfulness(model_name: str, score: float) -> None:
    LLM_FAITHFULNESS.labels(model_name=model_name).observe(score)


def record_relevance(model_name: str, score: float) -> None:
    LLM_ANSWER_RELEVANCE.labels(model_name=model_name).observe(score)


def record_hnsw_recall(k: int, recall: float) -> None:
    HNSW_RECALL_RATE.labels(k=str(k)).set(recall)


def record_pg_buffer_hit(ratio: float) -> None:
    PG_BUFFER_HIT_RATIO.set(ratio)


def record_embedding_drift(category: str, js_divergence: float) -> None:
    EMBEDDING_DRIFT_SCORE.labels(category=category).set(js_divergence)
