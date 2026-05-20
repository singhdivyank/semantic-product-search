import logging
import time
from contextlib import contextmanager
from typing import Generator, Optional

import mlflow

from services.tracking.rolling import RollingStats
from services.tracking.per_request import SearchRunContext
from config.read_configs import (
    get_dag_conf,
    get_embedding_conf,
    get_generation_conf,
    read_vector_search,
)

log = logging.getLogger("app.ml_tracking")


class MLTracker:
    """
    Central MLflow tracking service for the FastAPI inference layer.
    Instantiated once at startup; injected via FastAPI dependency.
    """

    def __init__(self) -> None:
        self._initialise()

    def _initialise(self):
        mlflow_config = get_dag_conf()["mlflow"]
        mlflow.set_tracking_uri(mlflow_config["tracking_uri"])
        mlflow.set_experiment(mlflow_config["experiment_name"])

        self.embedding_stats = RollingStats()
        self.stage1_stats = RollingStats()
        self.stage2_stats = RollingStats()
        self.generation_stats = RollingStats()
        self.e2e_stats = RollingStats()

        log.info(
            "MLTracker initialised — tracking URI: %s | experiment: %s",
            mlflow_config["tracking_uri"],
            mlflow_config["experiment_name"],
        )

    @contextmanager
    def search_run(
        self, query: str, top_k: int, run_name: str = "search-request"
    ) -> Generator[SearchRunContext, None, None]:
        """Context manager that opens an MLflow run for one search request"""

        t0 = time.perf_counter()
        try:
            vector_config = read_vector_search()
            embedding_config = get_embedding_conf()
            with mlflow.start_run(run_name=run_name, nested=True) as run:
                # Log quantisation / search config once per run
                mlflow.log_params(
                    {
                        "embedding_model": embedding_config["model_name"],
                        "hnsw_ef_search": vector_config["hnsw_ef_search"],
                        "oversample_factor": vector_config["oversample_factor"],
                        "quantisation": "binary_quantize+halfvec",
                    }
                )
                ctx = SearchRunContext(query=query, top_k=top_k, run=run)
                yield ctx
                ctx._flush()
        finally:
            elapsed_ms = (time.perf_counter() - t0) * 1000
            self.e2e_stats.record(elapsed_ms)
            self.embedding_stats.record(ctx._embedding_ms)
            self.stage1_stats.record(ctx._stage1_ms)
            self.stage2_stats.record(ctx._stage2_ms)
            self.generation_stats.record(ctx._generation_ms)

    def log_prompt_variant(
        self,
        variant_name: str,
        prompt_template: str,
        input_token_count: int,
        output_token_count: int,
        faithfulness: Optional[float] = None,
        answer_relevance: Optional[float] = None,
    ) -> None:
        """
        Log a named prompt variant with evaluation scores.
        Enables comparison of prompt versions in the MLflow UI.
        """

        generation_configs = get_generation_conf()

        with mlflow.start_run(run_name=f"prompt-{variant_name}", nested=True):
            mlflow.log_params(
                {
                    "variant_name": variant_name,
                    "generation_model": generation_configs["model_name"],
                    "max_new_tokens": generation_configs["max_new_tokens"],
                    "temperature": generation_configs["temperature"],
                    "prompt_char_length": len(prompt_template),
                }
            )
            metrics: dict[str, float] = {
                "input_token_count": float(input_token_count),
                "output_token_count": float(output_token_count),
            }
            if faithfulness is not None:
                metrics["faithfulness"] = faithfulness
            if answer_relevance is not None:
                metrics["answer_relevance"] = answer_relevance

            mlflow.log_metrics(metrics)
            mlflow.log_text(prompt_template, artifact_file="prompt_template.txt")

        log.info(
            "Prompt variant '%s' logged — faithfulness=%.3f, answer_relevance=%.3f",
            variant_name,
            faithfulness or 0.0,
            answer_relevance or 0.0,
        )

    def latency_summary(self) -> dict[str, dict]:
        """Return a snapshot of rolling latency stats for all stages."""
        return {
            "embedding": self.embedding_stats.as_dict("embedding"),
            "stage1": self.stage1_stats.as_dict("stage1"),
            "stage2": self.stage2_stats.as_dict("stage2"),
            "generation": self.generation_stats.as_dict("generation"),
            "e2e": self.e2e_stats.as_dict("e2e"),
        }
