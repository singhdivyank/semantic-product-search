"""
Prometheus metric definitions for the Semantic Product Search API.

All metrics are defined here in one place so that:
  - src/main.py mounts the /metrics scrape endpoint
  - src/api/v1/search.py instruments the hybrid search pipeline
  - src/services/hf_client.py instruments token counts and TTFT

Metric categories (from project spec)
--------------------------------------
A. Core Database & Vector Index Metrics
   - HNSW Stage-1 read latency    (Histogram)
   - Stage-2 cosine rerank latency (Histogram)
   - DB query latency              (Histogram)
   - HNSW recall rate              (Gauge — set by periodic eval job)
   - Shared buffer hit ratio       (Gauge — set by periodic PG stats job)

B. LLM Application & Inference Metrics (LLMOps)
   - Time to First Token / TTFT    (Histogram)
   - Total generation latency      (Histogram)
   - Input + output token counts   (Counter, labelled by model + type)
   - Relevance & faithfulness      (Histogram)

C. Search Pipeline Metrics (per spec snippet)
   - Full hybrid search latency    (Histogram, labelled by has_vector + category_filter)
   - Embedding latency             (Histogram)
   - Requests total / errors       (Counter)
"""

import time
from contextlib import contextmanager
from typing import Generator

from consts import (
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
    """
    Context manager that times the full search block and records it.
    """
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
    """
    Context manager that times LLM generation and records total latency.
    TTFT must be recorded separately by the generation client.
    """
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


def record_token_counts(
    model_name: str,
    input_tokens: int,
    output_tokens: int,
) -> None:
    """Increment token counters after a generation call."""
    LLM_TOKEN_COUNT.labels(model_name=model_name, token_type="input").inc(input_tokens)
    LLM_TOKEN_COUNT.labels(model_name=model_name, token_type="output").inc(
        output_tokens
    )


def record_faithfulness(model_name: str, score: float) -> None:
    LLM_FAITHFULNESS.labels(model_name=model_name).observe(score)


def record_relevance(model_name: str, score: float) -> None:
    LLM_ANSWER_RELEVANCE.labels(model_name=model_name).observe(score)


def record_hnsw_recall(k: int, recall: float) -> None:
    """Called by the periodic Airflow recall-evaluation task."""
    HNSW_RECALL_RATE.labels(k=str(k)).set(recall)


def record_pg_buffer_hit(ratio: float) -> None:
    """Called by the periodic Airflow PG-stats task."""
    PG_BUFFER_HIT_RATIO.set(ratio)


def record_embedding_drift(category: str, js_divergence: float) -> None:
    """Called by the Airflow vector drift monitoring task."""
    EMBEDDING_DRIFT_SCORE.labels(category=category).set(js_divergence)
