#!/bin/sh
# docker/scripts/start_api.sh
# Runs Alembic migrations then starts uvicorn.
# Using a script instead of an inline docker-compose command avoids the
# YAML '>' folded scalar bug where newlines collapse and uvicorn args
# become separate shell commands ("--host: not found").

set -e

echo "Running Alembic migrations..."
alembic -c db/alembic.ini upgrade head

echo "Starting FastAPI..."
exec uvicorn src.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --workers 2 \
    --log-config config/logging.conf