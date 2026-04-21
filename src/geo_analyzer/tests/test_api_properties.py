"""
Property-based tests for the FastAPI endpoints.
Properties 12 (invalid inputs → 422).
"""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from hypothesis import given, settings
from hypothesis import strategies as st

import geo_analyzer.api as api_module
from geo_analyzer.api import app
from geo_analyzer.ev_scoring import EVScoringEngine
from geo_analyzer.models import PointScoreResponse


@pytest.fixture(autouse=True)
def setup_app():
    db = MagicMock()
    mock_conn = MagicMock()

    def execute_side_effect(sql, params=None):
        sql_str = str(sql)
        mock_result = MagicMock()
        if "ev_adoption_zones" in sql_str:
            mock_result.fetchone.return_value = (25.0,)
        elif "income_zones" in sql_str:
            mock_result.fetchone.return_value = (60.0,)
        elif "population_zones" in sql_str:
            mock_result.fetchone.return_value = (8000.0,)
        elif "city_roads" in sql_str and "GROUP BY" in sql_str:
            mock_result.fetchall.return_value = [("primary", 3)]
        elif "city_roads" in sql_str:
            mock_result.fetchone.return_value = (5,)
        elif "ev_stations" in sql_str and "ST_Distance" in sql_str:
            mock_result.fetchone.return_value = (25000.0,)
        elif "ev_stations" in sql_str:
            mock_result.fetchone.return_value = (2,)
        elif "highway_corridors" in sql_str:
            mock_result.fetchone.return_value = ("NH",)
        elif "fuel_stations" in sql_str:
            mock_result.fetchone.return_value = (3,)
        elif "rest_stops" in sql_str:
            mock_result.fetchone.return_value = (2,)
        elif "risk_zones" in sql_str:
            mock_result.fetchone.return_value = ("low", "low")
        elif "city_boundaries" in sql_str:
            mock_result.fetchone.return_value = (1,)
        else:
            mock_result.fetchone.return_value = None
            mock_result.fetchall.return_value = []
        return mock_result

    mock_conn.execute.side_effect = execute_side_effect
    db.connect.return_value.__enter__ = MagicMock(return_value=mock_conn)
    db.connect.return_value.__exit__ = MagicMock(return_value=False)

    api_module._engine = db
    api_module._scoring_engine = EVScoringEngine(db)
    yield


client = TestClient(app)


# Property 12: Invalid API inputs always return HTTP 422
# Validates: Requirements 10.6
@given(mode=st.text(min_size=1, max_size=20).filter(lambda s: s not in ("city", "highway")))
@settings(max_examples=50)
def test_invalid_mode_returns_422(mode):
    """Property 12: Invalid mode string returns HTTP 422"""
    resp = client.post("/score/point", json={"lat": 23.03, "lon": 72.58, "mode": mode})
    assert resp.status_code == 422, f"Expected 422 for mode={mode!r}, got {resp.status_code}"


@given(lat=st.floats(min_value=91.0, max_value=180.0))
@settings(max_examples=30)
def test_invalid_lat_returns_422(lat):
    """Property 12: Latitude out of [-90, 90] returns HTTP 422"""
    resp = client.post("/score/point", json={"lat": lat, "lon": 72.58, "mode": "city"})
    assert resp.status_code == 422, f"Expected 422 for lat={lat}, got {resp.status_code}"


@given(lon=st.floats(min_value=181.0, max_value=360.0))
@settings(max_examples=30)
def test_invalid_lon_returns_422(lon):
    """Property 12: Longitude out of [-180, 180] returns HTTP 422"""
    resp = client.post("/score/point", json={"lat": 23.03, "lon": lon, "mode": "city"})
    assert resp.status_code == 422, f"Expected 422 for lon={lon}, got {resp.status_code}"


def test_invalid_geojson_type_returns_422():
    """Property 12: Non-polygon GeoJSON returns HTTP 422"""
    resp = client.post("/score/batch", json={
        "polygon_geojson": {"type": "Point", "coordinates": [72.58, 23.03]},
        "mode": "city",
    })
    assert resp.status_code == 422


def test_valid_point_score_returns_200():
    """Sanity check: valid request returns 200"""
    resp = client.post("/score/point", json={"lat": 23.03, "lon": 72.58, "mode": "city"})
    assert resp.status_code == 200
    data = resp.json()
    assert "score" in data
    assert 0.0 <= data["score"] <= 100.0


def test_valid_batch_score_returns_200():
    """Sanity check: valid batch request returns 200"""
    polygon = {
        "type": "Polygon",
        "coordinates": [[
            [72.55, 23.00], [72.60, 23.00],
            [72.60, 23.05], [72.55, 23.05],
            [72.55, 23.00],
        ]]
    }
    resp = client.post("/score/batch", json={"polygon_geojson": polygon, "mode": "city"})
    assert resp.status_code == 200
    data = resp.json()
    assert "sites" in data
    assert "top10" in data


def test_csv_export_returns_csv():
    """CSV export returns correct content type"""
    resp = client.post("/export/csv", json={
        "sites": [{"lat": 23.03, "lon": 72.58, "score": 75.0, "mode": "city", "breakdown": []}],
        "mode": "city",
    })
    assert resp.status_code == 200
    assert "text/csv" in resp.headers.get("content-type", "")
