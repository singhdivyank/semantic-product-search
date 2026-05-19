"""Utility functions to read from config.yaml"""

from pathlib import Path
from typing import Any, Dict

import yaml


def get_embedding_conf() -> Dict[str, Any]:

    with open("config/config.yaml", "r") as f:
        data = yaml.safe_load(f)

    return data["embedding"]


def get_sentiment_model_conf() -> Dict[str, Any]:

    with open("config/config.yaml", "r") as f:
        data = yaml.safe_load(f)

    return data["sentiment"]


def get_dag_conf() -> Dict[str, Any]:
    """Get MLflow and Airflow consts"""

    import os
    from dotenv import load_dotenv

    load_dotenv()

    with open("config/config.yaml", "r") as f:
        raw_yaml = f.read()

    parsed_yaml = os.path.expandvars(raw_yaml)
    data = yaml.safe_load(parsed_yaml)
    return {"mlflow": data["mlflow"], "airflow": data["airflow"]}


def get_db_configs() -> Dict[str, Any]:

    import os
    from dotenv import load_dotenv

    load_dotenv()

    with open("config/config.yaml", "r") as f:
        raw_yaml = f.read()

    parsed_yaml = os.path.expandvars(raw_yaml)
    data = yaml.safe_load(parsed_yaml)
    return data["database"]


def read_ingestion_configs() -> Dict[str, Any]:

    import os
    from dotenv import load_dotenv

    load_dotenv()

    with open("config/config.yaml", "r") as f:
        raw_yaml = f.read()

    parsed_yaml = os.path.expandvars(raw_yaml)
    data = yaml.safe_load(parsed_yaml)
    ingestion_data = data["ingestion"]
    data_dir = Path(ingestion_data["data_dir"])

    return {
        "data_dir": data_dir,
        "meta_path": data_dir / ingestion_data["meta_filename"],
        "reviews_path": data_dir / ingestion_data["reviews_filename"],
        "clean_reviews_path": data_dir / ingestion_data["clean_reviews_filename"],
        "clean_meta_path": data_dir / ingestion_data["clean_meta_filename"],
        "embeddings_path": data_dir / ingestion_data["embeddings_filename"],
    }


def get_db_url() -> str:

    import os
    from dotenv import load_dotenv

    load_dotenv()

    with open("config/config.yaml", "r") as f:
        raw_yaml = f.read()

    parsed_yaml = os.path.expandvars(raw_yaml)
    data = yaml.safe_load(parsed_yaml)
    db_configs = data["database"]
    return f"postgresql://{db_configs['DB_USER']}:{db_configs['DB_PASSWORD']}@{db_configs['DB_HOST']}:{db_configs['DB_PORT']}/{db_configs['DB_NAME']}"
