"""
measure_timing.py - Core pipeline timing benchmark.

Runs the core tracking chain (sensor fusion + Alpha-Beta + Kalman)
10,000 times on the host machine and reports mean / median / P99.

Scope: core algorithm chain only. Excludes network, WebSocket
serialization, and browser rendering. Result depends on host
hardware; it is NOT an embedded performance claim.

Usage (from backend/):
    uv run python scripts/measure_timing.py
"""
import sys
import time
from pathlib import Path

import numpy as np

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from app.algorithms.alpha_beta_filter import AlphaBetaFilter
from app.algorithms.kalman_filter import KalmanFilter
from app.algorithms.sensor_fusion import fuse_sensors


def measure_pipeline(n_warmup: int = 1000, n_measure: int = 10000) -> None:
    kf = KalmanFilter(dt=0.1, target_type="pedestrian")
    ab = AlphaBetaFilter(alpha=0.4, dt=0.1)

    obs_lat, obs_lon, obs_alt = 10.762622, 106.660172, 10.0
    noisy_az, noisy_el, noisy_rng = 45.0, 5.0, 500.0

    for _ in range(n_warmup):
        fused = fuse_sensors(obs_lat, obs_lon, obs_alt, noisy_az, noisy_el, noisy_rng)
        kf.step(fused.east, fused.north, sigma_pos_m=fused.sigma_pos_m)
        ab.step(fused.east, fused.north)

    latencies = []
    for _ in range(n_measure):
        t0 = time.perf_counter_ns()
        fused = fuse_sensors(obs_lat, obs_lon, obs_alt, noisy_az, noisy_el, noisy_rng)
        ab.step(fused.east, fused.north)
        kf.step(fused.east, fused.north, sigma_pos_m=fused.sigma_pos_m)
        latencies.append((time.perf_counter_ns() - t0) / 1000.0)

    lat = np.array(latencies)
    print(f"N repetitions: {n_measure}")
    print(f"Mean:   {np.mean(lat):.2f} us")
    print(f"Median: {np.median(lat):.2f} us")
    print(f"Min:    {np.min(lat):.2f} us")
    print(f"Max:    {np.max(lat):.2f} us")
    print(f"P95:    {np.percentile(lat, 95):.2f} us")
    print(f"P99:    {np.percentile(lat, 99):.2f} us")


if __name__ == "__main__":
    measure_pipeline()
