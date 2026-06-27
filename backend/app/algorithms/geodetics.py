"""
geodetics.py — Geodetic coordinate conversion utilities
=======================================================
Handles all coordinate system conversions needed for the tracking system:
  - LLA (Latitude, Longitude, Altitude)  <->  ECEF (Earth-Centred Earth-Fixed)
  - LLA  <->  ENU (East-North-Up local frame relative to an observer)
  - Haversine forward/inverse geodesy
  - Bearing calculation

These functions form the mathematical foundation that connects raw sensor
readings (observer GPS + laser range + IMU angles) to the target's geographic
coordinates shown on the map.
"""

import math
import numpy as np
from typing import Tuple

# ----- WGS-84 ellipsoid constants -----
EARTH_A = 6_378_137.0          # Semi-major axis (m)
EARTH_B = 6_356_752.314_245    # Semi-minor axis (m)
EARTH_E2 = 1 - (EARTH_B ** 2) / (EARTH_A ** 2)   # First eccentricity squared
EARTH_R_MEAN = 6_371_000.0     # Mean radius (m), used for spherical approx

DEG2RAD = math.pi / 180.0
RAD2DEG = 180.0 / math.pi


# ─────────────────────────────────────────────────────────────────────────────
# Spherical (Haversine) approximation — adequate for ranges < 100 km
# ─────────────────────────────────────────────────────────────────────────────

def haversine_destination(
    lat_deg: float, lon_deg: float,
    azimuth_deg: float, distance_m: float
) -> Tuple[float, float]:
    """
    Compute destination point from observer + bearing + distance.
    Uses spherical Earth model (Haversine).

    Args:
        lat_deg:      Observer latitude  (degrees)
        lon_deg:      Observer longitude (degrees)
        azimuth_deg:  Bearing from North (degrees, 0-360)
        distance_m:   Distance to target (metres)

    Returns:
        (target_lat_deg, target_lon_deg)

    Mathematical basis:
        δ  = d / R
        φ₂ = asin(sin φ₁ · cos δ + cos φ₁ · sin δ · cos θ)
        λ₂ = λ₁ + atan2(sin θ · sin δ · cos φ₁, cos δ − sin φ₁ · sin φ₂)
    """
    lat1 = lat_deg * DEG2RAD
    lon1 = lon_deg * DEG2RAD
    theta = azimuth_deg * DEG2RAD
    delta = distance_m / EARTH_R_MEAN          # angular distance (rad)

    lat2 = math.asin(
        math.sin(lat1) * math.cos(delta) +
        math.cos(lat1) * math.sin(delta) * math.cos(theta)
    )
    lon2 = lon1 + math.atan2(
        math.sin(theta) * math.sin(delta) * math.cos(lat1),
        math.cos(delta) - math.sin(lat1) * math.sin(lat2)
    )
    # Normalise longitude to [-180, 180]
    lon_out = ((lon2 * RAD2DEG + 540) % 360) - 180
    return lat2 * RAD2DEG, lon_out


def haversine_distance(
    lat1_deg: float, lon1_deg: float,
    lat2_deg: float, lon2_deg: float
) -> float:
    """
    Great-circle distance between two points (metres).

    Returns:
        Distance in metres.
    """
    phi1, phi2 = lat1_deg * DEG2RAD, lat2_deg * DEG2RAD
    dphi = (lat2_deg - lat1_deg) * DEG2RAD
    dlambda = (lon2_deg - lon1_deg) * DEG2RAD

    a = (math.sin(dphi / 2) ** 2 +
         math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return EARTH_R_MEAN * c


def calculate_bearing(
    lat1_deg: float, lon1_deg: float,
    lat2_deg: float, lon2_deg: float
) -> float:
    """
    Initial bearing from point 1 to point 2 (degrees, 0-360).
    """
    phi1 = lat1_deg * DEG2RAD
    phi2 = lat2_deg * DEG2RAD
    dl = (lon2_deg - lon1_deg) * DEG2RAD

    y = math.sin(dl) * math.cos(phi2)
    x = (math.cos(phi1) * math.sin(phi2) -
         math.sin(phi1) * math.cos(phi2) * math.cos(dl))
    bearing = (math.atan2(y, x) * RAD2DEG + 360) % 360
    return bearing


# ─────────────────────────────────────────────────────────────────────────────
# ECEF ↔ LLA conversions  (WGS-84 ellipsoid)
# ─────────────────────────────────────────────────────────────────────────────

def lla_to_ecef(
    lat_deg: float, lon_deg: float, alt_m: float = 0.0
) -> np.ndarray:
    """
    Convert LLA (degrees, metres) → ECEF (metres).

    Returns:
        numpy array [X, Y, Z] in metres
    """
    lat = lat_deg * DEG2RAD
    lon = lon_deg * DEG2RAD

    N = EARTH_A / math.sqrt(1 - EARTH_E2 * math.sin(lat) ** 2)  # prime vertical radius
    X = (N + alt_m) * math.cos(lat) * math.cos(lon)
    Y = (N + alt_m) * math.cos(lat) * math.sin(lon)
    Z = (N * (1 - EARTH_E2) + alt_m) * math.sin(lat)
    return np.array([X, Y, Z])


def ecef_to_lla(ecef: np.ndarray) -> Tuple[float, float, float]:
    """
    Convert ECEF (metres) → LLA (degrees, degrees, metres).
    Uses Bowring's iterative method.

    Returns:
        (lat_deg, lon_deg, alt_m)
    """
    X, Y, Z = ecef
    lon = math.atan2(Y, X)
    p = math.sqrt(X ** 2 + Y ** 2)

    # Iterative latitude
    lat = math.atan2(Z, p * (1 - EARTH_E2))
    for _ in range(10):
        N = EARTH_A / math.sqrt(1 - EARTH_E2 * math.sin(lat) ** 2)
        lat_new = math.atan2(Z + EARTH_E2 * N * math.sin(lat), p)
        if abs(lat_new - lat) < 1e-12:
            break
        lat = lat_new
    lat = lat_new

    N = EARTH_A / math.sqrt(1 - EARTH_E2 * math.sin(lat) ** 2)
    alt = p / math.cos(lat) - N if abs(math.cos(lat)) > 1e-10 else abs(Z) / math.sin(lat) - N * (1 - EARTH_E2)

    return lat * RAD2DEG, lon * RAD2DEG, alt


def lla_to_enu(
    target_lat: float, target_lon: float, target_alt: float,
    origin_lat: float, origin_lon: float, origin_alt: float
) -> np.ndarray:
    """
    Convert target LLA to local ENU frame centred on observer (origin).

    Args:
        target_*:  Target position in LLA
        origin_*:  Observer position in LLA (ENU origin)

    Returns:
        numpy array [East, North, Up] in metres
    """
    ecef_target = lla_to_ecef(target_lat, target_lon, target_alt)
    ecef_origin = lla_to_ecef(origin_lat, origin_lon, origin_alt)
    d_ecef = ecef_target - ecef_origin

    # Rotation matrix ECEF → ENU
    lat0 = origin_lat * DEG2RAD
    lon0 = origin_lon * DEG2RAD
    sin_lat, cos_lat = math.sin(lat0), math.cos(lat0)
    sin_lon, cos_lon = math.sin(lon0), math.cos(lon0)

    R = np.array([
        [-sin_lon,        cos_lon,         0       ],
        [-sin_lat*cos_lon, -sin_lat*sin_lon, cos_lat],
        [ cos_lat*cos_lon,  cos_lat*sin_lon, sin_lat],
    ])
    return R @ d_ecef


def enu_to_lla(
    enu: np.ndarray,
    origin_lat: float, origin_lon: float, origin_alt: float
) -> Tuple[float, float, float]:
    """
    Convert local ENU vector (metres) back to LLA, given observer as origin.

    Returns:
        (lat_deg, lon_deg, alt_m)
    """
    lat0 = origin_lat * DEG2RAD
    lon0 = origin_lon * DEG2RAD
    sin_lat, cos_lat = math.sin(lat0), math.cos(lat0)
    sin_lon, cos_lon = math.sin(lon0), math.cos(lon0)

    # Inverse rotation ENU → ECEF delta
    R_inv = np.array([
        [-sin_lon,  -sin_lat*cos_lon,  cos_lat*cos_lon],
        [ cos_lon,  -sin_lat*sin_lon,  cos_lat*sin_lon],
        [ 0,         cos_lat,          sin_lat        ],
    ])
    ecef_origin = lla_to_ecef(origin_lat, origin_lon, origin_alt)
    ecef_target = ecef_origin + R_inv @ enu
    return ecef_to_lla(ecef_target)


def polar_to_enu(
    azimuth_deg: float, elevation_deg: float, range_m: float
) -> np.ndarray:
    """
    Convert polar sensor measurement (azimuth, elevation, range) to ENU vector.

    The system uses compass convention:
        azimuth = 0°  →  North (Y / North axis)
        azimuth = 90° →  East  (X / East axis)

    Args:
        azimuth_deg:   Horizontal angle from North (0-360°)
        elevation_deg: Vertical angle above horizon (positive up)
        range_m:       Slant range from laser rangefinder (metres)

    Returns:
        numpy [East, North, Up] in metres
    """
    az = azimuth_deg * DEG2RAD
    el = elevation_deg * DEG2RAD

    horizontal = range_m * math.cos(el)   # projected ground distance
    east  = horizontal * math.sin(az)
    north = horizontal * math.cos(az)
    up    = range_m * math.sin(el)
    return np.array([east, north, up])
