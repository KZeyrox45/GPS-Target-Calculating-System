# Full Audit & Upgrade Design Spec

**Date:** 2026-08-20
**Project:** GPS-Target-Calculating-System (Laser-IMU-GNSS sensor fusion, real-time moving-target tracking)
**Branch:** develop
**Status:** Approved in principle — pending user review of this spec

---

## 1. Purpose

Execute the three URGENT MISSIONS from `IMPORTANT_NOTE.md` in the approved order:

1. **Mission II — Write report** (anti-AI, persuasive, phase-2-focused, ≥15 pages/week, ~150+ total, professional images)
2. **Mission I — Refine project code** (static + runtime audit, findings first, fixes after approval)
3. **Mission III — Update workspace files** (Commands/, defense-prep/, docs/, AGENTS.md, RULES.md, .agents/, MCP_PROMPT/, Simulation_Results/)

Hardware is not available. Datasets (Geolife, AMIT, HCMC road network) substitute for real hardware — this substitution is supervisor-approved. All work must make phase 2 clearly different from phase 1 (the archived `phase1/` static single-point calculator).

**Global anti-AI stance (applies to EVERY file in the project, not just reports):** All files — reports, defense-prep, docs, code comments, README, scripts — must show no signs of AI generation. We write and audit as a real human would: no formulaic connectors, no robotic tone, no AI-characteristic `--`/em-dash in prose, no inflated symbolism, no rule-of-three filler. Anything that reads AI-generated is removed or rewritten.

## 2. Confirmed Decisions (user-approved)

| # | Decision | Choice |
|---|----------|--------|
| 1 | Execution order | Mission II → Mission I → Mission III |
| 2 | Dashboard (IMPORTANT_NOTE Q1) | Enhance TrackingPage as the live dashboard (real-time sim = hardware stand-in) |
| 3 | Peripheral files (IMPORTANT_NOTE Q2) | Keep all, reorganize & integrate (AUDIT_REPORT history; raspberry_pi documented stub; relocate root scripts) |
| 4 | RULES.md organization | Single source at root; `.agents/rules/RULES.md` becomes a short pointer |
| 5 | Report scope | Expand ALL weeks 1-10 to 15+ pages each (~150+ total) |
| 6 | Week expansion style | Full audit of every word/character — no AI signs in text, charts, tables, images. Review every image for correctness vs official info BEFORE changing |
| 7 | Mission I fixes | Report findings FIRST; fix only after user approval |
| 8 | Runtime access | Granted — backend, frontend, browser, screenshots, tests, lint |
| 9 | Git commits | Commit per mission, conventional-commit style, on develop |
| 10 | Dashboard change size | Moderate enhancement to TrackingPage (stats strip, comparison chart, export buttons, system status) |
| 11 | Spec file | This document — committed to `docs/superpowers/specs/` |

## 3. Verification Gate (applies to every mission before commit)

All must pass before a mission is committed:

- Backend tests: `uv run pytest tests/ -v` (from `backend/`) → **162/162 pass**
- Ruff lint: `uv tool run ruff check app/ tests/` (from `backend/`) → **0 errors** (7 remaining E402 in scripts/ are intentional, do not "fix")
- Frontend lint: `npm run lint` (from `frontend/`) → **0 warnings**
- Frontend build: `npm run build` (from `frontend/`) → succeeds (chunk-size warning for Leaflet+Recharts is expected)
- LaTeX (report missions): 5-pass `pdflatex -interaction=nonstopmode main.tex` → **0 errors**
- Commit: conventional-commit style on `develop`, one commit per mission

---

## 4. Mission II — Write Report

### 4a. Anti-AI text audit

Scope: `report-weekly/week-1.tex` … `week-10.tex`, `report-weekly/main.tex`, `defense-prep/bao-ve.tex`, `defense-prep/phan-bien.tex` (root copies + `report-weekly/Contents/` copies — audit both, then keep single consistent set).

Audit targets (AI-writing signs):
- Formulaic connectors ("Mặt khác", "Ngoài ra", "Hơn nữa", "Cụ thể", "Như vậy", "Đồng thời", "Do đó", rule-of-three constructions)
- AI-characteristic hyphen/em-dash: any `--` in prose renders as em-dash and is an AI sign. **EXCEPTION:** `--` inside TikZ path syntax is required and acceptable. Outside TikZ: replace with natural human wording, or use `-` when representing null data in a table
- Robotic tone: inflated symbolism, vague attributions, excessive conjunctive phrases, superficial "-ing" analyses (Vietnamese equivalents)
- Meta/commentary phrases that reference the document structure itself and would not appear in a real report — e.g., week-1.tex ends with "Week 1 presents an overview..." which will NOT appear in the official report; such phrases must be replaced with the actual content/wording used in the official report
- Redundancy and filler that pads without content
- Repetition of identical phrasing across weeks

Every number in the report must be cross-checked against the verified source-of-truth tables (see §7) and the actual benchmark outputs (`tests/benchmark_rmse.py` seed=42, `tests/statistical_analysis.py` seeds 1-10). No fabricated numbers.

**Benchmark rigor:** Benchmark scripts themselves may be inaccurate. Before trusting any number they produce, rigorously review the benchmark code (correct RMSE computation, correct ground-truth pairing, correct units) and re-run to confirm the outputs match the verified tables. The data is crucial — a wrong number in the report is disqualifying.

**Parameter justification (report content):** The chosen simulation parameters — seed=42, 120s duration, 10Hz sample rate, 400m boundary — must be properly explained in the report and defended in defense-prep, including anticipating common questions: "Why choose these values?", "What do these values mean?", "If the sensors have different frequencies or correlations, what solution would you have?" (answers: frequency alignment/resampling strategy, cross-correlation handling in sensor fusion).

Report constraints (from RULES.md, enforced):
- No code file names, code commands, API endpoint paths, or unexplained jargon (B2 Report-to-PDF rule)
- No cross-week references ("tuần 5 đã chỉ ra...") — each section self-contained; use `\ref{}` for intra-document figures/tables/equations
- No mention of specific weeks in a way that breaks self-containment
- Required term translations (WebSocket → kênh truyền dữ liệu hai chiều, sensor fusion → hợp nhất cảm biến, pipeline → chuỗi xử lý, render → hiển thị, raw → đo thô with first-occurrence annotation, REST API/FastAPI/JSON keep as-is)
- First-occurrence annotation: English term + Vietnamese in parentheses
- English labels kept as-is in TikZ nodes, figure captions, visual elements
- `[htbp]` floats (never `[h!]`); `\texorpdfstring` for math in section titles; `\hspace{0.5cm}` paragraph indents preserved; intentional `\newpage` preserved

### 4b. Image audit

Inventory all images in `report-weekly/Images/`:
- **Official/user-drawn** (root of Images/): activity-diagram.{bmp,jpg,png}, activity-tracking.png, alpha_sensitivity.png, class-diagram.png, coord-flow.png, error-prop.png, hcmut.png, kalman-detail.png, multi_seed_rmse_spec.png, real-time-data-pipeline.png, use-case-diagram.png
- **figures/** and **sim/** subfolders: review strictly for (a) repetition of official images, (b) bad/ridiculous drawings, (c) factual correctness against implemented algorithms

For each image: verify factual correctness vs the actual implemented algorithms and verified numbers; check duplication; check professional rendering; check English text (per B9b); explain every retained image in the report.

New asset pipeline (no fabricated visuals):
- Real app screenshots via Playwright / Chrome-devtools of the running backend + frontend
- matplotlib / graphviz charts generated from real benchmark/statistical data
- mermaid → PNG generation for architecture/flow diagrams
- All new images with English text; captions written in Vietnamese

### 4c. Expansion to 15+ pages/week

Method for reaching ≥15 pages per week (~150+ total, currently 96):
- Phase-2 implementation narrative (real code behavior described in plain language — not code dumps)
- Real result tables from benchmark/statistical outputs
- Screenshots with explanatory Vietnamese captions
- Deeper sensor-fusion and coordinate-system prose (ECEF→ENU, RSS error propagation, filter derivations explained verbally)
- Each week self-contained; no cross-week references

Deliverable: compile via `compile_latex.bat` (5 passes) with 0 errors; total page count ≥150 documented.

---

## 5. Mission I — Refine Project Code

### 5a. Static audit

Scope: `backend/`, `frontend/`, `backend/tests/`, `js/`, `css/`, `index.html`, `README.md`, `.gitignore`, `.gitattributes`.

Checks:
- Outdated code / dead code / deprecated patterns
- Deadlocks or blocking patterns (esp. async WebSocket paths, threading in SimulationEngine)
- Unreasonable exception handling (bare `except`, swallowed errors, masking bugs)
- **Real-time performance optimization:** this is a real-time system — optimize for the best possible time efficiency, especially on Windows. Python hot paths (filter steps, sensor-fusion loop, data-loader walks, numpy calls, WS frame serialization) must be profiled and optimized for efficiency while strictly maintaining the problem logic and numerical results (verified numbers must not drift)
- Robotic/AI-like comments in code
- Input-validation error messages returning raw `Error: ...` → must become user-friendly messages
- AI-generated content in README/.gitignore/.gitattributes

### 5b. Runtime audit

Procedure (run order matters):
1. Start backend (`start_backend.bat` / `uv run uvicorn app.main:app --port 8000` from `backend/`)
2. Start frontend (`npm run dev` from `frontend/`)
3. Check for port conflicts (8000/5173) and clean startup
4. Open browser, interact with every component per page: HomePage, TrackingPage, StaticCalcPage, ComparisonPage
5. Verify dark/light toggle is functional, not decorative
6. Verify TrackingPage functions as the live dashboard
7. Test **3 targets (pedestrian/motorcycle/drone) × 3 algorithms (KF+AB, KF ONLY, AB ONLY) × 2 modes (Synthetic, Real-World Data)** — all combinations
8. Check user-friendly I/O notifications (start/stop feedback, errors, export)
9. Capture screenshots for Mission II asset pipeline
10. Close all processes after checks (`kill_servers.bat`)

### 5c. Deliverable & approval gate

- Written findings report first: location (file:line), severity, proposed fix, for every finding
- **No fixes applied until user approves the findings report**

---

## 6. Mission III — Update Workspace Files

- **RULES.md**: single authoritative source at root; `.agents/rules/RULES.md` → short pointer/redirect to root (one file to maintain)
- **AGENTS.md**: full informational audit vs reality (fix documented discrepancies, e.g., root `scripts/` still containing `generate_report_figures.py` + `run_all_combos.py` despite AGENTS.md claiming deletion); keep complete, not lacking/excessive; may use EXA/Context7/DeepWiki
- **Commands/**: verify each .bat works (`start_backend`, `start_frontend`, `start_both`, `run_tests`, `kill_servers`, `compile_latex`)
- **docs/ + defense-prep/**: spoken-language pass — fluent, not theoretical. Defense-prep Q&A must be closely tied to the project topic, spoken (conversational) not written, and free of every AI-writing element listed in §4a
- **Data hygiene (`data/`)**: delete any unused dataset data to free up disk space; keep only what the loaders and reports actually use
- **MCP_PROMPT/**: expand beyond the thin Exa.md
- **Simulation_Results/**: populate with real results (videos, images, text) generated during Mission I runtime audit + Mission II asset pipeline
- **Peripherals**: keep AUDIT_REPORT.md (audit history), raspberry_pi/ (documented future-hardware stub), relocate root `scripts/generate_report_figures.py` + `run_all_combos.py` to `backend/scripts/` (keep `demo_script.md`)

---

## 7. Verified Source-of-Truth Numbers (do not use others in report)

From `tests/benchmark_rmse.py` (seed=42, 120s, 10Hz, boundary=400m):

| Metric | Value |
|---|---|
| Pedestrian RMSE (raw / α-β / Kalman) | 0.48 / 0.26 / 0.86 m |
| Motorcycle RMSE (raw / α-β / Kalman) | 1.89 / 1.02 / 1.80 m |
| Drone RMSE (raw / α-β / Kalman) | 1.94 / 1.06 / 2.10 m |
| Cross-over range (laser vs GPS dominance) | **794 m** |
| β formula (Benedict-Bordner) | β = (2-α) − 2√(1-α) → β ≈ 0.051 at α=0.4 |
| Kalman pipeline share | 82% |
| ECEF→ENU pipeline share | 6% |
| Total pipeline cycle | 59 µs at 10 Hz |
| Geolife walk segments (valid) | 252 |
| KinematicDrone V_MAX_H / V_MAX_ASC | 15 / 5 m/s |

Multi-seed (seeds 1-10): Pedestrian AB 0.34±0.08, Kalman 0.92±0.22; Motorcycle AB 0.91±0.08, Kalman 1.53±0.22; Drone AB 1.09±0.23, Kalman 2.39±0.32. All scenarios PASS spec (<5.0 m).

Per-type observer coordinates (District 10, HCMC): Pedestrian 10.7726/106.6983 (Ben Thanh); Motorcycle 10.7709/106.7030 (Ham Nghi/Le Loi); Drone 10.7280/106.7180 (District 7/Phu My Hung).

Key facts: WS endpoint `/ws/tracking/{session_id}` mounted at root (not /api); Vite proxies `/api` and `/ws`; motorcycle always follows HCMC road network; backend uses uv; frontend is React 19 + Vite (.jsx, no tsconfig); 162 tests; ruff 0 errors expected (7 E402 in scripts/ intentional).

---

## 8. Out of Scope / Constraints

- Do NOT touch `report-new/` (phase-2 official report) until explicitly notified
- Do NOT modify hardware-specific code in `raspberry_pi/` (no physical hardware)
- Do NOT delete context files — only reorganize/integrate
- No fabricated or deceptive images in the report
- Mission I fixes happen only after user approves the findings report
- Each mission gets its own commit; no commits until verification gate passes

## 9. Risks / Open Items

- LaTeX page-count target (~150+) may require careful prose expansion without padding; verify page count from actual 5-pass compile
- Root copies of week-*.tex vs `report-weekly/Contents/` copies must be reconciled to a single consistent set
- The runtime audit's 18 combination matrix (3×3×2) is time-consuming; screenshots captured during it double as Mission II assets
- Benchmark scripts may be inaccurate — the rigor pass may reveal corrected numbers that supersede current verified tables; report numbers must be updated to match corrected ground truth
- Python performance optimization must not change numerical results — verified RMSE/pipeline numbers must remain identical after optimization
- `--` em-dash sweep across all LaTeX is mechanical but error-prone — TikZ paths must be preserved; every non-TikZ occurrence needs a human rewrite