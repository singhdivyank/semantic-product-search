-- docker/postgres/init.sql

-- Create Airflow metadata database
SELECT 'CREATE DATABASE airflow'
    WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'airflow')\gexec

-- Create MLflow backend database
SELECT 'CREATE DATABASE mlflow'
    WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'mlflow')\gexec

-- Enable pgvector on the main application database
\connect amazon_reviews
CREATE EXTENSION IF NOT EXISTS vector;

-- Confirm
SELECT extname, extversion FROM pg_extension WHERE extname = 'vector';