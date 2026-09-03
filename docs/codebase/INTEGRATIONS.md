# External Integrations

> Default context: `AGENTS.md` (repo root) + `RULES/RULES.md`. Deep-dive: `docs/03-backend.md`.

## Core Sections (Required)

### 1) Integration Inventory

| System | Type | Purpose | Auth model | Criticality | Evidence |
|--------|------|---------|------------|-------------|----------|
| Vite dev proxy (`/api`, `/ws`) | HTTP/WS proxy | Bridges React dev server (5173) to FastAPI (8000); needed because CORS middleware does not apply to WS upgrades | none | high | `frontend/vite.config.js` |
| OpenStreetMap / Overpass API | external API | Road-network visualization layers on the Leaflet map | none (public) | medium | AGENTS.md "Per-type Observer Coordinates" |
| OSM data via osmnx | library + downloaded artifact | `scripts/download_hcmc_road_network.py` → `data/hcmc_roads.graphml` (102.5 MB, 337K nodes, 305K edges) consumed by `RoadNetworkMotorcycleLoader` | none | high (motorcycle trajectories) | AGENTS.md "HCM City Road Network" |
| Git LFS | storage | Large dataset files (AMIT CSVs, graphml, CSV exports) tracked via `.gitattributes` | n/a | low | git log: "chore: move existing CSV files to Git LFS" |

No third-party SaaS integrations (no auth provider, no message queue, no monitoring SaaS) exist in the code.

> **Scope note (2026-09-03)**: Documentation is frozen at the simulation-only state. The embedded HAL / `raspberry_pi/` hardware client described in AGENTS.md "Target Embedded Architecture" is out of scope for these docs — it has no code in the repo and no integration surface yet. Revisit this inventory if/when hardware modules land.

### 2) Data Stores

| Store | Role | Access layer | Key risk | Evidence |
|-------|------|--------------|----------|----------|
| In-process memory (`_sessions` dict, engine `_frames` ring buffer) | Session registry + recent frames for `/stats` and `/export` | `routers/simulation.py`, `target_simulator.py` | Lost on restart; breaks with multiple uvicorn workers | `routers/simulation.py:38` |
| File-based datasets (`data/`) | Trajectory sources: Geolife `.plt`, AMIT `_TRJ.csv`, road `graphml` | `app/simulation/data_loaders.py` | Large files; GraphML load time at session start | scan CODE METRICS |
| Browser memory (Zustand) | Frontend trajectory history (MAX_HISTORY=500) | `trackingStore.js` | Refresh clears state (by design) | `trackingStore.js` |

There is **no database** in this project.

### 3) Secrets and Credentials Handling

- Credential sources: none. No `.env`/`.env.example` found (scan: "No .env.example or .env.template found"); no `os.environ` reads in `backend/app/`.
- Hardcoding checks: CORS origins hardcoded in `backend/app/main.py:58-62` (localhost only); Overpass/OSM URLs in frontend road-layer component. No secrets present, so no exposure.
- Rotation/lifecycle: not applicable.

### 4) Reliability and Failure Behavior

- Retry/backoff: none implemented for external calls; OSM data is pre-downloaded to avoid runtime OSM dependency for motorcycle trajectories.
- Timeout policy: none configured beyond ASGI defaults.
- Fallback behavior: `RoadNetworkMotorcycleTrajectory` falls back to the old `MotorcycleTrajectory` (kinematic model) when the road graph is unavailable (AGENTS.md "Motorcycle Road-Network").
- WS disconnect cleans up the session (AGENTS.md WebSocket section).

### 5) Observability for Integrations

- Logging around external calls: module-level `logging` in backend files; no dedicated correlation IDs.
- Metrics/tracing: none (no APM/Prometheus). Per-session RMSE/frame stats exposed via `GET /api/simulation/stats/{id}` and `/api/simulation/dashboard`.
- Missing visibility gaps: no request tracing, no error-rate aggregation, no health probe beyond `/health` and `/`.

### 6) Evidence

- `frontend/vite.config.js`, `backend/app/main.py`, `backend/app/routers/simulation.py`
- `docs/codebase/.codebase-scan.txt` (ENV TEMPLATES: none; SECURITY: none)
- `AGENTS.md` (road network, embedded architecture, WebSocket quirk sections)
