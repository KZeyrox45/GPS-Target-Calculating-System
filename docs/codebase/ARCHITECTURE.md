# Architecture

> Default context: `AGENTS.md` (repo root) + `RULES/RULES.md`. Deep-dive docs: `docs/01-architecture.md`, `docs/02-algorithms.md`, `docs/03-backend.md`.

## Core Sections (Required)

### 1) Architectural Style

- Primary style: **layered client-server** — React SPA ↔ FastAPI backend with REST for control plane and WebSocket for the data plane; backend internally layered (routers → simulation/engine → algorithms).
- Why: routers import from `simulation` and `models` only; `app/algorithms/` contains no HTTP imports (verified by reading `backend/app/main.py`, `backend/app/routers/simulation.py`, `backend/app/algorithms/*.py`).
- Primary constraints:
  1. **Sessions are in-memory only** — `_sessions: dict[str, SimulationEngine]` in `backend/app/routers/simulation.py:38`; no DB anywhere in the stack.
  2. **WebSocket mounted at root, not `/api`** — FastAPI CORS middleware does not apply to WS upgrades; frontend proxies `/ws` via Vite instead (`backend/app/routers/simulation.py:1-14` docstring, `frontend/vite.config.js`).
  3. Single-process, single-user demo posture (thesis project): no auth, no persistence, no horizontal scaling.

### 2) System Flow

```text
Browser (frontend/src) ──POST /api/simulation/start──► routers/simulation.py
        │ creates SimulationConfig → SimulationEngine (thread offload via asyncio.to_thread)
        ◄── { session_id, ws_url } ──
        │
        ├─ WS /ws/tracking/{session_id} (root-mounted ws_router)
        │     per tick: TrajectoryGenerator → SensorNoiseModel → fuse_sensors()
        │               → KalmanFilter3D / AlphaBetaFilter → SimulationBoundary
        │     → JSON frame: {step, ground_truth, raw_measurement, kalman, alpha_beta, pan_tilt, metrics}
        ▼
Zustand store (trackingStore.js, ring buffer 500) → Leaflet map + Chart.js charts
```

1. `SimulationPanel.jsx` POSTs config to `/api/simulation/start`.
2. `routers/simulation.py:44-70` builds `SimulationConfig`, constructs `SimulationEngine` in a worker thread, registers it in `_sessions`.
3. `useWebSocket.js` connects to `ws_url` (through the Vite `/ws` proxy); frames stream at `update_rate_hz`.
4. Each frame is appended to `trackingStore.js` histories (MAX_HISTORY=500) and rendered by `TrackingMap.jsx` / charts.
5. `GET /api/simulation/stats/{id}` and `/export/{id}` read the engine's ring buffer (`_frames`) for RMSE stats and CSV export; WS disconnect cleans up the session.

### 3) Layer/Module Responsibilities

| Layer or module | Owns | Must not own | Evidence |
|-----------------|------|--------------|----------|
| `routers/simulation.py` | Session lifecycle, REST, WS streaming, CSV export | Filter math | file itself |
| `simulation/target_simulator.py` (846 lines) | `SimulationConfig`, `SimulationEngine`, trajectory classes (pedestrian/motorcycle/drone/kinematic drone + dataset/road-network variants) | HTTP concerns | file |
| `simulation/data_loaders.py` (717 lines) | `GeolifeWalkLoader`, `AMITMotorcycleLoader`, `RoadNetworkMotorcycleLoader`, PCHIP interpolation | API layer | file |
| `simulation/boundary.py`, `sensor_noise.py` | Soft potential-field boundary; per-target-type Gaussian noise models | — | AGENTS.md + file headers |
| `algorithms/kalman_filter.py` (426 lines) | 2D + 3D Kalman; uses `np.linalg.solve` (never `inv`) | — | RULES A2, AGENTS.md |
| `algorithms/sensor_fusion.py` | `fuse_sensors()` module-level function (NOT a class) | — | AGENTS.md |
| `routers/calculator.py` | Static single-point calculation | — | file (46 lines) |
| `store/trackingStore.js` | Frame/metric history, layer toggles, per-type observer defaults | Network I/O | file |
| `hooks/useWebSocket.js` | WS connection lifecycle, store updates | Rendering | file |

### 4) Reused Patterns

| Pattern | Where found | Why it exists |
|---------|-------------|---------------|
| In-memory registry dict | `routers/simulation.py:_sessions` | Zero-persistence demo sessions; cleanup on WS disconnect |
| Strategy/class-per-trajectory | `_TRAJECTORY_MAP` in `target_simulator.py` (`pedestrian`/`motorcycle`/`drone` classes; motorcycle maps to `RoadNetworkMotorcycleTrajectory` in both modes) | Swap trajectory models without touching engine |
| Ring buffer | `SimulationEngine._frames` (backend), `trackingStore.js` MAX_HISTORY=500 (frontend) | Bounded memory for live streaming |
| Offloaded CPU init | `asyncio.to_thread(SimulationEngine, config)` | Avoid blocking the event loop on road-network load |
| Router split (REST vs WS) | `router` vs `ws_router` in `simulation.py` | CORS middleware limitation for WS upgrades |

### 5) Known Architectural Risks

- In-memory sessions: backend restart or multi-worker deployment (`--workers >1`) loses/breaks sessions and WS routing.
- No auth on any endpoint (intentional for thesis demo, documented in AGENTS.md).
- `target_simulator.py` (846 lines) and `data_loaders.py` (717 lines) mix several trajectory classes in single files — see CONCERNS.md.

### 6) Evidence

- `backend/app/main.py` (router mounting, CORS, lifespan)
- `backend/app/routers/simulation.py` (sessions, WS docstring)
- `frontend/vite.config.js` (proxy), `frontend/src/store/trackingStore.js`, `frontend/src/hooks/useWebSocket.js`
- `AGENTS.md` (WebSocket critical-path quirk section)
- `docs/codebase/.codebase-scan.txt`
