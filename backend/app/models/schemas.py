"""Pydantic schemas for API request/response bodies."""

from pydantic import BaseModel, Field
from typing import Literal


class SimulationStartRequest(BaseModel):
    """Body for POST /api/simulation/start"""
    observer_lat: float = Field(10.762622,  ge=-90,  le=90,  description="Observer latitude (degrees)")
    observer_lon: float = Field(106.660172, ge=-180, le=180, description="Observer longitude (degrees)")
    observer_alt: float = Field(10.0, ge=0, description="Observer altitude (metres)")
    target_type: Literal["pedestrian", "motorcycle", "drone"] = "pedestrian"
    algorithm: Literal["kalman", "alpha_beta", "both"] = "both"
    duration_s: float = Field(120.0, ge=5, le=600, description="Simulation duration (seconds)")
    update_rate_hz: float = Field(10.0, ge=1, le=30, description="Frame rate (Hz)")
    alpha: float = Field(0.4, ge=0.01, le=0.99, description="α-β filter alpha parameter")
    seed: int | None = Field(None, description="RNG seed for reproducibility (null = random)")
    boundary_radius_m: float = Field(
        400.0,
        ge=100.0,
        le=1000.0,
        description="Boundary radius (metres). Range: [100, 1000]."
    )

    class Config:
        json_schema_extra = {
            "example": {
                "observer_lat": 10.762622,
                "observer_lon": 106.660172,
                "observer_alt": 10.0,
                "target_type": "motorcycle",
                "algorithm": "both",
                "duration_s": 60.0,
                "update_rate_hz": 10.0,
                "alpha": 0.4,
                "seed": None,
                "boundary_radius_m": 400.0,
            }
        }


class SimulationStartResponse(BaseModel):
    session_id: str
    ws_url: str
    message: str


class StaticCalcRequest(BaseModel):
    """Body for POST /api/calculate (Phase 1 single-point)"""
    observer_lat: float = Field(..., ge=-90,  le=90)
    observer_lon: float = Field(..., ge=-180, le=180)
    observer_alt: float = Field(0.0, ge=0)
    azimuth_deg: float  = Field(..., ge=0, le=360)
    elevation_deg: float = Field(0.0, ge=-90, le=90)
    distance_m: float   = Field(..., gt=0, le=100_000)

    class Config:
        json_schema_extra = {
            "example": {
                "observer_lat": 10.762622,
                "observer_lon": 106.660172,
                "observer_alt": 10.0,
                "azimuth_deg": 45.0,
                "elevation_deg": 2.0,
                "distance_m": 500.0,
            }
        }


class StaticCalcResponse(BaseModel):
    target_lat: float
    target_lon: float
    target_alt: float
    bearing_deg: float
    distance_m: float
    estimated_error_m: float
