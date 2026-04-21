#!/bin/bash
set -e

echo "==> Waiting for PostgreSQL to be ready..."
for i in $(seq 1 30); do
  python -c "
import psycopg2, os, sys
try:
    conn = psycopg2.connect(os.environ.get('DATABASE_URL', '').replace('postgresql+psycopg2://', 'postgresql://'))
    conn.close()
    sys.exit(0)
except Exception as e:
    print(f'  DB not ready yet ({e}), retrying...')
    sys.exit(1)
" && break
  sleep 2
done

echo "==> Running database migrations..."
python -m alembic upgrade head

echo "==> Generating sample data..."
python data_pipeline/generate_sample_data.py

echo "==> Fetching OSM data (timeout 120s)..."
timeout 120 python data_pipeline/fetch_osm_data.py || echo "WARNING: OSM fetch partial or failed — using sample data only"

echo "==> Seeding database..."
python data_pipeline/seed_database.py || echo "WARNING: Some tables failed to seed"

echo "==> Starting API server on :8000 ..."
exec python run_api.py
