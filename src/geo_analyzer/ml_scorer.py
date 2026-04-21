from __future__ import annotations

import os
from typing import Optional

import joblib
import numpy as np
import pandas as pd

_MODEL_PATH = os.environ.get(
    "ML_MODEL_PATH",
    os.path.join(os.path.dirname(__file__), "..", "..", "Score model", "ev_site_model.pkl")
)

_model = None
_model_load_error: Optional[str] = None

ML_FEATURES = [
    "latitude", "longitude", "ev_adoption_percent", "avg_income",
    "population_density", "traffic_density", "competition_count",
    "accessibility_meters", "traffic_flow_daily", "distance_gap_km",
    "fuel_station_count", "rest_stop_count", "risk_index",
]


def _load_model():
    global _model, _model_load_error
    if _model is not None:
        return _model
    if _model_load_error:
        return None
    try:
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            _model = joblib.load(_MODEL_PATH)
        return _model
    except Exception as exc:
        _model_load_error = str(exc)
        return None


_load_model()


def is_available() -> bool:
    return _load_model() is not None


def _map_city_features(lat: float, lon: float, raw: dict) -> dict:
    ev_density = raw.get("ev_adoption", 50.0)
    ev_adoption_pct = min(ev_density / 50.0 * 35.0, 35.0)

    income_score = raw.get("income", 50.0)
    avg_income = income_score * 1000.0

    pop_density = raw.get("population", 5000.0)

    traffic_raw = raw.get("traffic", 50.0)
    traffic_density = traffic_raw * 80.0

    competition_count = max(0, int((100.0 - raw.get("competition", 100.0)) / 20.0))

    accessibility_raw = raw.get("accessibility", 50.0)
    accessibility_meters = max(50.0, (100.0 - accessibility_raw) * 20.0)

    distance_gap_km = raw.get("distance_gap", 25000.0) / 1000.0

    fuel_station_count = int(raw.get("fuel_proximity", 50.0) / 100.0 * 5)
    rest_stop_count = int(raw.get("rest_stop_proximity", 50.0) / 100.0 * 5)

    risk_raw = raw.get("risk", 50.0)
    risk_index = (100.0 - risk_raw) / 10.0

    return {
        "latitude": lat,
        "longitude": lon,
        "ev_adoption_percent": ev_adoption_pct,
        "avg_income": avg_income,
        "population_density": pop_density,
        "traffic_density": traffic_density,
        "competition_count": competition_count,
        "accessibility_meters": accessibility_meters,
        "traffic_flow_daily": traffic_density * 10.0,
        "distance_gap_km": distance_gap_km,
        "fuel_station_count": fuel_station_count,
        "rest_stop_count": rest_stop_count,
        "risk_index": risk_index,
    }


def _map_highway_features(lat: float, lon: float, raw: dict) -> dict:
    traffic_flow_raw = raw.get("traffic_flow", 50.0)
    traffic_flow_daily = traffic_flow_raw * 600.0

    distance_gap_km = raw.get("distance_gap", 25000.0) / 1000.0

    fuel_score = raw.get("fuel_proximity", 50.0)
    fuel_station_count = int(fuel_score / 100.0 * 5)

    rest_score = raw.get("rest_stop_proximity", 50.0)
    rest_stop_count = int(rest_score / 100.0 * 5)

    risk_raw = raw.get("risk", 50.0)
    risk_index = (100.0 - risk_raw) / 10.0

    return {
        "latitude": lat,
        "longitude": lon,
        "ev_adoption_percent": 8.0,
        "avg_income": 45000.0,
        "population_density": 500.0,
        "traffic_density": traffic_flow_daily / 10.0,
        "competition_count": 0,
        "accessibility_meters": 200.0,
        "traffic_flow_daily": traffic_flow_daily,
        "distance_gap_km": distance_gap_km,
        "fuel_station_count": fuel_station_count,
        "rest_stop_count": rest_stop_count,
        "risk_index": risk_index,
    }


def predict(lat: float, lon: float, mode: str, raw_values: dict) -> Optional[float]:
    model = _load_model()
    if model is None:
        return None

    try:
        if mode == "city":
            features = _map_city_features(lat, lon, raw_values)
        else:
            features = _map_highway_features(lat, lon, raw_values)

        df = pd.DataFrame([features])[ML_FEATURES]
        pred = float(model.predict(df)[0])
        return max(0.0, min(100.0, pred))
    except Exception as e:
        import sys
        print(f"[ml_scorer] predict error: {e}", file=sys.stderr)
        return None


def blend_scores(rule_score: float, ml_score: Optional[float], ml_weight: float = 0.4) -> float:
    if ml_score is None:
        return rule_score
    return round(rule_score * (1.0 - ml_weight) + ml_score * ml_weight, 2)
