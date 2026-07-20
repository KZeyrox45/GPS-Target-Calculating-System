# Report Content Explanation (Weeks 1-6)

## Week 1: Introduction & Problem Statement

### Content
- **Problem**: Track moving targets using Laser-IMU-GNSS sensor fusion
- **Phase 1 recap**: Single-point static calculator (Haversine-based)
- **Phase 2 expansion**: Real-time tracking with filtering and WebSocket

### Key Concepts Introduced
- 4-layer architecture (Sensor → Embedded → Server → Frontend)
- Sensor characteristics: GPS (2-5m accuracy, 1-10 Hz), IMU (100-1000 Hz, drifts), Laser (±1-2 cm, LOS only)
- Body frame coordinate system and rotation matrix
- Kalman filter basics (state vector, F matrix)
- Alpha-beta filter basics (α, β parameters)

### Figures
- Use-case diagram (`Images/use-case-diagram.png`)

## Week 2: System Architecture

### Content
- Detailed 4-layer architecture with component descriptions
- Data flow from sensor to frontend
- Raspberry Pi embedded design (UART/I2C/SPI connections)
- FastAPI server design (REST + WebSocket)
- React frontend design (Leaflet maps)

### Key Concepts
- WebSocket vs HTTP polling (full-duplex, persistent connection)
- Session lifecycle (start → WS loop → stop)
- Class diagram of software components

### Figures
- Architecture diagram (TikZ)
- Class diagram (`Images/class-diagram.png`)
- Activity diagrams (processing + tracking)

## Week 3: Coordinate Pipeline & Error Analysis

### Content
- **Coordinate conversion pipeline**: WGS84 → ECEF → ENU → target → WGS84
- **Error propagation**: RSS formula for σ_pos
- **Sensor noise parameters** (1-sigma values)
- **Cross-over range calculation** (794 m)
- **Kalman filter structure**: F, Q (DWNA), adaptive R
- **Alpha-beta filter**: Benedict-Bordner critically damped formula

### Key Formulas
- RSS: `σ_pos² = σ_gps² + (R·sin(σ_az))² + σ_range² + (R·sin(σ_el))²`
- Cross-over: `R_cross = σ_gps / √(sin²(σ_az) + sin²(σ_el))`
- Beta: `β = (2-α) - 2√(1-α)`

### Tables
- Sensor noise parameters
- σ_a values per target type
- Kalman vs Alpha-beta comparison

### Figures
- Coordinate flow diagram (`Images/coord-flow.png`)
- Error propagation chart (`Images/error-prop.png`)
- Kalman detail diagram (`Images/kalman-detail.png`)

## Week 4: Simulation Results

### Content
- **Simulation setup**: 400m boundary, 120s, 10 Hz, seed=42
- **RMSE results**: All 3 scenarios pass <5m spec
- **Alpha-beta outperforms Kalman** in this CV simulation (expected)
- **Kalman advantages**: Uncertainty estimate (P matrix), adaptive R
- **Error vs distance analysis**: σ_pos(R) curve

### Key Results
| Scenario | Raw | Alpha-Beta | Kalman |
|----------|-----|-----------|--------|
| Pedestrian | 0.46 m | 0.24 m | 0.84 m |
| Motorcycle | 1.79 m | 1.01 m | 2.18 m |
| Drone | 1.28 m | 0.73 m | 2.33 m |

### Figures
- RMSE bar chart (TikZ/pgfplots)
- Sigma vs range curve (TikZ/pgfplots)

## Week 5: Real-Time Pipeline & UI

### Content
- **Real-time data flow**: Sensor → WS → Server → Filter → WS → Frontend
- **WebSocket protocol**: JSON message formats (upstream + downstream)
- **Session management**: In-memory, ring buffer N_max=500
- **UI performance**: ~3ms WS latency, ~8ms render, ~4% CPU
- **Layer control**: 3 trajectory layers (raw/kalman/alphabeta) + uncertainty circle
- **Pipeline timing**: 59 µs total, Kalman dominates at 82%

### Key Numbers
- WebSocket latency: ~3 ms (server → browser)
- Render time: ~8 ms/frame
- Total trajectory points: 3 × 500 = 1500
- Leaflet memory: ~2.1 MB
- CPU usage: ~4%

### Tables
- WebSocket vs HTTP comparison
- Session lifecycle
- UI performance metrics
- Pipeline timing breakdown

### Figures
- Real-time data pipeline (`Images/real-time-data-pipeline.png`)
- Error over time (TikZ/pgfplots)

## Week 6: Data Export & Post-Session Analysis

### Content
- **CSV export**: StreamingResponse, 19 columns, ~120 KB per session
- **RMSE convergence curve**: Shows filter initialization phase
- **Error decomposition by axis**: East vs North symmetry
- **Error histogram**: Alpha-beta concentrated near 0, Kalman wider (convergence tail)
- **Negative elevation handling**: Mathematical proof + verification table

### Key Insights
- Kalman convergence takes ~50-100 timesteps (5-10 seconds)
- Alpha-beta: 93% of errors within 0-0.4 m
- Kalman: wider distribution due to initial P matrix instability
- polar_to_enu() handles negative elevation correctly without branching

### Tables
- CSV schema (19 columns)
- Error by axis (σ_E, σ_N)
- Negative elevation test results

### Figures
- RMSE convergence (TikZ/pgfplots)
- Error histogram (TikZ/pgfplots)

## Overall Report Structure

```
main.tex (master)
├── week-1.tex  — Introduction, problem statement, theory
├── week-2.tex  — Architecture, data flow, Raspberry Pi
├── week-3.tex  — Coordinate pipeline, error analysis, filters
├── week-4.tex  — Simulation results, RMSE evaluation
├── week-5.tex  — Real-time pipeline, WebSocket, UI
└── week-6.tex  — Data export, post-analysis, edge cases
```

Compiler: pdfLaTeX (Overleaf). BibTeX for references. 3-pass compilation for cross-references.
