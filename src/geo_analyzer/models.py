from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, field_validator


class PointScoreRequest(BaseModel):
    lat: float
    lon: float
    mode: Literal["city", "highway"]

    @field_validator("lat")
    @classmethod
    def validate_lat(cls, v: float) -> float:
        if not -90.0 <= v <= 90.0:
            raise ValueError(f"Latitude must be in [-90, 90], got {v}")
        return v

    @field_validator("lon")
    @classmethod
    def validate_lon(cls, v: float) -> float:
        if not -180.0 <= v <= 180.0:
            raise ValueError(f"Longitude must be in [-180, 180], got {v}")
        return v


class BatchScoreRequest(BaseModel):
    polygon_geojson: dict
    mode: Literal["city", "highway"]


class HotspotRequest(BaseModel):
    polygon_geojson: dict
    mode: Literal["city", "highway"]


class FactorBreakdown(BaseModel):
    factor_name: str
    raw_value: float
    normalized_score: float
    weight: float
    weighted_contribution: float


class PointScoreResponse(BaseModel):
    lat: float
    lon: float
    score: float
    mode: str
    breakdown: list[FactorBreakdown]
    out_of_bounds: bool = False
    warnings: list[str] = []
    rule_score: Optional[float] = None
    ml_score: Optional[float] = None
    ml_active: bool = False


class BatchScoreResponse(BaseModel):
    sites: list[PointScoreResponse]
    top10: list[PointScoreResponse]
    grid_reduced: bool = False


class H3CellScore(BaseModel):
    h3_index: str
    center_lat: float
    center_lon: float
    score: float
    breakdown: list[FactorBreakdown]


class HotspotResponse(BaseModel):
    geojson_features: dict
    top10: list[H3CellScore]
