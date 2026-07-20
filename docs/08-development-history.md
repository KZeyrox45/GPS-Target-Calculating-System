# Development History

## Phase 1 (Static Calculator)
- Vanilla JS single-point calculator
- Haversine + trigonometric target calculation
- Static HTML/CSS, no build step
- Archived in `phase1/`

## Phase 2 (Real-Time Tracking)

### Week 1: Planning
- Problem definition: moving target tracking
- Architecture design: 4 layers
- Technology selection: FastAPI, React, WebSocket

### Week 2: Architecture
- Detailed system design
- Raspberry Pi integration plan
- Class diagrams and activity diagrams

### Week 3: Algorithms
- Coordinate conversion pipeline (WGS84 → ECEF → ENU)
- Error propagation analysis (RSS formula)
- Kalman filter implementation (2D + 3D)
- Alpha-beta filter with Benedict-Bordner formula
- Cross-over range calculation (794 m)

### Week 4: Simulation
- Monte Carlo simulation engine
- 3 trajectory types (pedestrian, motorcycle, drone)
- RMSE evaluation: all scenarios pass <5m spec
- Alpha-beta outperforms Kalman in CV simulation

### Week 5: Real-Time Pipeline
- WebSocket integration
- Session management
- Ring buffer (500 points)
- UI performance optimization (59 µs pipeline)
- Layer control and uncertainty visualization

### Week 6: Data Export & Analysis
- CSV export endpoint (StreamingResponse)
- RMSE convergence analysis
- Error histogram visualization
- Negative elevation edge case verification

### Code Quality Audit (Latest)
- Full Ruff scan: 153 → 7 remaining (E402 in scripts, intentional)
- Full ESLint scan: 0 warnings
- Removed unused imports across 10 files
- Fixed AI-pattern `--` in docstrings
- Fixed Vietnamese mixing ("âm" → "negative")
- Removed 105 semicolons (E702) in scripts
- Removed 8 f-strings without placeholders (F541)
- Split 6 multi-imports (E401)
- Fixed 1 ambiguous variable name (E741)
- Fixed import ordering (E402) in test_simulation_phase2.py
- Fixed ESLint: removed `setFps` from useCallback dependency

## File Inventory

### Backend Python (27 files)
```
backend/app/__init__.py
backend/app/main.py
backend/app/algorithms/__init__.py
backend/app/algorithms/alpha_beta_filter.py
backend/app/algorithms/geodetics.py
backend/app/algorithms/kalman_filter.py
backend/app/algorithms/sensor_fusion.py
backend/app/models/__init__.py
backend/app/routers/calculator.py
backend/app/routers/simulation.py
backend/app/simulation/__init__.py
backend/app/simulation/boundary.py
backend/app/simulation/sensor_noise.py
backend/app/simulation/target_simulator.py
backend/tests/test_alpha_beta.py
backend/tests/test_geodetics.py
backend/tests/test_kalman.py
backend/tests/test_sensor_fusion.py
backend/tests/test_simulation_phase2.py
backend/tests/test_stats_endpoint.py
backend/tests/benchmark_rmse.py
backend/scripts/audit_and_generate.py
backend/scripts/generate_figures.py
backend/scripts/ws_smoke.py
```

### Frontend JS/JSX (17 files)
```
frontend/src/main.jsx
frontend/src/App.jsx
frontend/src/App.css
frontend/src/index.css
frontend/src/pages/HomePage.jsx
frontend/src/pages/TrackingPage.jsx
frontend/src/pages/StaticCalcPage.jsx
frontend/src/pages/ComparisonPage.jsx
frontend/src/components/charts/AltitudeChart.jsx
frontend/src/components/charts/ErrorMetricsChart.jsx
frontend/src/components/controls/SimulationPanel.jsx
frontend/src/components/controls/LayerControl.jsx
frontend/src/components/map/TrackingMap.jsx
frontend/src/components/map/TargetMarker.jsx
frontend/src/components/map/TrajectoryPolyline.jsx
frontend/src/components/ui/CoordDisplay.jsx
frontend/src/components/ui/StatusBar.jsx
frontend/src/store/trackingStore.js
frontend/src/hooks/useWebSocket.js
```

### Report LaTeX (6 weeks)
```
report-weekly/Contents/week-1.tex through week-6.tex
report-weekly/main.tex
```
