from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Literal, Optional

import h3
from shapely.geometry import Point, shape
from sqlalchemy import text

from .ml_scorer import blend_scores, is_available as ml_available, predict as ml_predict
from .models import BatchScoreResponse, FactorBreakdown, H3CellScore, HotspotResponse, PointScoreResponse


@dataclass
class FactorConfig:
    weight: float
    norm_max: float
    invert: bool = False


@dataclass
class ScoringProfile:
    mode: Literal["city", "highway"]
    factors: dict[str, FactorConfig]
    spatial_radii: dict[str, float] = field(default_factory=dict)


CITY_PROFILE = ScoringProfile(
    mode="city",
    factors={
        "ev_adoption":   FactorConfig(weight=0.25, norm_max=50.0),
        "income":        FactorConfig(weight=0.20, norm_max=100.0),
        "population":    FactorConfig(weight=0.20, norm_max=20000.0),
        "traffic":       FactorConfig(weight=0.15, norm_max=100.0),
        "competition":   FactorConfig(weight=0.10, norm_max=100.0),
        "accessibility": FactorConfig(weight=0.10, norm_max=100.0),
    },
    spatial_radii={"population": 1000.0, "traffic": 500.0, "competition": 1000.0, "accessibility": 300.0},
)

HIGHWAY_PROFILE = ScoringProfile(
    mode="highway",
    factors={
        "traffic_flow":        FactorConfig(weight=0.30, norm_max=100.0),
        "distance_gap":        FactorConfig(weight=0.25, norm_max=50000.0),
        "fuel_proximity":      FactorConfig(weight=0.20, norm_max=100.0),
        "rest_stop_proximity": FactorConfig(weight=0.15, norm_max=100.0),
        "risk":                FactorConfig(weight=0.10, norm_max=100.0, invert=True),
    },
    spatial_radii={"fuel_proximity": 5000.0, "rest_stop_proximity": 5000.0},
)

_CITY_SQL = text("""
WITH pt AS (SELECT ST_SetSRID(ST_MakePoint(:lon, :lat), 4326) AS g)
SELECT
    (SELECT ev_density FROM ev_adoption_zones WHERE ST_Contains(geom, (SELECT g FROM pt)) LIMIT 1),
    (SELECT income_score FROM income_zones WHERE ST_Contains(geom, (SELECT g FROM pt)) LIMIT 1),
    (SELECT pop_density FROM population_zones
     WHERE geom && ST_Expand((SELECT g FROM pt), 0.009)
       AND ST_DWithin(geom, (SELECT g FROM pt), 0.009)
     ORDER BY geom <-> (SELECT g FROM pt) LIMIT 1),
    (SELECT COALESCE(SUM(CASE road_class WHEN 'primary' THEN 1.0 WHEN 'trunk' THEN 1.0
        WHEN 'secondary' THEN 0.7 ELSE 0.4 END) / NULLIF(COUNT(*),0) * 100, 50)
     FROM city_roads
     WHERE geom && ST_Expand((SELECT g FROM pt), 0.0045)
       AND ST_DWithin(geom, (SELECT g FROM pt), 0.0045)),
    (SELECT COUNT(*) FROM ev_stations
     WHERE geom && ST_Expand((SELECT g FROM pt), 0.009)
       AND ST_DWithin(geom, (SELECT g FROM pt), 0.009)),
    (SELECT COUNT(*) FROM city_roads
     WHERE geom && ST_Expand((SELECT g FROM pt), 0.0027)
       AND ST_DWithin(geom, (SELECT g FROM pt), 0.0027)),
    (SELECT 1 FROM city_boundaries WHERE ST_Contains(geom, (SELECT g FROM pt)) LIMIT 1)
""")

_HIGHWAY_SQL = text("""
WITH pt AS (SELECT ST_SetSRID(ST_MakePoint(:lon, :lat), 4326) AS g)
SELECT
    (SELECT highway_class FROM highway_corridors
     WHERE geom && ST_Expand((SELECT g FROM pt), 0.009)
       AND ST_DWithin(geom, (SELECT g FROM pt), 0.009)
     ORDER BY geom <-> (SELECT g FROM pt) LIMIT 1),
    (SELECT ST_Distance(geom, (SELECT g FROM pt)) * 111320
     FROM ev_stations ORDER BY geom <-> (SELECT g FROM pt) LIMIT 1),
    (SELECT COUNT(*) FROM fuel_stations
     WHERE geom && ST_Expand((SELECT g FROM pt), 0.045)
       AND ST_DWithin(geom, (SELECT g FROM pt), 0.045)),
    (SELECT COUNT(*) FROM rest_stops
     WHERE geom && ST_Expand((SELECT g FROM pt), 0.045)
       AND ST_DWithin(geom, (SELECT g FROM pt), 0.045)),
    (SELECT flood_risk FROM risk_zones WHERE ST_Contains(geom, (SELECT g FROM pt)) LIMIT 1),
    (SELECT 1 FROM highway_corridors
     WHERE geom && ST_Expand((SELECT g FROM pt), 0.045)
       AND ST_DWithin(geom, (SELECT g FROM pt), 0.045) LIMIT 1)
""")

_NORM_MAP = {
    "ev_adoption": (50.0, False), "income": (100.0, False),
    "population": (20000.0, False), "traffic": (100.0, False),
    "competition": (100.0, False), "accessibility": (100.0, False),
    "traffic_flow": (100.0, False), "distance_gap": (50000.0, False),
    "fuel_proximity": (100.0, False), "rest_stop_proximity": (100.0, False),
    "risk": (100.0, True),
}


def normalize(raw: float, norm_max: float, invert: bool = False) -> float:
    clamped = max(0.0, min(raw, norm_max))
    score = (clamped / norm_max) * 100.0 if norm_max > 0 else 0.0
    return max(0.0, min(100.0, 100.0 - score if invert else score))


def _parse_city_row(row) -> tuple[dict, list[str], bool]:
    warnings = []
    in_city = row[6] is not None
    ev_density = float(row[0]) if row[0] is not None else None
    income_score = float(row[1]) if row[1] is not None else None
    pop_density = float(row[2]) if row[2] is not None else None
    traffic_score = float(row[3]) if row[3] is not None else 50.0
    ev_count = int(row[4]) if row[4] is not None else 0
    road_count = int(row[5]) if row[5] is not None else 0
    if ev_density is None:
        ev_density = 50.0
    if income_score is None:
        income_score = 50.0
    if pop_density is None:
        pop_density = 5000.0
    return {
        "ev_adoption": ev_density, "income": income_score, "population": pop_density,
        "traffic": traffic_score, "competition": max(0.0, 100.0 - ev_count * 20.0),
        "accessibility": min(100.0, road_count * 10.0),
    }, warnings, in_city


def _parse_highway_row(row) -> tuple[dict, list[str], bool]:
    class_map = {"NH": 100.0, "SH": 70.0, "MDR": 40.0}
    risk_map = {"high": 100.0, "medium": 50.0, "low": 0.0}
    near_highway = row[5] is not None
    hc = str(row[0]).upper() if row[0] else None
    return {
        "traffic_flow": class_map.get(hc, 40.0) if hc else 50.0,
        "distance_gap": float(row[1]) if row[1] is not None else 25000.0,
        "fuel_proximity": min(int(row[2] or 0) / 3.0, 1.0) * 100.0,
        "rest_stop_proximity": min(int(row[3] or 0) / 3.0, 1.0) * 100.0,
        "risk": risk_map.get(str(row[4]).lower() if row[4] else "", 50.0),
    }, [], near_highway


def _score_city_fast(lat, lon, engine):
    try:
        with engine.connect() as conn:
            row = conn.execute(_CITY_SQL, {"lat": lat, "lon": lon}).fetchone()
        return _parse_city_row(row)
    except Exception:
        return {k: 50.0 for k in CITY_PROFILE.factors}, [], True


def _score_highway_fast(lat, lon, engine):
    try:
        with engine.connect() as conn:
            row = conn.execute(_HIGHWAY_SQL, {"lat": lat, "lon": lon}).fetchone()
        return _parse_highway_row(row)
    except Exception:
        return {k: 50.0 for k in HIGHWAY_PROFILE.factors}, [], True


def _build_response(lat, lon, mode, profile, raw_values, warnings, out_of_bounds=False):
    breakdown, composite = [], 0.0
    for factor_name, cfg in profile.factors.items():
        raw = raw_values.get(factor_name, 50.0)
        nm, inv = _NORM_MAP.get(factor_name, (cfg.norm_max, cfg.invert))
        norm = normalize(raw, nm, inv)
        weighted = norm * cfg.weight
        composite += weighted
        breakdown.append(FactorBreakdown(
            factor_name=factor_name, raw_value=raw,
            normalized_score=norm, weight=cfg.weight, weighted_contribution=weighted,
        ))

    rule_score = max(0.0, min(100.0, composite))

    import geo_analyzer.ml_scorer as _ml
    ml_score = _ml.predict(lat, lon, mode, raw_values)
    final_score = _ml.blend_scores(rule_score, ml_score, ml_weight=0.4)

    return PointScoreResponse(
        lat=lat, lon=lon, score=final_score,
        mode=mode, breakdown=breakdown, out_of_bounds=out_of_bounds, warnings=warnings,
        rule_score=round(rule_score, 1),
        ml_score=round(ml_score, 1) if ml_score is not None else None,
        ml_active=ml_score is not None,
    )


def _generate_grid_points(polygon_geojson, max_points=500):
    import numpy as np
    geom = shape(polygon_geojson)
    minx, miny, maxx, maxy = geom.bounds
    grid_reduced = False
    step = 0.003
    for _ in range(20):
        xs = np.arange(minx + step * 0.3, maxx, step)
        ys = np.arange(miny + step * 0.3, maxy, step)
        rng = np.random.default_rng(42)
        candidates = []
        for x in xs:
            for y in ys:
                jx = x + rng.uniform(-step * 0.25, step * 0.25)
                jy = y + rng.uniform(-step * 0.25, step * 0.25)
                if geom.contains(Point(jx, jy)):
                    candidates.append((float(jy), float(jx)))
        if len(candidates) <= max_points:
            break
        step *= 1.5
        grid_reduced = True
    return candidates, grid_reduced


def _get_city_polygon(engine):
    try:
        with engine.connect() as conn:
            row = conn.execute(text("SELECT ST_AsGeoJSON(ST_Union(geom)) FROM city_boundaries")).fetchone()
        if row and row[0]:
            return json.loads(row[0])
    except Exception:
        pass
    return {"type": "Polygon", "coordinates": [[[72.47, 22.92], [72.69, 22.92], [72.72, 23.30], [72.58, 23.30], [72.47, 22.92]]]}


def _bulk_score_city(cells_latlon, engine):
    if not cells_latlon:
        return {}
    results = {}
    with ThreadPoolExecutor(max_workers=min(20, len(cells_latlon))) as executor:
        def score_one(item):
            h3_idx, lat, lon = item
            try:
                with engine.connect() as conn:
                    row = conn.execute(_CITY_SQL, {"lat": lat, "lon": lon}).fetchone()
                raw, _, in_city = _parse_city_row(row)
                return h3_idx, (raw, in_city)
            except Exception:
                return h3_idx, ({k: 50.0 for k in CITY_PROFILE.factors}, True)
        futures = [executor.submit(score_one, item) for item in cells_latlon]
        for f in futures:
            try:
                h3_idx, val = f.result()
                results[h3_idx] = val
            except Exception:
                pass
    return results


def _bulk_score_highway(cells_latlon, engine):
    if not cells_latlon:
        return {}
    results = {}
    with ThreadPoolExecutor(max_workers=min(20, len(cells_latlon))) as executor:
        def score_one(item):
            h3_idx, lat, lon = item
            try:
                with engine.connect() as conn:
                    row = conn.execute(_HIGHWAY_SQL, {"lat": lat, "lon": lon}).fetchone()
                raw, _, near_hw = _parse_highway_row(row)
                return h3_idx, (raw, near_hw)
            except Exception:
                return h3_idx, ({k: 50.0 for k in HIGHWAY_PROFILE.factors}, True)
        futures = [executor.submit(score_one, item) for item in cells_latlon]
        for f in futures:
            try:
                h3_idx, val = f.result()
                results[h3_idx] = val
            except Exception:
                pass
    return results


def _h3_cells_from_polygon(polygon_geojson: dict, resolution: int) -> list[str]:
    cells = []
    try:
        geom = shape(polygon_geojson)
        cells = list(h3.geo_to_cells(geom.__geo_interface__, resolution))
    except Exception:
        pass
    if not cells:
        try:
            cells = list(h3.polyfill_geojson(polygon_geojson, resolution))
        except Exception:
            pass
    if not cells:
        try:
            cells = list(h3.polyfill(polygon_geojson, resolution))
        except Exception:
            pass
    return cells


def _cell_center(cell: str) -> tuple[float, float]:
    try:
        return h3.cell_to_latlng(cell)
    except AttributeError:
        return h3.h3_to_geo(cell)


def _cell_boundary_coords(cell: str) -> list[list[float]]:
    try:
        boundary = h3.cell_to_boundary(cell)
    except AttributeError:
        boundary = h3.h3_to_geo_boundary(cell)
    coords = [[lon, lat] for lat, lon in boundary]
    coords.append(coords[0])
    return coords


class EVScoringEngine:
    def __init__(self, engine, redis_client=None):
        self._engine = engine
        self._redis = redis_client

    def _cache_key(self, lat, lon, mode):
        return f"ev3:{lat:.5f}:{lon:.5f}:{mode}"

    def score_point(self, lat, lon, mode, engine=None, redis=None):
        db = engine or self._engine
        rc = redis or self._redis

        cache_key = self._cache_key(lat, lon, mode)
        if rc:
            try:
                cached = rc.get(cache_key)
                if cached:
                    return PointScoreResponse.model_validate_json(cached)
            except Exception:
                pass

        profile = CITY_PROFILE if mode == "city" else HIGHWAY_PROFILE

        if mode == "city":
            raw_values, warnings, in_city = _score_city_fast(lat, lon, db)
            if not in_city:
                return PointScoreResponse(lat=lat, lon=lon, score=0.0, mode=mode,
                    breakdown=[], out_of_bounds=True,
                    warnings=["Point is outside Ahmedabad/Gandhinagar city limits"])
        else:
            raw_values, warnings, near_highway = _score_highway_fast(lat, lon, db)
            if not near_highway:
                return PointScoreResponse(lat=lat, lon=lon, score=0.0, mode=mode,
                    breakdown=[], out_of_bounds=True,
                    warnings=["Point is more than 5 km from a highway corridor"])

        result = _build_response(lat, lon, mode, profile, raw_values, warnings)

        if rc:
            try:
                rc.setex(cache_key, 3600, result.model_dump_json())
            except Exception:
                pass

        return result

    def score_batch(self, points, mode, engine=None):
        db = engine or self._engine
        results = []
        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(self.score_point, lat, lon, mode, db) for lat, lon in points]
            for f in futures:
                try:
                    results.append(f.result())
                except Exception:
                    pass
        sorted_valid = sorted([r for r in results if not r.out_of_bounds], key=lambda r: r.score, reverse=True)
        return BatchScoreResponse(sites=results, top10=sorted_valid[:10])

    def score_hotspots(self, polygon_geojson, mode, engine=None):
        db = engine or self._engine
        resolution = 7 if mode == "city" else 6

        if mode == "city" or polygon_geojson is None:
            polygon_geojson = _get_city_polygon(db)

        if polygon_geojson is None:
            return HotspotResponse(geojson_features={"type": "FeatureCollection", "features": []}, top10=[])

        cells = _h3_cells_from_polygon(polygon_geojson, resolution)
        if not cells:
            return HotspotResponse(geojson_features={"type": "FeatureCollection", "features": []}, top10=[])

        cells_latlon = [(cell, *_cell_center(cell)) for cell in cells]

        if mode == "city":
            bulk_results = _bulk_score_city(cells_latlon, db)
        else:
            bulk_results = _bulk_score_highway(cells_latlon, db)

        profile = CITY_PROFILE if mode == "city" else HIGHWAY_PROFILE
        cell_scores = []
        for cell, lat, lon in cells_latlon:
            if cell in bulk_results:
                raw_values, in_bounds = bulk_results[cell]
            else:
                raw_values = {k: 50.0 for k in profile.factors}
                in_bounds = True
            result = _build_response(lat, lon, mode, profile, raw_values, [])
            cell_scores.append(H3CellScore(
                h3_index=cell, center_lat=lat, center_lon=lon,
                score=result.score, breakdown=result.breakdown,
            ))

        sorted_cells = sorted(cell_scores, key=lambda c: c.score, reverse=True)
        top10 = sorted_cells[:10]

        features = [{
            "type": "Feature",
            "geometry": {"type": "Polygon", "coordinates": [_cell_boundary_coords(cs.h3_index)]},
            "properties": {"h3_index": cs.h3_index, "score": cs.score,
                           "center_lat": cs.center_lat, "center_lon": cs.center_lon},
        } for cs in cell_scores]

        return HotspotResponse(
            geojson_features={"type": "FeatureCollection", "features": features},
            top10=top10,
        )
