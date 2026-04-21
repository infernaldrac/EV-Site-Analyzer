"""EV Analyzer schema - all 10 PostGIS tables

Revision ID: 0002
Revises:
Create Date: 2024-01-01 00:00:00.000000
"""

from alembic import op

revision = "0002"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")

    op.execute("""
        CREATE TABLE IF NOT EXISTS city_boundaries (
            id   SERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            geom GEOMETRY(POLYGON, 4326) NOT NULL
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_city_boundaries_geom ON city_boundaries USING GIST(geom)")

    op.execute("""
        CREATE TABLE IF NOT EXISTS highway_corridors (
            id            SERIAL PRIMARY KEY,
            name          TEXT,
            highway_class TEXT NOT NULL,
            geom          GEOMETRY(LINESTRING, 4326) NOT NULL
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_highway_corridors_geom ON highway_corridors USING GIST(geom)")

    op.execute("""
        CREATE TABLE IF NOT EXISTS ev_stations (
            id       SERIAL PRIMARY KEY,
            name     TEXT,
            operator TEXT,
            source   TEXT NOT NULL,
            geom     GEOMETRY(POINT, 4326) NOT NULL
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_ev_stations_geom ON ev_stations USING GIST(geom)")

    op.execute("""
        CREATE TABLE IF NOT EXISTS fuel_stations (
            id    SERIAL PRIMARY KEY,
            name  TEXT,
            brand TEXT,
            geom  GEOMETRY(POINT, 4326) NOT NULL
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_fuel_stations_geom ON fuel_stations USING GIST(geom)")

    op.execute("""
        CREATE TABLE IF NOT EXISTS rest_stops (
            id        SERIAL PRIMARY KEY,
            name      TEXT,
            stop_type TEXT,
            geom      GEOMETRY(POINT, 4326) NOT NULL
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_rest_stops_geom ON rest_stops USING GIST(geom)")

    op.execute("""
        CREATE TABLE IF NOT EXISTS city_roads (
            id         SERIAL PRIMARY KEY,
            name       TEXT,
            road_class TEXT NOT NULL,
            geom       GEOMETRY(LINESTRING, 4326) NOT NULL
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_city_roads_geom ON city_roads USING GIST(geom)")

    op.execute("""
        CREATE TABLE IF NOT EXISTS ev_adoption_zones (
            id         SERIAL PRIMARY KEY,
            zone_name  TEXT,
            ev_density FLOAT NOT NULL,
            geom       GEOMETRY(POLYGON, 4326) NOT NULL
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_ev_adoption_zones_geom ON ev_adoption_zones USING GIST(geom)")

    op.execute("""
        CREATE TABLE IF NOT EXISTS income_zones (
            id           SERIAL PRIMARY KEY,
            zone_name    TEXT,
            income_level TEXT NOT NULL,
            income_score FLOAT NOT NULL,
            geom         GEOMETRY(POLYGON, 4326) NOT NULL
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_income_zones_geom ON income_zones USING GIST(geom)")

    op.execute("""
        CREATE TABLE IF NOT EXISTS risk_zones (
            id           SERIAL PRIMARY KEY,
            zone_name    TEXT,
            flood_risk   TEXT NOT NULL,
            terrain_risk TEXT NOT NULL,
            geom         GEOMETRY(POLYGON, 4326) NOT NULL
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_risk_zones_geom ON risk_zones USING GIST(geom)")

    op.execute("""
        CREATE TABLE IF NOT EXISTS population_zones (
            id          SERIAL PRIMARY KEY,
            zone_name   TEXT,
            pop_density FLOAT NOT NULL,
            geom        GEOMETRY(POLYGON, 4326) NOT NULL
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_population_zones_geom ON population_zones USING GIST(geom)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS population_zones")
    op.execute("DROP TABLE IF EXISTS risk_zones")
    op.execute("DROP TABLE IF EXISTS income_zones")
    op.execute("DROP TABLE IF EXISTS ev_adoption_zones")
    op.execute("DROP TABLE IF EXISTS city_roads")
    op.execute("DROP TABLE IF EXISTS rest_stops")
    op.execute("DROP TABLE IF EXISTS fuel_stations")
    op.execute("DROP TABLE IF EXISTS ev_stations")
    op.execute("DROP TABLE IF EXISTS highway_corridors")
    op.execute("DROP TABLE IF EXISTS city_boundaries")
