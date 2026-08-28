# Defense Presentation Outline — GPS Target Calculating System

> **Real-time Moving-Target Tracking via Laser-IMU-GNSS Sensor Fusion**
> Static single-point calculator + 3D Kalman / alpha-beta tracking simulation

| Meta | Detail |
|------|--------|
| **Duration** | 20 minutes total (~15 slides) + 5-10 min Q&A |
| **Team** | 2 members (parts not yet assigned — all slides marked **TBD**) |
| **Format** | **PowerPoint (.pptx)** — convertible to **Beamer (LaTeX)** if needed (`report-weekly/main.tex` toolchain, pdfLaTeX 5 passes) |
| **How to reassign** | Change the `Speaker` field per slide in the table below; time column is independent of speaker so reordering is drag-and-drop safe |
| **Source of truth** | Verified numbers from `tests/benchmark_rmse.py` (seed=42, 120 s, 10 Hz, boundary=400 m) — see `docs/09-statistical-analysis.md` |

**Conventions for this outline:**

- `Speaker: TBD (A/B)` — replace `TBD` with `Member A` or `Member B` once assigned; `Both` only for Q&A.
- `Visual` paths are relative to repo root and point to **actual figures** in `report-weekly/Images/` and `report-weekly/Images/figures/`. No placeholder names.
- Time is wall-clock presentation time, not including transitions; sum = **20:00**.
- Language note: slide titles/visual labels stay in **English** (cleaner for diagrams); spoken explanation can be Vietnamese per `RULES/RULES.md` term translations.

---

## Slide 1 — Title Slide

| Field | Value |
|-------|-------|
| **Time** | 1:00 (00:00-01:00) |
| **Speaker** | **TBD** (either member; 30 s each if split) |
| **Visual** | `report-weekly/Images/hcmut.png` (logo, top-right) + `report-weekly/Images/real-time-data-pipeline.png` as faint background |

**Key points (what to say):**

- Project title, student names + MSSV, supervisor, date; thesis context: Laser-IMU-GNSS fusion for moving targets.
- One-sentence promise: "From raw sensor noise (~2 m) to filtered estimate (~1 m) at 10 Hz, 59 µs per cycle, fully demoable live."
- Roadmap of talk in 10 seconds: problem -> architecture -> algorithms -> data realism -> live demo -> results -> what's next.

---

## Slide 2 — Problem & Motivation

| Field | Value |
|-------|-------|
| **Time** | 1:20 (01:00-02:20) |
| **Speaker** | **TBD** |
| **Visual** | `report-weekly/Images/use-case-diagram.png` (left) + bullet overlay on right |

**Key points:**

- Static calculator (single shot) is solved; **tracking a moving target in real time** is the open challenge — occlusion, maneuvering, noisy sensors.
- Three target regimes matter: pedestrian (~1.4 m/s, gait pauses), motorcycle (road-constrained, 5-6 m/s), drone (3D, 15 m/s horiz / 5 m/s vertical, DJI Matrice 100 limits).
- Why fusion? No single sensor is enough: GPS 5 m, IMU angle drift, laser range sigma grows with distance — need crossover analysis.
- Success criterion: RMSE < 5 m across all scenarios, reproducible (seeded), and demoable at 10 Hz over WebSocket.

---

## Slide 3 — System Architecture

| Field | Value |
|-------|-------|
| **Time** | 1:30 (02:20-03:50) |
| **Speaker** | **TBD** |
| **Visual** | `report-weekly/Images/class-diagram.png` + `report-weekly/Images/activity-diagram.png` (two-panel) |

**Key points:**

- Layered design: **Sensors (simulated) -> SensorFusion (`fuse_sensors()`) -> ECEF/ENU -> Filters (Kalman / alpha-beta) -> FastAPI + WebSocket -> React 19 + Leaflet**.
- Two frontends are distinct: static `index.html + js/` (no build) vs. `frontend/` React 19 + Vite (active tracking UI) — do not confuse.
- Backend is stateless REST + stateful WS: `POST /api/simulation/start` returns `ws_url`; actual WS at `/ws/tracking/{id}` mounted at root (CORS/WebSocket upgrade quirk, proxied via `frontend/vite.config.js`).
- Sessions are in-memory (`_sessions` dict), ring buffer `MAX_HISTORY=500`; closing WS cleans up — no DB needed for demo.

---

## Slide 4 — Coordinate Chain & Sensor Fusion

| Field | Value |
|-------|-------|
| **Time** | 1:30 (03:50-05:20) |
| **Speaker** | **TBD** |
| **Visual** | `report-weekly/Images/coord-flow.png` + `report-weekly/Images/error-prop.png` + `report-weekly/Images/crossover_plot.png` (inset) |

**Key points:**

- Chain: **WGS84 (GNSS) -> ECEF -> ENU (observer-centric) -> target**. Explain why ENU: locally flat, intuitive east/north/up, city-agnostic (Geolife Beijing offsets still valid for HCMC).
- Fusion is a **function, not a class**: `app.algorithms.sensor_fusion.fuse_sensors()` — combines laser range + IMU orientation + GNSS observer pose with RSS error propagation.
- RSS gives `sigma_pos`; crossover at **794 m** (NOT 390 m): below 794 m GPS dominates, above it IMU angular error dominates — drives sensor selection by range.
- Pipeline cost: **59 µs/cycle at 10 Hz** — Kalman 82% + ECEF->ENU 6% (corrected from 85%/7% in early drafts); trivial vs. 100 ms budget.

---

## Slide 5 — Trajectory Realism — What Was Wrong & What Was Fixed

| Field | Value |
|-------|-------|
| **Time** | 1:20 (05:20-06:40) |
| **Speaker** | **TBD** |
| **Visual** | `report-weekly/Images/activity-tracking.png` (before/after) + small table of 6 fixes |

**Key points:**

- Pre-Tuan 10 realism gaps: segment-loop teleportation (`_DatasetTrajectory._step` modulo), origin-relative waypoints (U-turns), hard specular boundary (billiard-ball), motorcycle instant speed jumps (2%/step), drone per-step N(0,0.3) jitter, Kalman zero-velocity init lag.
- All 6 fixed in Tuan 10: **bidirectional replay**, waypoints relative to current position, **soft potential-field repulsion** (80% radius, linear), motorcycle exponential relaxation (tau=2.0 s), drone OU low-pass (tau=1.0 s), Kalman velocity from **finite difference of first two measurements**.
- Validation refs: Helbing & Molnar Social Force, Bongiorno vector navigation, Rodrigues DJI Matrice 100, Zhao & Huang init — not ad-hoc.
- Result: no more teleports/oscillations; each ENGAGE click yields a **different start position** (`_random_start_in_boundary`, 0.8 x boundary disc).

---

## Slide 6 — Kalman vs. Alpha-Beta — Design Choice

| Field | Value |
|-------|-------|
| **Time** | 1:30 (06:40-08:10) |
| **Speaker** | **TBD** |
| **Visual** | `report-weekly/Images/kalman-detail.png` + `report-weekly/Images/alpha_sensitivity.png` (or `report-weekly/Images/figures/alpha_sensitivity.png`) |

**Key points:**

- **Kalman (3D constant-velocity)**: optimal for linear-Gaussian, gives uncertainty `P` (ellipse on map), but pays **convergence cost** (~50 steps, higher RMSE early); uses `np.linalg.solve` for stability.
- **Alpha-beta (Benedict-Bordner, critically damped)**: `beta = (2-alpha) - 2*sqrt(1-alpha)`; at alpha=0.4, beta~0.051. Cheaper, lower RMSE in practice, but **no covariance** — can't draw uncertainty.
- Sensitivity: pedestrian optimum alpha=0.2 -> 0.21 m (default 0.4 -> 0.26 m); default is a compromise across target types, not tuned per scenario.
- Takeaway: alpha-beta wins on RMSE today; Kalman wins when downstream needs **confidence bounds** — we ship both and let the user choose (`KF_ONLY / AB_ONLY / KF+AB`).

---

## Slide 7 — Road Network & Datasets

| Field | Value |
|-------|-------|
| **Time** | 1:10 (08:10-09:20) |
| **Speaker** | **TBD** |
| **Visual** | `report-weekly/Images/real-time-data-pipeline.png` + screenshot `report-weekly/Images/sim/tracking-motorcycle-kfab-synthetic-running.png` (road-following trace) |

**Key points:**

- **Geolife 1.3** (MSR Asia, Beijing, 182 users, walk=6460 labels -> **252 valid segments** after 60-180 s / 400 m / gap<=3 s, cubic spline to 10 Hz).
- **AMIT** (Taiwan UAV, 6 intersections A01-A06, 5 Hz -> 10 Hz, 25,757 motorcycle tracks) — still in code, but **no longer the default** for motorcycle.
- **HCMC road network** `data/hcmc_roads.graphml` (102.5 MB, 337K nodes, 305K edges, via `scripts/download_hcmc_road_network.py`): `RoadNetworkMotorcycleLoader` random-walks real streets with speed-aware routing; dead-end fix backtracks full path (mean walk 256 nodes, short walks <15%).
- Per-type observer defaults (District 10 / Ham Nghi / Phu My Hung) + random start (`rng.integers`, inverse-distance^2 weighted intersection picker) -> diversity across ENGAGE clicks.

---

## Slide 8 — Live Demo (the centerpiece)

| Field | Value |
|-------|-------|
| **Time** | 2:00 (09:20-11:20) |
| **Speaker** | **TBD** (one drives, one narrates — or single presenter) |
| **Visual** | **LIVE** `http://localhost:5173` TrackingPage; fallback stills: `report-weekly/Images/sim/tracking-motorcycle-kfab-synthetic-running.png`, `report-weekly/Images/sim/tracking-drone-kfab-synthetic-running.png`, `report-weekly/Images/sim/calculator.png` |

**Key points (script, ~60 s + 60 s buffer):**

- Pre-flight: `uv run uvicorn app.main:app --port 8000` + `npm run dev` (Vite proxies `/api` -> :8000, `/ws` -> ws://:8000); seed=42, boundary=400 m, duration 60 s.
- Start with **Motorcycle / KF+AB / 400 m** — narrate while running: orange=raw (noisy), blue=alpha-beta (smooth, ~1.14 m), red=Kalman (converges after ~10 s, ~1.52 m), range rings 200/400/600 m + uncertainty ellipse.
- Show **Comparison** tab and **Export CSV** (600 rows = 60 s x 10 Hz) — header: step, time, true position, estimates.
- If live fails: cut to `docs/10-demo-guide.md` FAQ — "Why is Kalman worse early?" (P convergence) and "Why pedestrian looks stationary?" (1.4 m/s vs 5 m GPS noise, SNR~0.028; needs RTK-GPS in real hardware).

---

## Slide 9 — Performance Results (single-seed baseline)

| Field | Value |
|-------|-------|
| **Time** | 1:30 (11:20-12:50) |
| **Speaker** | **TBD** |
| **Visual** | `report-weekly/Images/rmse_bar.png` or `report-weekly/Images/figures/rmse_comparison_bar.png` + `report-weekly/Images/pipeline_timing.png` (or `report-weekly/Images/figures/pipeline_timing.png`) |

**Key points (seed=42, authoritative `tests/benchmark_rmse.py`):**

- Pedestrian: raw 0.48 m / alpha-beta **0.26 m** / Kalman 0.86 m.
- Motorcycle-kinematic: 1.89 / **1.02** / 1.80 m; **Motorcycle-road (deployed default): 2.14 / 1.14 / 1.52 m**.
- Drone: 1.94 / **1.06** / 2.10 m; altitude panel `report-weekly/Images/altitude_drone.png` shows 3D tracking (30-75 m).
- Alpha-beta is consistently best on RMSE; pipeline **59 µs** leaves ~99.94 ms headroom at 10 Hz — not a bottleneck.

---

## Slide 10 — Robustness — Multi-Seed Statistics

| Field | Value |
|-------|-------|
| **Time** | 1:20 (12:50-14:10) |
| **Speaker** | **TBD** |
| **Visual** | `report-weekly/Images/multi_seed_rmse_spec.png` or `report-weekly/Images/figures/multiseed_rmse.png` |

**Key points (`tests/statistical_analysis.py`, seeds 1-10, 120 s, 10 Hz):**

- All scenarios **PASS spec (< 5.0 m)** across seeds 1-10 — 9 scenarios x 10 seeds = 90 runs.
- Pedestrian AB: mean 0.34 m, std 0.08 m (min 0.21, max 0.30 m in table; full 10-seed sweep confirms stability).
- Motorcycle has highest variance (random acceleration), drone most stable; std values in `docs/09-statistical-analysis.md` table.
- Message: single-seed numbers are not cherry-picked; distribution is tight enough for deployment claims.

---

## Slide 11 — Ablation & Diagnostics

| Field | Value |
|-------|-------|
| **Time** | 1:20 (14:10-15:30) |
| **Speaker** | **TBD** |
| **Visual** | `report-weekly/Images/error_cdf.png` (or `report-weekly/Images/figures/error_cdf_*` per target) + `report-weekly/Images/error_timeseries.png` + `report-weekly/Images/figures/mode_comparison.png` |

**Key points:**

- **Filter ablation**: raw vs AB vs Kalman per target — AB smooths without lag, Kalman trades early error for later confidence; CDF shows AB dominates at P50/P90.
- **Trajectory ablation**: synthetic vs Geolife/road-network — real data adds micro-maneuvers (turns at intersections, gait pauses) that synthetic underestimates; hence road-network is default for motorcycle.
- **Alpha sweep**: `alpha_sensitivity.png` — pedestrian optimum 0.2, but 0.4 is the shared default to avoid overfitting one regime; per-target tuning is future work.
- Time-series `error_ts_*` confirms convergence: Kalman error drops after ~5-10 s, then tracks AB within 0.3-0.5 m.

---

## Slide 12 — Limitations (honest)

| Field | Value |
|-------|-------|
| **Time** | 1:00 (15:30-16:30) |
| **Speaker** | **TBD** |
| **Visual** | `report-weekly/Images/error-prop.png` (error budget) + one trajectory still with small overshoot |

**Key points:**

- Pedestrian filtering looks "stationary" — not a bug: **0.14 m/step vs 5 m GPS sigma** (SNR ~0.028); both filters correctly smooth; real fix is **RTK-GPS (cm-level)**, not a better filter.
- Constant-velocity Kalman is intentionally linear — EKF/UKF unnecessary here; would matter only for coordinated-turn or acceleration models.
- Road-network loader depends on `hcmc_roads.graphml` (102.5 MB) and `osmnx`/`networkx`; offline fallback is the old bicycle kinematic model — less realistic.
- In-memory sessions: no persistence, no multi-observer fusion, no occlusion handling yet.

---

## Slide 13 — Future Work — Hardware Path

| Field | Value |
|-------|-------|
| **Time** | 1:20 (16:30-17:50) |
| **Speaker** | **TBD** |
| **Visual** | `raspberry_pi/README.md` wiring diagram (photo if available) + `report-weekly/Images/real-time-data-pipeline.png` with RPi block highlighted |

**Key points:**

- **Raspberry Pi stub** `raspberry_pi/sensor_client.py` — WebSocket client ready; all `[HARDWARE]` tags mark sim-to-real replacement points.
- Hardware plan: RPi + GNSS (RTK), IMU (BNO055-class), laser rangefinder -> `ws://` to server; same `fuse_sensors()` + filter chain, no API change.
- Next steps: field calibration for IMU bias, laser mounting alignment, time sync (PTP/NTP), and logging `hcmc_roads.graphml` traces for replay.
- Simulation remains the validation harness until hardware arrives — no hardware-specific code is modified until physical devices are in hand (per `AGENTS.md`).

---

## Slide 14 — Lessons Learned

| Field | Value |
|-------|-------|
| **Time** | 1:00 (17:50-18:50) |
| **Speaker** | **TBD** |
| **Visual** | `docs/lessons-learned.md` excerpt (3 bullets) + `report-weekly/Images/figures/mode_comparison.png` |

**Key points:**

- **Realism > complexity**: fixing 6 trajectory/boundary/init issues beat adding a fancier filter — 0.2-0.3 m RMSE gain from data hygiene alone.
- **Measure before optimizing**: 59 µs profiling showed Kalman is not the bottleneck; effort went to data loaders and boundary logic instead.
- **Reproducibility is a feature**: seeded RNG (`np.random.default_rng(seed)`), `benchmark_rmse.py` as single source of truth, and `statistical_analysis.py` (10 seeds) prevented "lucky seed" claims.
- Process: 162 tests (pytest, `backend/` CWD), `ruff` 0 errors, `npm run lint` clean, 5-pass pdfLaTeX — CI discipline kept the report honest (see `AUDIT_REPORT.md`).

---

## Slide 15 — Q&A

| Field | Value |
|-------|-------|
| **Time** | 1:10 (18:50-20:00) + overflow 5-10 min |
| **Speaker** | **Both** (see split below) |
| **Visual** | Title slide repeat + QR to `http://localhost:5173` + Swagger `/docs` + `docs/10-demo-guide.md` FAQ |

**Key points (anticipated questions — from `docs/10-demo-guide.md` + `defense-prep/`):**

- *Why does Kalman lose to alpha-beta?* — Convergence of `P`; after ~50 steps instantaneous error is comparable (0.3-0.5 m); Kalman still needed for uncertainty.
- *794 m crossover?* — Where GPS sigma equals IMU angular error x range; determines laser vs GPS dominance.
- *Why not EKF/UKF?* — Model is linear (constant velocity); nonlinear filters add cost without benefit.
- *Where is the hardware?* — Sim is the validation environment; `raspberry_pi/` stub + `[HARDWARE]` tags are the handoff; no premade hardware claims.

---

## Appendix (backup slides — not timed, use if asked)

| # | Title | Visual |
|---|-------|--------|
| A1 | Geodetics — WGS84/ECEF/ENU math | `report-weekly/Images/coord-flow.png`, `report-weekly/Images/error-prop.png` |
| A2 | Per-target observer coordinates | Table from `AGENTS.md` (Ben Thanh / Ham Nghi / Phu My Hung) |
| A3 | Full 10-seed table | `docs/09-statistical-analysis.md` + `report-weekly/Images/figures/multiseed_rmse.png` |
| A4 | Pedestrian SNR calculation | 1.4 m/s / 10 Hz = 0.14 m/step vs 5 m sigma -> SNR 0.028 |
| A5 | Demo fallback screenshots | `report-weekly/Images/sim/*.png`, `report-weekly/Images/figures/trajectory_*.png`, `report-weekly/Images/figures/error_ts_*.png`, `report-weekly/Images/figures/altitude_drone-kf_ab-synthetic.png` |

---

## Chia phần cho 2 thành viên (TBD)

> **Trạng thái hiện tại: chưa phân công.** Tất cả slide trên để `Speaker: TBD` để dễ kéo-thả. Dưới đây là **đề xuất chia** — giữ nguyên nếu hợp lý, hoặc hoán đổi bằng cách sửa cột `Speaker` (không cần đụng tới `Time` hay `Visual`).

### Phương án đề xuất (cân bằng thời gian ~10:00 / 10:00)

| Người | Slide | Nội dung | Tổng thời gian |
|-------|-------|----------|----------------|
| **Member A — Lý thuyết & Kiến trúc** | 1 (chung), 2, 3, 4, 5, 6 | Title (mở đầu) + Problem + Architecture + Coordinate/Fusion + Trajectory Realism + Kalman vs Alpha-Beta | ~08:10 (nếu chia đôi slide 1) |
| **Member B — Triển khai & Đánh giá** | 7, 8, 9, 10, 11, 12, 13, 14 | Road Network & Datasets + **Live Demo** (điều khiển) + Performance + Robustness + Ablation + Limitations + Future Work + Lessons | ~10:40 (nặng hơn do Demo 2:00) |
| **Cả hai** | 1, 15 | Mở đầu (mỗi người 30 s tự giới thiệu) + **Q&A** (cả hai trả lời; A lo thuật toán/kiến trúc, B lo dữ liệu/demo/kết quả) | ~02:10 |

**Biến thể nếu muốn cân bằng chính xác 10/10:**

- Chuyển **Slide 7 (Road Network, 1:10)** sang Member A -> A ~09:20, B ~09:30 (còn lại Q&A chung).
- Hoặc để Member A demo phần **Static Calculator** trong Slide 8 (30 s), Member B demo **Tracking** (90 s) — vẫn trong 2:00.

### Gợi ý trả lời Q&A theo thế mạnh

| Loại câu hỏi | Người trả lời chính | Người hỗ trợ |
|--------------|---------------------|--------------|
| Thuật toán (Kalman, alpha-beta, RSS, crossover 794 m, EKF/UKF) | Member A | Member B bổ sung số liệu benchmark |
| Kiến trúc hệ thống (FastAPI, WebSocket `/ws/tracking/{id}`, Vite proxy, session/ring buffer) | Member A | Member B demo lại nếu cần |
| Dữ liệu & mô phỏng (Geolife, AMIT, HCMC graph, 6 fixes Tuan 10, random start) | Member B | Member A bổ sung refs học thuật |
| Kết quả & độ tin cậy (RMSE, multi-seed, ablation, alpha sensitivity) | Member B | Member A giải thích ý nghĩa thống kê |
| Phần cứng & tương lai (RPi, `[HARDWARE]` tags, RTK-GPS) | Member B | Member A nói về kiến trúc không đổi khi thay sensor thật |

### Cách đổi phân công (30 giây)

1. Tìm slide cần đổi trong bảng trên.
2. Sửa `Speaker: TBD` -> `Speaker: Member A` hoặc `Member B`.
3. Cập nhật bảng tổng hợp ở mục này cho khớp — không cần sửa `Time` hay `Visual`.

---

## Ghi chú trình bày (PowerPoint -> Beamer)

- **PowerPoint là bản chính**: dùng theme HCMUT (xanh dương + trắng, logo `hcmut.png`), font sans-serif, 16:9.
- **Chuyển sang Beamer khi cần nộp**: `report-weekly/main.tex` đã cấu hình `graphicspath` nên `\includegraphics{figures/file.png}` hoạt động; giữ label tiếng Anh trong TikZ/figure caption; dùng `[htbp]` cho float, `\texorpdfstring` cho tiêu đề có toán, `\hspace{0.5cm}` sau subsection — theo `AGENTS.md` / `RULES/RULES.md`.
- Mỗi slide PowerPoint nên có **footer nhỏ**: `GPS Target Calculating System — Defense 2026 | Seed 42 | 10 Hz | 400 m boundary` để giám khảo luôn thấy điều kiện đánh giá.
- In handout: 6 slide/trang, có số trang; mang bản in `AUDIT_REPORT.md` tóm tắt số liệu để đối chiếu khi bị hỏi số.

---

*File này là outline — không phải slide hoàn chỉnh. Tạo slide PowerPoint từ outline này, mỗi slide lấy `Visual` làm hình nền/chính và `Key points` làm bullet nói (không copy nguyên văn lên slide; slide chỉ 3-5 từ khóa/bullet ngắn, lời nói mới đầy đủ).*
