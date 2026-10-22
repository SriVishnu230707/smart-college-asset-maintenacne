#!/bin/sh
set -eu

# Credentials stay out of source, terminal output, and process arguments.
PGPASSWORD=$(cat /run/secrets/college_learner_password)
export PGPASSWORD
export PGCONNECT_TIMEOUT=5

exec psql -X --no-password --set=ON_ERROR_STOP=on \
    --host=127.0.0.1 --port=5432 \
    --username=college_learner --dbname=college_learning "$@"
