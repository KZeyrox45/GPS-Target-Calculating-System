# Coding Conventions

> Default context: `RULES/RULES.md` is the **canonical, non-negotiable rule set** for this repo (code + reports). `AGENTS.md` (repo root) adds verified facts and conventions. This doc summarizes what is enforced and observable; RULES.md wins on any conflict.

## Core Sections (Required)

### 1) Naming Rules

| Item | Rule | Example | Evidence |
|------|------|---------|----------|
| Backend files | `snake_case.py` | `kalman_filter.py`, `target_simulator.py` | `backend/app/` listing |
| Backend classes | `PascalCase`, domain-prefixed | `KalmanFilter3D`, `SimulationEngine`, `GeolifeWalkLoader` | file scan |
| Private module members | leading underscore | `_sessions`, `_TRAJECTORY_MAP`, `_random_start_in_boundary` | `routers/simulation.py:38`, `target_simulator.py` |
| Frontend component files | `PascalCase.jsx` | `TrackingMap.jsx`, `SimulationPanel.jsx` | `frontend/src/` listing |
| Frontend non-component files | `camelCase.js` | `trackingStore.js`, `useWebSocket.js`, `apiError.js` | `frontend/src/` listing |
| Constants | `UPPER_SNAKE` | `MAX_HISTORY`, `TYPE_DEFAULTS`, `V_MAX_H` | `trackingStore.js:7` |

### 2) Formatting and Linting

- Python formatter: none configured; **linter: ruff** (config inside `backend/pyproject.toml`: target py311, line-length 120, rules F/E/W/I/UP/B/BLE/S/RUF/TRY/PERF; ignores E402/E501/RUF001-3/TRY003/TRY300/B905; `scripts/*` ignores E402; `tests/*` allows assert).
- JS linter: ESLint 9 flat config (`frontend/eslint.config.js`); `no-unused-vars` error with `varsIgnorePattern: '^[A-Z_]'`; react-hooks recommended + react-refresh.
- No TypeScript: all frontend files are `.jsx` (RULES A3 forbids TS even though `@types/react` is a dev dep).
- Run commands: `uv tool run ruff check app/ tests/` (0 errors) and `npm run lint` (0 warnings) before any commit.

### 3) Import and Module Conventions

- Backend: absolute-ish package imports (`from ..models.schemas import ...`, `from app.algorithms.sensor_fusion import fuse_sensors`); ruff isort (I) enforces ordering; `import *` forbidden (RULES A2).
- Frontend: ES modules with named/default imports; no path aliases configured.
- Pydantic v2 only: `model_config = ConfigDict(...)`; `class Config` forbidden (RULES A2).
- Kalman filters must use `np.linalg.solve`, never `np.linalg.inv` (RULES A2, numerical stability).

### 4) Error and Logging Conventions

- Backend errors: `HTTPException` with 404 for unknown session (`routers/simulation.py:77-78`); plain-dict error payloads not observed in routers.
- Logging: stdlib `logging` with `basicConfig(level=logging.INFO)` in `main.py`; one module logger per file (`log = logging.getLogger(__name__)`).
- Frontend errors: `frontend/src/utils/apiError.js` (13 lines) centralizes API error handling.
- No sensitive-data redaction rules — no secrets exist in the repo (no `.env`, no env var reads in `backend/app/`).

### 5) Testing Conventions

- Tests in `backend/tests/`, run from `backend/` (imports are `from app...`; CWD matters). Fixed RNG seeds via `np.random.default_rng(seed)`; do not change seed values (RULES A4). Do not add/modify tests without being asked (RULES A4).
- Report writing (LaTeX) conventions live in `RULES/RULES.md` section B and AGENTS.md "Report Writing Conventions" (Vietnamese body, first-occurrence English annotations, no cross-week references, `[htbp]` floats, 5-pass compilation, no em-dashes).

### 6) Evidence

- `RULES/RULES.md` (canonical rules; read in full during doc creation)
- `backend/pyproject.toml` `[tool.ruff]` sections
- `frontend/eslint.config.js`
- `backend/app/main.py`, `backend/app/routers/simulation.py`, `frontend/src/store/trackingStore.js`
- `AGENTS.md` ("Conventions worth knowing")
