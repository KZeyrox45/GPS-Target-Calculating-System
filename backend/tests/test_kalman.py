"""
test_kalman.py — Kalman Filter unit tests

Tests verify:
  - Convergence on a linear trajectory
  - Stationary target: noise rejection
  - RMSE < 5m thesis requirement at 500 m range
  - Filter state dimensions
"""

import math
import numpy as np
import pytest
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.algorithms.kalman_filter import KalmanFilter


class TestKalmanInit:
    def test_state_shape(self):
        kf = KalmanFilter()
        assert kf.x.shape == (4,)
        assert kf.P.shape == (4, 4)
        assert kf.F.shape == (4, 4)
        assert kf.H.shape == (2, 4)
        assert kf.Q.shape == (4, 4)
        assert kf.R.shape == (2, 2)

    def test_default_not_initialized(self):
        kf = KalmanFilter()
        assert not kf._initialized

    def test_initialize(self):
        kf = KalmanFilter()
        kf.initialize(10.0, 20.0)
        assert kf._initialized
        assert kf.x[0] == pytest.approx(10.0)
        assert kf.x[1] == pytest.approx(20.0)

    @pytest.mark.parametrize("target_type", ["pedestrian", "motorcycle", "drone"])
    def test_presets(self, target_type):
        kf = KalmanFilter(target_type=target_type)
        # Q should be positive semi-definite (allow float epsilon ~1e-16)
        eigvals = np.linalg.eigvals(kf.Q).real
        assert np.all(eigvals >= -1e-10), f"Q not PSD for {target_type}: {eigvals}"


class TestKalmanPredict:
    def test_predict_advances_position(self):
        kf = KalmanFilter(dt=0.1)
        kf.initialize(0.0, 0.0)
        # Give it some velocity by hand
        kf.x = np.array([0.0, 0.0, 2.0, 1.0])  # vE=2, vN=1
        kf.predict()
        assert kf.x[0] == pytest.approx(0.2, abs=1e-9)   # E += vE*dt
        assert kf.x[1] == pytest.approx(0.1, abs=1e-9)   # N += vN*dt

    def test_covariance_grows_without_update(self):
        kf = KalmanFilter(dt=0.1)
        kf.initialize(0.0, 0.0)
        p0 = kf.P.copy()
        kf.predict()
        # Uncertainty should increase (or stay same with zero Q — but Q > 0 here)
        assert np.trace(kf.P) >= np.trace(p0)


class TestKalmanUpdate:
    def test_update_moves_state_towards_measurement(self):
        kf = KalmanFilter(dt=0.1)
        kf.initialize(0.0, 0.0)
        kf.predict()
        state_after_update = kf.update(np.array([10.0, 5.0]))
        # Filter should shift towards [10, 5]
        assert state_after_update[0] > 0
        assert state_after_update[1] > 0

    def test_covariance_decreases_after_update(self):
        kf = KalmanFilter(dt=0.1)
        kf.initialize(0.0, 0.0)
        kf.predict()
        p_pred = np.trace(kf.P)
        kf.update(np.array([0.0, 0.0]))
        assert np.trace(kf.P) <= p_pred


class TestKalmanConvergence:
    """Integration tests: run many steps and verify the filter converges."""

    def _simulate_linear(self, speed_e: float, speed_n: float,
                          steps: int = 200, noise_sigma: float = 3.0,
                          seed: int = 42) -> tuple[list, list]:
        """
        Simulate a target moving at constant velocity.
        Returns (errors, states) per step.
        """
        rng = np.random.default_rng(seed)
        kf = KalmanFilter(dt=0.1, sigma_pos_m=noise_sigma, target_type="pedestrian")
        errors = []
        for step in range(steps):
            true_e = speed_e * step * 0.1
            true_n = speed_n * step * 0.1
            meas_e = true_e + rng.normal(0, noise_sigma)
            meas_n = true_n + rng.normal(0, noise_sigma)
            state = kf.step(meas_e, meas_n)
            errors.append(math.sqrt((state[0] - true_e)**2 + (state[1] - true_n)**2))
        return errors

    def test_convergence_pedestrian(self):
        """After initial transient, position error should be < 5 m (thesis spec)."""
        errors = self._simulate_linear(1.4, 0.5, steps=300, noise_sigma=3.0)
        # Ignore first 30 steps (filter settling)
        steady_rmse = math.sqrt(sum(e**2 for e in errors[30:]) / len(errors[30:]))
        assert steady_rmse < 5.0, f"RMSE {steady_rmse:.2f}m exceeds 5m thesis requirement"

    def test_convergence_motorcycle(self):
        """Motorcycle speed: expect RMSE < 5 m with properly tuned sigma_a."""
        rng = np.random.default_rng(0)
        kf = KalmanFilter(dt=0.1, target_type="motorcycle", sigma_pos_m=5.0)
        errors = []
        for step in range(300):
            true_e = 10.0 * step * 0.1    # 10 m/s constant East
            true_n = 0.0
            state = kf.step(
                true_e + rng.normal(0, 5.0),
                true_n + rng.normal(0, 5.0)
            )
            errors.append(math.sqrt((state[0] - true_e)**2 + (state[1] - true_n)**2))
        rmse = math.sqrt(sum(e**2 for e in errors[50:]) / len(errors[50:]))
        assert rmse < 5.0

    def test_stationary_target_noise_rejection(self):
        """Stationary target: filter should converge to near-zero position."""
        rng = np.random.default_rng(7)
        kf = KalmanFilter(dt=0.1, sigma_pos_m=5.0)
        for step in range(200):
            kf.step(rng.normal(0, 5.0), rng.normal(0, 5.0))
        # After 200 steps, estimated position should be close to (0, 0)
        assert abs(kf.position[0]) < 3.0
        assert abs(kf.position[1]) < 3.0

    def test_rmse_within_thesis_spec_500m(self):
        """
        Thesis requirement: positional error < 5m at range < 1km.
        Simulate target at ~500m range (East=500, North=0).
        """
        # At 500m, azimuth noise 0.3° → lateral error ≈ 500 * sin(0.3°) ≈ 2.6m
        # GPS noise ≈ 5m, laser noise ≈ 0.5m → RSS ≈ 5.7m per measurement
        # Kalman filter should reduce this significantly over time
        rng = np.random.default_rng(99)
        kf = KalmanFilter(dt=0.1, sigma_pos_m=6.0, target_type="pedestrian")
        noise_sigma = 5.7   # combined measurement noise at 500m
        errors = []
        for step in range(500):
            true_e = 500.0 + 1.4 * step * 0.1   # pedestrian moving East from 500m
            true_n = 0.0
            state = kf.step(
                true_e + rng.normal(0, noise_sigma),
                true_n + rng.normal(0, noise_sigma)
            )
            errors.append(math.sqrt((state[0] - true_e)**2 + (state[1] - true_n)**2))
        final_rmse = math.sqrt(sum(e**2 for e in errors[100:]) / len(errors[100:]))
        assert final_rmse < 5.0, f"RMSE {final_rmse:.2f}m @ 500m exceeds 5m thesis spec"


class TestKalmanProperties:
    def test_speed_property(self):
        kf = KalmanFilter(dt=0.1)
        kf.initialize(0.0, 0.0)
        kf.x[2] = 3.0   # vE = 3
        kf.x[3] = 4.0   # vN = 4
        assert kf.speed == pytest.approx(5.0)  # 3-4-5 triangle

    def test_reset(self):
        kf = KalmanFilter(dt=0.1)
        kf.initialize(10.0, 20.0)
        kf.reset()
        assert not kf._initialized
        assert np.all(kf.x == 0.0)

    def test_get_state_dict_keys(self):
        kf = KalmanFilter()
        d = kf.get_state_dict()
        for key in ("east", "north", "v_east", "v_north", "speed", "uncertainty_m"):
            assert key in d
