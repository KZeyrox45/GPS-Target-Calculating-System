"""
sensor_fusion.py — Sensor Fusion: GPS + IMU + Laser Rangefinder
================================================================
Combines three complementary sensor streams to produce a single ENU
position measurement for the tracking filters.

  GPS     → Observer position (lat, lon, alt) + accuracy σ_gps
  IMU     → Azimuth + Elevation angles        + accuracy σ_az, σ_el
  Laser   → Slant range to target             + accuracy σ_range

Fusion output: ENU vector [East, North, Up] with combined uncertainty σ².

This module also applies Gaussian noise models when *simulating* sensor
imperfections (used by the simulation engine).
"""

import math
import numpy as np
from dataclasses import dataclass

from .geodetics import polar_to_enu, lla_to_enu, enu_to_lla


# ─────────────────────────────────────────────────────────────────────────────
# Sensor specification dataclasses (1-sigma values)
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class GPSSpec:
    """Consumer-grade GNSS receiver specification."""
    sigma_lat_m: float = 5.0       # Horizontal accuracy (m, 1-sigma)
    sigma_lon_m: float = 5.0
    sigma_alt_m: float = 10.0      # Vertical accuracy (m, 1-sigma)


@dataclass
class IMUSpec:
    """Compass / IMU angular accuracy."""
    sigma_azimuth_deg: float = 0.3      # Azimuth std dev (degrees)
    sigma_elevation_deg: float = 0.2    # Elevation std dev (degrees)


@dataclass
class LaserSpec:
    """Laser rangefinder specification."""
    sigma_range_m: float = 0.5          # Range std dev (metres)
    max_range_m: float = 5000.0         # Maximum reliable range
    min_range_m: float = 1.0            # Minimum reliable range


# ─────────────────────────────────────────────────────────────────────────────
# Measurement result
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class FusedMeasurement:
    """Output of the sensor fusion pipeline."""
    east:  float       # Target East  (m relative to observer)
    north: float       # Target North (m relative to observer)
    up:    float       # Target Up    (m relative to observer)
    sigma_pos_m: float # Combined position uncertainty 1-sigma (m)
    target_lat: float  # Target latitude  (degrees)
    target_lon: float  # Target longitude (degrees)
    target_alt: float  # Target altitude  (metres)


# ─────────────────────────────────────────────────────────────────────────────
# Fusion function
# ─────────────────────────────────────────────────────────────────────────────

def fuse_sensors(
    observer_lat: float, observer_lon: float, observer_alt: float,
    azimuth_deg: float, elevation_deg: float, range_m: float,
    gps_spec: GPSSpec | None = None,
    imu_spec: IMUSpec | None = None,
    laser_spec: LaserSpec | None = None,
) -> FusedMeasurement:
    """
    Compute fused ENU target measurement from three sensor inputs.

    The combined position uncertainty σ_pos is derived by propagating
    individual sensor errors through the polar-to-enu transform using
    first-order error propagation (RSS model):

        σ_lateral  = range · sin(σ_azimuth)     (azimuth error → cross-range)
        σ_along    = σ_range                     (range error → along-range)
        σ_pos²     = σ_GPS² + σ_lateral² + σ_along² + σ_elevation²

    Args:
        observer_lat/lon/alt: Observer GNSS position
        azimuth_deg:           IMU bearing (0-360°, from North)
        elevation_deg:         IMU elevation angle (positive = above horizon)
        range_m:               Laser slant range (metres)
        *_spec:                Sensor accuracy specs (defaults = typical values)

    Returns:
        FusedMeasurement with ENU coordinates + uncertainty
    """
    gps   = gps_spec   or GPSSpec()
    imu   = imu_spec   or IMUSpec()
    laser = laser_spec or LaserSpec()

    # 1. Convert polar measurement → local ENU vector
    enu = polar_to_enu(azimuth_deg, elevation_deg, range_m)

    # 2. Propagate to geographic coordinates
    target_lat, target_lon, target_alt = enu_to_lla(
        enu, observer_lat, observer_lon, observer_alt
    )

    # 3. Combined position uncertainty (first-order error propagation)
    az_rad = imu.sigma_azimuth_deg * (math.pi / 180)
    el_rad = imu.sigma_elevation_deg * (math.pi / 180)

    sigma_lateral   = range_m * math.sin(az_rad)          # cross-range from azimuth
    sigma_along     = laser.sigma_range_m                  # along-range from laser
    sigma_elevation = range_m * math.sin(el_rad)           # vertical error from elevation
    sigma_gps       = math.sqrt(gps.sigma_lat_m ** 2 + gps.sigma_lon_m ** 2) / math.sqrt(2)

    sigma_pos = math.sqrt(
        sigma_gps ** 2 +
        sigma_lateral ** 2 +
        sigma_along ** 2 +
        sigma_elevation ** 2
    )

    return FusedMeasurement(
        east=float(enu[0]),
        north=float(enu[1]),
        up=float(enu[2]),
        sigma_pos_m=sigma_pos,
        target_lat=target_lat,
        target_lon=target_lon,
        target_alt=target_alt,
    )
