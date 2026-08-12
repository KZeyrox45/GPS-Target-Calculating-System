"""
statistical_analysis.py - Multi-seed RMSE Statistical Analysis
==============================================================
Runs each target type over seeds 1-10, computes mean +/- std RMSE.
Outputs a multi-seed RMSE summary table across all target scenarios.

Usage (from backend/):
    uv run python tests/statistical_analysis.py
"""

import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.algorithms.alpha_beta_filter import AlphaBetaFilter
from app.algorithms.kalman_filter import KalmanFilter, KalmanFilter3D
from app.algorithms.sensor_fusion import fuse_sensors
from app.simulation.boundary import SimulationBoundary
from app.simulation.sensor_noise import SensorNoiseModel
from app.simulation.target_simulator import (
    DroneTrajectory,
    MotorcycleTrajectory,
    PedestrianTrajectory,
)

SEEDS = list(range(1, 11))
DURATION_S = 120.0
UPDATE_RATE_HZ = 10.0
BOUNDARY_RADIUS_M = 400.0
ALPHA = 0.4
SPEC_RMSE_M = 5.0


def run_scenario(target_type: str, seed: int):
    """Run one scenario, return (raw_rmse, ab_rmse, kf_rmse)."""
    dt = 1.0 / UPDATE_RATE_HZ
    rng = np.random.default_rng(seed)

    TRAJ_MAP = {
        "pedestrian": PedestrianTrajectory,
        "motorcycle": MotorcycleTrajectory,
        "drone": DroneTrajectory,
    }
    traj = TRAJ_MAP[target_type](rng=rng, dt=dt)
    noise = SensorNoiseModel.from_target_type(target_type, seed=seed)
    boundary = SimulationBoundary(radius_m=BOUNDARY_RADIUS_M)
    is_3d = target_type == "drone"

    if is_3d:
        kf = KalmanFilter3D(dt=dt)
    else:
        kf = KalmanFilter(dt=dt, target_type=target_type)
    ab = AlphaBetaFilter(alpha=ALPHA, dt=dt)

    obs_lat, obs_lon, obs_alt = 10.762622, 106.660172, 10.0
    n_steps = int(DURATION_S * UPDATE_RATE_HZ)
    raw_sq, ab_sq, kf_sq = [], [], []

    for _ in range(n_steps):
        gt_e, gt_n, gt_u = traj.step()

        if hasattr(traj, 'heading'):
            gt_e, gt_n, new_h = boundary.constrain(gt_e, gt_n, traj.heading)
            traj.east = gt_e
            traj.north = gt_n
            traj.heading = new_h

        true_az = math.degrees(math.atan2(gt_e, gt_n)) % 360
        true_rng = math.sqrt(gt_e**2 + gt_n**2 + gt_u**2)
        horiz = math.sqrt(gt_e**2 + gt_n**2)
        true_el = math.degrees(math.atan2(gt_u, horiz)) if horiz > 0 else 0.0

        noisy_az = noise.apply_azimuth_noise(true_az)
        noisy_el = noise.apply_elevation_noise(true_el)
        noisy_rng = noise.apply_range_noise(true_rng)

        fused = fuse_sensors(obs_lat, obs_lon, obs_alt, noisy_az, noisy_el, noisy_rng)

        if is_3d:
            kf_state = kf.step(fused.east, fused.north, fused.up,
                               sigma_pos_m=fused.sigma_pos_m)
        else:
            kf_state = kf.step(fused.east, fused.north,
                               sigma_pos_m=fused.sigma_pos_m)
        ab_state = ab.step(fused.east, fused.north)

        def pos_err(e, n, _ge=gt_e, _gn=gt_n):
            return math.sqrt((e - _ge)**2 + (n - _gn)**2)

        raw_sq.append(pos_err(fused.east, fused.north) ** 2)
        ab_sq.append(pos_err(float(ab_state[0]), float(ab_state[1])) ** 2)
        kf_sq.append(pos_err(float(kf_state[0]), float(kf_state[1])) ** 2)

    n = len(raw_sq)
    return (
        math.sqrt(sum(raw_sq) / n),
        math.sqrt(sum(ab_sq) / n),
        math.sqrt(sum(kf_sq) / n),
    )


def main():
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    target_types = ["pedestrian", "motorcycle", "drone"]
    results = {}

    print("GPS Target Calculating System - Multi-seed Statistical Analysis")
    print("=" * 65)
    print(f"Seeds: {SEEDS[0]}-{SEEDS[-1]}  |  Duration: {int(DURATION_S)}s  |  Rate: {int(UPDATE_RATE_HZ)}Hz  |  Boundary: {int(BOUNDARY_RADIUS_M)}m")
    print()

    for ttype in target_types:
        raw_list, ab_list, kf_list = [], [], []
        for seed in SEEDS:
            raw, ab, kf = run_scenario(ttype, seed)
            raw_list.append(raw)
            ab_list.append(ab)
            kf_list.append(kf)
            print(f"  {ttype:12s} seed={seed:2d}  raw={raw:.3f}  ab={ab:.3f}  kf={kf:.3f}")

        results[ttype] = {
            'raw': (np.mean(raw_list), np.std(raw_list, ddof=1), min(raw_list), max(raw_list)),
            'ab':  (np.mean(ab_list),  np.std(ab_list,  ddof=1), min(ab_list),  max(ab_list)),
            'kf':  (np.mean(kf_list),  np.std(kf_list,  ddof=1), min(kf_list),  max(kf_list)),
        }
        print()

    print("=" * 65)
    print(f"{'Scenario':<14} {'Method':<12} {'Mean (m)':<10} {'Std (m)':<10} {'Min':<8} {'Max':<8} Spec")
    print("-" * 65)
    for ttype, res in results.items():
        for method, key in [('Raw', 'raw'), ('Alpha-beta', 'ab'), ('Kalman', 'kf')]:
            mean, std, vmin, vmax = res[key]
            ok = "PASS" if mean < SPEC_RMSE_M else "FAIL"
            print(f"{ttype:<14} {method:<12} {mean:<10.3f} {std:<10.3f} {vmin:<8.3f} {vmax:<8.3f} {ok}")
        print()

    print(f"Spec: RMSE < {SPEC_RMSE_M} m  (boundary_radius = {int(BOUNDARY_RADIUS_M)} m)")


if __name__ == "__main__":
    main()
