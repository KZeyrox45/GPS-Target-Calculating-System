"""
test_alpha_beta.py — α-β Filter unit tests
"""
import math
import numpy as np
import pytest
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.algorithms.alpha_beta_filter import AlphaBetaFilter


class TestAlphaBetaInit:
    def test_default_beta_derived(self):
        ab = AlphaBetaFilter(alpha=0.5)
        # Critically damped beta from Benedict-Bordner
        expected_beta = (2 - 0.5) - 2 * math.sqrt(1 - 0.5)
        assert ab.beta == pytest.approx(expected_beta, rel=1e-5)

    def test_invalid_alpha_raises(self):
        with pytest.raises(ValueError):
            AlphaBetaFilter(alpha=0.0)
        with pytest.raises(ValueError):
            AlphaBetaFilter(alpha=1.0)

    def test_invalid_beta_raises(self):
        with pytest.raises(ValueError):
            AlphaBetaFilter(alpha=0.5, beta=2.0)   # exceeds max_beta

    def test_not_initialized(self):
        ab = AlphaBetaFilter()
        assert not ab._initialized


class TestAlphaBetaStep:
    def test_first_step_initializes(self):
        ab = AlphaBetaFilter(alpha=0.5, dt=0.1)
        state = ab.step(10.0, 20.0)
        assert ab._initialized
        assert state[0] == pytest.approx(10.0)
        assert state[1] == pytest.approx(20.0)

    def test_position_smoothing(self):
        """Filter position should be between measurement and previous estimate."""
        ab = AlphaBetaFilter(alpha=0.5, dt=0.1)
        ab.step(0.0, 0.0)
        state = ab.step(10.0, 10.0)
        # With alpha=0.5, filtered position should be 5.0 after one big jump
        # (approx; exact depends on beta too)
        assert 0.0 < state[0] < 10.0
        assert 0.0 < state[1] < 10.0

    def test_constant_velocity_tracking(self):
        """Filter should track a constant-velocity target reasonably well."""
        ab = AlphaBetaFilter(alpha=0.3, dt=0.1)
        speed = 2.0   # m/s East
        errors = []
        for step in range(200):
            true_e = speed * step * 0.1
            state = ab.step(true_e, 0.0)
            if step > 30:
                errors.append(abs(state[0] - true_e))
        rmse = math.sqrt(sum(e**2 for e in errors) / len(errors))
        assert rmse < 3.0   # reasonable for a no-noise test

    def test_velocity_estimation(self):
        """After many steps at constant velocity, estimated velocity should be close."""
        ab = AlphaBetaFilter(alpha=0.4, dt=0.1)
        speed_e, speed_n = 3.0, 1.5
        for step in range(300):
            ab.step(speed_e * step * 0.1, speed_n * step * 0.1)
        assert ab.velocity[0] == pytest.approx(speed_e, rel=0.05)
        assert ab.velocity[1] == pytest.approx(speed_n, rel=0.05)


class TestAlphaBetaReset:
    def test_reset_clears_state(self):
        ab = AlphaBetaFilter(alpha=0.5, dt=0.1)
        ab.step(100.0, 200.0)
        ab.reset()
        assert not ab._initialized
        assert ab._x_e == 0.0
        assert ab._v_e == 0.0

    def test_speed_property(self):
        ab = AlphaBetaFilter(alpha=0.5, dt=0.1)
        ab.step(0.0, 0.0)
        ab._v_e = 3.0
        ab._v_n = 4.0
        assert ab.speed == pytest.approx(5.0)
