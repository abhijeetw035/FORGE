#!/bin/bash
set -e

echo "Waiting for postgres..."
while ! nc -z postgres 5432; do
  sleep 0.1
done
echo "PostgreSQL started"

echo "Waiting for redis..."
while ! nc -z redis 6379; do
  sleep 0.1
done
echo "Redis started"

echo "Building Tree-sitter language grammars..."
python build_languages.py

echo "Initializing database tables..."
python -c "from database import Base, engine; Base.metadata.create_all(bind=engine)"

echo "Starting miner worker..."
exec python worker.py
