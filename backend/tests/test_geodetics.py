"""
test_geodetics.py — Unit tests for geodetic conversion functions
"""

import math
import numpy as np
import pytest
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.algorithms.geodetics import (
    haversine_destination, haversine_distance, calculate_bearing,
    lla_to_ecef, ecef_to_lla, lla_to_enu, enu_to_lla, polar_to_enu,
)

# ── Known reference values (HCMC region) ──────────────────────────────────
OBS_LAT = 10.762622
OBS_LON = 106.660172
OBS_ALT = 10.0

TOLERANCE_M = 0.5          # sub-metre for roundtrip tests
TOLERANCE_BEARING = 0.01   # degrees


class TestHaversineDestination:
    def test_north(self):
        """Moving due North 1 km should increase latitude by ~0.009° (≈ 1 km)."""
        lat2, lon2 = haversine_destination(OBS_LAT, OBS_LON, 0.0, 1000.0)
        assert lat2 > OBS_LAT
        assert abs(lon2 - OBS_LON) < 0.0001   # longitude unchanged for due North

    def test_east(self):
        """Moving due East 1 km should increase longitude."""
        lat2, lon2 = haversine_destination(OBS_LAT, OBS_LON, 90.0, 1000.0)
        assert lon2 > OBS_LON
        assert abs(lat2 - OBS_LAT) < 0.0001

    def test_distance_preserved(self):
        """Roundtrip: destination should be the correct distance from origin."""
        az, dist = 45.0, 500.0
        lat2, lon2 = haversine_destination(OBS_LAT, OBS_LON, az, dist)
        back = haversine_distance(OBS_LAT, OBS_LON, lat2, lon2)
        assert abs(back - dist) < TOLERANCE_M

    def test_zero_distance(self):
        """Zero distance should return the same point."""
        lat2, lon2 = haversine_destination(OBS_LAT, OBS_LON, 90.0, 0.0)
        assert abs(lat2 - OBS_LAT) < 1e-8
        assert abs(lon2 - OBS_LON) < 1e-8


class TestHaversineDistance:
    def test_same_point(self):
        d = haversine_distance(OBS_LAT, OBS_LON, OBS_LAT, OBS_LON)
        assert d == pytest.approx(0.0, abs=1e-6)

    def test_known_1km(self):
        """~1 km north: distance should be ~1000 m."""
        lat2, lon2 = haversine_destination(OBS_LAT, OBS_LON, 0.0, 1000.0)
        d = haversine_distance(OBS_LAT, OBS_LON, lat2, lon2)
        assert d == pytest.approx(1000.0, abs=1.0)

    def test_symmetry(self):
        d1 = haversine_distance(OBS_LAT, OBS_LON, 10.8, 106.7)
        d2 = haversine_distance(10.8, 106.7, OBS_LAT, OBS_LON)
        assert d1 == pytest.approx(d2, rel=1e-6)


class TestBearing:
    def test_east(self):
        lat2, lon2 = haversine_destination(OBS_LAT, OBS_LON, 90.0, 500.0)
        b = calculate_bearing(OBS_LAT, OBS_LON, lat2, lon2)
        assert b == pytest.approx(90.0, abs=TOLERANCE_BEARING)

    def test_north(self):
        lat2, lon2 = haversine_destination(OBS_LAT, OBS_LON, 0.0, 500.0)
        b = calculate_bearing(OBS_LAT, OBS_LON, lat2, lon2)
        # 360.0 and 0.0 are equivalent bearings
        b_normalised = b % 360
        assert b_normalised == pytest.approx(0.0, abs=TOLERANCE_BEARING) or b_normalised == pytest.approx(360.0, abs=TOLERANCE_BEARING)

    def test_northeast(self):
        lat2, lon2 = haversine_destination(OBS_LAT, OBS_LON, 45.0, 500.0)
        b = calculate_bearing(OBS_LAT, OBS_LON, lat2, lon2)
        assert b == pytest.approx(45.0, abs=0.02)


class TestECEFRoundtrip:
    @pytest.mark.parametrize("lat,lon,alt", [
        (OBS_LAT, OBS_LON, OBS_ALT),
        (0.0, 0.0, 0.0),        # equator / prime meridian
        (90.0, 0.0, 0.0),       # North Pole
        (-33.87, 151.21, 50.0), # Sydney
    ])
    def test_lla_ecef_lla_roundtrip(self, lat, lon, alt):
        ecef = lla_to_ecef(lat, lon, alt)
        lat2, lon2, alt2 = ecef_to_lla(ecef)
        assert lat2 == pytest.approx(lat, abs=1e-6)
        assert lon2 == pytest.approx(lon, abs=1e-6)
        assert alt2 == pytest.approx(alt, abs=0.01)   # < 1 cm altitude error


class TestENURoundtrip:
    @pytest.mark.parametrize("east,north,up", [
        (100.0, 200.0, 5.0),
        (500.0, 0.0, 0.0),
        (0.0, -300.0, 20.0),
        (0.0, 0.0, 0.0),
    ])
    def test_enu_lla_enu_roundtrip(self, east, north, up):
        enu_in = np.array([east, north, up])
        lat, lon, alt = enu_to_lla(enu_in, OBS_LAT, OBS_LON, OBS_ALT)
        enu_out = lla_to_enu(lat, lon, alt, OBS_LAT, OBS_LON, OBS_ALT)
        assert enu_out[0] == pytest.approx(east,  abs=TOLERANCE_M)
        assert enu_out[1] == pytest.approx(north, abs=TOLERANCE_M)
        assert enu_out[2] == pytest.approx(up,    abs=TOLERANCE_M)


class TestPolarToENU:
    def test_north(self):
        """Azimuth=0, el=0 → pure North direction."""
        enu = polar_to_enu(0.0, 0.0, 100.0)
        assert enu[0] == pytest.approx(0.0, abs=1e-6)   # East ≈ 0
        assert enu[1] == pytest.approx(100.0, abs=1e-4)  # North = range

    def test_east(self):
        """Azimuth=90, el=0 → pure East direction."""
        enu = polar_to_enu(90.0, 0.0, 100.0)
        assert enu[0] == pytest.approx(100.0, abs=1e-4)
        assert enu[1] == pytest.approx(0.0, abs=1e-6)

    def test_elevation(self):
        """45° elevation should split range equally between horizontal and vertical."""
        enu = polar_to_enu(0.0, 45.0, 100.0)
        expected_horizontal = 100 * math.cos(math.radians(45))
        expected_up = 100 * math.sin(math.radians(45))
        assert enu[2] == pytest.approx(expected_up, rel=1e-5)
        total_h = math.sqrt(enu[0]**2 + enu[1]**2)
        assert total_h == pytest.approx(expected_horizontal, rel=1e-5)
