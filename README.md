# EV Site Analyzer

A geospatial decision-support tool for identifying optimal EV charging station locations in Ahmedabad and Gandhinagar, India.

## Features

- **City Mode**: Score urban locations using EV adoption, income, population, traffic, competition, and accessibility factors
- **Highway Mode**: Score highway corridor locations using traffic flow, distance gap, fuel proximity, rest stop proximity, and risk factors
- **Batch Scoring**: Draw a polygon and score all candidate points within it
- **Hotspot Analysis**: H3 hexagonal grid analysis to identify the best zones
- **Top 10 Panel**: Ranked list of best candidate locations with fly-to navigation
- **CSV Export**: Download scored results for offline analysis

## Architecture

- **Backend**: FastAPI + PostGIS (PostgreSQL) + Redis caching
- **Scoring Engine**: Weighted-sum models with configurable factor profiles
- **Data Pipeline**: OSM Overpass API + realistic sample datasets for Ahmedabad/Gandhinagar
- **Frontend**: MapLibre GL JS with polygon draw, score cards, and H3 hotspot visualization

## Quick Start

```bash
docker-compose up
```

The app will be available at `http://localhost:8080`.

On startup, the container will:
1. Run Alembic migrations to create all PostGIS tables
2. Fetch OSM data for the Ahmedabad/Gandhinagar region
3. Generate realistic sample data (EV adoption zones, income zones, risk zones, population zones)
4. Seed all data into PostGIS
5. Start the FastAPI server

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/score/point` | Score a single lat/lon |
| POST | `/score/batch` | Score all grid points within a polygon |
| POST | `/score/hotspots` | H3 hotspot analysis for a polygon |
| GET | `/layers/city-boundary` | GeoJSON of city boundaries |
| GET | `/layers/highways` | GeoJSON of highway corridors |
| GET | `/layers/ev-stations` | GeoJSON of existing EV stations |
| POST | `/export/csv` | Download scored results as CSV |

## Scoring Profiles

### City Mode Weights
| Factor | Weight |
|--------|--------|
| EV Adoption | 25% |
| Income Level | 20% |
| Population Density | 20% |
| Traffic Density | 15% |
| Competition | 10% |
| Accessibility | 10% |

### Highway Mode Weights
| Factor | Weight |
|--------|--------|
| Traffic Flow | 30% |
| Distance Gap | 25% |
| Fuel Proximity | 20% |
| Rest Stop Proximity | 15% |
| Risk | 10% |

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql+psycopg2://postgres:postgres@localhost:5432/geo_analyzer` | PostGIS connection string |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis connection string (optional) |
