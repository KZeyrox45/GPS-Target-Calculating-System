"""
target_simulator.py - Moving Target Trajectory Simulation
===========================================================
Generates trajectories for pedestrians, motorcycles, and drones in a
local ENU frame.  Two modes are supported:

  Synthetic mode (use_realistic_sim=False, default):
    Random-waypoint generators with parameterised dynamics.
    Motorcycle always uses the road-network trajectory regardless of mode,
    because a purely kinematic motorcycle driving through buildings is
    unrealistic.

  Realistic mode (use_realistic_sim=True):
    Replays actual field measurements from the Geolife and AMIT datasets.
    - Pedestrian: Geolife GPS walk segments, PCHIP-interpolated to 10 Hz.
    - Motorcycle:  Road-network random walk on HCM City streets (same as
                  synthetic mode — motorcycle always follows roads).
    - Drone:       Kinematic model with DJI Matrice 100 verified parameters.
    If the dataset cannot be loaded, the engine falls back to synthetic mode.
"""

import asyncio
import math
import time
from collections.abc import AsyncGenerator
from dataclasses import dataclass
from typing import ClassVar

import numpy as np

from ..algorithms.alpha_beta_filter import AlphaBetaFilter
from ..algorithms.geodetics import enu_to_lla
from ..algorithms.kalman_filter import KalmanFilter, KalmanFilter3D
from ..algorithms.sensor_fusion import fuse_sensors
from .boundary import SimulationBoundary
from .data_loaders import (
    AMITMotorcycleLoader,
    GeolifeWalkLoader,
    RoadNetworkMotorcycleLoader,
)
from .sensor_noise import SensorNoiseModel

# ---------------------------------
# Output frame (sent over WebSocket)
# ---------------------------------

@dataclass
class TrackingFrame:
    """One data frame streamed to the frontend at each time step."""
    timestamp: float
    step: int

    # True ground-truth target position
    ground_truth: dict        # {lat, lon, alt, east, north}

    # Raw (noisy) sensor observation
    raw_measurement: dict     # {lat, lon, alt, east, north, azimuth, elevation, range}

    # Kalman filter output
    kalman: dict              # {lat, lon, alt, east, north, v_east, v_north, speed, uncertainty_m}

    # α-β filter output
    alpha_beta: dict          # {lat, lon, alt, east, north, v_east, v_north, speed}

    # Pan-tilt system pointing angles (degrees)
    pan_tilt: dict            # {azimuth, elevation, range}

    # Instantaneous error metrics (metres)
    metrics: dict             # {kalman_error, alpha_beta_error, raw_error, kalman_rmse, alpha_beta_rmse}

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "step": self.step,
            "ground_truth": self.ground_truth,
            "raw_measurement": self.raw_measurement,
            "kalman": self.kalman,
            "alpha_beta": self.alpha_beta,
            "pan_tilt": self.pan_tilt,
            "metrics": self.metrics,
        }


# ---------------------------------
# Trajectory generators (ENU in metres relative to observer)
# ---------------------------------

class _Trajectory:
    """Base class for synthetic target trajectory generators."""

    def __init__(self, rng: np.random.Generator, dt: float):
        self.rng = rng
        self.dt = dt
        self.east = 0.0
        self.north = 0.0
        self.alt = 0.0

    def step(self) -> tuple[float, float, float]:
        """Return (east, north, alt) after advancing one time step."""
        raise NotImplementedError


class PedestrianTrajectory(_Trajectory):
    """
    Realistic pedestrian motion model based on research literature
    (Helbing & Molnar 1995 Social Force Model, simplified).

    Key improvements over previous model:
      - Ornstein-Uhlenbeck process for heading: produces correlated random
        walk with natural curved paths instead of zigzag.
      - Gait speed modulation at ~1.8 Hz step frequency: simulates natural
        stride variation.
      - Poisson-process pauses with exponential duration: realistic stop
        distribution at intersections, looking at phone, etc.
      - Speed-dependent turning: slower in tight turns, faster on straights.
      - Boundary repulsion: soft push-back when near edge, not hard reflection.
    """
    _SPEED_MEAN = 1.4    # m/s - average walking speed
    _SPEED_STD  = 0.2    # m/s - natural variation
    _SPEED_MIN  = 0.3    # m/s - minimum (not zero, just very slow)
    _SPEED_MAX  = 2.0    # m/s - fast walk
    _GAIT_FREQ  = 1.8    # Hz - step frequency modulation
    _GAIT_AMP   = 0.08   # m/s - stride speed amplitude

    # OU process parameters for heading
    _OU_TAU     = 2.0    # s - heading correlation time (larger = smoother turns)
    _OU_SIGMA   = 0.4    # rad/s - heading noise intensity

    # Pause model (Poisson process)
    _PAUSE_RATE = 0.003  # per step - probability of starting a pause
    _PAUSE_MEAN_S = 2.0  # seconds - mean pause duration (exponential)

    # Waypoint navigation
    _WAYPOINT_RADIUS = 120.0   # metres
    _WAYPOINT_ARRIVAL_M = 10.0  # metres
    _DEST_REPULSION_SCALE = 50.0  # metres - soft repulsion from boundary

    def __init__(self, rng, dt, start_east=50.0, start_north=50.0):
        super().__init__(rng, dt)
        self.east    = start_east
        self.north   = start_north
        self.heading = rng.uniform(0, 2 * math.pi)
        self._speed  = self._SPEED_MEAN
        self._pause_steps = 0
        self._t = 0.0  # cumulative time for gait modulation
        # Pick an initial destination
        self._dest_e, self._dest_n = self._new_waypoint()

    def _new_waypoint(self) -> tuple[float, float]:
        """Generate waypoint relative to current position (forward-progressing path)."""
        angle = self.rng.uniform(0, 2 * math.pi)
        dist  = self.rng.uniform(20.0, self._WAYPOINT_RADIUS)
        return self.east + dist * math.cos(angle), self.north + dist * math.sin(angle)

    def step(self) -> tuple[float, float, float]:
        self._t += self.dt

        # --- Pause phase (exponential duration) ---
        if self._pause_steps > 0:
            self._pause_steps -= 1
            self._speed = max(0.0, self._speed - 1.0 * self.dt)
            return self.east, self.north, self.alt

        # --- Maybe start a pause (Poisson process) ---
        if self.rng.random() < self._PAUSE_RATE:
            dur_s = self.rng.exponential(self._PAUSE_MEAN_S)
            dur_s = min(dur_s, 5.0)  # cap at 5 seconds
            self._pause_steps = max(1, int(dur_s / self.dt))

        # --- Check if destination reached ---
        dw = self._dest_e - self.east
        dn = self._dest_n - self.north
        dist_to_dest = math.sqrt(dw ** 2 + dn ** 2)
        if dist_to_dest < self._WAYPOINT_ARRIVAL_M:
            self._dest_e, self._dest_n = self._new_waypoint()
            dw = self._dest_e - self.east
            dn = self._dest_n - self.north

        # --- Desired heading toward destination ---
        desired_heading = math.atan2(dw, dn)

        # --- OU process for heading (correlated random walk) ---
        diff = (desired_heading - self.heading + math.pi) % (2 * math.pi) - math.pi
        # Mean-reverting toward desired + noise
        ou_drift = diff / self._OU_TAU
        ou_noise = self.rng.normal(0, self._OU_SIGMA)
        self.heading += (ou_drift + ou_noise) * self.dt

        # --- Gait speed modulation ---
        gait_mod = self._GAIT_AMP * math.sin(2 * math.pi * self._GAIT_FREQ * self._t)
        target_speed = self._SPEED_MEAN + gait_mod
        # Add slow random walk on target speed (every ~2 seconds)
        if self.rng.random() < 0.005:
            target_speed += self.rng.normal(0, self._SPEED_STD)
        target_speed = np.clip(target_speed, self._SPEED_MIN, self._SPEED_MAX)

        # Smooth speed transition (exponential relaxation, tau=1.5s)
        alpha = self.dt / 1.5
        self._speed += alpha * (float(target_speed) - self._speed)
        self._speed = max(self._SPEED_MIN, self._speed)

        self.east  += self._speed * math.sin(self.heading) * self.dt
        self.north += self._speed * math.cos(self.heading) * self.dt
        return self.east, self.north, self.alt


class MotorcycleTrajectory(_Trajectory):
    """
    Realistic motorcycle trajectory based on bicycle kinematic model.

    Key improvements:
      - Bicycle kinematic model: heading_rate = (v / L) * tan(steering_angle),
        where L = 1.4 m wheelbase for a motorcycle.
      - Lateral acceleration limit: a_lat = v²/R ≤ 3.0 m/s² (comfort limit).
      - Longitudinal acceleration profile: ±2.5 m/s², deceleration into turns.
      - Steering rate limit: 45°/s (mechanical limit).
      - State machine: straight → brake → turn → accelerate → straight.
    """
    _SPEED_MEAN = 10.0   # m/s
    _SPEED_MIN  =  7.0   # m/s
    _SPEED_MAX  = 13.0   # m/s

    # Physical parameters
    _WHEELBASE   = 1.4    # m - motorcycle wheelbase
    _A_LAT_MAX   = 3.0    # m/s² - max lateral acceleration
    _A_LONG_MAX  = 2.5    # m/s² - max longitudinal acceleration
    _STEER_RATE_MAX = math.radians(45)  # rad/s
    _STEER_ANGLE_MAX = math.radians(30) # rad

    _STRAIGHT_DUR_RANGE = (3.0, 15.0)  # seconds per straight segment

    class _State:
        STRAIGHT  = "straight"
        BRAKING   = "braking"
        TURNING   = "turning"
        ACCEL     = "accel"

    def __init__(self, rng, dt, start_east=0.0, start_north=0.0):
        super().__init__(rng, dt)
        self.east    = start_east
        self.north   = start_north
        self.heading = rng.uniform(0, 2 * math.pi)
        self._speed  = float(rng.uniform(self._SPEED_MIN, self._SPEED_MAX))
        self._speed_target = self._speed  # target for smooth transitions

        # State machine
        self._state  = self._State.STRAIGHT
        self._steps_left = self._new_straight_duration()
        self._steering_angle  = 0.0
        self._steering_target = 0.0
        self._turn_steps_left = 0
        self._turn_radius = 0.0

    def _new_straight_duration(self) -> int:
        return max(1, int(self.rng.uniform(*self._STRAIGHT_DUR_RANGE) / self.dt))

    def _begin_turn(self) -> None:
        """Pick a new turn and compute parameters."""
        self._turn_radius = self.rng.uniform(15.0, 40.0)
        direction = self.rng.choice([-1, 1])
        # Target steering angle from kinematic relationship: tan(δ) = L / R
        self._steering_target = math.atan(self._WHEELBASE / self._turn_radius) * direction
        # Duration: arc length / speed
        angle = self.rng.uniform(math.radians(60), math.radians(120))
        arc_len = self._turn_radius * angle
        self._turn_steps_left = max(1, int(arc_len / max(self._speed, 1.0) / self.dt))
        self._state = self._State.BRAKING

    def step(self) -> tuple[float, float, float]:
        if self._state == self._State.STRAIGHT:
            self._steps_left -= 1
            # Smooth speed variation (exponential relaxation, tau=2.0s)
            if self.rng.random() < 0.02:
                self._speed_target = float(np.clip(
                    self.rng.normal(self._SPEED_MEAN, 1.0),
                    self._SPEED_MIN, self._SPEED_MAX,
                ))
            alpha_s = self.dt / 2.0
            self._speed += alpha_s * (self._speed_target - self._speed)
            if self._steps_left <= 0:
                self._begin_turn()

        elif self._state == self._State.BRAKING:
            # Decelerate toward turn entry speed (60% of current)
            target = max(self._SPEED_MIN, self._speed * 0.6)
            accel = max(-self._A_LONG_MAX, (target - self._speed) * 1.0)
            self._speed += accel * self.dt
            # Smoothly steer into the turn
            steer_diff = self._steering_target - self._steering_angle
            self._steering_angle += np.clip(steer_diff * 2.0, -self._STEER_RATE_MAX, self._STEER_RATE_MAX) * self.dt
            if self._speed <= target + 0.5:
                self._state = self._State.TURNING

        elif self._state == self._State.TURNING:
            self._turn_steps_left -= 1
            # Bicycle kinematic model: heading_rate = (v/L) * tan(δ)
            heading_rate = (self._speed / self._WHEELBASE) * math.tan(self._steering_angle)
            # Lateral acceleration limit
            a_lat = abs(self._speed * heading_rate)
            if a_lat > self._A_LAT_MAX:
                heading_rate = math.copysign(self._A_LAT_MAX / max(self._speed, 0.1), heading_rate)
            self.heading += heading_rate * self.dt
            if self._turn_steps_left <= 0:
                self._steering_target = 0.0
                self._state = self._State.ACCEL

        elif self._state == self._State.ACCEL:
            # Return steering to straight
            steer_diff = self._steering_target - self._steering_angle
            self._steering_angle += np.clip(steer_diff * 2.0, -self._STEER_RATE_MAX, self._STEER_RATE_MAX) * self.dt
            heading_rate = (self._speed / self._WHEELBASE) * math.tan(self._steering_angle)
            self.heading += heading_rate * self.dt
            # Accelerate back to cruise
            target = float(np.clip(
                self.rng.normal(self._SPEED_MEAN, 1.0),
                self._SPEED_MIN, self._SPEED_MAX,
            ))
            accel = min(self._A_LONG_MAX, (target - self._speed) * 0.8)
            self._speed += accel * self.dt
            if abs(self._steering_angle) < math.radians(1) and self._speed >= target - 0.5:
                self._speed = target
                self._steering_angle = 0.0
                self._steps_left = self._new_straight_duration()
                self._state = self._State.STRAIGHT

        self.east  += self._speed * math.sin(self.heading) * self.dt
        self.north += self._speed * math.cos(self.heading) * self.dt
        return self.east, self.north, self.alt


class DroneTrajectory(_Trajectory):
    """
    Drone with 3-D motion based on Dubins path principles.

    Key improvements:
      - Dubins-inspired smooth arcs: speed-dependent turn rate,
        ω = a_lat_max / v, producing smooth constant-curvature arcs.
      - Step-hold altitude model: holds altitude for 10-30 s, then
        steps up/down by 5-15 m. Much more realistic than continuous
        sinusoidal oscillation.
      - Speed-dependent bank angle: tighter turns at higher speeds.
      - Altitude hold with smooth transitions between levels.
    """
    H_SPEED_MEAN = 11.0   # m/s
    H_SPEED_STD  = 1.5
    H_SPEED_MIN  = 7.0
    H_SPEED_MAX  = 15.0
    A_LAT_MAX    = 4.0    # m/s² - max lateral acceleration (drone turn)

    # Altitude parameters (step-hold model)
    ALT_BASE       = 30.0   # m
    ALT_MIN        = 15.0   # m
    ALT_MAX        = 60.0   # m
    ALT_STEP_SIZE  = 10.0   # m - altitude change per step event
    ALT_STEP_DUR_RANGE = (10.0, 30.0)  # seconds between altitude changes

    WAYPOINT_RADIUS  = 180.0  # metres
    WAYPOINT_ARRIVAL_M = 12.0  # metres
    MAX_TURN_RAD_S   = math.radians(35)  # max turn rate

    def __init__(self, rng, dt, start_east=80.0, start_north=80.0, start_alt=30.0):
        super().__init__(rng, dt)
        self.east  = start_east
        self.north = start_north
        self.alt   = start_alt
        self.heading = rng.uniform(0, 2 * math.pi)
        self._h_speed = self.H_SPEED_MEAN
        self._actual_speed = self.H_SPEED_MEAN  # smoothed speed (OU process)
        self.t = 0.0
        self._waypoint_e, self._waypoint_n = self._new_waypoint()

        # Altitude step-hold state
        self._alt_steps_left = self._new_alt_step_duration()
        self._alt_target     = start_alt

    def _new_waypoint(self) -> tuple[float, float]:
        """Generate waypoint relative to current position (forward-progressing path)."""
        angle = self.rng.uniform(0, 2 * math.pi)
        dist  = self.rng.uniform(40.0, self.WAYPOINT_RADIUS)
        return self.east + dist * math.cos(angle), self.north + dist * math.sin(angle)

    def _new_alt_step_duration(self) -> int:
        dur_s = self.rng.uniform(*self.ALT_STEP_DUR_RANGE)
        return max(1, int(dur_s / self.dt))

    def _compute_turn_rate(self, desired_heading: float) -> float:
        """Dubins-inspired: ω = a_lat_max / v for speed-dependent curvature."""
        diff = (desired_heading - self.heading + math.pi) % (2 * math.pi) - math.pi
        # Speed-dependent turn rate
        if self._h_speed > 0.5:
            omega_max = self.A_LAT_MAX / self._h_speed  # rad/s
        else:
            omega_max = self.MAX_TURN_RAD_S
        omega_max = min(omega_max, self.MAX_TURN_RAD_S)
        return np.clip(diff / 0.4, -omega_max, omega_max)

    def step(self):
        self.t += self.dt

        # --- Check waypoint arrival ---
        dw = self._waypoint_e - self.east
        dn = self._waypoint_n - self.north
        if math.sqrt(dw ** 2 + dn ** 2) < self.WAYPOINT_ARRIVAL_M:
            self._waypoint_e, self._waypoint_n = self._new_waypoint()
            dw = self._waypoint_e - self.east
            dn = self._waypoint_n - self.north
            # Vary speed on new waypoint
            self._h_speed = float(np.clip(
                self.rng.normal(self.H_SPEED_MEAN, self.H_SPEED_STD),
                self.H_SPEED_MIN, self.H_SPEED_MAX,
            ))

        # --- Smooth banking toward waypoint (Dubins-inspired) ---
        desired_heading = math.atan2(dw, dn)
        turn_rate = self._compute_turn_rate(desired_heading)
        self.heading += turn_rate * self.dt

        # Smooth speed with OU process (tau=1.0s) instead of per-step noise
        speed_target = self._h_speed + self.rng.normal(0, 0.3)
        alpha_spd = self.dt / 1.0
        self._actual_speed += alpha_spd * (speed_target - self._actual_speed)
        h_speed = self._actual_speed
        self.east  += h_speed * math.sin(self.heading) * self.dt
        self.north += h_speed * math.cos(self.heading) * self.dt

        # --- Step-hold altitude model ---
        self._alt_steps_left -= 1
        if self._alt_steps_left <= 0:
            # Pick new altitude step
            step = self.rng.uniform(-self.ALT_STEP_SIZE, self.ALT_STEP_SIZE)
            self._alt_target = np.clip(self._alt_target + step, self.ALT_MIN, self.ALT_MAX)
            self._alt_steps_left = self._new_alt_step_duration()

        # Smooth altitude transition (exponential approach, tau=2s)
        alpha = self.dt / 2.0
        self.alt += alpha * (float(self._alt_target) - self.alt)

        return self.east, self.north, self.alt


# ---------------------------------
# Dataset-driven trajectory classes
# ---------------------------------

class _DatasetTrajectory(_Trajectory):
    """
    Base class for trajectory replayers that step through a preloaded
    NumPy ENU array.  The boundary reflection logic in SimulationEngine
    is skipped for dataset trajectories (segments are already filtered
    to stay within 390 m of their centroid).

    Bidirectional replay: when the segment ends, the direction reverses
    instead of teleporting back to the start.  This avoids the jarring
    position jump that occurred with the previous modulo-loop approach.
    """
    is_dataset_based: bool = True

    def __init__(self, rng: np.random.Generator, dt: float, segment: np.ndarray):
        super().__init__(rng, dt)
        self._seg = segment  # (N, 2) float64: (east, north)
        self._idx = 0
        self._len = len(segment)
        self._direction = 1  # +1 forward, -1 backward
        # heading is computed from successive positions for diagnostics
        self.heading = 0.0

    def step(self) -> tuple[float, float, float]:
        e = float(self._seg[self._idx, 0])
        n = float(self._seg[self._idx, 1])

        prev_idx = max(0, self._idx - 1)
        de = e - float(self._seg[prev_idx, 0])
        dn = n - float(self._seg[prev_idx, 1])
        if abs(de) > 1e-9 or abs(dn) > 1e-9:
            self.heading = math.atan2(de, dn)

        self.east = e
        self.north = n
        # Bidirectional replay: reverse direction at segment ends
        self._idx += self._direction
        if self._idx >= self._len:
            self._idx = self._len - 2  # step back so next call reads len-2
            self._direction = -1
        elif self._idx < 0:
            self._idx = 1  # step forward so next call reads 1
            self._direction = 1
        return e, n, 0.0


class GeolifeWalkTrajectory(_DatasetTrajectory):
    """
    Replays a pedestrian walk segment from the Geolife GPS dataset.

    Segments are PCHIP-interpolated to 10 Hz and centred at their
    geographic centroid.  If no valid segments are available, the
    constructor raises RuntimeError so the caller can fall back to
    the synthetic PedestrianTrajectory.
    """

    def __init__(self, rng: np.random.Generator, dt: float):
        seg = GeolifeWalkLoader.get_segment(rng)
        if seg is None:
            raise RuntimeError("GeolifeWalkLoader: no valid walk segments found")
        super().__init__(rng, dt, seg)


class AMITMotorcycleTrajectory(_DatasetTrajectory):
    """
    Replays a motorcycle track from the AMIT UAV intersection dataset.

    Tracks are linearly interpolated from 5 Hz to 10 Hz and centred at
    their metric centroid.  If no valid tracks are available, the
    constructor raises RuntimeError so the caller can fall back to
    the synthetic MotorcycleTrajectory.
    """

    def __init__(self, rng: np.random.Generator, dt: float):
        seg = AMITMotorcycleLoader.get_segment(rng)
        if seg is None:
            raise RuntimeError("AMITMotorcycleLoader: no valid motorcycle tracks found")
        super().__init__(rng, dt, seg)


class RoadNetworkMotorcycleTrajectory(_DatasetTrajectory):
    """
    Replays a motorcycle trajectory generated by random walking on a
    real OpenStreetMap road network.

    The trajectory follows actual HCM City streets with speed limits
    derived from OSM ``maxspeed`` tags (or Vietnamese default speed
    limits by road type).  Positions are linearly interpolated to
    10 Hz in an ENU frame centred on the observer.

    Falls back to synthetic MotorcycleTrajectory if the road network
    GraphML file is unavailable.
    """

    def __init__(self, rng: np.random.Generator, dt: float,
                 observer_lat: float = 10.7709, observer_lon: float = 106.7030):
        seg = RoadNetworkMotorcycleLoader.get_segment(
            rng, observer_lat=observer_lat, observer_lon=observer_lon,
        )
        if seg is None:
            raise RuntimeError("RoadNetworkMotorcycleLoader: no road network or walk too short")
        super().__init__(rng, dt, seg)


class KinematicDroneTrajectory(_Trajectory):
    """
    Physics-based drone trajectory using parameters from the DJI Matrice 100
    quadcopter (Rodrigues et al., Nature Scientific Data, 2021,
    arXiv-2103.13313v1).

    Unlike the random-waypoint DroneTrajectory, this model enforces
    acceleration and velocity limits derived from the actual airframe:

      v_max_horiz  = 15 m/s  (maximum horizontal speed)
      v_max_ascent =  5 m/s  (maximum ascent speed)
      v_max_descent=  4 m/s  (maximum descent speed)
      a_max_horiz  =  4 m/s^2 (maximum horizontal acceleration)
      a_max_vert   =  3 m/s^2 (maximum vertical acceleration)

    The drone navigates between random 3-D waypoints.  On each step the
    controller computes desired acceleration toward the waypoint, clamps
    it to the airframe limits, then integrates velocity and position.
    This produces realistic speed-up / slow-down behaviour rather than
    constant-speed flight.
    """
    V_MAX_H  = 15.0   # m/s horizontal
    V_MAX_ASC =  5.0  # m/s ascent
    V_MAX_DES =  4.0  # m/s descent
    A_MAX_H  =  4.0   # m/s^2 horizontal
    A_MAX_V  =  3.0   # m/s^2 vertical
    WP_RADIUS = 180.0  # m - max waypoint distance from origin
    WP_ARRIVE =  12.0  # m - arrival threshold
    ALT_MIN   =  10.0  # m
    ALT_MAX   =  80.0  # m

    def __init__(self, rng: np.random.Generator, dt: float,
                 start_east: float = 60.0, start_north: float = 60.0,
                 start_alt: float = 30.0):
        super().__init__(rng, dt)
        self.east  = start_east
        self.north = start_north
        self.alt   = start_alt
        self.heading = rng.uniform(0, 2 * math.pi)
        self._ve = 0.0   # velocity east
        self._vn = 0.0   # velocity north
        self._vu = 0.0   # velocity up
        self._wp = self._new_waypoint()

    def _new_waypoint(self) -> tuple[float, float, float]:
        """Generate waypoint relative to current position (forward-progressing path)."""
        angle = self.rng.uniform(0, 2 * math.pi)
        dist  = self.rng.uniform(40.0, self.WP_RADIUS)
        alt   = self.rng.uniform(self.ALT_MIN, self.ALT_MAX)
        return self.east + dist * math.cos(angle), self.north + dist * math.sin(angle), alt

    def step(self) -> tuple[float, float, float]:
        wp_e, wp_n, wp_u = self._wp

        # Check arrival
        d = math.sqrt((wp_e - self.east)**2 + (wp_n - self.north)**2
                      + (wp_u - self.alt)**2)
        if d < self.WP_ARRIVE:
            self._wp = self._new_waypoint()
            wp_e, wp_n, wp_u = self._wp
            d = max(1.0, math.sqrt((wp_e - self.east)**2
                                    + (wp_n - self.north)**2
                                    + (wp_u - self.alt)**2))

        # Desired direction to waypoint (unit vector)
        dx = (wp_e - self.east) / d
        dy = (wp_n - self.north) / d
        dz = (wp_u - self.alt) / d

        # Acceleration toward waypoint, clamped to a_max
        ae = dx * self.A_MAX_H
        an = dy * self.A_MAX_H
        au = dz * self.A_MAX_V

        # Integrate velocity - clamp total horizontal speed (not per-component)
        self._ve += ae * self.dt
        self._vn += an * self.dt
        h_speed_now = math.sqrt(self._ve ** 2 + self._vn ** 2)
        if h_speed_now > self.V_MAX_H:
            scale = self.V_MAX_H / h_speed_now
            self._ve *= scale
            self._vn *= scale
        v_up_min = -self.V_MAX_DES
        v_up_max =  self.V_MAX_ASC
        self._vu = float(np.clip(self._vu + au * self.dt, v_up_min, v_up_max))

        # Integrate position
        self.east  += self._ve * self.dt
        self.north += self._vn * self.dt
        self.alt    = float(np.clip(self.alt + self._vu * self.dt, self.ALT_MIN, self.ALT_MAX))

        h_speed = math.sqrt(self._ve ** 2 + self._vn ** 2)
        if h_speed > 1e-6:
            self.heading = math.atan2(self._ve, self._vn)

        return self.east, self.north, self.alt


def _random_start_in_boundary(rng: np.random.Generator, boundary_radius_m: float) -> tuple[float, float]:
    """Generate a random (east, north) starting position within the boundary.

    Positions are uniformly distributed in a disc of radius 0.8 * boundary_radius_m
    (inside the soft zone, so the trajectory starts without triggering boundary
    reflection).  This ensures different ENGAGE clicks produce different starting
    positions for the same target type.
    """
    max_r = 0.8 * boundary_radius_m  # stay inside the soft repulsion zone
    r = float(rng.uniform(0, max_r))
    angle = float(rng.uniform(0, 2 * math.pi))
    return r * math.cos(angle), r * math.sin(angle)


# ---------------------------------
# Simulation engine
# ---------------------------------

# Per-type default observer coordinates (HCM City)
_DEFAULT_OBSERVER_POSITIONS: dict[str, tuple[float, float]] = {
    "pedestrian": (10.7726, 106.6983),   # Ben Thanh Market area
    "motorcycle": (10.7709, 106.7030),   # Ham Nghi Blvd / Le Loi intersection
    "drone":      (10.7280, 106.7180),   # District 7 / Phu My Hung
}


@dataclass
class SimulationConfig:
    """Configuration passed in from the REST API.

    Default observer coordinates are set to the pedestrian position in
    District 10, HCMC.  Use ``defaults_for_target`` to obtain type-specific
    defaults (pedestrian / motorcycle / drone).
    """
    observer_lat: float = 10.7743
    observer_lon: float = 106.7031
    observer_alt: float = 10.0         # metres above sea level
    target_type: str = "pedestrian"    # pedestrian | motorcycle | drone
    algorithm: str = "both"            # kalman | alpha_beta | both
    duration_s: float = 120.0          # max simulation duration
    update_rate_hz: float = 10.0       # WebSocket frame rate
    alpha: float = 0.4                 # for α-β filter (if used)
    seed: int | None = None            # RNG seed for reproducibility
    boundary_radius_m: float = 400.0   # max distance from observer (metres)
    use_realistic_sim: bool = False    # True -> use dataset-based trajectory

    @classmethod
    def defaults_for_target(cls, target_type: str) -> dict:
        """Return default config values adjusted for the given target type."""
        lat, lon = _DEFAULT_OBSERVER_POSITIONS.get(target_type, (10.7743, 106.7031))
        return {"observer_lat": lat, "observer_lon": lon}


class SimulationEngine:
    """
    Orchestrates the full simulation loop:
      trajectory generator -> noise model -> sensor fusion -> filters

    Usage:
        engine = SimulationEngine(config)
        async for frame in engine.run():
            await ws.send_json(frame.to_dict())
    """

    _TRAJECTORY_MAP: ClassVar[dict[str, type]] = {
        "pedestrian": PedestrianTrajectory,
        "motorcycle": RoadNetworkMotorcycleTrajectory,  # always follow roads
        "drone":      DroneTrajectory,
    }

    _REALISTIC_MAP: ClassVar[dict[str, type]] = {
        "pedestrian": GeolifeWalkTrajectory,
        "motorcycle": RoadNetworkMotorcycleTrajectory,
        "drone":      KinematicDroneTrajectory,
    }

    def __init__(self, config: SimulationConfig):
        self.config = config
        self.dt = 1.0 / config.update_rate_hz

        rng = np.random.default_rng(config.seed)

        if config.use_realistic_sim:
            real_cls = self._REALISTIC_MAP.get(config.target_type)
            try:
                # RoadNetworkMotorcycleTrajectory needs observer coordinates
                if real_cls is RoadNetworkMotorcycleTrajectory:
                    self._traj = real_cls(
                        rng=rng, dt=self.dt,
                        observer_lat=config.observer_lat,
                        observer_lon=config.observer_lon,
                    )
                elif real_cls is KinematicDroneTrajectory:
                    # Randomize drone starting position for diversity
                    start_e, start_n = _random_start_in_boundary(rng, config.boundary_radius_m)
                    self._traj = real_cls(
                        rng=rng, dt=self.dt,
                        start_east=start_e, start_north=start_n,
                    )
                else:
                    self._traj = real_cls(rng=rng, dt=self.dt)
                self._using_realistic = True
            except (RuntimeError, TypeError) as exc:
                import logging as _log
                _log.warning(
                    "SimulationEngine: %s real-world trajectory failed (%s), "
                    "falling back to synthetic",
                    config.target_type, exc,
                )
                # Generate random starting position for fallback too
                # Use old kinematic model as ultimate fallback (road network already failed)
                start_e, start_n = _random_start_in_boundary(rng, config.boundary_radius_m)
                if config.target_type == "motorcycle":
                    # Road network already failed; use kinematic model as last resort
                    self._traj = MotorcycleTrajectory(
                        rng=rng, dt=self.dt, start_east=start_e, start_north=start_n,
                    )
                else:
                    fallback_cls = self._TRAJECTORY_MAP.get(config.target_type, PedestrianTrajectory)
                    self._traj = fallback_cls(rng=rng, dt=self.dt, start_east=start_e, start_north=start_n)
                self._using_realistic = False
        else:
            traj_cls = self._TRAJECTORY_MAP.get(config.target_type, PedestrianTrajectory)
            if traj_cls is RoadNetworkMotorcycleTrajectory:
                # Motorcycle always follows roads — observer coords are needed
                # to find the nearest intersection; no start_east/start_north.
                try:
                    self._traj = traj_cls(
                        rng=rng, dt=self.dt,
                        observer_lat=config.observer_lat,
                        observer_lon=config.observer_lon,
                    )
                except (RuntimeError, TypeError):
                    import logging as _log
                    _log.warning(
                        "SimulationEngine: motorcycle road-network trajectory failed, "
                        "falling back to synthetic kinematic model",
                    )
                    start_e, start_n = _random_start_in_boundary(rng, config.boundary_radius_m)
                    self._traj = MotorcycleTrajectory(
                        rng=rng, dt=self.dt, start_east=start_e, start_north=start_n,
                    )
            else:
                start_e, start_n = _random_start_in_boundary(rng, config.boundary_radius_m)
                self._traj = traj_cls(rng=rng, dt=self.dt, start_east=start_e, start_north=start_n)
            self._using_realistic = False

        self._noise = SensorNoiseModel.from_target_type(config.target_type, seed=config.seed)

        # Pick filter: drone uses 3D Kalman (tracks altitude), others use 2D
        if config.target_type == "drone":
            self._kf: KalmanFilter | KalmanFilter3D = KalmanFilter3D(dt=self.dt)
        else:
            self._kf = KalmanFilter(dt=self.dt, target_type=config.target_type)

        self._ab = AlphaBetaFilter(alpha=config.alpha, dt=self.dt)
        self._boundary = SimulationBoundary(radius_m=config.boundary_radius_m)
        self._is_3d = config.target_type == "drone"

        # Running RMSE accumulators
        self._kalman_sq_errors: list[float] = []
        self._ab_sq_errors: list[float] = []
        self._raw_sq_errors: list[float] = []

        # Frame buffer for CSV export (all frames, bounded by duration)
        self._frames: list[dict] = []

        self._running = False

    def stop(self) -> None:
        self._running = False

    def get_stats(self) -> dict:
        """Return RMSE summary and step count for the current session."""
        n = len(self._kalman_sq_errors)
        if n == 0:
            return {
                "steps": 0,
                "kalman_rmse_m": None,
                "alpha_beta_rmse_m": None,
                "raw_rmse_m": None,
                "duration_s": 0.0,
                "target_type": self.config.target_type,
            }
        kf_rmse  = math.sqrt(sum(self._kalman_sq_errors) / n)
        ab_rmse  = math.sqrt(sum(self._ab_sq_errors)     / n)
        raw_rmse = math.sqrt(sum(self._raw_sq_errors)    / n)
        return {
            "steps": n,
            "kalman_rmse_m":     round(kf_rmse,  4),
            "alpha_beta_rmse_m": round(ab_rmse,  4),
            "raw_rmse_m":        round(raw_rmse, 4),
            "duration_s":        round(n / self.config.update_rate_hz, 2),
            "target_type":       self.config.target_type,
        }

    async def run(self) -> AsyncGenerator[TrackingFrame, None]:
        """Async generator: yields one TrackingFrame per tick."""
        self._running = True
        obs_lat = self.config.observer_lat
        obs_lon = self.config.observer_lon
        obs_alt = self.config.observer_alt

        max_steps = int(self.config.duration_s * self.config.update_rate_hz)

        for step in range(max_steps):
            if not self._running:
                break

            t_start = time.perf_counter()

            # 1. Ground truth position (ENU, then LLA)
            gt_e, gt_n, gt_u = self._traj.step()

            # 1b. Apply circular boundary only for synthetic trajectories.
            # Dataset trajectories are pre-filtered to stay within 390 m of
            # their centroid, so reflection would distort the real movement.
            is_dataset = getattr(self._traj, 'is_dataset_based', False)
            if hasattr(self._traj, 'heading') and not is_dataset:
                gt_e, gt_n, new_heading = self._boundary.constrain(
                    gt_e, gt_n, self._traj.heading
                )
                self._traj.east    = gt_e
                self._traj.north   = gt_n
                self._traj.heading = new_heading

            gt_enu = np.array([gt_e, gt_n, gt_u])
            gt_lat, gt_lon, gt_alt = enu_to_lla(gt_enu, obs_lat, obs_lon, obs_alt)

            # 2. Compute true sensor readings from geometry
            true_azimuth = math.degrees(math.atan2(gt_e, gt_n)) % 360
            horiz_dist = math.sqrt(gt_e**2 + gt_n**2)
            true_range = math.sqrt(gt_e**2 + gt_n**2 + gt_u**2)
            true_elevation = math.degrees(math.atan2(gt_u, horiz_dist))

            # 3. Apply sensor noise
            noisy_az  = self._noise.apply_azimuth_noise(true_azimuth)
            noisy_el  = self._noise.apply_elevation_noise(true_elevation)
            noisy_rng = self._noise.apply_range_noise(true_range)

            # 4. Sensor fusion -> ENU measurement
            fused = fuse_sensors(
                obs_lat, obs_lon, obs_alt,
                noisy_az, noisy_el, noisy_rng
            )
            # 5. Run tracking filters
            # --- Adaptive R: pass fused sigma_pos_m so Kalman trusts clean
            #     measurements more and noisy ones less automatically.
            if self._is_3d:
                kf_state = self._kf.step(
                    fused.east, fused.north, fused.up,
                    sigma_pos_m=fused.sigma_pos_m
                )
                # kf_state[0..2] = E, N, U filtered
                kf_up = float(kf_state[2])
            else:
                kf_state = self._kf.step(
                    fused.east, fused.north,
                    sigma_pos_m=fused.sigma_pos_m
                )
                kf_up = fused.up   # 2D filter - take raw fused altitude

            ab_state = self._ab.step(fused.east, fused.north)

            # 6. Convert filtered positions back to LLA
            kf_enu = np.array([float(kf_state[0]), float(kf_state[1]), kf_up])
            kf_lat, kf_lon, kf_alt = enu_to_lla(kf_enu, obs_lat, obs_lon, obs_alt)

            ab_enu = np.array([ab_state[0], ab_state[1], fused.up])
            ab_lat, ab_lon, ab_alt = enu_to_lla(ab_enu, obs_lat, obs_lon, obs_alt)

            # 7. Compute error metrics (metres)
            def pos_error(e, n, _ge=gt_e, _gn=gt_n) -> float:
                return math.sqrt((e - _ge)**2 + (n - _gn)**2)

            kf_err  = pos_error(kf_state[0], kf_state[1])
            ab_err  = pos_error(ab_state[0], ab_state[1])
            raw_err = pos_error(fused.east, fused.north)

            self._kalman_sq_errors.append(kf_err**2)
            self._ab_sq_errors.append(ab_err**2)
            self._raw_sq_errors.append(raw_err**2)

            kf_rmse  = math.sqrt(sum(self._kalman_sq_errors) / len(self._kalman_sq_errors))
            ab_rmse  = math.sqrt(sum(self._ab_sq_errors)     / len(self._ab_sq_errors))

            # 8. Build frame
            frame = TrackingFrame(
                timestamp=time.time(),
                step=step,
                ground_truth={
                    "lat": gt_lat, "lon": gt_lon, "alt": gt_alt,
                    "east": gt_e, "north": gt_n,
                },
                raw_measurement={
                    "lat": fused.target_lat, "lon": fused.target_lon, "alt": fused.target_alt,
                    "east": fused.east, "north": fused.north,
                    "azimuth": noisy_az, "elevation": noisy_el, "range": noisy_rng,
                },
                kalman={
                    "lat": kf_lat, "lon": kf_lon, "alt": kf_alt,
                    "east":  float(kf_state[0]),
                    "north": float(kf_state[1]),
                    "up":    kf_up,
                    "v_east":  float(kf_state[3 if self._is_3d else 2]),
                    "v_north": float(kf_state[4 if self._is_3d else 3]),
                    "speed": self._kf.speed,
                    "uncertainty_m": self._kf.position_uncertainty,
                },
                alpha_beta={
                    "lat": ab_lat, "lon": ab_lon, "alt": ab_alt,
                    "east": float(ab_state[0]), "north": float(ab_state[1]),
                    "v_east": float(ab_state[2]), "v_north": float(ab_state[3]),
                    "speed": self._ab.speed,
                },
                pan_tilt={
                    # Pan-tilt uses FILTERED position (Kalman output)
                    # so it reflects what the real servo system would target.
                    # For drone: use Kalman-filtered Up (3D); for 2D: use fused.up.
                    "azimuth":   math.degrees(math.atan2(
                                     float(kf_state[0]), float(kf_state[1])
                                 )) % 360,
                    "elevation": math.degrees(math.atan2(
                                     kf_up,
                                     math.sqrt(float(kf_state[0])**2 + float(kf_state[1])**2)
                                 )),
                    "range":     math.sqrt(
                                     float(kf_state[0])**2 + float(kf_state[1])**2 + kf_up**2
                                 ),
                },
                metrics={
                    "kalman_error": kf_err,
                    "alpha_beta_error": ab_err,
                    "raw_error": raw_err,
                    "kalman_rmse": kf_rmse,
                    "alpha_beta_rmse": ab_rmse,
                },
            )

            yield frame

            # Store frame for export (bounded by max simulation steps)
            self._frames.append(frame.to_dict())

            # 9. Maintain real-time rate
            elapsed = time.perf_counter() - t_start
            sleep_time = self.dt - elapsed
            if sleep_time > 0:
                await asyncio.sleep(sleep_time)
