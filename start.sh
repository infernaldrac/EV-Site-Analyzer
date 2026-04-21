#!/bin/bash
# ─────────────────────────────────────────────────────────────────────────────
# GeoSpatial Site Readiness Analyzer — One-command startup
# Usage: ./start.sh
# ─────────────────────────────────────────────────────────────────────────────
set -e

echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║   GeoSpatial Site Readiness Analyzer                ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""

# Check Docker is available
if ! command -v docker &> /dev/null; then
  echo "ERROR: Docker is not installed. Install Docker Desktop from https://docker.com"
  exit 1
fi

if ! docker info &> /dev/null; then
  echo "ERROR: Docker daemon is not running. Please start Docker Desktop."
  exit 1
fi

echo "▶  Building and starting all services..."
docker compose up --build -d

echo ""
echo "▶  Waiting for services to be healthy..."
sleep 5

# Wait for API to be ready (up to 60s)
echo "▶  Waiting for API to be ready..."
for i in $(seq 1 30); do
  if curl -sf http://localhost:8000/health > /dev/null 2>&1; then
    break
  fi
  sleep 2
done

echo ""
echo "✅  All services are running!"
echo ""
echo "   🗺   Frontend (Map UI)  →  http://localhost:3000"
echo "   ⚡  API (REST)          →  http://localhost:8000"
echo "   📖  API Docs (Swagger)  →  http://localhost:8000/docs"
echo ""
echo "   To stop everything:  docker compose down"
echo "   To view logs:        docker compose logs -f api"
echo ""
