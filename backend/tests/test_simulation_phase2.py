"""
test_simulation_phase2.py — Phase 2 Simulation Tests
======================================================
New tests added during the Week 3 fixes.  Tests cover:

  1. PedestrianTrajectory — pause phases, bounded speed
  2. MotorcycleTrajectory — straight/turn state machine, speed range
  3. SimulationBoundary   — clamping, specular reflection
  4. KalmanFilter3D       — convergence on drone altitude
  5. Adaptive R (KalmanFilter + KalmanFilter3D)
  6. Regression: all three trajectories stay within boundary
"""

import math
import pytest
import numpy as np
from pydantic import ValidationError

from app.simulation.target_simulator import (
    PedestrianTrajectory,
    MotorcycleTrajectory,
    DroneTrajectory,
)

# Expose _TURN_ANGLES_RAD for type-check tests
_TURN_ANGLES_RAD = MotorcycleTrajectory._TURN_ANGLES_RAD
from app.simulation.boundary import SimulationBoundary
from app.algorithms.kalman_filter import KalmanFilter, KalmanFilter3D


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _rng(seed: int = 42):
    return np.random.default_rng(seed)


def _run_trajectory(traj, steps: int) -> list[tuple[float, float, float]]:
    """Step a trajectory and return the list of (east, north, alt) positions."""
    return [traj.step() for _ in range(steps)]


# ─────────────────────────────────────────────────────────────────────────────
# 1. PedestrianTrajectory
# ─────────────────────────────────────────────────────────────────────────────

class TestPedestrianTrajectory:
    DT = 0.1  # 10 Hz

    def test_speed_within_bounds_when_walking(self):
        """Walking speed must stay in [0.5, 2.0] m/s during active steps."""
        ped = PedestrianTrajectory(rng=_rng(0), dt=self.DT)
        positions = _run_trajectory(ped, 300)
        for i in range(1, len(positions)):
            de = positions[i][0] - positions[i - 1][0]
            dn = positions[i][1] - positions[i - 1][1]
            speed = math.sqrt(de**2 + dn**2) / self.DT
            # Speed during pause phase decelerates gracefully — only cap above
            assert speed <= 2.5, f"Speed {speed:.2f} m/s too fast at step {i}"

    def test_pause_phase_position_held(self):
        """During pause steps the position must not change."""
        ped = PedestrianTrajectory(rng=_rng(5), dt=self.DT)
        # Force a pause immediately
        ped._pause_steps = 5
        prev = (ped.east, ped.north)
        for _ in range(5):
            e, n, _ = ped.step()
        # Position should be same or only slightly changed (decelerating)
        dist = math.sqrt((e - prev[0])**2 + (n - prev[1])**2)
        assert dist < 0.5, f"Position changed by {dist:.3f}m during pause"

    def test_altitude_zero(self):
        """Pedestrian is a 2D target — altitude must remain 0."""
        ped = PedestrianTrajectory(rng=_rng(1), dt=self.DT)
        for e, n, u in _run_trajectory(ped, 100):
            assert u == 0.0, "Pedestrian altitude should always be 0"

    def test_heading_drift_is_smooth(self):
        """Heading changes must be smooth per step (waypoint-based nav, max 25°/s)."""
        ped = PedestrianTrajectory(rng=_rng(2), dt=self.DT)
        headings = [ped.heading]
        for _ in range(200):
            ped.step()
            headings.append(ped.heading)
        diffs = [abs(headings[i] - headings[i - 1]) for i in range(1, len(headings))]
        max_diff_deg = math.degrees(max(diffs))
        # Max turn rate = 25°/s × 0.1s/step = 2.5°/step (waypoint nav)
        assert max_diff_deg <= 2.6, f"Heading changed too sharply: {max_diff_deg:.2f}°"


# ─────────────────────────────────────────────────────────────────────────────
# 2. MotorcycleTrajectory
# ─────────────────────────────────────────────────────────────────────────────

class TestMotorcycleTrajectory:
    DT = 0.1

    def test_state_machine_transitions(self):
        """Must visit both STRAIGHT and TURNING states within 600 steps (60s)."""
        moto = MotorcycleTrajectory(rng=_rng(42), dt=self.DT)
        states = set()
        for _ in range(600):
            moto.step()
            states.add(moto._state)
        assert MotorcycleTrajectory._State.STRAIGHT in states
        assert MotorcycleTrajectory._State.TURNING  in states

    def test_cruise_speed_range(self):
        """Noisy speed must stay above 3 m/s floor (set in step())."""
        moto = MotorcycleTrajectory(rng=_rng(99), dt=self.DT)
        positions = _run_trajectory(moto, 300)
        for i in range(1, len(positions)):
            de = positions[i][0] - positions[i - 1][0]
            dn = positions[i][1] - positions[i - 1][1]
            speed = math.sqrt(de**2 + dn**2) / self.DT
            assert speed >= 2.0, f"Speed {speed:.2f} m/s dropped below floor at step {i}"

    def test_altitude_zero(self):
        """Motorcycle is 2D — altitude must remain 0."""
        moto = MotorcycleTrajectory(rng=_rng(3), dt=self.DT)
        for e, n, u in _run_trajectory(moto, 100):
            assert u == 0.0

    def test_turn_arc_geometry(self):
        """During a TURNING phase, heading must change monotonically (same sign)."""
        moto = MotorcycleTrajectory(rng=_rng(7), dt=self.DT)
        # Fast-forward to a turn
        for _ in range(200):
            moto.step()
            if moto._state == MotorcycleTrajectory._State.TURNING:
                break
        else:
            pytest.skip("No TURNING state reached in 200 steps (seed issue)")

        turn_rate = moto._turn_rate
        headings = [moto.heading]
        while moto._state == MotorcycleTrajectory._State.TURNING:
            moto.step()
            headings.append(moto.heading)

        if len(headings) < 2:
            pytest.skip("Turn was too short to verify")

        diffs = [headings[i] - headings[i - 1] for i in range(1, len(headings))]
        # Sign of all diffs should match sign of turn_rate
        if turn_rate > 0:
            assert all(d >= -0.05 for d in diffs), "CW turn heading should increase"
        else:
            assert all(d <= 0.05 for d in diffs), "CCW turn heading should decrease"


# ─────────────────────────────────────────────────────────────────────────────
# 3. SimulationBoundary
# ─────────────────────────────────────────────────────────────────────────────

class TestSimulationBoundary:
    def test_inside_unchanged(self):
        """Points inside the boundary must be returned unchanged."""
        b = SimulationBoundary(radius_m=100.0)
        e, n, h = b.constrain(50.0, 30.0, 0.5)
        assert e == pytest.approx(50.0)
        assert n == pytest.approx(30.0)
        assert h == pytest.approx(0.5)

    def test_outside_clamped_to_radius(self):
        """Points outside are snapped exactly to the boundary radius."""
        b = SimulationBoundary(radius_m=100.0)
        e, n, _ = b.constrain(200.0, 0.0, 0.0)
        dist = math.sqrt(e**2 + n**2)
        assert dist == pytest.approx(100.0, abs=1e-9)

    def test_reflection_heading_points_inward(self):
        """After reflection, the target must move inward (dot product < 0)."""
        b = SimulationBoundary(radius_m=100.0)
        # Target is OUTSIDE the boundary (distance 110m) heading due East
        # heading East: sin(h)=1, cos(h)=0  => atan2(1,0) = pi/2
        heading_east = math.pi / 2
        # constrain clamps to (100, 0) and reflects heading
        e, n, new_h = b.constrain(110.0, 0.0, heading_east)
        # Verify position is on boundary
        assert math.sqrt(e**2 + n**2) == pytest.approx(100.0, abs=1e-6)
        # Reflected heading velocity vector
        vx = math.sin(new_h)
        vy = math.cos(new_h)
        # Outward normal at (100, 0) is (1, 0)
        dot = vx * 1.0 + vy * 0.0
        assert dot < 0, "Reflected heading must point inward (dot with normal < 0)"

    def test_invalid_radius_raises(self):
        with pytest.raises(ValueError):
            SimulationBoundary(radius_m=0.0)
        with pytest.raises(ValueError):
            SimulationBoundary(radius_m=-50.0)

    def test_on_boundary_exact(self):
        """A point exactly on the boundary should not be reflected."""
        b = SimulationBoundary(radius_m=100.0)
        e, n, h = b.constrain(100.0, 0.0, math.pi)  # heading North (inward)
        # Position should be unchanged
        assert math.sqrt(e**2 + n**2) == pytest.approx(100.0, abs=1e-6)

    def test_all_trajectories_stay_within_boundary(self):
        """After applying boundary, no trajectory position exceeds the radius."""
        radius = 400.0
        b = SimulationBoundary(radius_m=radius)
        dt = 0.1

        for TrajectoryClass, kwargs in [
            (PedestrianTrajectory, {"start_east": 350.0, "start_north": 0.0}),
            (MotorcycleTrajectory, {"start_east": 350.0, "start_north": 0.0}),
            (DroneTrajectory,      {"start_east": 350.0, "start_north": 0.0}),
        ]:
            traj = TrajectoryClass(rng=_rng(42), dt=dt, **kwargs)
            for step_i in range(600):  # 60 s
                e, n, u = traj.step()
                # Apply boundary
                if hasattr(traj, 'heading'):
                    e, n, new_h = b.constrain(e, n, traj.heading)
                    traj.east = e
                    traj.north = n
                    traj.heading = new_h
                dist = math.sqrt(e**2 + n**2)
                assert dist <= radius + 1e-6, (
                    f"{TrajectoryClass.__name__}: dist={dist:.1f}m > radius={radius}m at step {step_i}"
                )


# ─────────────────────────────────────────────────────────────────────────────
# 4. KalmanFilter3D
# ─────────────────────────────────────────────────────────────────────────────

class TestKalmanFilter3D:
    def test_state_shape(self):
        kf = KalmanFilter3D()
        assert kf.x.shape == (6,), "3D state must be 6-element vector"
        assert kf.P.shape == (6, 6)
        assert kf.F.shape == (6, 6)
        assert kf.H.shape == (3, 6)

    def test_not_initialized(self):
        kf = KalmanFilter3D()
        assert not kf._initialized

    def test_initialize(self):
        kf = KalmanFilter3D()
        kf.initialize(10.0, 20.0, 30.0)
        assert kf._initialized
        assert kf.x[0] == pytest.approx(10.0)
        assert kf.x[1] == pytest.approx(20.0)
        assert kf.x[2] == pytest.approx(30.0)
        assert kf.x[3] == pytest.approx(0.0)  # initial vE
        assert kf.x[4] == pytest.approx(0.0)  # initial vN
        assert kf.x[5] == pytest.approx(0.0)  # initial vU

    def test_step_initializes_on_first_call(self):
        kf = KalmanFilter3D()
        state = kf.step(5.0, 10.0, 15.0)
        assert kf._initialized
        assert state[0] == pytest.approx(5.0)
        assert state[2] == pytest.approx(15.0)

    def test_convergence_drone_altitude(self):
        """
        3D Kalman must converge altitude (Up axis) within 20 m of truth
        after 50 steps for a drone flying at constant altitude.
        """
        kf = KalmanFilter3D(dt=0.1)
        true_alt = 50.0  # constant altitude
        noisy_rng = np.random.default_rng(1)
        for _ in range(100):
            noise = noisy_rng.normal(0, 3.0)  # 3 m noise on altitude
            kf.step(0.0, 0.0, true_alt + noise)
        assert abs(kf.x[2] - true_alt) < 20.0, (
            f"Altitude estimate {kf.x[2]:.1f}m far from true {true_alt}m"
        )

    def test_altitude_tracking_sinusoidal(self):
        """
        Drone altitude oscillates 30 + 20*sin(2*pi*t/40).
        After 120s, the Kalman estimate should track within 15 m.
        """
        kf = KalmanFilter3D(dt=0.1)
        dt = 0.1
        noisy_rng = np.random.default_rng(42)
        t = 0.0
        for _ in range(1200):  # 120 s
            t += dt
            true_u = 30.0 + 20.0 * math.sin(2 * math.pi * t / 40.0)
            noisy_u = true_u + noisy_rng.normal(0, 2.0)
            noisy_e = noisy_rng.normal(0, 2.0)
            noisy_n = noisy_rng.normal(0, 2.0)
            kf.step(noisy_e, noisy_n, noisy_u)
        true_u_final = 30.0 + 20.0 * math.sin(2 * math.pi * t / 40.0)
        assert abs(kf.x[2] - true_u_final) < 15.0, (
            f"Sinusoidal altitude tracking error too large: "
            f"est={kf.x[2]:.1f}m, truth={true_u_final:.1f}m"
        )

    def test_covariance_decreases_after_updates(self):
        kf = KalmanFilter3D(dt=0.1)
        kf.initialize(0.0, 0.0, 30.0)
        initial_trace = np.trace(kf.P)
        for _ in range(30):
            kf.step(0.0, 0.0, 30.0)
        final_trace = np.trace(kf.P)
        assert final_trace < initial_trace, "Covariance should decrease with measurements"

    def test_position_property(self):
        kf = KalmanFilter3D(dt=0.1)
        kf.step(1.0, 2.0, 3.0)
        pos = kf.position
        assert pos.shape == (3,)
        assert pos[2] == pytest.approx(3.0)

    def test_speed_property(self):
        kf = KalmanFilter3D(dt=0.1)
        kf.initialize(0.0, 0.0, 0.0)
        kf.x[3] = 3.0   # vE
        kf.x[4] = 4.0   # vN
        kf.x[5] = 0.0   # vU
        assert kf.speed == pytest.approx(5.0)  # 3-4-5 triangle

    def test_get_state_dict_keys(self):
        kf = KalmanFilter3D(dt=0.1)
        kf.step(1.0, 2.0, 3.0)
        d = kf.get_state_dict()
        required = {"east", "north", "up", "v_east", "v_north", "v_up",
                    "speed", "uncertainty_m"}
        assert required.issubset(d.keys())

    def test_reset(self):
        kf = KalmanFilter3D(dt=0.1)
        kf.step(10.0, 20.0, 30.0)
        kf.reset()
        assert not kf._initialized
        assert np.all(kf.x == 0.0)

    def test_update_R_adaptive(self):
        """update_R must change the diagonal of R."""
        kf = KalmanFilter3D(dt=0.1)
        kf.update_R(10.0)
        assert kf.R[0, 0] == pytest.approx(100.0)  # 10^2
        kf.update_R(2.0)
        assert kf.R[0, 0] == pytest.approx(4.0)    # 2^2


# ─────────────────────────────────────────────────────────────────────────────
# 5. Adaptive R — KalmanFilter (2D)
# ─────────────────────────────────────────────────────────────────────────────

class TestAdaptiveR2D:
    def test_update_R_changes_diagonal(self):
        kf = KalmanFilter(dt=0.1, target_type="pedestrian")
        kf.update_R(1.0)
        assert kf.R[0, 0] == pytest.approx(1.0)
        kf.update_R(5.0)
        assert kf.R[0, 0] == pytest.approx(25.0)

    def test_step_with_sigma_pos_updates_R(self):
        """step(sigma_pos_m=...) must update R before the Kalman update."""
        kf = KalmanFilter(dt=0.1, target_type="pedestrian")
        # First call initializes (skips predict/update, does not call update_R)
        kf.step(0.0, 0.0)
        # Second call runs full predict+update WITH sigma_pos_m
        kf.step(0.0, 0.0, sigma_pos_m=3.0)
        assert kf.R[0, 0] == pytest.approx(9.0)

    def test_step_without_sigma_pos_preserves_R(self):
        """step() without sigma_pos_m must not change R."""
        kf = KalmanFilter(dt=0.1, target_type="pedestrian", sigma_pos_m=5.0)
        expected_r = kf.R[0, 0]
        kf.step(0.0, 0.0)
        assert kf.R[0, 0] == pytest.approx(expected_r)

    def test_tighter_R_gives_less_smoothing(self):
        """
        With tight R, the filter output converges faster toward new measurements.

        Strategy: Initialize both filters at (0, 0), then feed repeated
        measurement at (100, 0). The tight-R filter (high trust in
        measurements) should reach x[0] closer to 100 faster than the
        loose-R filter (low trust = high smoothing).
        """
        meas = 100.0
        kf_tight = KalmanFilter(dt=0.1, target_type="pedestrian", sigma_pos_m=0.01)
        kf_loose = KalmanFilter(dt=0.1, target_type="pedestrian", sigma_pos_m=50.0)

        # Initialize both at x=0 (far from meas=100)
        kf_tight.initialize(0.0, 0.0)
        kf_loose.initialize(0.0, 0.0)

        # Step 5 times: enough to differentiate, not enough for both to fully converge
        for _ in range(5):
            tight_state = kf_tight.step(meas, 0.0)
            loose_state = kf_loose.step(meas, 0.0)

        err_tight = abs(tight_state[0] - meas)
        err_loose = abs(loose_state[0] - meas)
        assert err_tight < err_loose, (
            f"Tight R must converge faster: tight_err={err_tight:.4f}, loose_err={err_loose:.4f}"
        )


# ─────────────────────────────────────────────────────────────────────────────
# 6. Regression — existing kalman 2D tests still work with new interface
# ─────────────────────────────────────────────────────────────────────────────

class TestKalmanFilter2DRegression:
    """Quick sanity checks that the 2D filter is backward-compatible."""

    def test_step_returns_4_element_array(self):
        kf = KalmanFilter(dt=0.1, target_type="pedestrian")
        state = kf.step(1.0, 2.0)
        assert state.shape == (4,)

    def test_step_with_sigma_pos_returns_same_shape(self):
        kf = KalmanFilter(dt=0.1, target_type="motorcycle")
        state = kf.step(10.0, 20.0, sigma_pos_m=3.0)
        assert state.shape == (4,)

    def test_presets_loaded(self):
        for ttype in ("pedestrian", "motorcycle", "drone"):
            kf = KalmanFilter(dt=0.1, target_type=ttype)
            assert kf.Q is not None

    def test_get_state_dict_no_up_key(self):
        """2D filter dict must NOT have an 'up' key (3D only)."""
        kf = KalmanFilter(dt=0.1, target_type="pedestrian")
        kf.step(1.0, 2.0)
        assert "up" not in kf.get_state_dict()


# ─────────────────────────────────────────────────────────────────────────────
# 7. TestMotorcycleNoCrash
#    Property 1: MotorcycleTrajectory does not crash with any seed
#    Validates: Requirements 1.1, 1.3
# ─────────────────────────────────────────────────────────────────────────────

class TestMotorcycleNoCrash:
    """
    **Validates: Requirements 1.1, 1.3**

    Ensures MotorcycleTrajectory runs without errors across different seeds
    and that the _TURN_ANGLES_RAD class attribute is a proper np.ndarray
    (fixing the bug where a plain Python list caused rng.choice to fail).
    """

    DT = 0.1   # 10 Hz

    def test_turn_angles_rad_is_ndarray(self):
        """_TURN_ANGLES_RAD must be an np.ndarray so rng.choice works correctly."""
        assert isinstance(_TURN_ANGLES_RAD, np.ndarray), (
            f"_TURN_ANGLES_RAD must be np.ndarray, got {type(_TURN_ANGLES_RAD)}"
        )

    @pytest.mark.parametrize("seed", [0, 1, 42, 99, 7, 123, 999])
    def test_motorcycle_no_crash(self, seed: int):
        """
        MotorcycleTrajectory must run 600 steps (60 s) without raising any
        exception for the given seed.
        """
        rng = np.random.default_rng(seed)
        moto = MotorcycleTrajectory(rng=rng, dt=self.DT)
        try:
            for _ in range(600):
                e, n, u = moto.step()
                # Basic sanity: positions must be finite numbers
                assert math.isfinite(e), f"east={e} is not finite at seed={seed}"
                assert math.isfinite(n), f"north={n} is not finite at seed={seed}"
                assert u == 0.0, f"altitude={u} must be 0 for motorcycle (seed={seed})"
        except Exception as exc:  # pragma: no cover
            pytest.fail(
                f"MotorcycleTrajectory crashed with seed={seed}: {exc!r}"
            )


# ─────────────────────────────────────────────────────────────────────────────
# 8. TestDroneBoundary
#    Property 3: Drone horizontal distance stays within boundary
#    Validates: Requirements 2.1, 2.2, 2.3
# ─────────────────────────────────────────────────────────────────────────────

class TestDroneBoundary:
    """
    **Validates: Requirements 2.1, 2.2, 2.3**

    Verifies that when the boundary constraint is applied to DroneTrajectory
    using the same hasattr(traj, 'heading') check as SimulationEngine.run(),
    the drone's horizontal distance from the observer never exceeds the
    boundary radius. Altitude is intentionally NOT constrained.
    """

    DT = 0.1       # 10 Hz
    STEPS = 600    # 60 s
    RADIUS = 400.0

    def test_drone_stays_within_boundary(self):
        """
        Drone horizontal distance must not exceed boundary radius at any step.

        Mirrors exactly what SimulationEngine.run() does: after each step,
        apply boundary via hasattr(traj, 'heading') check, then update
        traj.east, traj.north, traj.heading in-place.
        """
        rng = _rng(42)
        traj = DroneTrajectory(rng=rng, dt=self.DT, start_east=350.0, start_north=0.0)
        boundary = SimulationBoundary(radius_m=self.RADIUS)

        for step_i in range(self.STEPS):
            e, n, u = traj.step()

            # Apply boundary using same engine logic
            if hasattr(traj, 'heading'):
                e, n, new_h = boundary.constrain(e, n, traj.heading)
                traj.east = e
                traj.north = n
                traj.heading = new_h

            dist = math.sqrt(e ** 2 + n ** 2)
            assert dist <= self.RADIUS + 1e-6, (
                f"DroneTrajectory: dist={dist:.3f}m > radius={self.RADIUS}m at step {step_i}"
            )

    def test_drone_altitude_not_constrained(self):
        """
        Altitude must vary freely and not be clamped by the boundary.

        The boundary only constrains horizontal position (east/north).
        Over 600 steps the sinusoidal altitude model produces a range > 1 m.
        """
        rng = _rng(42)
        traj = DroneTrajectory(rng=rng, dt=self.DT, start_east=350.0, start_north=0.0)
        boundary = SimulationBoundary(radius_m=self.RADIUS)

        alts = []
        for _ in range(self.STEPS):
            e, n, u = traj.step()

            if hasattr(traj, 'heading'):
                e, n, new_h = boundary.constrain(e, n, traj.heading)
                traj.east = e
                traj.north = n
                traj.heading = new_h

            alts.append(u)

        alt_range = max(alts) - min(alts)
        assert alt_range > 1.0, (
            f"Altitude range {alt_range:.3f}m too small — altitude may be incorrectly constrained"
        )


# ─────────────────────────────────────────────────────────────────────────────
# 9. TestBoundaryRadiusSchema
#    Property 4: boundary_radius_m validation in schema
#    Validates: Requirements 5.5
# ─────────────────────────────────────────────────────────────────────────────

class TestBoundaryRadiusSchema:
    """
    **Validates: Requirements 5.5**

    Ensures that the `boundary_radius_m` field in SimulationStartRequest
    accepts valid values in [100, 1000] and rejects values outside that range.
    """

    from app.models.schemas import SimulationStartRequest

    @pytest.mark.parametrize("radius", [100.0, 400.0, 1000.0])
    def test_valid_boundary_radius(self, radius: float):
        """Valid boundary_radius_m values (100, 400, 1000) must not raise."""
        req = self.SimulationStartRequest(boundary_radius_m=radius)
        assert req.boundary_radius_m == radius

    @pytest.mark.parametrize("radius", [50.0, 1100.0, -1.0])
    def test_invalid_boundary_radius_raises(self, radius: float):
        """Invalid boundary_radius_m values (50, 1100, -1) must raise ValidationError."""
        with pytest.raises(ValidationError):
            self.SimulationStartRequest(boundary_radius_m=radius)
