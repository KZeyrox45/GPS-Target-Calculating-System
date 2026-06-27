"""
target_simulator.py — Moving Target Trajectory Simulation
===========================================================
Generates realistic synthetic trajectories for pedestrians, motorcycles,
and drones in a local ENU frame. Used by the SimulationEngine to
drive the tracking filters.
"""

import math
import time
import asyncio
import numpy as np
from typing import AsyncGenerator
from dataclasses import dataclass, field

from ..algorithms.geodetics import enu_to_lla, polar_to_enu, lla_to_enu, calculate_bearing, haversine_distance
from ..algorithms.kalman_filter import KalmanFilter, KalmanFilter3D
from ..algorithms.alpha_beta_filter import AlphaBetaFilter
from ..algorithms.sensor_fusion import fuse_sensors, GPSSpec, IMUSpec, LaserSpec
from .sensor_noise import SensorNoiseModel
from .boundary import SimulationBoundary


# ─────────────────────────────────────────────────────────────────────────────
# Output frame (sent over WebSocket)
# ─────────────────────────────────────────────────────────────────────────────

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


# ─────────────────────────────────────────────────────────────────────────────
# Trajectory generators (ENU in metres relative to observer)
# ─────────────────────────────────────────────────────────────────────────────

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
    Realistic pedestrian motion model.

    Behaviour:
      - Walks at 1.0–1.8 m/s with smooth inertial speed changes.
      - Uses a waypoint-based navigation: picks a random destination within
        the boundary, walks toward it, then picks a new waypoint. This
        produces natural turning patterns rather than random drift.
      - Occasionally pauses (0.3 s – 2 s) to simulate stopping at
        intersections, looking at a phone, etc.
      - Heading smoothly tracks the waypoint direction with lag.
    """
    _SPEED_MIN  = 1.0   # m/s – slow stroll
    _SPEED_MAX  = 1.8   # m/s – brisk walk
    _SPEED_MEAN = 1.4   # m/s – target cruise speed
    _PAUSE_PROB = 0.004  # probability of starting a pause each step
    _PAUSE_DUR_S_RANGE = (0.5, 3.0)  # seconds paused
    _WAYPOINT_RADIUS = 120.0  # metres — max waypoint distance from origin
    _WAYPOINT_ARRIVAL_M = 8.0  # metres — distance to consider waypoint reached

    def __init__(self, rng, dt, start_east=50.0, start_north=50.0):
        super().__init__(rng, dt)
        self.east    = start_east
        self.north   = start_north
        self.heading = rng.uniform(0, 2 * math.pi)
        self._speed  = self._SPEED_MEAN
        self._target_speed = self._SPEED_MEAN
        self._pause_steps  = 0
        # Pick an initial waypoint
        self._waypoint_e, self._waypoint_n = self._new_waypoint()

    def _new_waypoint(self) -> tuple[float, float]:
        """Pick a random waypoint within a circular area."""
        angle = self.rng.uniform(0, 2 * math.pi)
        dist  = self.rng.uniform(20.0, self._WAYPOINT_RADIUS)
        return dist * math.cos(angle), dist * math.sin(angle)

    def step(self) -> tuple[float, float, float]:
        # --- Pause phase ---
        if self._pause_steps > 0:
            self._pause_steps -= 1
            self._speed = max(0.0, self._speed - 0.5 * self.dt)
            return self.east, self.north, self.alt

        # --- Maybe start a pause ---
        if self.rng.random() < self._PAUSE_PROB:
            dur_s = self.rng.uniform(*self._PAUSE_DUR_S_RANGE)
            self._pause_steps = int(dur_s / self.dt)

        # --- Check if waypoint reached; pick a new one ---
        dw = self._waypoint_e - self.east
        dn = self._waypoint_n - self.north
        dist_to_wp = math.sqrt(dw ** 2 + dn ** 2)
        if dist_to_wp < self._WAYPOINT_ARRIVAL_M:
            self._waypoint_e, self._waypoint_n = self._new_waypoint()
            dw = self._waypoint_e - self.east
            dn = self._waypoint_n - self.north

        # --- Desired heading toward waypoint ---
        desired_heading = math.atan2(dw, dn)  # atan2(East, North) → heading from North

        # --- Smoothly rotate heading toward desired (max 25°/s turn rate) ---
        MAX_TURN_RAD_S = math.radians(25)
        diff = (desired_heading - self.heading + math.pi) % (2 * math.pi) - math.pi
        turn = max(-MAX_TURN_RAD_S, min(MAX_TURN_RAD_S, diff / 0.5))
        self.heading += turn * self.dt

        # --- Inertial speed ---
        if self.rng.random() < 0.02:
            self._target_speed = self.rng.uniform(self._SPEED_MIN, self._SPEED_MAX)
        alpha = self.dt / 3.0
        self._speed += alpha * (self._target_speed - self._speed)
        self._speed = max(0.5, self._speed)

        self.east  += self._speed * math.sin(self.heading) * self.dt
        self.north += self._speed * math.cos(self.heading) * self.dt
        return self.east, self.north, self.alt


class MotorcycleTrajectory(_Trajectory):
    """
    Realistic motorbike motion: alternating straight segments and banked turns.

    Behaviour:
      - Cruises along a straight segment for 3–15 s at 8–12 m/s.
      - Decelerates into a turn, executes a smooth arc (turn radius 15–40 m),
        then accelerates back to cruise speed.
      - This produces the characteristically long straight → hard-corner
        pattern of urban motorcycle traffic.

    Why this model:
      The original constant-turn-rate arc looks identical to a pedestrian
      random walk when rendered on a map.  A discrete state machine
      (STRAIGHT → TURNING → STRAIGHT) produces a visually unmistakable
      trajectory that correctly reflects how motorcycles actually move.
    """
    _CRUISE_SPEED_MEAN = 10.0   # m/s
    _CRUISE_SPEED_STD  =  1.0   # m/s
    _CRUISE_SPEED_MIN  =  7.0
    _CRUISE_SPEED_MAX  = 13.0

    _STRAIGHT_DUR_RANGE = (3.0, 15.0)   # seconds per straight segment
    _TURN_RADIUS_RANGE  = (15.0, 40.0)  # metres, urban intersection scale
    _TURN_ANGLE_CHOICES = [            # common intersection angles (kept for reference)
        math.radians(60),
        math.radians(90),
        math.radians(120),
    ]
    _TURN_ANGLES_RAD = np.array([
        math.radians(60),
        math.radians(90),
        math.radians(120),
    ], dtype=np.float64)

    class _State:
        STRAIGHT = "straight"
        TURNING  = "turning"

    def __init__(self, rng, dt, start_east=100.0, start_north=100.0):
        super().__init__(rng, dt)
        self.east    = start_east
        self.north   = start_north
        self.heading = rng.uniform(0, 2 * math.pi)
        self._speed  = self._CRUISE_SPEED_MEAN

        # State machine
        self._state         = self._State.STRAIGHT
        self._straight_steps_left = self._new_straight_duration()
        self._turn_steps_left     = 0
        self._turn_rate           = 0.0  # rad/s during turn

    # -- helpers ---------------------------------------------------------------

    def _new_straight_duration(self) -> int:
        dur_s = self.rng.uniform(*self._STRAIGHT_DUR_RANGE)
        return max(1, int(dur_s / self.dt))

    def _begin_turn(self) -> None:
        """Pick a new turn and compute steps + angular rate."""
        radius  = self.rng.uniform(*self._TURN_RADIUS_RANGE)
        angle   = self.rng.choice(self._TURN_ANGLES_RAD)
        direction = self.rng.choice([-1, 1])   # left or right

        # arc length = radius * |angle|  -> duration = arc / speed
        arc_len = radius * abs(angle)
        dur_s   = arc_len / max(self._speed, 1.0)
        self._turn_steps_left = max(1, int(dur_s / self.dt))
        self._turn_rate       = direction * (self._speed / radius)  # ω = v/r
        self._state           = self._State.TURNING

    # -- step ------------------------------------------------------------------

    def step(self) -> tuple[float, float, float]:
        if self._state == self._State.STRAIGHT:
            self._straight_steps_left -= 1
            if self._straight_steps_left <= 0:
                self._begin_turn()
        else:  # TURNING
            self._turn_steps_left -= 1
            self.heading += self._turn_rate * self.dt
            if self._turn_steps_left <= 0:
                # Back to straight with a fresh cruise speed
                self._speed = float(np.clip(
                    self.rng.normal(self._CRUISE_SPEED_MEAN, self._CRUISE_SPEED_STD),
                    self._CRUISE_SPEED_MIN, self._CRUISE_SPEED_MAX,
                ))
                self._straight_steps_left = self._new_straight_duration()
                self._state = self._State.STRAIGHT

        # Small noise on speed regardless of state
        noisy_speed = self._speed + self.rng.normal(0, 0.3)
        noisy_speed = max(3.0, noisy_speed)  # never stop

        self.east  += noisy_speed * math.sin(self.heading) * self.dt
        self.north += noisy_speed * math.cos(self.heading) * self.dt
        return self.east, self.north, self.alt


class DroneTrajectory(_Trajectory):
    """
    Drone with 3-D motion: waypoint-based patrol pattern with altitude variation.

    Behaviour:
      - Flies toward a series of random waypoints at 8–15 m/s horizontal speed.
      - Banks smoothly toward each waypoint (max 35°/s turn rate).
      - Altitude varies sinusoidally ±20 m around 30 m baseline — independent
        of horizontal motion, simulating a surveillance drone changing altitude.
      - On waypoint arrival, immediately picks a new waypoint at a random
        bearing and distance (30–200 m), creating a realistic patrol pattern.
    """
    H_SPEED_MEAN = 11.0   # m/s
    H_SPEED_STD  = 1.5
    H_SPEED_MIN  = 7.0
    H_SPEED_MAX  = 15.0
    ALT_AMPLITUDE = 20.0
    ALT_PERIOD_S = 40.0
    WAYPOINT_RADIUS = 180.0   # metres — max waypoint distance from origin
    WAYPOINT_ARRIVAL_M = 12.0  # metres — distance to consider waypoint reached
    MAX_TURN_RAD_S = math.radians(35)  # max turn rate

    def __init__(self, rng, dt, start_east=80.0, start_north=80.0, start_alt=30.0):
        super().__init__(rng, dt)
        self.east = start_east
        self.north = start_north
        self.alt = start_alt
        self.heading = rng.uniform(0, 2 * math.pi)
        self._h_speed = self.H_SPEED_MEAN
        self.t = 0.0
        self._waypoint_e, self._waypoint_n = self._new_waypoint()

    def _new_waypoint(self) -> tuple[float, float]:
        angle = self.rng.uniform(0, 2 * math.pi)
        dist  = self.rng.uniform(40.0, self.WAYPOINT_RADIUS)
        return dist * math.cos(angle), dist * math.sin(angle)

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

        # --- Smoothly bank toward waypoint ---
        desired_heading = math.atan2(dw, dn)
        diff = (desired_heading - self.heading + math.pi) % (2 * math.pi) - math.pi
        turn = max(-self.MAX_TURN_RAD_S, min(self.MAX_TURN_RAD_S, diff / 0.4))
        self.heading += turn * self.dt

        h_speed = self._h_speed + self.rng.normal(0, 0.5)
        self.east  += h_speed * math.sin(self.heading) * self.dt
        self.north += h_speed * math.cos(self.heading) * self.dt

        # Sinusoidal altitude variation
        self.alt = 30.0 + self.ALT_AMPLITUDE * math.sin(
            2 * math.pi * self.t / self.ALT_PERIOD_S
        )
        return self.east, self.north, self.alt


# ─────────────────────────────────────────────────────────────────────────────
# Simulation engine
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class SimulationConfig:
    """Configuration passed in from the REST API."""
    observer_lat: float = 10.762622
    observer_lon: float = 106.660172
    observer_alt: float = 10.0         # metres above sea level
    target_type: str = "pedestrian"    # pedestrian | motorcycle | drone
    algorithm: str = "both"            # kalman | alpha_beta | both
    duration_s: float = 120.0          # max simulation duration
    update_rate_hz: float = 10.0       # WebSocket frame rate
    alpha: float = 0.4                 # for α-β filter (if used)
    seed: int | None = None            # RNG seed for reproducibility
    boundary_radius_m: float = 400.0   # max distance from observer (metres)


class SimulationEngine:
    """
    Orchestrates the full simulation loop:
      trajectory generator → noise model → sensor fusion → filters

    Usage:
        engine = SimulationEngine(config)
        async for frame in engine.run():
            await ws.send_json(frame.to_dict())
    """

    _TRAJECTORY_MAP = {
        "pedestrian": PedestrianTrajectory,
        "motorcycle": MotorcycleTrajectory,
        "drone":      DroneTrajectory,
    }

    def __init__(self, config: SimulationConfig):
        self.config = config
        self.dt = 1.0 / config.update_rate_hz

        rng = np.random.default_rng(config.seed)
        traj_cls = self._TRAJECTORY_MAP.get(config.target_type, PedestrianTrajectory)
        self._traj = traj_cls(rng=rng, dt=self.dt)

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

        self._running = False

    def stop(self) -> None:
        self._running = False

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

            # 1b. Apply circular boundary — reflect heading if target drifts out
            if hasattr(self._traj, 'heading'):
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

            # 4. Sensor fusion → ENU measurement
            fused = fuse_sensors(
                obs_lat, obs_lon, obs_alt,
                noisy_az, noisy_el, noisy_rng
            )
            raw_enu = np.array([fused.east, fused.north, fused.up])

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
                kf_up = fused.up   # 2D filter — take raw fused altitude

            ab_state = self._ab.step(fused.east, fused.north)

            # 6. Convert filtered positions back to LLA
            kf_enu = np.array([float(kf_state[0]), float(kf_state[1]), kf_up])
            kf_lat, kf_lon, kf_alt = enu_to_lla(kf_enu, obs_lat, obs_lon, obs_alt)

            ab_enu = np.array([ab_state[0], ab_state[1], fused.up])
            ab_lat, ab_lon, ab_alt = enu_to_lla(ab_enu, obs_lat, obs_lon, obs_alt)

            # 7. Compute error metrics (metres)
            def pos_error(e, n) -> float:
                return math.sqrt((e - gt_e)**2 + (n - gt_n)**2)

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

            # 9. Maintain real-time rate
            elapsed = time.perf_counter() - t_start
            sleep_time = self.dt - elapsed
            if sleep_time > 0:
                await asyncio.sleep(sleep_time)
