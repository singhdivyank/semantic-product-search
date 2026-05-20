import logging
from dataclasses import dataclass, field

import mlflow

log = logging.getLogger("app.ml_tracking")


@dataclass
class SearchRunContext:
    """
    Holds timing data for a single search request and flushes to MLflow
    when the context manager exits
    """

    query: str
    top_k: int
    run: "mlflow.ActiveRun"

    _embedding_ms: float = field(default=0.0, init=False)
    _stage1_ms: float = field(default=0.0, init=False)
    _stage2_ms: float = field(default=0.0, init=False)
    _generation_ms: float = field(default=0.0, init=False)
    _result_asins: list = field(default_factory=list, init=False)

    def log_embedding_latency(self, ms: float) -> None:
        self._embedding_ms = ms

    def log_stage1_latency(self, ms: float) -> None:
        """Stage 1: binary-quantised HNSW Hamming scan"""

        self._stage1_ms = ms

    def log_stage2_latency(self, ms: float) -> None:
        """Stage 2: cosine re-ranking on full FP32 vectors"""

        self._stage2_ms = ms

    def log_generation_latency(self, ms: float) -> None:
        self._generation_ms = ms

    def log_results(self, parent_asins: list[str]) -> None:
        self._result_asins = parent_asins

    def _flush(self) -> None:
        total_ms = (
            self._embedding_ms + self._stage1_ms + self._stage2_ms + self._generation_ms
        )
        mlflow.log_metrics(
            {
                "embedding_latency_ms": self._embedding_ms,
                "stage1_scan_ms": self._stage1_ms,
                "stage2_rerank_ms": self._stage2_ms,
                "generation_latency_ms": self._generation_ms,
                "total_latency_ms": total_ms,
                "results_returned": len(self._result_asins),
            }
        )
        mlflow.log_params(
            {
                "query_length_chars": len(self.query),
                "top_k": self.top_k,
            }
        )
        log.debug(
            "Search run logged — total %.1f ms | results: %d",
            total_ms,
            len(self._result_asins),
        )
