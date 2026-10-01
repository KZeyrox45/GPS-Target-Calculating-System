# Technology Stack

> Default context: read alongside `AGENTS.md` (repo root) and `RULES/RULES.md` (canonical rules). Those two documents are the authoritative intent/constraint sources for this codebase; `docs/01-architecture.md` ... `docs/10-demo-guide.md` hold topic deep-dives.

## Core Sections (Required)

### 1) Runtime Summary

| Area | Value | Evidence |
|------|-------|----------|
| Primary language (backend) | Python 3.11+ (`requires-python = ">=3.11"`) | `backend/pyproject.toml` |
| Primary language (frontend) | JavaScript (JSX only; TypeScript explicitly forbidden by `RULES/RULES.md` A3 despite `@types/react` being installed) | `frontend/package.json`, `frontend/src/**` |
| Backend package manager | `uv` (mandatory; `pip` forbidden by `RULES/RULES.md` A1) | `backend/pyproject.toml`, `RULES/RULES.md` |
| Frontend package manager | npm | `frontend/package.json` |
| Module/build system | Backend: uv + pyproject; Frontend: Vite 8 (`"type": "module"`) | `backend/pyproject.toml`, `frontend/vite.config.js` |

### 2) Production Frameworks and Dependencies

Backend (`backend/pyproject.toml` `dependencies`, all pinned):

| Dependency | Version | Role in system |
|------------|---------|----------------|
| fastapi | 0.115.5 | REST API framework |
| uvicorn[standard] | 0.34.0 | ASGI server |
| websockets | 14.2 | WebSocket streaming |
| numpy | 2.2.6 | Filter math, trajectory generation |
| scipy | 1.15.3 | PCHIP interpolation, statistics |
| pydantic | 2.13.4 | Request/response schemas (v2 `ConfigDict` style) |
| python-dotenv | 1.0.1 | Env file loading |
| httpx | 0.28.1 | HTTP client |
| osmnx | >=2.0.0 | OSM road-network download/processing |

Frontend (`frontend/package.json` `dependencies`):

| Dependency | Version | Role in system |
|------------|---------|----------------|
| react / react-dom | ^19.2.5 | UI framework |
| zustand | ^5.0.12 | Global state (single store, no middleware) |
| leaflet + react-leaflet | ^1.9.4 / ^5.0.0 | Map rendering |
| chart.js + react-chartjs-2 | ^4.5.1 / ^5.3.1 | Error/altitude charts |
| react-router-dom | ^6.30.3 | Page routing |

### 3) Development Toolchain

| Tool | Purpose | Evidence |
|------|---------|----------|
| ruff (configured in `pyproject.toml`) | Python lint — rules F, E, W, I, UP, B, BLE, S, RUF, TRY, PERF; line-length 120 | `backend/pyproject.toml` |
| pytest 8.4.1 + pytest-asyncio 0.26.0 + pytest-xdist | Test runner (async auto-enabled, `slow` marker defined) | `backend/pyproject.toml` |
| matplotlib | Dev-group only; figure generation for analysis scripts | `backend/pyproject.toml` |
| ESLint 9 (flat config) + react-hooks + react-refresh plugins | Frontend lint (`npm run lint`) | `frontend/eslint.config.js` |
| Vite 8 + `@vitejs/plugin-react` | Dev server (port 5173) + build | `frontend/vite.config.js` |
| pdfLaTeX (5 passes) | Weekly report / defense-prep compilation | `Commands/compile_latex.bat`, `GATES.md` |

### 4) Key Commands

```bash
# Backend (from backend/)
uv sync --group dev
uv run uvicorn app.main:app --reload --port 8000
uv run pytest tests/ -v
uv tool run ruff check app/ tests/

# Frontend (from frontend/)
npm install
npm run dev      # port 5173, proxies /api and /ws to :8000
npm run lint
npm run build
```

### 5) Environment and Config

- Config sources: `backend/pyproject.toml` (source of truth; `backend/requirements.txt` is reference only), `frontend/vite.config.js` (dev proxy), `frontend/eslint.config.js`.
- Required env vars: none found — no `.env`, `.env.example`, or `os.environ` reads in `backend/app/`. CORS origins are hardcoded in `backend/app/main.py`.
- Deployment/runtime constraints: sessions are in-memory only (no DB); large data files (`data/hcmc_roads.graphml` ~102 MB, AMIT CSVs) are tracked via Git LFS (`.gitattributes`).

### 6) Evidence

- `backend/pyproject.toml`
- `frontend/package.json`
- `frontend/vite.config.js`
- `frontend/eslint.config.js`
- `backend/app/main.py`
- `RULES/RULES.md` (A1: uv only; A3: no TypeScript)
- `docs/codebase/.codebase-scan.txt` (STACK DETECTION, CODE METRICS sections)
