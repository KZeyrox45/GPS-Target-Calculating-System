"""
test_sensor_fusion.py — Sensor fusion unit tests
"""
import math
import pytest
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.algorithms.sensor_fusion import fuse_sensors, GPSSpec, IMUSpec, LaserSpec

OBS_LAT = 10.762622
OBS_LON = 106.660172
OBS_ALT = 10.0


class TestFuseSensors:
    def test_north_target(self):
        """Target at azimuth=0, el=0, range=100m should be ~100m North."""
        m = fuse_sensors(OBS_LAT, OBS_LON, OBS_ALT, 0.0, 0.0, 100.0)
        assert m.north == pytest.approx(100.0, abs=0.5)
        assert abs(m.east) < 0.5

    def test_east_target(self):
        """Target at azimuth=90, el=0, range=100m should be ~100m East."""
        m = fuse_sensors(OBS_LAT, OBS_LON, OBS_ALT, 90.0, 0.0, 100.0)
        assert m.east == pytest.approx(100.0, abs=0.5)
        assert abs(m.north) < 0.5

    def test_elevated_target(self):
        """Target at 45° elevation, 100m range: Up ≈ East ≈ 70.7m."""
        m = fuse_sensors(OBS_LAT, OBS_LON, OBS_ALT, 90.0, 45.0, 100.0)
        expected = 100 * math.cos(math.radians(45))
        assert m.east == pytest.approx(expected, abs=0.5)
        assert m.up   == pytest.approx(100 * math.sin(math.radians(45)), abs=0.5)

    def test_sigma_pos_positive(self):
        """Combined uncertainty should always be positive."""
        m = fuse_sensors(OBS_LAT, OBS_LON, OBS_ALT, 45.0, 5.0, 500.0)
        assert m.sigma_pos_m > 0

    def test_sigma_pos_increases_with_range(self):
        """Angular noise contribution grows with range → larger sigma at distance."""
        m_near = fuse_sensors(OBS_LAT, OBS_LON, OBS_ALT, 45.0, 0.0, 100.0)
        m_far  = fuse_sensors(OBS_LAT, OBS_LON, OBS_ALT, 45.0, 0.0, 1000.0)
        assert m_far.sigma_pos_m > m_near.sigma_pos_m

    def test_target_lla_reasonable(self):
        """Target LLA should be near observer for short range."""
        m = fuse_sensors(OBS_LAT, OBS_LON, OBS_ALT, 0.0, 0.0, 200.0)
        dist = abs(m.target_lat - OBS_LAT) * 111_000  # rough metres per degree
        assert dist < 300   # 200m north, should be < 300m lat diff
