"""
alpha_beta_filter.py — α-β (g-h) Tracking Filter
==================================================
A simpler two-parameter fixed-gain filter, useful as a comparison baseline
against the Kalman filter in the thesis.

The α-β filter is a special case of the Kalman filter where gains are
constant (not adaptive). It is computationally trivial but adequate for
targets with roughly constant velocity.

Equations per cycle (1D, applied independently to East and North):
    x_pred  = x + v · dt
    x_filt  = x_pred + α · (z - x_pred)
    v_filt  = v + (β / dt) · (z - x_pred)

Stability condition:  0 < α < 1,  0 < β ≤ 2α − α²
"""

import numpy as np
import math


class AlphaBetaFilter:
    """
    α-β filter for 2D constant-velocity target tracking in ENU frame.

    Operates on East and North axes independently.

    Attributes:
        alpha: Position smoothing factor  (0 < α < 1)
        beta:  Velocity adaptation factor (0 < β ≤ 2α − α²)
        dt:    Time step (seconds)
    """

    @staticmethod
    def _beta_from_alpha(alpha: float) -> float:
        """Compute the critically-damped beta from alpha (Benedict-Bordner)."""
        return (2 - alpha) - 2 * math.sqrt(1 - alpha)

    def __init__(
        self,
        alpha: float = 0.5,
        beta: float | None = None,
        dt: float = 0.1,
    ):
        """
        Args:
            alpha: Position smoothing (higher = trust measurement more).
                   Typical range: 0.2 – 0.8.
            beta:  Velocity smoothing. If None, derived from alpha via
                   the critically-damped Benedict-Bordner condition.
            dt:    Sample period (seconds).
        """
        if not (0 < alpha < 1):
            raise ValueError(f"alpha must be in (0, 1), got {alpha}")

        self.alpha = alpha
        self.beta = beta if beta is not None else self._beta_from_alpha(alpha)
        self.dt = dt

        max_beta = 2 * alpha - alpha ** 2
        if not (0 < self.beta <= max_beta):
            raise ValueError(
                f"beta must be in (0, {max_beta:.3f}] for alpha={alpha}, got {self.beta}"
            )

        # State: [East, North, vEast, vNorth]
        self._x_e = 0.0    # East position (m)
        self._x_n = 0.0    # North position (m)
        self._v_e = 0.0    # East velocity (m/s)
        self._v_n = 0.0    # North velocity (m/s)
        self._initialized = False

    # ─────────────────────────────────────────────────────────── public API ──

    def initialize(self, east: float, north: float) -> None:
        """Seed filter with first measurement (zero velocity assumption)."""
        self._x_e = east
        self._x_n = north
        self._v_e = 0.0
        self._v_n = 0.0
        self._initialized = True

    def step(self, east: float, north: float) -> np.ndarray:
        """
        Process one measurement and return filtered state.

        Args:
            east:  Measured East coordinate (metres)
            north: Measured North coordinate (metres)

        Returns:
            numpy array [East, North, vEast, vNorth]
        """
        if not self._initialized:
            self.initialize(east, north)
            return np.array([self._x_e, self._x_n, self._v_e, self._v_n])

        # --- Predict ---
        x_pred_e = self._x_e + self._v_e * self.dt
        x_pred_n = self._x_n + self._v_n * self.dt

        # --- Residuals (innovation) ---
        res_e = east  - x_pred_e
        res_n = north - x_pred_n

        # --- Update ---
        self._x_e = x_pred_e + self.alpha * res_e
        self._x_n = x_pred_n + self.alpha * res_n
        self._v_e = self._v_e + (self.beta / self.dt) * res_e
        self._v_n = self._v_n + (self.beta / self.dt) * res_n

        return np.array([self._x_e, self._x_n, self._v_e, self._v_n])

    def reset(self) -> None:
        """Reset to uninitialised state."""
        self._x_e = self._x_n = 0.0
        self._v_e = self._v_n = 0.0
        self._initialized = False

    # ───────────────────────────────────────────────── read-only properties ──

    @property
    def position(self) -> np.ndarray:
        return np.array([self._x_e, self._x_n])

    @property
    def velocity(self) -> np.ndarray:
        return np.array([self._v_e, self._v_n])

    @property
    def speed(self) -> float:
        return float(np.linalg.norm(self.velocity))

    def get_state_dict(self) -> dict:
        return {
            "east":    self._x_e,
            "north":   self._x_n,
            "v_east":  self._v_e,
            "v_north": self._v_n,
            "speed":   self.speed,
        }
