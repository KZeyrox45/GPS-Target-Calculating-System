"""
kalman_filter.py — Kalman Filters for Target Tracking
=======================================================
Two filters are provided:

  KalmanFilter    — 2D constant-velocity (pedestrian, motorcycle)
    State:  x = [East, North, vEast, vNorth]          (4x1)
    Measure: z = [East, North]                         (2x1)

  KalmanFilter3D  — 3D constant-velocity (drone)
    State:  x = [East, North, Up, vEast, vNorth, vUp]  (6x1)
    Measure: z = [East, North, Up]                     (3x1)

Both operate in the ENU (East-North-Up) frame in metres relative to the
observer, which linearises geodetic coordinates for short ranges (< 50 km).

Design rationale
----------------
* A single constant-velocity (CV) model is sufficient for the target types
  in this thesis (pedestrian ~1.4 m/s, motorcycle ~10 m/s, drone ~10 m/s)
  because the tracking update rate (10 Hz) is high enough that prediction
  errors from the CV assumption are absorbed by the process noise Q.
* Drone tracking requires a third Up axis because altitude changes
  (sinusoidal, +/-20 m over 40 s) cannot be ignored at close ranges -- the
  laser measures slant range, so altitude errors directly corrupt the
  horizontal position estimate.
* The measurement noise covariance R is kept adaptive: each step the engine
  passes the fused sigma_pos_m (RSS from GPS + IMU + laser errors) so R
  automatically tightens when the laser lock is clean and widens when noisy.
"""

import numpy as np
from typing import Optional


# -----------------------------------------------------------------------------
# Helper: Discrete White Noise Acceleration (DWNA) Q matrix builders
# -----------------------------------------------------------------------------

def _build_Q_2d(sigma_a: float, dt: float) -> np.ndarray:
    """
    2D process noise covariance for constant-velocity model.

    Derived from Singer model (independent E, N axes):
        Q = sigma_a^2 * block_diag(Q_1d, Q_1d)
    where Q_1d = [[dt^4/4, dt^3/2], [dt^3/2, dt^2]]

    Args:
        sigma_a: Acceleration std dev (m/s^2)
        dt:      Time step (s)

    Returns:
        4x4 numpy array
    """
    q   = sigma_a ** 2
    dt2 = dt ** 2
    dt3 = dt ** 3
    dt4 = dt ** 4
    return q * np.array([
        [dt4 / 4, 0,       dt3 / 2, 0      ],
        [0,       dt4 / 4, 0,       dt3 / 2],
        [dt3 / 2, 0,       dt2,     0      ],
        [0,       dt3 / 2, 0,       dt2    ],
    ], dtype=float)


def _build_Q_3d(sigma_a: float, dt: float) -> np.ndarray:
    """
    3D process noise covariance -- same DWNA model extended to Up axis.

    State ordering: [E, N, U, vE, vN, vU]
    Each position-velocity pair gets its own Q_1d block on the diagonal.

    Returns:
        6x6 numpy array
    """
    q   = sigma_a ** 2
    dt2 = dt ** 2
    dt3 = dt ** 3
    dt4 = dt ** 4
    # 1D block for one axis: [[pos-pos, pos-vel], [vel-pos, vel-vel]]
    q11 = q * dt4 / 4   # pos-pos
    q12 = q * dt3 / 2   # pos-vel
    q22 = q * dt2       # vel-vel
    Q = np.zeros((6, 6), dtype=float)
    # Axes: E=(0,3), N=(1,4), U=(2,5)
    for pos_idx, vel_idx in [(0, 3), (1, 4), (2, 5)]:
        Q[pos_idx, pos_idx] = q11
        Q[pos_idx, vel_idx] = q12
        Q[vel_idx, pos_idx] = q12
        Q[vel_idx, vel_idx] = q22
    return Q


# -----------------------------------------------------------------------------
# 2D Kalman Filter  (pedestrian / motorcycle)
# -----------------------------------------------------------------------------

class KalmanFilter:
    """
    Linear Kalman Filter for 2D constant-velocity target tracking.

    Process model (constant velocity):
        x[k] = F * x[k-1] + w,   w ~ N(0, Q)

    Measurement model (position only):
        z[k] = H * x[k] + v,     v ~ N(0, R)

    Attributes:
        dt:   Time step (seconds)
        x:    State estimate  [E, N, vE, vN]  (4x1)
        P:    Error covariance matrix          (4x4)
        F:    State transition matrix          (4x4)
        H:    Measurement matrix               (2x4)
        Q:    Process noise covariance         (4x4)
        R:    Measurement noise covariance     (2x2)
    """

    # Recommended sigma_a (m/s^2) acceleration noise per target type
    SIGMA_A_PRESETS = {
        "pedestrian":  0.5,    # slow, smooth motion — low maneuverability
        "motorcycle":  5.0,    # banked turns at ~10 m/s; a_lat = v^2/r ~ 6.7 m/s^2
        "drone":       5.0,    # agile 3-axis movement
    }

    def __init__(
        self,
        dt: float = 0.1,
        sigma_a: float = 1.0,
        sigma_pos_m: float = 5.0,
        target_type: str = "pedestrian",
    ):
        """
        Initialise filter matrices.

        Args:
            dt:          Time step in seconds (default 0.1 s = 10 Hz)
            sigma_a:     Process noise -- acceleration std dev (m/s^2).
                         Overridden by target_type preset if recognised.
            sigma_pos_m: Measurement position noise std dev (metres).
                         Represents combined GPS + laser + IMU pointing error.
            target_type: One of "pedestrian", "motorcycle", "drone".
                         Sets sigma_a from SIGMA_A_PRESETS if specified.
        """
        if target_type in self.SIGMA_A_PRESETS:
            sigma_a = self.SIGMA_A_PRESETS[target_type]

        self.dt = dt

        # ----- State transition matrix F (constant velocity) -----
        # x[k] = [E + vE*dt, N + vN*dt, vE, vN]^T
        self.F = np.array([
            [1, 0, dt, 0 ],
            [0, 1, 0,  dt],
            [0, 0, 1,  0 ],
            [0, 0, 0,  1 ],
        ], dtype=float)

        # ----- Measurement matrix H (observe position only) -----
        self.H = np.array([
            [1, 0, 0, 0],
            [0, 1, 0, 0],
        ], dtype=float)

        # ----- Process noise Q -----
        self.Q = _build_Q_2d(sigma_a, dt)

        # ----- Measurement noise R -----
        # sigma_pos_m captures combined sensor uncertainty in ENU position.
        # Updated adaptively each step via update_R().
        self.R = (sigma_pos_m ** 2) * np.eye(2)

        # ----- Initial state and covariance -----
        self.x = np.zeros(4)                            # [E, N, vE, vN]
        self.P = np.eye(4) * (sigma_pos_m * 10) ** 2   # large initial uncertainty

        self._initialized = False

    # ───────────────────────────────────────────────────────── public API ──

    def initialize(self, east: float, north: float) -> None:
        """
        Seed the filter with the first measurement.

        Call this before the first predict/update cycle.
        """
        self.x = np.array([east, north, 0.0, 0.0])
        self._initialized = True

    def predict(self) -> np.ndarray:
        """
        Propagate state forward by one time step.

        x^- = F * x
        P^- = F * P * F^T + Q

        Returns:
            Predicted state x^-  [E, N, vE, vN]
        """
        self.x = self.F @ self.x
        self.P = self.F @ self.P @ self.F.T + self.Q
        return self.x.copy()

    def update(self, measurement: np.ndarray) -> np.ndarray:
        """
        Correct the prediction with a new 2D measurement z = [East, North].

        K  = P^- * H^T * (H * P^- * H^T + R)^-1
        x  = x^- + K * (z - H * x^-)
        P  = (I - K * H) * P^-

        Returns:
            Updated state  [E, N, vE, vN]
        """
        z = np.asarray(measurement, dtype=float)
        S = self.H @ self.P @ self.H.T + self.R
        K = self.P @ self.H.T @ np.linalg.inv(S)
        innovation = z - self.H @ self.x
        self.x = self.x + K @ innovation
        self.P = (np.eye(4) - K @ self.H) @ self.P
        return self.x.copy()

    def update_R(self, sigma_pos_m: float) -> None:
        """
        Adaptively update measurement noise covariance R.

        Called each step by the simulation engine with the fused sigma_pos_m
        from sensor fusion (which varies with range and sensor quality).

        Args:
            sigma_pos_m: New 1-sigma position uncertainty (metres).
        """
        self.R = (sigma_pos_m ** 2) * np.eye(2)

    def step(
        self,
        east: float,
        north: float,
        sigma_pos_m: Optional[float] = None,
    ) -> np.ndarray:
        """
        Convenience: predict then update in one call.

        Args:
            east:         Measured East position (metres)
            north:        Measured North position (metres)
            sigma_pos_m:  If provided, updates R adaptively before update step.

        Returns:
            Filtered state [E, N, vE, vN]
        """
        if not self._initialized:
            self.initialize(east, north)
            return self.x.copy()
        if sigma_pos_m is not None:
            self.update_R(sigma_pos_m)
        self.predict()
        return self.update(np.array([east, north]))

    def reset(self, sigma_pos_m: float = 500.0) -> None:
        """Reset filter state (call when tracking is lost)."""
        self.x = np.zeros(4)
        self.P = np.eye(4) * sigma_pos_m ** 2
        self._initialized = False

    # ──────────────────────────────────────────────── read-only properties ──

    @property
    def position(self) -> np.ndarray:
        """Estimated [East, North] position (metres)."""
        return self.x[:2].copy()

    @property
    def velocity(self) -> np.ndarray:
        """Estimated [vEast, vNorth] velocity (m/s)."""
        return self.x[2:].copy()

    @property
    def speed(self) -> float:
        """Estimated speed magnitude (m/s)."""
        return float(np.linalg.norm(self.velocity))

    @property
    def position_uncertainty(self) -> float:
        """RMS position uncertainty from diagonal of P (metres)."""
        return float(np.sqrt((self.P[0, 0] + self.P[1, 1]) / 2))

    def get_state_dict(self) -> dict:
        """Return current filter state as a plain dict for WS serialisation."""
        return {
            "east":          float(self.x[0]),
            "north":         float(self.x[1]),
            "v_east":        float(self.x[2]),
            "v_north":       float(self.x[3]),
            "speed":         self.speed,
            "uncertainty_m": self.position_uncertainty,
        }


# -----------------------------------------------------------------------------
# 3D Kalman Filter  (drone)
# -----------------------------------------------------------------------------

class KalmanFilter3D:
    """
    Linear Kalman Filter for 3D constant-velocity drone tracking.

    Extends KalmanFilter to include an Up (altitude) axis, which is
    necessary for drone targets whose altitude varies significantly
    (+/-20 m in this simulation).  Without the Up axis the slant-range
    measurement from the laser rangefinder cannot be correctly decomposed
    into horizontal and vertical components, leading to systematic bias
    in the horizontal position estimate.

    State vector:  x = [East, North, Up, vEast, vNorth, vUp]^T  (6x1)
    Measurement:   z = [East, North, Up]^T                       (3x1)

    Attributes:
        dt:  Time step (seconds)
        x:   State estimate  [E, N, U, vE, vN, vU]   (6x1)
        P:   Error covariance                          (6x6)
        F:   State transition                          (6x6)
        H:   Measurement matrix                        (3x6)
        Q:   Process noise covariance                  (6x6)
        R:   Measurement noise covariance              (3x3)
    """

    SIGMA_A = 5.0   # m/s^2 -- drone is agile

    def __init__(
        self,
        dt: float = 0.1,
        sigma_a: float = SIGMA_A,
        sigma_pos_m: float = 5.0,
    ):
        """
        Args:
            dt:          Time step (seconds)
            sigma_a:     Acceleration noise std dev (m/s^2)
            sigma_pos_m: Initial measurement noise std dev (metres)
        """
        self.dt = dt

        # ----- State transition F (6x6) -----
        # [E, N, U, vE, vN, vU]^T -- each position integrates its velocity
        self.F = np.array([
            [1, 0, 0, dt, 0,  0 ],
            [0, 1, 0, 0,  dt, 0 ],
            [0, 0, 1, 0,  0,  dt],
            [0, 0, 0, 1,  0,  0 ],
            [0, 0, 0, 0,  1,  0 ],
            [0, 0, 0, 0,  0,  1 ],
        ], dtype=float)

        # ----- Measurement matrix H (3x6) -- observe E, N, U positions -----
        self.H = np.array([
            [1, 0, 0, 0, 0, 0],
            [0, 1, 0, 0, 0, 0],
            [0, 0, 1, 0, 0, 0],
        ], dtype=float)

        # ----- Process noise Q (6x6) -----
        self.Q = _build_Q_3d(sigma_a, dt)

        # ----- Measurement noise R (3x3) -----
        self.R = (sigma_pos_m ** 2) * np.eye(3)

        # ----- Initial state and covariance -----
        self.x = np.zeros(6)
        self.P = np.eye(6) * (sigma_pos_m * 10) ** 2

        self._initialized = False

    # ───────────────────────────────────────────────────────── public API ──

    def initialize(self, east: float, north: float, up: float) -> None:
        """Seed filter with first measurement. Initial velocity = 0."""
        self.x = np.array([east, north, up, 0.0, 0.0, 0.0])
        self._initialized = True

    def predict(self) -> np.ndarray:
        """x^- = F*x,  P^- = F*P*F^T + Q"""
        self.x = self.F @ self.x
        self.P = self.F @ self.P @ self.F.T + self.Q
        return self.x.copy()

    def update(self, measurement: np.ndarray) -> np.ndarray:
        """
        Correct with 3D position measurement z = [East, North, Up].

        K = P^-*H^T*(H*P^-*H^T + R)^-1
        x = x^- + K*(z - H*x^-)
        P = (I - K*H)*P^-
        """
        z = np.asarray(measurement, dtype=float)
        S = self.H @ self.P @ self.H.T + self.R
        K = self.P @ self.H.T @ np.linalg.inv(S)
        innovation = z - self.H @ self.x
        self.x = self.x + K @ innovation
        self.P = (np.eye(6) - K @ self.H) @ self.P
        return self.x.copy()

    def update_R(self, sigma_pos_m: float) -> None:
        """Adaptively update R from fused sensor uncertainty (same API as 2D)."""
        self.R = (sigma_pos_m ** 2) * np.eye(3)

    def step(
        self,
        east: float,
        north: float,
        up: float,
        sigma_pos_m: Optional[float] = None,
    ) -> np.ndarray:
        """
        Predict + update in one call.

        Args:
            east, north, up: Fused ENU position measurement (metres)
            sigma_pos_m:     If provided, updates R adaptively.

        Returns:
            Filtered state [E, N, U, vE, vN, vU]
        """
        if not self._initialized:
            self.initialize(east, north, up)
            return self.x.copy()
        if sigma_pos_m is not None:
            self.update_R(sigma_pos_m)
        self.predict()
        return self.update(np.array([east, north, up]))

    def reset(self, sigma_pos_m: float = 500.0) -> None:
        """Reset to uninitialised state."""
        self.x = np.zeros(6)
        self.P = np.eye(6) * sigma_pos_m ** 2
        self._initialized = False

    # ──────────────────────────────────────────────── read-only properties ──

    @property
    def position(self) -> np.ndarray:
        """Estimated [East, North, Up] position (metres)."""
        return self.x[:3].copy()

    @property
    def velocity(self) -> np.ndarray:
        """Estimated [vEast, vNorth, vUp] velocity (m/s)."""
        return self.x[3:].copy()

    @property
    def speed(self) -> float:
        """Estimated 3D speed magnitude (m/s)."""
        return float(np.linalg.norm(self.velocity))

    @property
    def position_uncertainty(self) -> float:
        """RMS position uncertainty across E, N, U axes (metres)."""
        return float(np.sqrt((self.P[0, 0] + self.P[1, 1] + self.P[2, 2]) / 3))

    def get_state_dict(self) -> dict:
        """Serialisable state dict for WebSocket output."""
        return {
            "east":          float(self.x[0]),
            "north":         float(self.x[1]),
            "up":            float(self.x[2]),
            "v_east":        float(self.x[3]),
            "v_north":       float(self.x[4]),
            "v_up":          float(self.x[5]),
            "speed":         self.speed,
            "uncertainty_m": self.position_uncertainty,
        }
