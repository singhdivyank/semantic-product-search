import logging

import mlflow

from config.read_configs import (
    get_dag_conf,
    read_ingestion_configs,
    get_embedding_conf,
)
from dags.src.embedder import _write_embeddings

log = logging.getLogger("pipeline.dag")


def task_embed(**context) -> None:
    """Generate FP32 embeddings + FP16 downcasts; log run to MLflow"""

    ingestion_configs = read_ingestion_configs()
    embedding_config = get_embedding_conf()
    mlflow_config = get_dag_conf()["mlflow"]

    try:
        mlflow.set_tracking_uri(mlflow_config["tracking_uri"])
        mlflow.set_experiment(mlflow_config["experiment_name"])

        with mlflow.start_run(run_name="embed-gift-cards") as run:
            mlflow.log_params(
                {
                    "model_name": embedding_config["model_name"],
                    "batch_size": embedding_config["batch_size"],
                    "chunk_size": embedding_config["chunk_size"],
                    "normalize": embedding_config["normalize"],
                    "embedding_dim": embedding_config["dim"],
                }
            )

            embedding_metrics = _write_embeddings(
                embeddings_path=ingestion_configs["embeddings_path"],
                clean_meta_path=ingestion_configs["clean_meta_path"],
                chunk_size=embedding_config["chunk_size"],
                run_id=run.info.run_id,
            )
            if embedding_metrics:
                mlflow.log_metrics(embedding_metrics)
                log.info("Logged mlflow embeddings")
    except Exception as e:
        log.error("Error in task embed %s", e)
        raise
