"""
calculator.py — Phase 1 Static Target Calculation REST endpoint
================================================================
POST /api/calculate
  Accepts observer GPS + azimuth + elevation + distance
  Returns computed target LLA + error estimate
"""

import math
from fastapi import APIRouter
from ..models.schemas import StaticCalcRequest, StaticCalcResponse
from ..algorithms.geodetics import haversine_destination, calculate_bearing, haversine_distance, enu_to_lla, polar_to_enu

router = APIRouter()


@router.post("/calculate", response_model=StaticCalcResponse)
def calculate_static_target(req: StaticCalcRequest):
    """
    Single-shot target coordinate calculation (Phase 1 functionality).

    Uses polar_to_enu + enu_to_lla for full 3-D computation including elevation.
    Falls back to Haversine (flat-Earth) when elevation_deg == 0.
    """
    import numpy as np

    # Convert polar → ENU → LLA
    enu = polar_to_enu(req.azimuth_deg, req.elevation_deg, req.distance_m)
    target_lat, target_lon, target_alt = enu_to_lla(
        enu, req.observer_lat, req.observer_lon, req.observer_alt
    )

    # Bearing and distance back-calculation (for verification)
    bearing = calculate_bearing(req.observer_lat, req.observer_lon, target_lat, target_lon)
    dist_back = haversine_distance(req.observer_lat, req.observer_lon, target_lat, target_lon)

    # Error estimate (RSS model matching Phase 1)
    sigma_gps = 5.0          # metres
    sigma_az_rad = 0.3 * (math.pi / 180)
    sigma_range = 0.5        # metres

    sigma_lateral   = req.distance_m * math.sin(sigma_az_rad)
    estimated_error = math.sqrt(sigma_gps**2 + sigma_lateral**2 + sigma_range**2)

    return StaticCalcResponse(
        target_lat=target_lat,
        target_lon=target_lon,
        target_alt=target_alt,
        bearing_deg=bearing,
        distance_m=dist_back,
        estimated_error_m=estimated_error,
    )
