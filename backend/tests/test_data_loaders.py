"""
test_data_loaders.py - Tests for real-world dataset loaders
=============================================================
Tests cover:
  1. GeolifeWalkLoader  - loading, filtering, PCHIP interpolation
  2. AMITMotorcycleLoader - loading, filtering, linear interpolation
  3. GeolifeWalkTrajectory - replay mechanics
  4. AMITMotorcycleTrajectory - replay mechanics
  5. KinematicDroneTrajectory - velocity/acceleration limits, boundary
  6. SimulationEngine - use_realistic_sim flag and fallback behaviour
"""

import math
from datetime import UTC

import numpy as np
import pytest

from app.simulation.data_loaders import (
    _TARGET_HZ,
    _WALK_DURATION_MAX_S,
    _WALK_DURATION_MIN_S,
    _WALK_MAX_DISPLACEMENT_M,
    AMITMotorcycleLoader,
    GeolifeWalkLoader,
    _build_motorcycle_track,
    _build_walk_segment,
    _haversine_m,
    _lat_lon_to_enu,
)
from app.simulation.target_simulator import (
    AMITMotorcycleTrajectory,
    GeolifeWalkTrajectory,
    KinematicDroneTrajectory,
    PedestrianTrajectory,
    SimulationConfig,
    SimulationEngine,
)


def _rng(seed: int = 42) -> np.random.Generator:
    return np.random.default_rng(seed)


# -----------------------------------------------------------------------
# 1. Coordinate utility tests
# -----------------------------------------------------------------------

class TestCoordinateUtils:
    def test_enu_origin_zero(self):
        """ENU of reference point relative to itself is (0, 0)."""
        e, n = _lat_lon_to_enu(10.762622, 106.660172, 10.762622, 106.660172)
        assert abs(e) < 1e-6
        assert abs(n) < 1e-6

    def test_enu_north_positive(self):
        """Moving north (higher lat) increases north component."""
        e, n = _lat_lon_to_enu(10.763, 106.660172, 10.762622, 106.660172)
        assert n > 0
        assert abs(e) < 1.0

    def test_enu_east_positive(self):
        """Moving east (higher lon) increases east component."""
        e, n = _lat_lon_to_enu(10.762622, 106.661, 10.762622, 106.660172)
        assert e > 0
        assert abs(n) < 1.0

    def test_haversine_zero(self):
        """Distance from a point to itself is 0."""
        d = _haversine_m(10.762622, 106.660172, 10.762622, 106.660172)
        assert d < 1e-6

    def test_haversine_known(self):
        """Haversine for 1 degree latitude offset ~ 111 km."""
        d = _haversine_m(10.0, 106.0, 11.0, 106.0)
        assert abs(d - 111_320) < 1000  # within 1 km


# -----------------------------------------------------------------------
# 2. Walk segment builder tests
# -----------------------------------------------------------------------

class TestBuildWalkSegment:
    """Tests for the _build_walk_segment helper using synthetic records."""

    def _make_records(self, n_points: int, dt_s: float = 1.0,
                      speed_mps: float = 1.3) -> list:
        """Generate synthetic GPS records walking north at constant speed."""
        from datetime import datetime
        base = datetime(2007, 8, 4, 3, 30, 0, tzinfo=UTC)
        records = []
        lat = 39.921700
        lon = 116.472343
        dlat_per_step = speed_mps / 111_320 * dt_s
        for i in range(n_points):
            from datetime import timedelta
            dt = base + timedelta(seconds=i * dt_s)
            records.append((dt, lat + i * dlat_per_step, lon))
        return records

    def test_valid_segment_returned(self):
        """A 90-second walk segment at 1 s intervals should return an array."""
        records = self._make_records(90, dt_s=1.0)
        start = records[0][0]
        end = records[-1][0]
        seg = _build_walk_segment(records, start, end)
        assert seg is not None
        assert seg.ndim == 2
        assert seg.shape[1] == 2

    def test_too_short_returns_none(self):
        """Segments shorter than 60 s must be rejected."""
        records = self._make_records(30, dt_s=1.0)
        start = records[0][0]
        end = records[-1][0]
        assert _build_walk_segment(records, start, end) is None

    def test_too_long_returns_none(self):
        """Segments longer than 180 s must be rejected."""
        records = self._make_records(200, dt_s=1.0)
        start = records[0][0]
        end = records[-1][0]
        assert _build_walk_segment(records, start, end) is None

    def test_gap_rejection(self):
        """A gap > 3 s in the GPS trace must reject the segment."""
        records = self._make_records(90, dt_s=1.0)
        # Introduce a 5-second gap in the middle
        from datetime import timedelta
        mid = 45
        records[mid] = (records[mid][0] + timedelta(seconds=5),
                        records[mid][1], records[mid][2])
        start = records[0][0]
        end = records[-1][0]
        assert _build_walk_segment(records, start, end) is None

    def test_interpolated_at_10hz(self):
        """Output should contain approximately duration * 10 rows."""
        records = self._make_records(90, dt_s=1.0)
        start = records[0][0]
        end = records[-1][0]
        seg = _build_walk_segment(records, start, end)
        assert seg is not None
        # 89 seconds * 10 Hz = ~890 rows (tolerance ±2 for rounding)
        assert abs(len(seg) - 890) <= 5

    def test_enu_centred_near_zero(self):
        """Segment ENU should be centred near (0, 0) since it is centroid-relative."""
        records = self._make_records(90, dt_s=1.0)
        start = records[0][0]
        end = records[-1][0]
        seg = _build_walk_segment(records, start, end)
        assert seg is not None
        # For a straight-north walk the east component should be ~0
        assert np.max(np.abs(seg[:, 0])) < 2.0  # east near 0

    def test_max_displacement_rejection(self):
        """Walker with total path > 780 m (half > 390 m from centroid) is rejected.

        For a straight-line walk the centroid is at the midpoint, so the
        farthest point is at distance = total_path / 2 from the centroid.
        At 5 m/s for 180 s: total = 900 m, half = 450 m > 390 m -> rejected.
        """
        records = self._make_records(180, dt_s=1.0, speed_mps=5.0)
        start = records[0][0]
        end = records[-1][0]
        assert _build_walk_segment(records, start, end) is None


# -----------------------------------------------------------------------
# 3. Motorcycle track builder tests
# -----------------------------------------------------------------------

class TestBuildMotorcycleTrack:
    def _make_frames(self, n_frames: int, speed_pix: float = 2.0):
        """Generate straight-line motorcycle frames."""
        frames = []
        for i in range(n_frames):
            x = 100.0 + i * speed_pix
            y = 50.0
            frames.append((i + 1, x + 1.0, y + 0.5))  # (frame, cx, cy)
        return frames

    def test_valid_track_returned(self):
        """50 frames at 5 Hz = 10 s should return a valid array."""
        frames = self._make_frames(50)
        track = _build_motorcycle_track(frames)
        assert track is not None
        assert track.ndim == 2
        assert track.shape[1] == 2

    def test_too_short_returns_none(self):
        """Tracks with fewer than 30 frames should be rejected."""
        frames = self._make_frames(20)
        assert _build_motorcycle_track(frames) is None

    def test_interpolated_to_10hz(self):
        """Output rows should be (2 * n_frames - 1) after 2x linear upsampling."""
        n = 50
        frames = self._make_frames(n)
        track = _build_motorcycle_track(frames)
        assert track is not None
        assert len(track) == 2 * n - 1

    def test_centred_near_zero(self):
        """Track should be centred at (0, 0)."""
        frames = self._make_frames(50)
        track = _build_motorcycle_track(frames)
        assert track is not None
        assert abs(np.mean(track[:, 0])) < 1.0
        assert abs(np.mean(track[:, 1])) < 1.0


# -----------------------------------------------------------------------
# 4. GeolifeWalkLoader integration test
# -----------------------------------------------------------------------

@pytest.mark.slow
class TestGeolifeWalkLoader:
    def test_load_returns_list(self):
        """load() must return a list (possibly empty if dataset absent)."""
        segs = GeolifeWalkLoader.load()
        assert isinstance(segs, list)

    def test_segments_are_2d_float64(self):
        """Each segment must be a (N, 2) float64 array."""
        segs = GeolifeWalkLoader.load()
        for seg in segs[:5]:  # check first 5 if available
            assert seg.ndim == 2
            assert seg.shape[1] == 2
            assert seg.dtype == np.float64

    def test_segments_duration_within_bounds(self):
        """Each segment should have between 600 and 1800 rows (60-180 s at 10 Hz)."""
        segs = GeolifeWalkLoader.load()
        for seg in segs[:10]:
            n_rows = len(seg)
            assert int(_WALK_DURATION_MIN_S * _TARGET_HZ) <= n_rows <= int(_WALK_DURATION_MAX_S * _TARGET_HZ) + 5

    def test_segments_displacement_within_bound(self):
        """No point in any segment should exceed the max displacement limit."""
        segs = GeolifeWalkLoader.load()
        for seg in segs[:10]:
            dist = np.sqrt(seg[:, 0] ** 2 + seg[:, 1] ** 2)
            assert np.max(dist) <= _WALK_MAX_DISPLACEMENT_M + 0.5

    def test_get_segment_returns_array_or_none(self):
        """get_segment returns an ndarray or None."""
        rng = _rng(7)
        result = GeolifeWalkLoader.get_segment(rng)
        assert result is None or isinstance(result, np.ndarray)


# -----------------------------------------------------------------------
# 5. AMITMotorcycleLoader integration test
# -----------------------------------------------------------------------

class TestAMITMotorcycleLoader:
    def test_load_returns_list(self, amit_data):
        """load() must return a list."""
        assert isinstance(amit_data, list)

    def test_segments_are_2d_arrays(self, amit_data):
        """Each track must be a (N, 2) float64 array."""
        for seg in amit_data[:5]:
            assert seg.ndim == 2
            assert seg.shape[1] == 2

    def test_get_segment_returns_array_or_none(self, amit_data):
        """get_segment returns an ndarray or None."""
        rng = _rng(3)
        result = AMITMotorcycleLoader.get_segment(rng)
        assert result is None or isinstance(result, np.ndarray)


# -----------------------------------------------------------------------
# 6. GeolifeWalkTrajectory / AMITMotorcycleTrajectory mechanics
# -----------------------------------------------------------------------

class TestDatasetTrajectoryMechanics:
    """Test replay mechanics using a synthetic segment (bypasses file I/O)."""

    def _make_synthetic_segment(self, n: int = 200) -> np.ndarray:
        """Return a simple straight-line ENU segment for testing."""
        east = np.linspace(0, 50, n)
        north = np.zeros(n)
        return np.column_stack([east, north])

    def test_geolife_replays_segment(self, monkeypatch):
        """GeolifeWalkTrajectory replays the preloaded segment row by row."""
        seg = self._make_synthetic_segment(200)
        monkeypatch.setattr(GeolifeWalkLoader, "get_segment", lambda rng: seg)
        traj = GeolifeWalkTrajectory(rng=_rng(1), dt=0.1)
        e, n, u = traj.step()
        assert u == 0.0
        assert isinstance(e, float)
        assert isinstance(n, float)

    def test_geolife_loops_at_end(self, monkeypatch):
        """After the segment ends, bidirectional replay reverses direction."""
        seg = self._make_synthetic_segment(10)
        monkeypatch.setattr(GeolifeWalkLoader, "get_segment", lambda rng: seg)
        traj = GeolifeWalkTrajectory(rng=_rng(1), dt=0.1)
        positions = [traj.step() for _ in range(20)]
        # After reaching end (idx=9), direction reverses
        # Step 10 reads idx=8, step 11 reads idx=7, etc.
        # Verify positions are from the segment (not teleporting)
        for _i, (e, n, u) in enumerate(positions):
            assert u == 0.0
            assert isinstance(e, float)
            assert isinstance(n, float)
        # Verify reversal: position at step 11 should match step 7
        assert abs(positions[11][0] - positions[7][0]) < 1e-9

    def test_geolife_fallback_on_no_data(self, monkeypatch):
        """GeolifeWalkTrajectory raises RuntimeError when no segments available."""
        monkeypatch.setattr(GeolifeWalkLoader, "get_segment", lambda rng: None)
        with pytest.raises(RuntimeError):
            GeolifeWalkTrajectory(rng=_rng(1), dt=0.1)

    def test_amit_replays_segment(self, monkeypatch):
        """AMITMotorcycleTrajectory replays the preloaded segment row by row."""
        seg = self._make_synthetic_segment(200)
        monkeypatch.setattr(AMITMotorcycleLoader, "get_segment", lambda rng: seg)
        traj = AMITMotorcycleTrajectory(rng=_rng(2), dt=0.1)
        _e, _n, u = traj.step()
        assert u == 0.0


# -----------------------------------------------------------------------
# 7. KinematicDroneTrajectory tests
# -----------------------------------------------------------------------

class TestKinematicDroneTrajectory:
    DT = 0.1  # 10 Hz

    def _run(self, steps: int) -> list[tuple[float, float, float]]:
        traj = KinematicDroneTrajectory(rng=_rng(0), dt=self.DT)
        return [traj.step() for _ in range(steps)]

    def test_returns_three_floats(self):
        """Each step returns (east, north, alt) as floats."""
        traj = KinematicDroneTrajectory(rng=_rng(0), dt=self.DT)
        e, n, u = traj.step()
        assert isinstance(e, float)
        assert isinstance(n, float)
        assert isinstance(u, float)

    def test_altitude_within_bounds(self):
        """Altitude must remain within [ALT_MIN, ALT_MAX] at all times."""
        positions = self._run(1200)
        alts = [p[2] for p in positions]
        assert all(KinematicDroneTrajectory.ALT_MIN <= a <= KinematicDroneTrajectory.ALT_MAX
                   for a in alts)

    def test_horizontal_speed_within_limit(self):
        """Horizontal speed must not exceed V_MAX_H."""
        traj = KinematicDroneTrajectory(rng=_rng(5), dt=self.DT)
        prev_e, prev_n = traj.east, traj.north
        for _ in range(1200):
            e, n, _ = traj.step()
            h_speed = math.sqrt((e - prev_e)**2 + (n - prev_n)**2) / self.DT
            assert h_speed <= KinematicDroneTrajectory.V_MAX_H + 0.5
            prev_e, prev_n = e, n

    def test_vertical_speed_within_limit(self):
        """Vertical speed must respect ascent/descent limits."""
        traj = KinematicDroneTrajectory(rng=_rng(9), dt=self.DT)
        prev_alt = traj.alt
        for _ in range(600):
            _, _, alt = traj.step()
            v_vert = (alt - prev_alt) / self.DT
            assert v_vert <= KinematicDroneTrajectory.V_MAX_ASC + 0.5
            assert v_vert >= -(KinematicDroneTrajectory.V_MAX_DES + 0.5)
            prev_alt = alt

    def test_has_heading_attribute(self):
        """Heading attribute must exist for compatibility with engine."""
        traj = KinematicDroneTrajectory(rng=_rng(0), dt=self.DT)
        assert hasattr(traj, 'heading')
        traj.step()
        assert isinstance(traj.heading, float)


# -----------------------------------------------------------------------
# 8. SimulationEngine realistic mode tests
# -----------------------------------------------------------------------

class TestSimulationEngineRealisticMode:
    def test_use_realistic_sim_false_uses_synthetic(self):
        """Default mode must use a synthetic trajectory."""
        cfg = SimulationConfig(target_type="pedestrian", seed=42)
        engine = SimulationEngine(cfg)
        assert isinstance(engine._traj, PedestrianTrajectory)
        assert not engine._using_realistic

    def test_realistic_mode_falls_back_when_no_data(self, monkeypatch):
        """When dataset is unavailable, engine falls back to synthetic."""
        monkeypatch.setattr(GeolifeWalkLoader, "get_segment", lambda rng: None)
        cfg = SimulationConfig(
            target_type="pedestrian", seed=42, use_realistic_sim=True
        )
        engine = SimulationEngine(cfg)
        assert isinstance(engine._traj, PedestrianTrajectory)
        assert not engine._using_realistic

    def test_realistic_mode_uses_kinematic_drone(self):
        """Kinematic drone does not require external data and must be used directly."""
        cfg = SimulationConfig(
            target_type="drone", seed=42, use_realistic_sim=True
        )
        engine = SimulationEngine(cfg)
        assert isinstance(engine._traj, KinematicDroneTrajectory)
        assert engine._using_realistic

    def test_realistic_mode_geolife_when_data_available(self, monkeypatch):
        """When Geolife data is available, realistic pedestrian uses it."""
        seg = np.column_stack([np.linspace(0, 50, 600), np.zeros(600)])
        monkeypatch.setattr(GeolifeWalkLoader, "get_segment", lambda rng: seg)
        cfg = SimulationConfig(
            target_type="pedestrian", seed=42, use_realistic_sim=True
        )
        engine = SimulationEngine(cfg)
        assert isinstance(engine._traj, GeolifeWalkTrajectory)
        assert engine._using_realistic

    def test_boundary_not_applied_to_dataset_trajectory(self, monkeypatch):
        """Dataset trajectories must not have boundary reflection applied."""
        seg = np.column_stack([np.linspace(0, 50, 600), np.zeros(600)])
        monkeypatch.setattr(GeolifeWalkLoader, "get_segment", lambda rng: seg)
        cfg = SimulationConfig(
            target_type="pedestrian", seed=42, use_realistic_sim=True,
            duration_s=5.0
        )
        engine = SimulationEngine(cfg)
        assert getattr(engine._traj, 'is_dataset_based', False) is True
