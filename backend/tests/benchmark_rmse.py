"""
benchmark_rmse.py — Phase 2 RMSE Baseline Benchmark (Fast, non-real-time)
==========================================================================
Directly calls the simulation components without asyncio sleep pacing.
Runs each target type for 120 s at 10 Hz (1200 steps) with seed=42.

Usage:
    python tests/benchmark_rmse.py
"""

import sys
import math
import numpy as np

sys.path.insert(0, str(__import__('pathlib').Path(__file__).parent.parent))

from app.simulation.target_simulator import (
    PedestrianTrajectory, MotorcycleTrajectory, DroneTrajectory,
    SimulationConfig,
)
from app.simulation.boundary import SimulationBoundary
from app.simulation.sensor_noise import SensorNoiseModel
from app.algorithms.kalman_filter import KalmanFilter, KalmanFilter3D
from app.algorithms.alpha_beta_filter import AlphaBetaFilter
from app.algorithms.sensor_fusion import fuse_sensors
from app.algorithms.geodetics import enu_to_lla


def run_scenario(
    target_type: str,
    duration_s: float = 120.0,
    update_rate_hz: float = 10.0,
    seed: int = 42,
    boundary_radius_m: float = 400.0,
    alpha: float = 0.4,
):
    """
    Run one simulation scenario without real-time pacing.
    Returns (raw_rmse, ab_rmse, kf_rmse, n_steps).
    """
    dt = 1.0 / update_rate_hz
    rng = np.random.default_rng(seed)

    # --- Build components ---
    TRAJ_MAP = {
        "pedestrian": PedestrianTrajectory,
        "motorcycle": MotorcycleTrajectory,
        "drone": DroneTrajectory,
    }
    traj = TRAJ_MAP[target_type](rng=rng, dt=dt)
    noise = SensorNoiseModel.from_target_type(target_type, seed=seed)
    boundary = SimulationBoundary(radius_m=boundary_radius_m)
    is_3d = target_type == "drone"

    if is_3d:
        kf = KalmanFilter3D(dt=dt)
    else:
        kf = KalmanFilter(dt=dt, target_type=target_type)
    ab = AlphaBetaFilter(alpha=alpha, dt=dt)

    # Observer at HCMUT
    obs_lat, obs_lon, obs_alt = 10.762622, 106.660172, 10.0

    n_steps = int(duration_s * update_rate_hz)
    raw_sq, ab_sq, kf_sq = [], [], []

    for _ in range(n_steps):
        # 1. Ground truth
        gt_e, gt_n, gt_u = traj.step()

        # 2. Apply boundary
        if hasattr(traj, 'heading'):
            gt_e, gt_n, new_h = boundary.constrain(gt_e, gt_n, traj.heading)
            traj.east = gt_e
            traj.north = gt_n
            traj.heading = new_h

        # 3. Noisy sensor readings
        true_az = math.degrees(math.atan2(gt_e, gt_n)) % 360
        true_rng = math.sqrt(gt_e**2 + gt_n**2 + gt_u**2)
        horiz = math.sqrt(gt_e**2 + gt_n**2)
        true_el = math.degrees(math.atan2(gt_u, horiz))

        noisy_az  = noise.apply_azimuth_noise(true_az)
        noisy_el  = noise.apply_elevation_noise(true_el)
        noisy_rng = noise.apply_range_noise(true_rng)

        # 4. Sensor fusion
        fused = fuse_sensors(obs_lat, obs_lon, obs_alt, noisy_az, noisy_el, noisy_rng)

        # 5. Filters
        if is_3d:
            kf_state = kf.step(fused.east, fused.north, fused.up,
                               sigma_pos_m=fused.sigma_pos_m)
        else:
            kf_state = kf.step(fused.east, fused.north,
                               sigma_pos_m=fused.sigma_pos_m)
        ab_state = ab.step(fused.east, fused.north)

        # 6. Errors (horizontal plane only, comparable across 2D and 3D)
        def pos_err(e, n):
            return math.sqrt((e - gt_e)**2 + (n - gt_n)**2)

        raw_sq.append(pos_err(fused.east, fused.north) ** 2)
        ab_sq.append(pos_err(float(ab_state[0]), float(ab_state[1])) ** 2)
        kf_sq.append(pos_err(float(kf_state[0]), float(kf_state[1])) ** 2)

    n = len(raw_sq)
    raw_rmse = math.sqrt(sum(raw_sq) / n)
    ab_rmse  = math.sqrt(sum(ab_sq)  / n)
    kf_rmse  = math.sqrt(sum(kf_sq)  / n)
    return raw_rmse, ab_rmse, kf_rmse, n


def main():
    print("GPS Target Calculating System — RMSE Baseline Benchmark")
    print("=" * 60)
    print(f"Duration: 120 s | Rate: 10 Hz | Seed: 42 | Boundary: 400 m")
    print()

    scenarios = [
        ("pedestrian", "Pedestrian (2D KF)"),
        ("motorcycle", "Motorcycle (2D KF)"),
        ("drone",      "Drone     (3D KF)"),
    ]

    results = {}
    for target_type, label in scenarios:
        print(f"Running {label}...", end=" ", flush=True)
        raw_rmse, ab_rmse, kf_rmse, n = run_scenario(target_type)
        results[label] = (raw_rmse, ab_rmse, kf_rmse, n)
        print(f"done ({n} steps) — KF RMSE: {kf_rmse:.2f} m")

    print()
    print("=" * 60)
    print("RESULTS TABLE (markdown)")
    print("=" * 60)
    print()

    SPEC_M = 5.0  # thesis spec: RMSE < 5m at <= 500m range
    header = "| Scenario | Raw RMSE | α-β RMSE | Kalman RMSE | Spec (<5m) |"
    sep    = "|---|---|---|---|---|"
    print(header)
    print(sep)
    for label, (raw_rmse, ab_rmse, kf_rmse, _) in results.items():
        pass_fail = "✅ PASS" if kf_rmse < SPEC_M else "❌ FAIL"
        print(
            f"| {label} | {raw_rmse:.2f} m | {ab_rmse:.2f} m "
            f"| {kf_rmse:.2f} m | {pass_fail} |"
        )

    print()
    print("Filter improvement over raw measurement (horizontal RMSE):")
    for label, (raw_rmse, ab_rmse, kf_rmse, _) in results.items():
        kf_imp = (1 - kf_rmse / raw_rmse) * 100 if raw_rmse > 0 else 0
        ab_imp = (1 - ab_rmse / raw_rmse) * 100 if raw_rmse > 0 else 0
        print(f"  {label}: KF {kf_imp:+.1f}%  α-β {ab_imp:+.1f}%")

    print()
    all_pass = all(r[2] < SPEC_M for r in results.values())
    print("OVERALL:", "✅ ALL PASS — thesis spec met" if all_pass else "❌ SOME FAIL")


if __name__ == "__main__":
    main()
