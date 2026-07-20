# Testing & Verification

## Test Suite

**Location**: `backend/tests/`
**Framework**: pytest + pytest-asyncio
**Count**: 125 tests (all passing)
**Run**:
```bash
cd backend
uv run pytest tests/ -v
```

## Test Files

| File | Tests | Coverage |
|------|-------|----------|
| `test_alpha_beta.py` | 10 | Alpha-beta filter: init, step, reset, speed |
| `test_geodetics.py` | 14 | Haversine, bearing, ECEF/ENU roundtrips, negative elevation |
| `test_kalman.py` | 15 | Kalman filter: init, predict, update, convergence, RMSE spec |
| `test_sensor_fusion.py` | 6 | fuse_sensors: direction, sigma, LLA output |
| `test_simulation_phase2.py` | 49 | Trajectories, boundary, Kalman3D, adaptive R, motorcycle crash, drone |
| `test_stats_endpoint.py` | 15 | Stats engine, stats endpoint, export endpoint |
| `benchmark_rmse.py` | (script) | Authoritative RMSE baseline for report numbers |

## Key Test Categories

### Algorithm Correctness
- Kalman convergence for all 3 target types
- Alpha-beta smoothing behavior
- Sensor fusion sigma increases with range
- ECEF/ENU roundtrip accuracy

### Boundary Constraints
- Pedestrian stays within boundary
- Motorcycle reflects correctly
- Drone horizontal constrained, altitude free
- Invalid radius raises validation error

### Edge Cases
- Negative elevation (observer looking down)
- Zero distance (target at observer position)
- First-step initialization of filters
- Motorcycle turn angles (regression: no crash)

### API Endpoints
- Stats returns 404 for unknown session
- Stats returns 200 for active session
- Export returns CSV with correct header/row count
- Export returns 204 when no frames

## Reproducibility

All tests use fixed RNG seeds via `np.random.default_rng(seed)`. The `seed` field in the API request controls reproducibility. Default seed in tests: 42.

## Scripts (Non-Test Verification)

### benchmark_rmse.py
```bash
cd backend
uv run python tests/benchmark_rmse.py
```
Authoritative RMSE numbers for the thesis report. Uses actual simulation engine, no server needed.

### generate_figures.py
```bash
cd backend
uv run python scripts/generate_figures.py
```
Generates all report PNG figures into `report-weekly/figures/` and `report-weekly/Images/`.

### ws_smoke.py
```bash
cd backend
uv run python scripts/ws_smoke.py
```
Full REST→WS pipeline smoke test. **Requires backend already running on :8000.**

## Linting

### Python (Ruff)
```bash
cd backend
uv run ruff check .
```
Default rules: 115 errors → 7 remaining (all E402 in scripts, intentional due to `sys.path.insert` before imports).

### JavaScript (ESLint)
```bash
cd frontend
npm run lint
```
Result: 0 warnings.

## Frontend Build
```bash
cd frontend
npm run build
```
Output: `frontend/dist/`. Build succeeds with expected chunk size warning.

## CI/CD

None configured. No pre-commit hooks. No GitHub Actions.
