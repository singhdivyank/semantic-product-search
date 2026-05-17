"""
Main Airflow orchestration file for the Gift Cards ingestion pipeline.

Task chain (from scoping doc):
    extract → transform → embed → load

Heavy logic lives in dags/src/:
    - dags/src/transformer.py  (text cleaning, sentiment scoring)
    - dags/src/embedder.py     (FP32 vector generation, FP16 downscaling)

This file contains only the task callables and DAG wiring so that
Airflow's scheduler can parse it quickly without importing heavy ML libs.
"""

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator

from tasks.embeddings import task_embed
from tasks.extraction import task_extract
from tasks.load import task_load
from tasks.transformation import task_transform

with DAG(
    dag_id="product_ingestion",
    description=(
        "Extract → Transform → Embed → Load pipeline "
        "for McAuley-Lab Amazon Gift Cards dataset"
    ),
    default_args={
        "owner": "data-engineering",
        "depends_on_past": False,
        "retries": 2,
        "retry_delay": timedelta(minutes=5),
        "email_on_failure": False,
    },
    start_date=datetime(2024, 1, 1),
    schedule="@weekly",
    catchup=False,
    tags=["amazon-reviews", "gift-cards", "ingestion", "pgvector"],
) as dag:

    extract = PythonOperator(
        task_id="extract",
        python_callable=task_extract,
        doc_md="Downloads and decompresses Gift_Cards.jsonl.gz and meta_Gift_Cards.jsonl.gz.",
    )

    transform = PythonOperator(
        task_id="transform",
        python_callable=task_transform,
        doc_md="Strips HTML, normalises text, scores sentiment via DistilBERT.",
    )

    embed = PythonOperator(
        task_id="embed",
        python_callable=task_embed,
        doc_md="Encodes products with all-MiniLM-L6-v2; downcasts to FP16; logs to MLflow.",
    )

    load = PythonOperator(
        task_id="load",
        python_callable=task_load,
        doc_md="Bulk UPSERTs products, reviews, and embeddings into Cloud SQL PostgreSQL.",
    )

    extract >> transform >> embed >> load
