# Simulation Engine

## Overview

The simulation engine generates synthetic sensor data for algorithm validation. It creates realistic trajectories, adds sensor noise, fuses measurements, and runs filters — all without requiring physical hardware.

## Trajectory Types

### Pedestrian
- **Speed**: 0.8 – 1.5 m/s (random walk)
- **Heading**: Gradual drift with random perturbations
- **Altitude**: Fixed at 0 (2D tracking)
- **State machine**: Walking | Paused (random rest stops)
- **Boundary**: Clamped at radius boundary

### Motorcycle
- **Speed**: 5 – 15 m/s
- **State machine**: Cruise | Turn | Decelerate
- **Turning**: Arc geometry with configurable turn angle
- **Altitude**: Fixed at 0 (2D tracking)
- **Boundary**: Reflects off boundary (heading reverses radially)

### Drone
- **Speed**: Variable (sinusoidal + circular components)
- **Altitude**: Varies (sinusoidal, 50–200 m)
- **Axes**: Full 3D (East, North, Up)
- **State machine**: Cruise | Ascend | Descend
- **Boundary**: Horizontal constrained, altitude unconstrained

## Sensor Noise Model

Gaussian noise added to each measurement:

| Sensor | Noise (1σ) | Distribution |
|--------|-----------|-------------|
| GPS lat/lon | 5.0 m | Gaussian |
| GPS alt | 5.0 m | Gaussian |
| IMU azimuth | 0.3° | Gaussian |
| IMU elevation | 0.2° | Gaussian |
| Laser distance | 0.5 m | Gaussian |

Uses `np.random.default_rng(seed)` for reproducible results.

## Simulation Flow

```
For each timestep k (0 to N-1):
  1. Generate ground truth position from trajectory
  2. Calculate observer→target geometry
  3. Generate noisy sensor readings:
     - GPS: observer_lla + noise
     - IMU: true_azimuth + noise, true_elevation + noise
     - Laser: true_distance + noise
  4. Fuse sensors (RSS) → σ_pos
  5. Convert to ENU coordinates
  6. Run Kalman filter (predict + update with adaptive R)
  7. Run Alpha-Beta filter
  8. Compute errors vs ground truth
  9. Store frame in ring buffer
```

## Boundary Constraint

- Circular boundary centered at observer origin
- radius_m ∈ [100, 1000] (Pydantic constraint)
- Pedestrian: position clamped to boundary
- Motorcycle: heading reflected off boundary
- Drone: horizontal constrained, altitude free

## RMSE Calculation

```
RMSE_k = sqrt( (1/k) * Σ[(e_i - ê_i)² + (n_i - n̂_i)²] )
```

- Horizontal RMSE only (East + North)
- Drone includes Up in state but RMSE is horizontal
- Final RMSE reported after all N timesteps

## Verified Results (seed=42, 120s, 10Hz, 400m boundary)

| Scenario | Raw | Alpha-Beta | Kalman | Spec (<5m) |
|----------|-----|-----------|--------|-----------|
| Pedestrian | 0.46 m | 0.24 m | 0.84 m | PASS |
| Motorcycle | 1.79 m | 1.01 m | 2.18 m | PASS |
| Drone | 1.28 m | 0.73 m | 2.33 m | PASS |
