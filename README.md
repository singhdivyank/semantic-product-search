# semantic-product-search

```
semantic-product-search/
│
├── .github/
│ ├── workflows/ # CI/CD pipelines (Linting, Docker build)
| │ ├── ci.yml
│ | └── deployment.yml
│
├── config/ # Configuration management
│ ├── config.yaml # Application parameters
│ └── logging.conf # Standardized logger configurations
│
├── db/ # SQL Schema and Migration Control
│ ├── alembic/ # Alembic migration environment
│ │ └── versions/ # Database migration tracks
│ ├── alembic.ini # Alembic configuration
│ └── seed_data.py # Populates local instance for testing
│
├── dags/ # Apache Airflow Workflows
│ ├── src/ # Helper modules for ETL tasks
│ │ ├── embedder.py # Vector generation wrapper
│ │ └── transformer.py # Text cleaning and preprocessing
│ └── product_ingestion_dag.py # Main orchestration file
│
├── src/ # Backend FastAPI Core Engine
│ ├── api/ # Route endpoints
│ │ ├── v1/
│ │ │ ├── search.py # Main semantic search routes
│ │ │ └── products.py # CRUD and metrics routes
│ │ └── deps.py # API Dependencies (Database sessions, HF clients)
│ ├── core/ # App initialization, security, and env management
│ │ └── config.py
│ ├── services/ # Business logic layers
│ │ ├── hf_client.py # Interfacing with Hugging Face models
│ │ └── ml_tracking.py # MLflow tracking instrumentation
│ └── main.py # FastAPI ASGI Application entry point
│
├── tests/ # Unit and Integration test vectors
│ ├── conftest.py # Fixtures (mock DB, mock HF endpoints)
│ ├── test_api.py # Endpoint regression validations
│ └── test_pipeline.py # DAG operator component validation
│
├── docker-compose.yml # Local stack setup (Airflow, MLflow Server, Postgres)
├── Dockerfile # Multi-stage production container build
├── README.md # Comprehensive portfolio documentation
└── requirements.txt # Python dependency manifests
```
