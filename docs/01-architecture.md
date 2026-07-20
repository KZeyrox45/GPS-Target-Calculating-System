# System Architecture

## Overview

GPS Target Calculating System is a real-time moving-target tracking system using Laser-IMU-GNSS sensor fusion. Built as a thesis project at HCMC University of Technology (HCMUT).

## Two-Phase Development

### Phase 1: Static Single-Point Calculator
- **Location**: `index.html` + `js/` + `css/` (repo root), archived copy in `phase1/`
- **Purpose**: Calculate target coordinates from a single observation (observer GPS + IMU angles + laser distance)
- **Tech**: Vanilla JavaScript, CDN Leaflet, no build step
- **Algorithm**: Direct trigonometric calculation, no filtering

### Phase 2: Real-Time 3D Tracking Simulation
- **Location**: `backend/` (FastAPI) + `frontend/` (React 19 + Vite)
- **Purpose**: Continuous tracking of moving targets with sensor fusion and filtering
- **Tech**: Python 3.13, FastAPI, NumPy, SciPy, React 19, Zustand, Leaflet
- **Algorithms**: Kalman filter (2D/3D), Alpha-Beta filter, RSS sensor fusion

## Layered Architecture (4 Tiers)

```
┌─────────────────────────────────────────────┐
│  Frontend Layer (React + Leaflet)           │
│  - TrackingMap, TargetMarker, Polyline      │
│  - Zustand store (ring buffer MAX=500)      │
│  - WebSocket client via useWebSocket hook   │
├─────────────────────────────────────────────┤
│  Server Layer (FastAPI + WebSocket)         │
│  - REST API: /api/simulation/*              │
│  - WebSocket: /ws/tracking/{session_id}     │
│  - SimulationEngine (in-memory sessions)    │
├─────────────────────────────────────────────┤
│  Embedded Layer (Raspberry Pi stub)         │
│  - sensor_client.py (WebSocket client)      │
│  - UART/I2C sensor reading                  │
├─────────────────────────────────────────────┤
│  Sensor Layer (Hardware)                    │
│  - GPS/GNSS (U-Blox, UART)                 │
│  - IMU (MPU6050/BNO055, I2C)               │
│  - Laser rangefinder (LIDAR-Lite, I2C)     │
└─────────────────────────────────────────────┘
```

## Data Flow

```
GPS/IMU/Laser → RPi → WebSocket → FastAPI Server
                                      ↓
                              Coordinate conversion
                              (WGS84 → ECEF → ENU)
                                      ↓
                              Sensor fusion (RSS)
                                      ↓
                              Kalman/Alpha-Beta filter
                                      ↓
                              ENU → ECEF → WGS84
                                      ↓
                              WebSocket → React Frontend
                                      ↓
                              Leaflet Map + Charts
```

## Coordinate Systems

| System | Purpose | Usage |
|--------|---------|-------|
| WGS84 | Global lat/lon/alt | GPS input, final output |
| ECEF | Earth-centered Earth-fixed | Intermediate transform |
| ENU | East-North-Up local | Filter calculations, vector math |
| Body frame | Device-relative | IMU angles (azimuth, elevation) |

## Key Design Decisions

1. **WebSocket over HTTP polling**: Full-duplex, persistent connection for 10 Hz updates
2. **In-memory sessions**: No database, state cleaned up on WS disconnect
3. **Vite proxy**: Frontend proxies `/ws` → `ws://localhost:8000` (CORS middleware doesn't apply to WS upgrades)
4. **Ring buffer (500 points)**: Fixed memory footprint, 50 seconds of trajectory at 10 Hz
5. **Adaptive R matrix**: Kalman measurement noise updated dynamically from sensor fusion σ_pos
