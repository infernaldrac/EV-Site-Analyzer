from __future__ import annotations

import csv
import io
from typing import Optional

import sqlalchemy as sa
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from .ev_scoring import EVScoringEngine, _generate_grid_points
from .ml_scorer import is_available as ml_is_available, _model_load_error as ml_load_error
from .models import (
    BatchScoreRequest,
    BatchScoreResponse,
    HotspotRequest,
    HotspotResponse,
    PointScoreRequest,
    PointScoreResponse,
)

app = FastAPI(title="EV Charging Site Analyzer")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    from .ml_scorer import _load_model
    _load_model()

_engine = None
_scoring_engine: Optional[EVScoringEngine] = None
_redis_client = None


def get_engine():
    return _engine


def get_scoring_engine() -> EVScoringEngine:
    return _scoring_engine


@app.post("/score/point", response_model=PointScoreResponse)
def score_point(req: PointScoreRequest):
    engine = get_scoring_engine()
    if engine is None:
        raise HTTPException(status_code=503, detail="Scoring engine not initialized")
    return engine.score_point(req.lat, req.lon, req.mode)


@app.post("/score/batch", response_model=BatchScoreResponse)
def score_batch(req: BatchScoreRequest):
    engine = get_scoring_engine()
    if engine is None:
        raise HTTPException(status_code=503, detail="Scoring engine not initialized")

    try:
        geom_type = req.polygon_geojson.get("type", "")
        if geom_type not in ("Polygon", "MultiPolygon"):
            raise HTTPException(status_code=422, detail="polygon_geojson must be a Polygon or MultiPolygon")
    except AttributeError:
        raise HTTPException(status_code=422, detail="Invalid polygon_geojson")

    points, grid_reduced = _generate_grid_points(req.polygon_geojson, max_points=500)
    result = engine.score_batch(points, req.mode)
    result.grid_reduced = grid_reduced
    return result


@app.post("/score/hotspots", response_model=HotspotResponse)
def score_hotspots(req: HotspotRequest):
    engine = get_scoring_engine()
    if engine is None:
        raise HTTPException(status_code=503, detail="Scoring engine not initialized")
    return engine.score_hotspots(req.polygon_geojson, req.mode)


@app.get("/ml/status")
def ml_status():
    return {
        "available": ml_is_available(),
        "error": ml_load_error,
        "model": "GradientBoostingRegressor trained on 1000 Ahmedabad/Gandhinagar locations",
        "blend_weight": 0.4,
    }


@app.get("/ml/test")
def ml_test():
    import geo_analyzer.ml_scorer as _ml
    test_raw = {
        "ev_adoption": 48.0, "income": 85.0, "population": 3800.0,
        "traffic": 51.0, "competition": 80.0, "accessibility": 100.0
    }
    model_loaded = _ml._model is not None
    pred = _ml.predict(23.03, 72.505, "city", test_raw)
    rule = 68.0
    blended = _ml.blend_scores(rule, pred, 0.4)
    return {
        "model_loaded": model_loaded,
        "model_error": _ml._model_load_error,
        "ml_prediction": pred,
        "rule_score_example": rule,
        "blended_score": blended,
        "formula": f"{rule} x 0.6 + {pred} x 0.4 = {blended}" if pred else "ML unavailable"
    }


@app.post("/summary")
def generate_summary(body: dict):
    import json as _json
    sites = body.get("sites", [])
    mode = body.get("mode", "city")
    if not sites:
        raise HTTPException(status_code=422, detail="No sites provided")

    top = sorted([s for s in sites if not s.get("out_of_bounds") and s.get("score", 0) > 0],
                 key=lambda s: s["score"], reverse=True)[:10]
    if not top:
        raise HTTPException(status_code=422, detail="No valid sites")

    db = get_engine()
    summaries = []
    for i, site in enumerate(top):
        lat, lon = site["lat"], site["lon"]
        score = round(site["score"], 1)
        breakdown = {b["factor_name"]: b["normalized_score"] for b in site.get("breakdown", [])}

        area_name = _get_area_name(lat, lon, db)

        if mode == "city":
            reasons, profitability = _city_summary(breakdown, score)
        else:
            reasons, profitability = _highway_summary(breakdown, score, site)

        summaries.append({
            "rank": i + 1,
            "lat": lat,
            "lon": lon,
            "score": score,
            "area_name": area_name,
            "reasons": reasons,
            "profitability_rate": profitability,
            "profitability_label": _profitability_label(profitability),
        })

    return {"mode": mode, "total_analyzed": len(sites), "summaries": summaries}


def _get_area_name(lat: float, lon: float, db) -> str:
    if db is None:
        return f"Location ({lat:.4f}, {lon:.4f})"
    try:
        sql = sa.text("""
            SELECT zone_name FROM ev_adoption_zones
            WHERE ST_Contains(geom, ST_SetSRID(ST_MakePoint(:lon, :lat), 4326))
            LIMIT 1
        """)
        with db.connect() as conn:
            row = conn.execute(sql, {"lat": lat, "lon": lon}).fetchone()
        if row and row[0]:
            return row[0]
    except Exception:
        pass
    try:
        sql2 = sa.text("""
            SELECT name FROM highway_corridors
            WHERE ST_DWithin(geom::geography,
                ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography, 2000)
            ORDER BY geom::geography <-> ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography
            LIMIT 1
        """)
        with db.connect() as conn:
            row = conn.execute(sql2, {"lat": lat, "lon": lon}).fetchone()
        if row and row[0]:
            return f"Near {row[0]}"
    except Exception:
        pass
    return f"Location ({lat:.4f}, {lon:.4f})"


def _city_summary(breakdown: dict, score: float) -> tuple[list[str], float]:
    reasons = []
    ev = breakdown.get("ev_adoption", 0)
    income = breakdown.get("income", 0)
    pop = breakdown.get("population", 0)
    traffic = breakdown.get("traffic", 0)
    comp = breakdown.get("competition", 0)
    access = breakdown.get("accessibility", 0)

    if ev >= 70:
        reasons.append(f"High EV adoption rate ({int(ev)}%) — strong existing EV user base in this area")
    elif ev >= 40:
        reasons.append(f"Moderate EV adoption ({int(ev)}%) — growing EV market with expansion potential")

    if income >= 70:
        reasons.append(f"High-income neighbourhood ({int(income)}/100) — residents can afford EV charging")
    elif income >= 45:
        reasons.append(f"Middle-income area ({int(income)}/100) — good affordability for EV services")

    if pop >= 60:
        reasons.append(f"Dense population ({int(pop)}/100) — high footfall ensures consistent demand")

    if traffic >= 60:
        reasons.append(f"High road traffic density ({int(traffic)}/100) — maximum vehicle exposure")

    if comp >= 70:
        reasons.append(f"Low competition ({int(comp)}/100) — minimal existing EV stations nearby, first-mover advantage")
    elif comp >= 50:
        reasons.append(f"Moderate competition ({int(comp)}/100) — market not yet saturated")

    if access >= 70:
        reasons.append(f"Excellent road accessibility ({int(access)}/100) — easy entry/exit for vehicles")

    if not reasons:
        reasons.append(f"Balanced score across all factors (overall: {score})")

    profitability = _calc_city_profitability(ev, income, pop, traffic, comp, score)
    return reasons, profitability


def _highway_summary(breakdown: dict, score: float, site: dict) -> tuple[list[str], float]:
    reasons = []
    tf = breakdown.get("traffic_flow", 0)
    gap = breakdown.get("distance_gap", 0)
    fuel = breakdown.get("fuel_proximity", 0)
    rest = breakdown.get("rest_stop_proximity", 0)
    risk = breakdown.get("risk", 0)

    if tf >= 70:
        reasons.append(f"Major highway corridor ({int(tf)}/100) — high daily vehicle traffic ensures constant demand")
    elif tf >= 50:
        reasons.append(f"Active highway route ({int(tf)}/100) — steady intercity traffic flow")

    if gap >= 60:
        reasons.append(f"Large coverage gap ({int(gap)}/100) — no EV stations for significant distance, critical need")
    elif gap >= 40:
        reasons.append(f"Moderate coverage gap ({int(gap)}/100) — underserved stretch of highway")

    if fuel >= 60:
        reasons.append(f"Good fuel station infrastructure ({int(fuel)}/100) — proven refuelling demand at this location")

    if rest >= 60:
        reasons.append(f"Multiple rest stops nearby ({int(rest)}/100) — drivers already stop here, ideal for charging")

    if risk >= 70:
        reasons.append(f"Low flood/terrain risk ({int(risk)}/100) — safe infrastructure investment")

    if not reasons:
        reasons.append(f"Strategic highway location with balanced suitability score ({score})")

    profitability = _calc_highway_profitability(tf, gap, fuel, rest, risk, score)
    return reasons, profitability


def _calc_city_profitability(ev, income, pop, traffic, comp, score) -> float:
    base = score * 0.5
    ev_bonus = min(ev * 0.15, 15)
    income_bonus = min(income * 0.10, 10)
    pop_bonus = min(pop * 0.08, 8)
    comp_bonus = min(comp * 0.12, 12)
    return round(min(base + ev_bonus + income_bonus + pop_bonus + comp_bonus, 95), 1)


def _calc_highway_profitability(tf, gap, fuel, rest, risk, score) -> float:
    base = score * 0.5
    tf_bonus = min(tf * 0.15, 15)
    gap_bonus = min(gap * 0.15, 15)
    rest_bonus = min(rest * 0.08, 8)
    risk_bonus = min(risk * 0.07, 7)
    return round(min(base + tf_bonus + gap_bonus + rest_bonus + risk_bonus, 95), 1)


def _profitability_label(rate: float) -> str:
    if rate >= 80:
        return "Excellent"
    if rate >= 65:
        return "High"
    if rate >= 50:
        return "Moderate"
    if rate >= 35:
        return "Low"
    return "Poor"
@app.post("/score/hotspots/city")
def score_hotspots_city(body: dict):
    engine = get_scoring_engine()
    if engine is None:
        raise HTTPException(status_code=503, detail="Scoring engine not initialized")
    mode = body.get("mode", "city")
    return engine.score_hotspots(None, mode)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/layers/city-boundary")
def get_city_boundary():
    db = get_engine()
    if db is None:
        return {"type": "FeatureCollection", "features": []}
    sql = sa.text("SELECT name, ST_AsGeoJSON(geom) as geom FROM city_boundaries")
    try:
        with db.connect() as conn:
            rows = conn.execute(sql).fetchall()
        features = [
            {
                "type": "Feature",
                "geometry": __import__("json").loads(row[1]),
                "properties": {"name": row[0]},
            }
            for row in rows
        ]
        return {"type": "FeatureCollection", "features": features}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/layers/highways")
def get_highways():
    db = get_engine()
    if db is None:
        return {"type": "FeatureCollection", "features": []}
    sql = sa.text("SELECT name, highway_class, ST_AsGeoJSON(geom) as geom FROM highway_corridors")
    try:
        with db.connect() as conn:
            rows = conn.execute(sql).fetchall()
        features = [
            {
                "type": "Feature",
                "geometry": __import__("json").loads(row[2]),
                "properties": {"name": row[0], "highway_class": row[1]},
            }
            for row in rows
        ]
        return {"type": "FeatureCollection", "features": features}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/layers/ev-stations")
def get_ev_stations():
    db = get_engine()
    if db is None:
        return {"type": "FeatureCollection", "features": []}
    sql = sa.text("SELECT name, operator, source, ST_AsGeoJSON(geom) as geom FROM ev_stations")
    try:
        with db.connect() as conn:
            rows = conn.execute(sql).fetchall()
        features = [
            {
                "type": "Feature",
                "geometry": __import__("json").loads(row[3]),
                "properties": {"name": row[0], "operator": row[1], "source": row[2]},
            }
            for row in rows
        ]
        return {"type": "FeatureCollection", "features": features}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/export/csv")
def export_csv(body: dict):
    sites = body.get("sites", [])
    mode = body.get("mode", "city")

    city_factors = ["ev_adoption", "income", "population", "traffic", "competition", "accessibility"]
    highway_factors = ["traffic_flow", "distance_gap", "fuel_proximity", "rest_stop_proximity", "risk"]
    factor_cols = city_factors if mode == "city" else highway_factors

    base_cols = ["lat", "lon", "score", "mode"]
    all_cols = base_cols + factor_cols

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=all_cols)
    writer.writeheader()

    for site in sites:
        row = {
            "lat": site.get("lat", ""),
            "lon": site.get("lon", ""),
            "score": site.get("score", ""),
            "mode": site.get("mode", mode),
        }
        breakdown = {b["factor_name"]: b["normalized_score"] for b in site.get("breakdown", [])}
        for fc in factor_cols:
            row[fc] = breakdown.get(fc, "")
        writer.writerow(row)

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=ev_sites.csv"},
    )
