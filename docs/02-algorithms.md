# Algorithms

## Kalman Filter

### State Vectors

**2D (Pedestrian, Motorcycle)** — `KalmanFilter` class:
```
x = [e, n, ė, ṅ]^T    (East, North, velocity-East, velocity-North)
```

**3D (Drone)** — `KalmanFilter3D` class:
```
x = [e, n, u, ė, ṅ, u̇]^T    (+ Up axis and its velocity)
```

### State Transition Matrix F

Constant Velocity (CV) model with timestep Δt:

```
F_2D = [1  0  Δt  0 ]    F_3D = F_2D extended with
       [0  1   0  Δt ]         Up axis rows/columns
       [0  0   1   0 ]
       [0  0   0   1 ]
```

### Process Noise Q (DWNA Model)

Discrete White Noise Acceleration:
```
Q = σ_a² · [Δt⁴/4    0      Δt³/2    0     ]
            [0      Δt⁴/4    0      Δt³/2   ]
            [Δt³/2    0      Δt²      0     ]
            [0      Δt³/2    0      Δt²     ]
```

σ_a values:
| Target | σ_a (m/s²) | Reasoning |
|--------|------------|-----------|
| Pedestrian | 0.5 | Low acceleration, slow movement |
| Motorcycle | 5.0 | High acceleration, sudden turns |
| Drone | 5.0 | High acceleration on all 3 axes |

### Adaptive Measurement Noise R

Updated every timestep from sensor fusion uncertainty:
```
R_k = σ_pos,k² · I
```
Where σ_pos,k comes from the RSS error propagation formula. When target is far (>794m cross-over), R increases, reducing Kalman gain and relying more on the prediction model.

### Solving Method

Uses `np.linalg.solve` instead of `np.linalg.inv` for numerical stability:
```
K = P H^T (H P H^T + R)^{-1}   ← computed via solve()
```

## Alpha-Beta Filter

### Formulas

```
Predict:    x_p[k] = x[k-1] + Δt · ẋ[k-1]
Update pos: x[k]   = x_p[k] + α · (z[k] - x_p[k])
Update vel: ẋ[k]   = ẋ[k-1] + (β/Δt) · (z[k] - x_p[k])
```

### Benedict-Bordner Critically Damped

β is derived from α to ensure critically damped response (no overshoot):
```
β = (2 - α) - 2√(1 - α)
```
At α = 0.4 → β ≈ 0.051

### Limitations
- 2D only (East-North) — does not track altitude
- No uncertainty estimate (no P matrix)
- Fixed parameters — cannot adapt to changing noise conditions

## Sensor Fusion (RSS Error Propagation)

### Formula

```
σ_pos² = σ_gps² + σ_laser² + R² · (sin²(σ_az) + sin²(σ_el))
```

### Sensor Noise Parameters (1-sigma)

| Sensor | Symbol | Value |
|--------|--------|-------|
| GPS (horizontal) | σ_gps | 5.0 m |
| IMU (azimuth) | σ_az | 0.3° (0.00524 rad) |
| IMU (elevation) | σ_el | 0.2° (0.00349 rad) |
| Laser rangefinder | σ_range | 0.5 m |

### Cross-over Range

Distance where GPS error = IMU angular error:
```
R_cross = σ_gps / √(sin²(σ_az) + sin²(σ_el))
        = 5.0 / √(0.00002745 + 0.00001219)
        ≈ 794 m
```

- Below 794m: GPS dominates → better GPS improves accuracy
- Above 794m: IMU dominates → better IMU improves accuracy

### Error at Key Distances

| Range | σ_pos | GPS contribution | IMU contribution |
|-------|-------|-----------------|-----------------|
| 50 m | 5.0 m | ~98% | ~2% |
| 500 m | 5.9 m | ~72% | ~28% |
| 1000 m | 8.1 m | ~39% | ~61% |

## Coordinate Conversion Pipeline

```
WGS84 → ECEF → ENU (at observer) → + direction vector × distance → ENU target → WGS84
```

Step-by-step:
1. WGS84 → ECEF: Ellipsoid formulas (lat/lon/alt → X/Y/Z)
2. ECEF → ENU: Rotation matrix using observer's lat/lon
3. Polar → ENU vector: `v = [cos(el)·sin(az), cos(el)·cos(az), sin(el)]`
4. Target ENU = Observer ENU + distance × v
5. ENU → ECEF → WGS84: Inverse of steps 1-2

## Pipeline Timing (Benchmark)

| Step | Time | Share |
|------|------|-------|
| LLA → ECEF | 2.1 µs | 4% |
| ECEF → ENU | 3.8 µs | 6% |
| Sensor Fusion (RSS) | 1.2 µs | 2% |
| Kalman Filter | 48.5 µs | 82% |
| ENU → LLA | 3.4 µs | 6% |
| **Total** | **59.0 µs** | 100% |

Kalman filter dominates at 82% due to matrix operations. Total 59 µs is well within the 100 ms budget at 10 Hz.
