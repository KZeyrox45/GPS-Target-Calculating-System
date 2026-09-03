# Testing Patterns

> Default context: `AGENTS.md` (repo root) + `RULES/RULES.md` A4 (test rules are strict: fixed seeds, no unrequested test changes). Deep-dive: `docs/06-testing.md`.

## Core Sections (Required)

### 1) Test Stack and Commands

- Primary test framework: **pytest 8.4.1** with **pytest-asyncio 0.26.0** (async auto-enabled by plugin; `asyncio_default_fixture_loop_scope = "function"`) and pytest-xdist.
- Assertion tool: plain `assert` (S101 allowed in `tests/*` per ruff per-file-ignores).
- Commands:

```bash
cd backend
uv run pytest tests/ -v                  # full suite
uv run pytest tests/test_kalman.py -v    # single file
uv run pytest tests/ -k TestDroneBoundary # single class
uv run pytest tests/ -m "not slow"       # deselect slow marker (defined in pyproject)
uv run python tests/benchmark_rmse.py    # authoritative RMSE baseline (seed=42, no server)
uv run python tests/statistical_analysis.py  # multi-seed (1-10) mean/std RMSE
uv run python scripts/ws_smoke.py        # end-to-end smoke test (REQUIRES backend on :8000)
```

### 2) Test Layout

- Placement: central `backend/tests/` (not co-located). Run from `backend/` because tests import `from app...` (`pythonpath = ["."]` also set in `pyproject.toml`).
- Files: `test_alpha_beta.py`, `test_data_loaders.py` (38 tests), `test_geodetics.py`, `test_kalman.py`, `test_sensor_fusion.py`, `test_simulation.py`, `test_stats_endpoint.py`, plus `conftest.py`, `benchmark_rmse.py`, `statistical_analysis.py`.
- `pytest-xdist` installed for parallel runs; not part of documented default command.

### 3) Test Scope Matrix

| Scope | Covered? | Typical target | Notes |
|-------|----------|----------------|-------|
| Unit | yes | filters, geodetics, sensor fusion, data loaders, trajectory generators | per-module test files |
| Integration | yes | REST endpoints (`test_stats_endpoint.py`), engine routing logic | in-process FastAPI; no real network |
| E2E | partial | `scripts/ws_smoke.py` full REST→WS pipeline | manual/scripted; requires running server |
| Reproducibility | yes | fixed-seed RMSE benchmarks (`benchmark_rmse.py` seed=42) | source of truth for report numbers |

### 4) Mocking and Isolation Strategy

- Main approach: deterministic seeds (`np.random.default_rng(seed)`); no heavy mocking observed — algorithm and simulation code is pure/testable in-process.
- Isolation: each test constructs its own engines/loaders; API `seed` field controls reproducibility across the REST surface.
- Session registry `_sessions` is module-global; endpoint tests rely on per-test engine instances (see `test_stats_endpoint.py`).

### 5) Coverage and Quality Signals

- Coverage tool: none configured; no threshold.
- Expected count: **163 tests** per `AGENTS.md`/`GATES.md` G14 ("163 passed in 38.44s"); README says 162 — see CONCERNS.md divergence note. Verified during this documentation pass via `pytest --collect-only` (count confirmed below in Validation).
- Known gaps: no frontend tests at all (`npm run lint`/`npm run build` are the only frontend checks).

### 6) Evidence

- `backend/pyproject.toml` `[tool.pytest.ini_options]`
- `backend/tests/` listing; `GATES.md` G14; `AGENTS.md` Tests section
- Validation: `uv run pytest tests/ --collect-only -q` executed 2026-09-03
