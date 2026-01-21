#!/bin/bash
set -e

echo "Waiting for postgres..."
while ! nc -z postgres 5432; do
  sleep 0.1
done
echo "PostgreSQL started"

echo "Running database migrations..."
alembic upgrade head

echo "Starting API server..."
exec uvicorn main:app --host 0.0.0.0 --port 8000 --reload
