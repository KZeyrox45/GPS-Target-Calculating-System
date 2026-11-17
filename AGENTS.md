# AGENTS.md

Thesis project (HCMUT): real-time target-coordinate tracking from GPS + laser + IMU fusion. Docs, UI strings, and code comments are in **Vietnamese** — keep user-facing text in Vietnamese. Conventional commits (chore/fix/perf/docs), single `main` branch.

## Layout

- `backend/` — FastAPI + uv (Python ≥3.11). Entry: `app/main.py`; routers under `/api/*`, WebSocket `/ws/tracking/{id}`, `/health`.
- `frontend/` — React 19 + Vite 8 SPA (Zustand, react-leaflet). Routes live in `src/App.jsx`.
- Root `index.html` + `js/` + `css/` — standalone Phase-1 static calculator (vanilla JS, fully client-side). **Not** part of either app; never wire it into a build.
- `data/` — datasets (see gotchas). `frontend/README.md` is the untouched Vite template; ignore it.

## Commands (verified 2026-11-16)

### Backend — run from `backend/`

- Setup: `uv sync --python 3.11 --group dev`
  **Always pin 3.11.** Without it uv picks the newest system Python (3.15 here) and `pyproj` (via osmnx → geopandas) fails to build with `proj executable not found`. CI pins 3.11 too.
- Dev server: `uv run uvicorn app.main:app --reload --port 8000`
- Tests: `uv run pytest tests/ -q` → 165 passed in ~43 s. Single file: `uv run pytest tests/test_kalman.py -q` (17 passed in 0.14 s). Must run from `backend/` (pytest `pythonpath = "."`).
- Lint — use CI's exact command: `uv tool run ruff check app/ tests/`. ruff is **not** in the dev dependency group, so `uv run ruff ...` will not find it.
- Standalone checks (need the server running on :8000): `uv run python scripts/ws_smoke.py`.
- Repro/benchmark scripts (documented in README): `uv run python tests/benchmark_rmse.py`, `tests/statistical_analysis.py`, `scripts/measure_timing.py`.

### Frontend — run from `frontend/`

- Install: `npm ci` (lockfile authoritative).
- Dev: `npm run dev` → :5173, proxies `/api` and `/ws` to `localhost:8000` (override with `BACKEND_URL` / `WS_URL` env vars in `vite.config.js`).
- Build: `npm run build` — passes (chunk-size warning is expected).
- Lint: `npm run lint` — **passes on this branch** (`eslint.config.js` now grants node globals to config files like `vite.config.js`). On `main` it still fails with `process is not defined` ×2 — that is why the CI badge is red; backend CI job is green.

### Docker

`docker compose up --build` — backend :8000 (healthcheck `/health`), frontend :5173, `./data` mounted read-only.

## Verification order

CI (`.github/workflows/ci.yml`, runs on every push and PRs to `main`/`develop`): backend `uv sync --frozen --group dev` → `ruff check` → `pytest -q`; frontend `npm ci` → `eslint` → `vite build`. **No pre-commit hooks** — before committing, run ruff + pytest (backend) and `npm run lint` + `npm run build` (frontend).

## Gotchas

- **Git LFS**: `*.graphml`, `*.npz`, `*.csv` are LFS-tracked — run `git lfs pull` after cloning or tests/simulation break. Tests read `data/Geolife Trajectories 1.3/`, `data/AMIT/`, `data/hcmc_roads.graphml` (~102 MB); session-scoped fixtures in `tests/conftest.py` parse the datasets once, so the first full run is the slow one and later runs are fast.
- `data/hcmc_roads.pickle` is a generated cache (gitignored; rebuilt on backend startup, ~7 s cold) — safe to delete.
- `backend/requirements.txt` is deprecated: `pyproject.toml` + `uv.lock` is the single source of truth (the Dockerfile copies requirements.txt only for layer caching).
- The backend loads no `.env` (`python-dotenv` is an unused dependency); CORS allows only `localhost:5173`/`3000`.
