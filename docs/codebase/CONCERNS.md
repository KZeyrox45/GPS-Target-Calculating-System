# Codebase Concerns

> Default context: `AGENTS.md` (repo root) + `RULES/RULES.md`. The project already tracks trajectory-realism findings (6 fixes, Week 10) and verification gates (`GATES.md`) — this doc adds repo-level technical concerns only.

## Core Sections (Required)

### 1) Top Risks (Prioritized)

| Severity | Concern | Evidence | Impact | Suggested action |
|----------|---------|----------|--------|------------------|
| med | In-memory session registry breaks under multiple uvicorn workers or restart | `routers/simulation.py:38` `_sessions` dict | Sessions/WS unusable when scaled; lost on deploy | Accept (demo posture) or persist session registry |
| med | Pedestrian filtered output nearly stationary (GPS noise ~5 m vs 1.4 m/s walk; SNR≈0.028) | AGENTS.md "Known Limitation" | Demo may look wrong to reviewers | Documented; consider RTK-GPS noise preset |
| low | No CI despite test + lint gates documented — **RESOLVED 2026-09-03**: `.github/workflows/ci.yml` added (pytest+ruff, eslint+build) | `.github/workflows/ci.yml` | Gates now enforced on push/PR | Keep workflow in sync with `Commands/run_tests.bat` |
| low | Two docs disagree on test count (162 vs 163) — **RESOLVED 2026-09-03**: README synced to 163 | README.md now cites 163 everywhere | Stale doc confuses onboarding | Verified via `pytest --collect-only` (163 collected) |

### 2) Technical Debt

| Debt item | Why it exists | Where | Risk if ignored | Suggested fix |
|-----------|---------------|-------|-----------------|---------------|
| `target_simulator.py` = 846 lines mixing many trajectory classes | Incremental feature growth (synthetic + dataset + road-network + kinematic drone) | `backend/app/simulation/target_simulator.py` | Merge-conflict hot spot; highest backend churn (5 commits/90d) | Split per trajectory class |
| `data_loaders.py` = 717 lines, 3 loader classes | Dataset additions stacked in one module | `backend/app/simulation/data_loaders.py` | Same as above | Split per loader |
| No formatter (Python) | Ruff only lints | `backend/pyproject.toml` | Style drift despite line-length 120 | Add `ruff format` to workflow |
| Router docstring vs AGENTS.md drift | Doc counts updated ad hoc | README (162) vs AGENTS (163) | Wrong numbers in reports | Single source of truth check in GATES |
| Root litter: `test-week.aux/.log/.out`, `nul` file | LaTeX experiment artifacts | repo root | Noise in tree | Delete or gitignore |

### 3) Security Concerns

| Risk | OWASP | Evidence | Current mitigation | Gap |
|------|-------|----------|--------------------|-----|
| No authentication/authorization on any endpoint | A01/A07 | `main.py`, `routers/simulation.py` | None (intentional; thesis demo, localhost only) | Acceptable for demo; must not be deployed publicly as-is |
| CORS allows any method/headers for localhost origins | A05 | `main.py:56-66` | Origin allowlist is narrow (localhost) | Fine for dev; revisit before any hosting |
| WebSocket endpoint has no origin validation server-side | A07 | `ws_router` mounted at root | Browser same-origin policy + Vite proxy | Direct WS clients can connect; demo-only risk |
| Ruff bandit rules (S) enabled | — | `pyproject.toml` | Static scanning active | [TODO] no audit history |

### 4) Performance and Scaling Concerns

| Concern | Evidence | Current symptom | Scaling risk | Suggested improvement |
|---------|----------|-----------------|--------------|-----------------------|
| GraphML (102.5 MB) loaded at engine init (offloaded to thread) | AGENTS.md; `asyncio.to_thread(SimulationEngine, config)` | Slow first ENGAGE per backend start | Session-creation latency grows with graph size | Cache loaded graph at app lifespan, share across sessions |
| No CPU/IO perf configs; pipeline perf asserted manually (59 µs @ 10 Hz) | scan PERFORMANCE: none; AGENTS.md verified numbers | None observed | Only single-session posture | Fine for thesis; revisit if multi-user |
| Frontend ring buffer 500 frames with array copies per frame | `trackingStore.js` `appendHistories` | None at 10 Hz | GC churn at higher rates | Acceptable; document limit |

### 5) Fragile/High-Churn Areas

| Area | Why fragile | Churn signal (90d) | Safe change strategy |
|------|-------------|--------------------|----------------------|
| `backend/app/routers/simulation.py` | REST+WS+export+dashboard all in one router | 6 commits (top churn) | Run full pytest + ws_smoke after any change |
| `backend/app/simulation/target_simulator.py` | Core engine + all trajectory classes | 5 commits | Fixed-seed tests are the guardrail; never alter seeds |
| `backend/tests/benchmark_rmse.py` | Authoritative numbers source | 5 commits | Changing it invalidates all report numbers — treat as frozen baseline |
| `frontend/src/App.jsx`, `HomePage.jsx`, `trackingStore.js` | UI evolution + dashboard endpoint addition | 5/5/4 commits | `npm run lint` + `npm run build` before commit |
| `report-weekly/` LaTeX | Strict formatting rules (RULES B) | 5-6 commits per week file | 5-pass compile check + `scripts/audit_labels.py` |

### 6) `[ASK USER]` Questions — all RESOLVED 2026-09-03

1. ~~Test count: 162 vs 163~~ → **163** (live `pytest --collect-only`); README synced.
2. ~~Commit `docs/codebase/`?~~ → **Yes**, committed to git on `develop`.
3. ~~Hardware modules in scope for docs?~~ → **No** — documentation frozen at the simulation-only state; HAL/`raspberry_pi/` marked out of scope in INTEGRATIONS.md; future-facing section removed from README.

### 7) Evidence

- `docs/codebase/.codebase-scan.txt` (TODO: none; CI/CD: none; churn table; CODE METRICS)
- `git log --name-only` churn analysis (executed during Phase 2)
- `backend/app/routers/simulation.py`, `backend/app/main.py`, `backend/pyproject.toml`
- `frontend/src/store/trackingStore.js`
- `AGENTS.md` (Known Limitation, verified numbers, Code Quality Status)
- `GATES.md` (G14: 163 passed in 38.44s)
