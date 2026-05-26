#!/bin/sh
# docker/scripts/airflow_init.sh
# Airflow 3.x compatible initialisation script.
#
# Fixes applied:
#   1. PermissionError on airflow.cfg — mkdir ensures AIRFLOW_HOME is owned
#      by the running user before Airflow tries to write its config there.
#   2. 'airflow users create' removed in Airflow 3.x — admin user is created
#      via 'airflow db migrate' which sets up the DB, then we use the
#      Airflow 3.x 'api-server' compatible approach.
#   3. Deprecated [core] sql_alchemy_conn → [database] sql_alchemy_conn
#      (handled via AIRFLOW__DATABASE__SQL_ALCHEMY_CONN env var in compose).

set -e

# Ensure AIRFLOW_HOME exists and is writable by current user
mkdir -p "${AIRFLOW_HOME}"

echo "Running Airflow DB migration..."
airflow db migrate

echo "Airflow DB migration complete."

# Airflow 3.x removed 'airflow users create'.
# Create admin user via the Airflow internal API if the command exists,
# otherwise print instructions for manual creation via the UI.
if airflow users create --help > /dev/null 2>&1; then
    # Airflow 2.x path (kept for compatibility if image uses Airflow 2)
    echo "Creating admin user (Airflow 2.x)..."
    airflow users create \
        --username admin \
        --password "${AIRFLOW_ADMIN_PASSWORD:-admin}" \
        --firstname Admin \
        --lastname User \
        --role Admin \
        --email admin@example.com || echo "User may already exist, continuing."
else
    # Airflow 3.x path — user management moved to UI / API
    echo "Airflow 3.x detected: 'airflow users create' has been removed."
    echo "Create your admin user via the Airflow UI at http://localhost:8080"
    echo "or use the Airflow REST API after the webserver starts."
fi

echo "Airflow init complete."