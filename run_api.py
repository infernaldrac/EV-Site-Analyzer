import os

import redis as redis_lib
import uvicorn
from sqlalchemy import create_engine

import geo_analyzer.api as api_module
from geo_analyzer.api import app
from geo_analyzer.ev_scoring import EVScoringEngine

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql+psycopg2://postgres:postgres@localhost:5432/geo_analyzer",
)
REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

engine = create_engine(DATABASE_URL, pool_pre_ping=True)

try:
    redis_client = redis_lib.from_url(REDIS_URL, decode_responses=True)
    redis_client.ping()
except Exception:
    redis_client = None

api_module._engine = engine
api_module._scoring_engine = EVScoringEngine(engine, redis_client=redis_client)
api_module._redis_client = redis_client

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
