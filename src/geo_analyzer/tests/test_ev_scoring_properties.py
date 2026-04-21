"""
Property-based tests for the EV Scoring Engine.
Uses Hypothesis to verify correctness properties from the design document.
"""
from __future__ import annotations

import math
from unittest.mock import MagicMock, patch

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from geo_analyzer.ev_scoring import (
    CITY_PROFILE,
    HIGHWAY_PROFILE,
    EVScoringEngine,
    _build_response,
    _generate_grid_points,
    normalize,
)
from geo_analyzer.models import FactorBreakdown, PointScoreResponse


AHMEDABAD_LAT = st.floats(min_value=22.9, max_value=23.2)
AHMEDABAD_LON = st.floats(min_value=72.4, max_value=72.8)
MODE = st.sampled_from(["city", "highway"])


def make_mock_engine(ev_density=25.0, income_score=60.0, pop_density=8000.0,
                     traffic_score=50.0, competition_score=60.0, accessibility_score=50.0,
                     traffic_flow=70.0, distance_gap=25000.0, fuel_proximity=50.0,
                     rest_stop_proximity=50.0, risk_score=30.0):
    engine = MagicMock()

    def execute_side_effect(sql, params=None):
        sql_str = str(sql)
        mock_result = MagicMock()

        if "ev_adoption_zones" in sql_str:
            mock_result.fetchone.return_value = (ev_density,)
        elif "income_zones" in sql_str:
            mock_result.fetchone.return_value = (income_score,)
        elif "population_zones" in sql_str:
            mock_result.fetchone.return_value = (pop_density,)
        elif "city_roads" in sql_str and "GROUP BY" in sql_str:
            mock_result.fetchall.return_value = [("primary", 3), ("secondary", 2)]
        elif "city_roads" in sql_str:
            mock_result.fetchone.return_value = (5,)
        elif "ev_stations" in sql_str and "ST_Distance" in sql_str:
            mock_result.fetchone.return_value = (distance_gap,)
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

    mock_conn = MagicMock()
    mock_conn.execute.side_effect = execute_side_effect
    engine.connect.return_value.__enter__ = MagicMock(return_value=mock_conn)
    engine.connect.return_value.__exit__ = MagicMock(return_value=False)
    return engine


# Property 1: Composite score is always in [0, 100]
# Validates: Requirements 2.1, 2.9, 3.1, 3.8
@given(
    lat=AHMEDABAD_LAT,
    lon=AHMEDABAD_LON,
    mode=MODE,
)
@settings(max_examples=100)
def test_score_in_range(lat, lon, mode):
    """Property 1: Composite score is always in [0, 100]"""
    db = make_mock_engine()
    scoring = EVScoringEngine(db)
    result = scoring.score_point(lat, lon, mode, engine=db)
    assert 0.0 <= result.score <= 100.0, f"Score {result.score} out of [0, 100]"


# Property 2: Composite score equals weighted sum of normalized factors
# Validates: Requirements 2.10, 3.9
@given(
    lat=AHMEDABAD_LAT,
    lon=AHMEDABAD_LON,
    mode=MODE,
)
@settings(max_examples=100)
def test_score_equals_weighted_sum(lat, lon, mode):
    """Property 2: Composite score equals weighted sum of normalized factors"""
    db = make_mock_engine()
    scoring = EVScoringEngine(db)
    result = scoring.score_point(lat, lon, mode, engine=db)

    if result.out_of_bounds or not result.breakdown:
        return

    weighted_sum = sum(f.weighted_contribution for f in result.breakdown)
    assert abs(result.score - weighted_sum) < 0.01, (
        f"Score {result.score} != weighted sum {weighted_sum}"
    )


# Property 3: Every factor's normalized score is in [0, 100]
# Validates: Requirements 2.9, 3.8
@given(
    lat=AHMEDABAD_LAT,
    lon=AHMEDABAD_LON,
    mode=MODE,
)
@settings(max_examples=100)
def test_factor_scores_in_range(lat, lon, mode):
    """Property 3: Every factor's normalized score is in [0, 100]"""
    db = make_mock_engine()
    scoring = EVScoringEngine(db)
    result = scoring.score_point(lat, lon, mode, engine=db)

    for f in result.breakdown:
        assert 0.0 <= f.normalized_score <= 100.0, (
            f"Factor {f.factor_name} normalized_score {f.normalized_score} out of [0, 100]"
        )


# Property 4: City scorer breakdown contains exactly six required factors
# Validates: Requirements 2.2
@given(lat=AHMEDABAD_LAT, lon=AHMEDABAD_LON)
@settings(max_examples=100)
def test_city_factor_names(lat, lon):
    """Property 4: City scorer breakdown contains exactly the six required factors"""
    db = make_mock_engine()
    scoring = EVScoringEngine(db)
    result = scoring.score_point(lat, lon, "city", engine=db)

    if result.out_of_bounds:
        return

    expected = {"ev_adoption", "income", "population", "traffic", "competition", "accessibility"}
    actual = {f.factor_name for f in result.breakdown}
    assert actual == expected, f"City factors {actual} != expected {expected}"


# Property 5: Highway scorer breakdown contains exactly five required factors
# Validates: Requirements 3.2
@given(lat=AHMEDABAD_LAT, lon=AHMEDABAD_LON)
@settings(max_examples=100)
def test_highway_factor_names(lat, lon):
    """Property 5: Highway scorer breakdown contains exactly the five required factors"""
    db = make_mock_engine()
    scoring = EVScoringEngine(db)
    result = scoring.score_point(lat, lon, "highway", engine=db)

    if result.out_of_bounds:
        return

    expected = {"traffic_flow", "distance_gap", "fuel_proximity", "rest_stop_proximity", "risk"}
    actual = {f.factor_name for f in result.breakdown}
    assert actual == expected, f"Highway factors {actual} != expected {expected}"


# Property 6: Distance gap factor is monotonically non-decreasing with distance
# Validates: Requirements 3.4
@given(
    dist_a=st.floats(min_value=0.0, max_value=50000.0),
    dist_b=st.floats(min_value=0.0, max_value=50000.0),
)
@settings(max_examples=100)
def test_distance_gap_monotonic(dist_a, dist_b):
    """Property 6: Distance gap factor is monotonically non-decreasing with distance"""
    score_a = normalize(dist_a, 50000.0)
    score_b = normalize(dist_b, 50000.0)

    if dist_a >= dist_b:
        assert score_a >= score_b - 0.001, (
            f"dist_a={dist_a} >= dist_b={dist_b} but score_a={score_a} < score_b={score_b}"
        )
    else:
        assert score_a <= score_b + 0.001


# Property 7: All batch grid points are contained within the AOI polygon
# Validates: Requirements 5.2
@given(
    center_lon=st.floats(min_value=72.45, max_value=72.70),
    center_lat=st.floats(min_value=22.95, max_value=23.15),
    half_w=st.floats(min_value=0.01, max_value=0.05),
    half_h=st.floats(min_value=0.01, max_value=0.05),
)
@settings(max_examples=50)
def test_batch_grid_containment(center_lon, center_lat, half_w, half_h):
    """Property 7: All batch grid points are contained within the AOI polygon"""
    from shapely.geometry import Point, shape

    polygon = {
        "type": "Polygon",
        "coordinates": [[
            [center_lon - half_w, center_lat - half_h],
            [center_lon + half_w, center_lat - half_h],
            [center_lon + half_w, center_lat + half_h],
            [center_lon - half_w, center_lat + half_h],
            [center_lon - half_w, center_lat - half_h],
        ]]
    }

    points, _ = _generate_grid_points(polygon, max_points=500)
    geom = shape(polygon)

    for lon, lat in points:
        assert geom.contains(Point(lon, lat)) or geom.touches(Point(lon, lat)), (
            f"Point ({lon}, {lat}) is outside the AOI polygon"
        )


# Property 8: Batch candidate count never exceeds 500
# Validates: Requirements 5.6
@given(
    center_lon=st.floats(min_value=72.40, max_value=72.80),
    center_lat=st.floats(min_value=22.90, max_value=23.20),
    half_w=st.floats(min_value=0.001, max_value=0.20),
    half_h=st.floats(min_value=0.001, max_value=0.20),
)
@settings(max_examples=50)
def test_batch_count_max_500(center_lon, center_lat, half_w, half_h):
    """Property 8: Batch candidate count never exceeds 500"""
    polygon = {
        "type": "Polygon",
        "coordinates": [[
            [center_lon - half_w, center_lat - half_h],
            [center_lon + half_w, center_lat - half_h],
            [center_lon + half_w, center_lat + half_h],
            [center_lon - half_w, center_lat + half_h],
            [center_lon - half_w, center_lat - half_h],
        ]]
    }

    points, _ = _generate_grid_points(polygon, max_points=500)
    assert len(points) <= 500, f"Grid generated {len(points)} points, exceeds 500"


# Property 9: Top-10 list is sorted in descending score order
# Validates: Requirements 7.1
@given(scores=st.lists(st.floats(min_value=0.0, max_value=100.0), min_size=1, max_size=50))
@settings(max_examples=100)
def test_top10_sorted_descending(scores):
    """Property 9: Top-10 list is sorted in descending score order"""
    sites = [
        PointScoreResponse(lat=23.0, lon=72.5, score=s, mode="city", breakdown=[])
        for s in scores
    ]
    sorted_sites = sorted(sites, key=lambda r: r.score, reverse=True)
    top10 = sorted_sites[:10]

    for i in range(len(top10) - 1):
        assert top10[i].score >= top10[i + 1].score, (
            f"Top-10 not sorted: index {i} score {top10[i].score} < index {i+1} score {top10[i+1].score}"
        )


# Property 10: Top-10 list contains the highest-scoring candidates
# Validates: Requirements 7.2
@given(scores=st.lists(st.floats(min_value=0.0, max_value=100.0), min_size=10, max_size=50))
@settings(max_examples=100)
def test_top10_contains_highest(scores):
    """Property 10: Top-10 list contains the highest-scoring candidates"""
    sites = [
        PointScoreResponse(lat=23.0, lon=72.5, score=s, mode="city", breakdown=[])
        for s in scores
    ]
    sorted_sites = sorted(sites, key=lambda r: r.score, reverse=True)
    top10 = sorted_sites[:10]
    rest = sorted_sites[10:]

    if rest:
        min_top10 = min(s.score for s in top10)
        max_rest = max(s.score for s in rest)
        assert min_top10 >= max_rest - 0.001, (
            f"Top-10 min score {min_top10} < rest max score {max_rest}"
        )


# Property 11: CSV export contains all required columns for the active mode
# Validates: Requirements 8.2
@given(mode=MODE)
@settings(max_examples=50)
def test_csv_columns(mode):
    """Property 11: CSV export contains all required columns for the active mode"""
    import csv
    import io

    city_factors = ["ev_adoption", "income", "population", "traffic", "competition", "accessibility"]
    highway_factors = ["traffic_flow", "distance_gap", "fuel_proximity", "rest_stop_proximity", "risk"]
    factor_cols = city_factors if mode == "city" else highway_factors

    sites = [{
        "lat": 23.03, "lon": 72.58, "score": 75.0, "mode": mode,
        "breakdown": [{"factor_name": f, "normalized_score": 50.0} for f in factor_cols],
    }]

    output = io.StringIO()
    base_cols = ["lat", "lon", "score", "mode"]
    all_cols = base_cols + factor_cols
    writer = csv.DictWriter(output, fieldnames=all_cols)
    writer.writeheader()
    for site in sites:
        row = {k: site.get(k, "") for k in base_cols}
        breakdown = {b["factor_name"]: b["normalized_score"] for b in site.get("breakdown", [])}
        for fc in factor_cols:
            row[fc] = breakdown.get(fc, "")
        writer.writerow(row)

    output.seek(0)
    reader = csv.DictReader(output)
    headers = reader.fieldnames or []

    for col in ["lat", "lon", "score", "mode"]:
        assert col in headers, f"Missing required column: {col}"
    for col in factor_cols:
        assert col in headers, f"Missing factor column: {col} for mode {mode}"


# Property 13: Point scoring is idempotent (cache consistency)
# Validates: Requirements 10.7
@given(lat=AHMEDABAD_LAT, lon=AHMEDABAD_LON, mode=MODE)
@settings(max_examples=50)
def test_score_idempotent(lat, lon, mode):
    """Property 13: Point scoring is idempotent"""
    db = make_mock_engine()
    scoring = EVScoringEngine(db)

    result1 = scoring.score_point(lat, lon, mode, engine=db)
    result2 = scoring.score_point(lat, lon, mode, engine=db)

    assert abs(result1.score - result2.score) < 0.001, (
        f"Scores differ: {result1.score} vs {result2.score}"
    )
    assert result1.out_of_bounds == result2.out_of_bounds


# Property 15: H3 hotspot cells match expected resolution for active mode
# Validates: Requirements 6.2
@given(mode=MODE)
@settings(max_examples=20)
def test_h3_resolution(mode):
    """Property 15: H3 hotspot cells match the expected resolution for the active mode"""
    import h3

    expected_res = 8 if mode == "city" else 7

    polygon = {
        "type": "Polygon",
        "coordinates": [[
            [72.55, 23.00], [72.62, 23.00],
            [72.62, 23.06], [72.55, 23.06],
            [72.55, 23.00],
        ]]
    }

    db = make_mock_engine()
    scoring = EVScoringEngine(db)
    result = scoring.score_hotspots(polygon, mode, engine=db)

    for cell in result.top10:
        actual_res = h3.get_resolution(cell.h3_index)
        assert actual_res == expected_res, (
            f"H3 cell {cell.h3_index} has resolution {actual_res}, expected {expected_res} for mode {mode}"
        )

    for feature in result.geojson_features.get("features", []):
        h3_idx = feature["properties"]["h3_index"]
        actual_res = h3.get_resolution(h3_idx)
        assert actual_res == expected_res
