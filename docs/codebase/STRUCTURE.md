# Codebase Structure

> Default context: `AGENTS.md` (repo root) + `RULES/RULES.md` (canonical rules). AGENTS.md warns: there are TWO frontends — do not confuse them.

## Core Sections (Required)

### 1) Top-Level Map

| Path | Purpose | Evidence |
|------|---------|----------|
| `backend/` | FastAPI backend: app source, tests, scripts | `backend/app/main.py` |
| `backend/app/algorithms/` | Pure algorithm layer: geodetics (ENU↔LLA, haversine), KalmanFilter (2D/3D), AlphaBetaFilter, sensor fusion | `backend/app/algorithms/*.py` |
| `backend/app/simulation/` | Trajectory generators + `SimulationEngine` (846 lines), dataset loaders (717 lines), boundary, sensor noise models | line counts via `Get-ChildItem` |
| `backend/app/routers/` | `calculator.py` (POST /api/calculate), `simulation.py` (REST + `ws_router`) | `backend/app/routers/simulation.py` |
| `backend/tests/` | 8 test files + `benchmark_rmse.py`, `statistical_analysis.py`, `conftest.py` | directory listing |
| `frontend/` | React 19 + Vite 8 live-tracking UI (the active frontend) | `frontend/package.json` |
| `index.html` + `js/` + `css/` (repo root) | Static vanilla-JS single-point calculator; no build step; open directly in browser | `js/coordinateCalculator.js`, `js/mapViewer.js` |
| `phase1/` | Archived copy of the static app (+ `report-phase1/`); treat as read-only history | AGENTS.md |
| `data/` | Geolife 1.3, AMIT CSVs, `hcmc_roads.graphml` (102.5 MB), arXiv reference papers | `docs/codebase/.codebase-scan.txt` CODE METRICS |
| `docs/` | 10 project docs (01-architecture ... 10-demo-guide), Vietnamese | AGENTS.md |
| `report-weekly/` | LaTeX weekly reports (weeks 1–15, master `main.tex`, 249 pages) | `GATES.md` |
| `defense-prep/` | `bao-ve.tex`, `phan-bien.tex` (oral + reviewer Q&A, standalone LaTeX) | `defense-prep/` |
| `RULES/` | `RULES.md` — canonical project rules (`.agents/rules/RULES.md` is a pointer stub) | `RULES/RULES.md` line 2 |
| `scripts/` | LaTeX tooling (`compile_week.py`, `audit_labels.py`, ...) + `demo_script.md` | directory listing |
| `Commands/` | Windows batch helpers (start/kill servers, run tests, compile LaTeX) | directory listing |
| `GATES.md` | Verification-gate checklist with evidence per gate | `GATES.md` |
| `Simulation_Results/`, `report-phase2/` | Result artifacts / phase-2 report material | top-level listing |
| `.playwright-mcp/` | Browser-capture logs (page snapshots/console) from manual test sessions | directory listing |

### 2) Entry Points

- Main backend runtime entry: `backend/app/main.py` (`app` object, run via `uvicorn app.main:app --port 8000` from `backend/`).
- Frontend entry: `frontend/src/main.jsx` → `frontend/src/App.jsx` (routes: HomePage, TrackingPage, StaticCalcPage, ComparisonPage, DashboardPage).
- Secondary entries (scripts): `backend/tests/benchmark_rmse.py`, `backend/tests/statistical_analysis.py`, `backend/scripts/ws_smoke.py`, `scripts/compile_week.py`.
- Static calculator: `index.html` (repo root), loaded directly in browser.

### 3) Module Boundaries

| Boundary | What belongs here | What must not be here |
|----------|-------------------|------------------------|
| `app/algorithms/` | Numerical filters, geodesy, fusion — no I/O, no FastAPI imports | HTTP/session/state logic |
| `app/simulation/` | Trajectory generation, noise, boundary, engine, dataset loaders | HTTP routing; persistence |
| `app/routers/` | REST/WS endpoints, session registry (`_sessions` dict) | Filter/trajectory math |
| `app/models/` | Pydantic v2 schemas (`ConfigDict`, not `class Config`) | Business logic |
| `frontend/src/store/` | Zustand state (ring buffer MAX_HISTORY=500) | Fetch/WebSocket logic (lives in `hooks/`) |
| `frontend/src/hooks/` | `useWebSocket.js` connection management | UI rendering |

### 4) Naming and Organization Rules

- Backend: `snake_case.py`; class prefixes by domain (`KalmanFilter`, `SimulationEngine`, `GeolifeWalkLoader`, `RoadNetworkMotorcycleLoader`); module-level private registries use leading underscore (`_sessions`, `_TRAJECTORY_MAP`).
- Frontend: `PascalCase.jsx` for components/pages, `camelCase.js` for store/hooks/utils (`trackingStore.js`, `useWebSocket.js`, `apiError.js`).
- Directories organized by layer (backend) and by type (frontend: pages/components/charts|controls|map|ui, store, hooks, utils).

### 5) Evidence

- `backend/app/main.py` (routing layout docstring)
- `frontend/src/main.jsx`, `frontend/src/App.jsx`
- Directory listings (backend app line counts, frontend src tree)
- `AGENTS.md` ("Two frontends — do not confuse them" section)
- `docs/codebase/.codebase-scan.txt` (DIRECTORY TREE)
