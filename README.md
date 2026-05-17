# semantic-product-search

```
semantic-product-search/
│
├── .github/
│ ├── workflows/        # CI/CD pipelines (Linting, Docker build)
| │ ├── ci.yml
│ | └── deployment.yml
│
├── amazon-data/        # Dataset
│ ├── Gift_cards.jsonl  # Application parameters
│ └── meta_Gift_cards.jsonl
|
├── config/             # Configuration management
│ ├── config.yaml       # Application parameters
│ ├── logging.conf      # Standardized logger configurations
│ └── read_configs.py
│
├── db/                 # SQL Schema and Migration Control
│ ├── alembic/          # Alembic migration environment
│ │   └── versions/     # Database migration tracks
│ ├── alembic.ini       # Alembic configuration
│ ├── models.py         # SQLAlchemy classes with pgvector/halfvec types
│ └── seed_data.py      # Populates local instance for testing
│
├── dags/               # Apache Airflow Workflows
│ ├── src/              # Helper modules for ETL tasks
│ │ ├── helpers.py
│ │ ├── embedder.py     # Generates vectors & manages precision scaling (FP32 -> FP16)
│ │ └── transformer.py  # Text cleaning and preprocessing
│ ├── tasks/
│ │ ├── alchemy_helpers.py
│ │ ├── consts.py
│ │ ├── embeddings.py
│ │ ├── extraction.py
│ │ ├── load.py
│ │ └── transformation.py
│ └── product_ingestion_dag.py # Main orchestration file
│
├── src/                # Backend FastAPI Core Engine
│ ├── api/              # Route endpoints
│ │ ├── v1/
│ │ │ ├── search.py     # Main dynamic search (Two-stage: Binary Scan -> Scalar Re-rank)
│ │ │ └── products.py   # CRUD and metrics routes
│ │ └── deps.py         # API Dependencies (Database sessions, HF clients)
│ ├── core/             # App initialization, security, and env management
│ │ └── config.py
│ ├── services/         # Business logic layers
│ │ ├── hf_client.py    # Interfacing with Hugging Face models
│ │ └── ml_tracking.py  # Tracks Quantization parameters, latency metrics, and prompt variants
│ └── main.py           # FastAPI ASGI Application entry point
│
├── tests/              # Unit and Integration test vectors
│ ├── conftest.py       # Fixtures (mock DB, mock HF endpoints)
│ ├── test_api.py       # Validates varying column outputs and structural performance
│ └── test_pipeline.py  # DAG operator component validation
│
├── docker-compose.yml  # Local stack setup (Airflow, MLflow Server, Postgres with pgvector)
├── Dockerfile          # Multi-stage production container build
├── README.md           # Comprehensive portfolio documentation
├── requirements.txt    # Python dependency manifests (Includes pgvector, mlflow, fastapi)
└── Schema.sql
```

Steps:

```
1. brew install postgresql@16
2. brew services start postgresql@16
3. echo 'export PATH="/opt/homebrew/opt/postgresql@16/bin:$PATH"' >> ~/.zshrc
4. source ~/.zshrc
```

@article{hou2024bridging,
title={Bridging Language and Items for Retrieval and Recommendation},
author={Hou, Yupeng and Li, Jiacheng and He, Zhankui and Yan, An and Chen, Xiusi and McAuley, Julian},
journal={arXiv preprint arXiv:2403.03952},
year={2024}
}
