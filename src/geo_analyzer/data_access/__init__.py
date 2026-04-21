from __future__ import annotations

from sqlalchemy import text


class EVAdoptionDataAccess:
    def __init__(self, engine):
        self._engine = engine

    def get_ev_density(self, lat: float, lon: float) -> tuple[float, list[str]]:
        warnings = []
        sql = text("""
            SELECT ev_density
            FROM ev_adoption_zones
            WHERE ST_Contains(geom, ST_SetSRID(ST_MakePoint(:lon, :lat), 4326))
            LIMIT 1
        """)
        try:
            with self._engine.connect() as conn:
                row = conn.execute(sql, {"lat": lat, "lon": lon}).fetchone()
            if row:
                return float(row[0]), warnings
        except Exception:
            pass
        warnings.append("No zone data for factor: ev_adoption")
        return 50.0, warnings


class IncomeDataAccess:
    def __init__(self, engine):
        self._engine = engine

    def get_income_score(self, lat: float, lon: float) -> tuple[float, list[str]]:
        warnings = []
        sql = text("""
            SELECT income_score
            FROM income_zones
            WHERE ST_Contains(geom, ST_SetSRID(ST_MakePoint(:lon, :lat), 4326))
            LIMIT 1
        """)
        try:
            with self._engine.connect() as conn:
                row = conn.execute(sql, {"lat": lat, "lon": lon}).fetchone()
            if row:
                return float(row[0]), warnings
        except Exception:
            pass
        warnings.append("No zone data for factor: income")
        return 50.0, warnings


class RiskDataAccess:
    def __init__(self, engine):
        self._engine = engine

    def get_risk_score(self, lat: float, lon: float) -> tuple[float, list[str]]:
        warnings = []
        sql = text("""
            SELECT flood_risk, terrain_risk
            FROM risk_zones
            WHERE ST_Contains(geom, ST_SetSRID(ST_MakePoint(:lon, :lat), 4326))
            LIMIT 1
        """)
        risk_map = {"high": 100.0, "medium": 50.0, "low": 0.0}
        try:
            with self._engine.connect() as conn:
                row = conn.execute(sql, {"lat": lat, "lon": lon}).fetchone()
            if row:
                flood = risk_map.get(str(row[0]).lower(), 50.0)
                terrain = risk_map.get(str(row[1]).lower(), 50.0)
                return (flood * 0.7 + terrain * 0.3), warnings
        except Exception:
            pass
        warnings.append("No zone data for factor: risk")
        return 50.0, warnings


class PopulationDataAccess:
    def __init__(self, engine):
        self._engine = engine

    def get_population_density(self, lat: float, lon: float, radius_m: float = 1000.0) -> tuple[float, list[str]]:
        warnings = []
        sql = text("""
            SELECT pop_density
            FROM population_zones
            WHERE ST_DWithin(
                geom::geography,
                ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography,
                :radius
            )
            ORDER BY geom::geography <-> ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography
            LIMIT 1
        """)
        try:
            with self._engine.connect() as conn:
                row = conn.execute(sql, {"lat": lat, "lon": lon, "radius": radius_m}).fetchone()
            if row:
                return float(row[0]), warnings
        except Exception:
            pass
        warnings.append("No zone data for factor: population")
        return 50.0, warnings
