import logging

from config.read_configs import read_ingestion_configs
from dags.src.transformer import _clean_meta_file, _clean_reviews_file

log = logging.getLogger("pipeline.dag")


def task_transform(**context) -> None:
    ingestion_configs = read_ingestion_configs()
    meta_path = ingestion_configs["meta_path"]
    clean_meta_path = ingestion_configs["clean_meta_path"]
    reviews_path = ingestion_configs["reviews_path"]

    try:
        _clean_meta_file(clean_meta_path=clean_meta_path, meta_path=meta_path)
        clean_reviews_path = ingestion_configs["clean_reviews_path"]
        _clean_reviews_file(
            clean_reviews_path=clean_reviews_path, reviews_path=reviews_path
        )
    except Exception as e:
        log.error("Error in task transform %s", e)
