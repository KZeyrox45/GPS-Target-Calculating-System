# Backend (FastAPI)

## Setup

```bash
cd backend
uv sync --group dev          # First time: create venv + install deps
uv run uvicorn app.main:app --reload --port 8000
```

Swagger UI: `http://localhost:8000/docs`

## Project Structure

```
backend/
├── app/
│   ├── main.py              # FastAPI app, CORS, router mounting
│   ├── algorithms/
│   │   ├── kalman_filter.py     # KalmanFilter (2D) + KalmanFilter3D
│   │   ├── alpha_beta_filter.py # AlphaBetaFilter
│   │   ├── geodetics.py         # WGS84 ↔ ECEF ↔ ENU conversions
│   │   └── sensor_fusion.py     # fuse_sensors() — RSS combination
│   ├── models/
│   │   └── __init__.py          # Pydantic v2 schemas
│   ├── routers/
│   │   ├── simulation.py        # REST + WebSocket endpoints
│   │   └── calculator.py        # Phase 1 static calculator
│   └── simulation/
│       ├── target_simulator.py  # Trajectory generators (3 types)
│       ├── sensor_noise.py      # Gaussian noise models per sensor
│       └── boundary.py          # Circular boundary constraint
├── tests/                       # 125 tests
├── scripts/                     # Utility scripts
├── pyproject.toml               # Deps + config (source of truth)
└── requirements.txt             # Reference only
```

## REST API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/simulation/start` | Create session, returns `session_id` + `ws_url` |
| POST | `/api/simulation/stop/{id}` | Stop session, cleanup |
| GET | `/api/simulation/sessions` | List active sessions |
| GET | `/api/simulation/stats/{id}` | Per-session RMSE/frame stats |
| GET | `/api/simulation/export/{id}` | StreamingResponse CSV export |
| POST | `/api/calculate` | Phase 1 static calculator |

## WebSocket

**Endpoint**: `/ws/tracking/{session_id}` (mounted at root, NOT under `/api`)

**Why root?** FastAPI's CORS middleware doesn't apply to WebSocket upgrades. Frontend proxies through Vite instead.

**Protocol**:
```json
// Client → Server (sensor data)
{
  "timestamp": 1720000123.456,
  "gps": {"lat": 10.762622, "lon": 106.660172, "alt": 15.0},
  "imu": {"azimuth": 45.2, "elevation": 2.1},
  "laser": {"distance": 312.5}
}

// Server → Client (processed results)
{
  "timestamp": 1720000123.456,
  "target": {"lat": 10.764150, "lon": 106.662830, "alt": 22.1},
  "kalman": {"lat": 10.764135, "lon": 106.662812, "alt": 22.0},
  "alphabeta": {"lat": 10.764142, "lon": 106.662821},
  "uncertainty_m": 3.2,
  "step": 142
}
```

## Session Management

- Sessions stored in `_sessions` dict (in-memory only)
- Filter state (x, P) persisted in memory during session lifetime
- Ring buffer `_frames` stores recent frames for `/stats` and `/export`
- Closing WS disconnect triggers cleanup

## Key Classes

### SimulationEngine
- Manages the simulation loop (trajectory generation → sensor noise → fusion → filtering)
- Runs in async task, pushes frames to ring buffer
- Computes RMSE against ground truth

### Trajectory Generators
- `PedestrianTrajectory`: Random walk with heading drift, 0.8–1.5 m/s
- `MotorcycleTrajectory`: State machine (cruise/turn), 5–15 m/s
- `DroneTrajectory`: 3D sinusoidal + circular, altitude varies

### SensorNoiseModel
- Adds Gaussian noise to GPS (5m), IMU azimuth (0.3°), elevation (0.2°), laser (0.5m)
- Uses `np.random.default_rng(seed)` for reproducibility

### Boundary
- Circular boundary centered at observer origin
- radius_m constrained to [100, 1000] via Pydantic
- Trajectories reflect off boundary (motorcycle) or are clamped (pedestrian)
- Drone: horizontal constrained, altitude unconstrained

## Dependencies (pyproject.toml)

- FastAPI 0.115+
- NumPy, SciPy
- Pydantic v2 (model_config = ConfigDict)
- websockets
- pytest, pytest-asyncio (dev)
- ruff (dev, linter)

## Conventions

- Pydantic v2: `model_config = ConfigDict(...)` (NOT old `class Config`)
- Kalman `update()`: `np.linalg.solve` (NOT `np.linalg.inv`)
- `fuse_sensors()` is a module-level function, NOT a class
- `SensorFusion` class in models is for schema, not computation
- No linter/formatter configured, no CI, no pre-commit hooks
