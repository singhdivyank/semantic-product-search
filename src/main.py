"""
FastAPI ASGI application entry point for the Semantic Product Search engine.

Startup sequence
----------------
  1. Load config (src/core/config.py) — reads config.yaml + env vars
  2. Register routers  (/api/v1/search, /api/v1/products)
  3. Wire lifespan events:
       on startup  → warm-up embedding model, verify DB connectivity
       on shutdown → flush MLflow run if active
"""

import logging
import time
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import uvicorn
from fastapi import FastAPI, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from config.read_configs import (
    get_api_configs,
    get_dag_conf,
    get_db_url,
    get_embedding_conf,
)
from consts import HTTP_REQUEST_DURATION, HTTP_REQUESTS_TOTAL
from src.api.v1 import products as products_router
from src.api.v1 import search as search_router
from src.services.hf_client import get_embedding_client
from src.services.ml_tracking import MLTracker

log = logging.getLogger("app.main")

api_configs = get_api_configs()
embedding_configs = get_embedding_conf()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Async context manager executed around the app's lifetime.
    Startup: warm up models, verify DB, initialise tracker.
    Shutdown: orderly teardown
    """

    db_url = get_db_url()
    mlflow_config = get_dag_conf()["mlflow"]

    log.info("Starting up Semantic Product Search API v%s", api_configs["version"])
    log.info("Warming up embedding model: %s", embedding_configs["model_name"])

    try:
        embedder = get_embedding_client()
        _ = embedder.embed("warmup")
        log.info("Embedding model warm-up complete.")
    except Exception as exc:
        log.warning("Embedding model warm-up failed (non-fatal): %s", exc)

    log.info("Verifying database connectivity...")
    try:
        from sqlalchemy import create_engine, text as sa_text

        engine = create_engine(db_url, pool_pre_ping=True)
        with engine.connect() as conn:
            conn.execute(sa_text("SELECT 1"))
        engine.dispose()
        log.info("Database connectivity OK.")
    except Exception as exc:
        log.error("Database connectivity check failed: %s", exc)

    MLTracker()
    log.info("MLTracker initialised — tracking URI: %s", mlflow_config["tracking_uri"])

    log.info(
        "API ready — %s:%d | prefix: %s | metrics: /metrics",
        api_configs["host"],
        api_configs["port"],
        api_configs["prefix"],
    )

    yield

    log.info("Shutting down — cleaning up resources.")


def create_app() -> FastAPI:
    application = FastAPI(
        title=api_configs["title"],
        version=api_configs["version"],
        description=(
            "Semantic product search engine backed by pgvector (HNSW + IVFFlat), "
            "all-MiniLM-L6-v2 embeddings, and Mistral-7B review summarisation. "
            "Implements a two-stage binary scan → cosine re-rank retrieval pipeline."
        ),
        docs_url=f"{api_configs["prefix"]}/docs",
        redoc_url=f"{api_configs["prefix"]}/redoc",
        openapi_url=f"{api_configs["prefix"]}/openapi.json",
        lifespan=lifespan,
    )

    application.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Request timing middleware
    @application.middleware("http")
    async def prometheus_timing_middleware(request: Request, call_next):
        """
        Records per-endpoint HTTP request duration and total count for Prometheus.
        Complements the finer-grained route-level metrics in telemetry.py.
        """
        start = time.perf_counter()
        response = await call_next(request)
        duration = time.perf_counter() - start
        route = request.scope.get("route")
        endpoint = route.path if route else request.url.path
        labels = {
            "method": request.method,
            "endpoint": endpoint,
            "status_code": str(response.status_code),
        }
        HTTP_REQUEST_DURATION.labels(**labels).observe(duration)
        HTTP_REQUESTS_TOTAL.labels(**labels).inc()

        return response

    # Global exception handler
    @application.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        log.exception("Unhandled exception on %s %s", request.method, request.url)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "An internal error occurred. Please try again."},
        )

    # Prometheus scrape endpoint
    @application.get("/metrics", include_in_schema=False)
    async def prometheus_metrics() -> Response:
        """
        Prometheus text-format metrics scrape endpoint.
        Prometheus should be configured to scrape this URL at its configured
        scrape_interval (15s recommended).

        Exposes all metrics registered in src/services/telemetry.py plus the
        http_request_duration_seconds and http_requests_total middleware metrics.
        """
        return Response(
            content=generate_latest(),
            media_type=CONTENT_TYPE_LATEST,
        )

    # Routers
    application.include_router(search_router.router, prefix=api_configs["prefix"])
    application.include_router(products_router.router, prefix=api_configs["prefix"])

    # Health check
    @application.get(f"{api_configs["prefix"]}/health", tags=["health"])
    async def health() -> dict:
        return {
            "status": "ok",
            "version": api_configs["version"],
            "model": embedding_configs["model_name"],
        }

    return application


app = create_app()

if __name__ == "__main__":
    uvicorn.run(
        "src.main.app",
        host=api_configs["host"],
        port=api_configs["port"],
        reload=api_configs["port"],
        log_config=None,
    )
