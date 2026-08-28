# GPS Target Calculating System

**Real-Time Moving Target Tracking and Geolocation Using Laser-IMU-GNSS Fusion**

Đề tài tốt nghiệp - Khoa Kỹ thuật Máy tính, HCMUT  
Giảng viên hướng dẫn: TS. Võ Tuấn Bình

---

## Tổng quan

Hệ thống theo dõi và tính toán tọa độ mục tiêu di động theo thời gian thực, dựa trên dữ liệu hợp nhất từ GPS, góc ngắm (azimuth/elevation) và laser rangefinder. Hệ thống bao gồm hai giai đoạn phát triển:

- **Giai đoạn 1** - Tính toán tọa độ đơn điểm từ GPS + góc ngắm + khoảng cách (2D).
- **Giai đoạn 2** - Theo dõi mục tiêu di động trong không gian 3D với bộ lọc Kalman và α-β, mô phỏng quỹ đạo người đi bộ, xe máy, và drone.

---

## Kiến trúc hệ thống

```
┌─────────────────────────────────────────────────────────┐
│                     Frontend (React)                    │
│  TrackingPage -> TrackingMap (Leaflet) + Charts (CJ2)    │
│  SimulationPanel -> REST POST /api/simulation/start      │
│  WebSocket consumer -> cập nhật store mỗi 100ms          │
└────────────────────┬────────────────────────────────────┘
                     │ WebSocket ws://localhost:8000/ws/tracking/{id}
┌────────────────────▼────────────────────────────────────┐
│                  Backend (FastAPI)                      │
│  SimulationEngine -> TrajectoryGenerator                 │
│                   -> SensorNoiseModel                    │
│                   -> SensorFusion                        │
│                   -> KalmanFilter / KalmanFilter3D       │
│                   -> AlphaBetaFilter                     │
│                   -> SimulationBoundary                  │
└─────────────────────────────────────────────────────────┘
```

---

## Cấu trúc dự án

```
GPS-Target-Calculating-System/
├── backend/
│   ├── app/
│   │   ├── algorithms/
│   │   │   ├── geodetics.py        # Chuyển đổi ENU <-> LLA, haversine
│   │   │   ├── kalman_filter.py    # KalmanFilter (2D) + KalmanFilter3D
│   │   │   ├── alpha_beta_filter.py
│   │   │   └── sensor_fusion.py    # GPS + IMU + Laser fusion
│   │   ├── simulation/
│   │   │   ├── target_simulator.py # Trajectory generators + SimulationEngine
│   │   │   ├── boundary.py         # Circular boundary constraint
│   │   │   └── sensor_noise.py     # Noise models per target type
│   │   ├── routers/
│   │   │   ├── calculator.py       # POST /api/calculate
│   │   │   └── simulation.py       # POST /api/simulation/start + WebSocket
│   │   ├── models/schemas.py
│   │   └── main.py
│   ├── tests/                      # 162 pytest tests
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── pages/TrackingPage.jsx
│   │   ├── components/
│   │   │   ├── charts/             # ErrorMetricsChart, AltitudeChart
│   │   │   ├── controls/           # SimulationPanel, LayerControl
│   │   │   ├── map/TrackingMap.jsx
│   │   │   └── ui/CoordDisplay.jsx
│   │   ├── store/trackingStore.js  # Zustand global state
│   │   └── hooks/useWebSocket.js
│   └── package.json
└── README.md
```

---

## Yêu cầu hệ thống

| Thành phần | Phiên bản |
|---|---|
| Python | 3.11+ |
| Node.js | 20.19+ (yêu cầu của Vite 8) |
| npm | 9+ |

---

## Cài đặt và chạy

### Backend

Yêu cầu: Python 3.11+ và [uv](https://docs.astral.sh/uv/).

```bash
cd backend
uv sync --group dev        # tạo venv + cài dependencies
uv run uvicorn app.main:app --reload --port 8000
```

API sẽ khởi động tại `http://localhost:8000`.  
Swagger docs: `http://localhost:8000/docs`

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend sẽ chạy tại `http://localhost:5173` và tự proxy API/WebSocket sang port 8000.

---

## Chạy tests

```bash
cd backend
uv run pytest tests/ -v
```

Kết quả hiện tại: **162 tests passed**.

Các nhóm test bao gồm:
- `TestPedestrianTrajectory` - kiểm tra tốc độ, pause, waypoint navigation
- `TestMotorcycleTrajectory` - state machine STRAIGHT/TURNING
- `TestMotorcycleNoCrash` - chạy 600 bước với 7 seed khác nhau
- `TestDroneBoundary` - drone ở trong boundary, altitude không bị clamped
- `TestSimulationBoundary` - reflection geometry
- `TestKalmanFilter3D` - convergence, covariance, altitude tracking
- `TestAdaptiveR2D` - adaptive measurement noise
- `TestBoundaryRadiusSchema` - Pydantic validation [100, 1000]m

---

## Thuật toán

### 1. Sensor Fusion
Hợp nhất góc ngắm (azimuth, elevation) và khoảng cách từ laser rangefinder:

```
ENU = polar_to_enu(azimuth, elevation, range)
σ_pos = f(range)   # sai số tăng theo khoảng cách
```

### 2. Kalman Filter (2D - Pedestrian/Motorcycle)
State vector: `[East, North, vEast, vNorth]`

Adaptive measurement noise: `R = σ_pos² × I` - filter tự điều chỉnh độ tin cậy dựa trên chất lượng đo.

### 3. KalmanFilter3D (Drone)
State vector: `[East, North, Up, vEast, vNorth, vUp]`

Theo dõi độ cao độc lập với chuyển động ngang, phù hợp cho drone.

### 4. α-β Filter
Bộ lọc tham số cố định, đơn giản hơn Kalman, dùng để so sánh hiệu năng.

### 5. Trajectory Models

| Loại | Mô hình | Tốc độ |
|---|---|---|
| Người đi bộ | Waypoint navigation - di chuyển đến đích ngẫu nhiên, dừng lại, chọn đích mới | 1.0–1.8 m/s |
| Xe máy | State machine STRAIGHT -> TURNING -> STRAIGHT với bán kính cua 15–40m | 7–13 m/s |
| Drone | Waypoint patrol - ngắm đến waypoint ngẫu nhiên, altitude sin ±20m | 7–15 m/s |

---

## Giao diện web

### Màn hình chính

- **Sidebar trái** - cấu hình mô phỏng: vị trí quan sát viên, loại mục tiêu, thuật toán, thời lượng, bán kính ranh giới
- **Bản đồ trung tâm** (Leaflet) - hiển thị quỹ đạo 4 lớp: ground truth (xanh lá), raw measurement (vàng), Kalman (xanh dương), α-β (tím)
- **Biểu đồ RMSE** - sai số theo thời gian (Kalman vs α-β vs raw)
- **Biểu đồ Altitude** - độ cao ground truth vs Kalman (chỉ hiển thị khi chọn Drone)
- **Sidebar phải** - tọa độ tức thời, tốc độ, độ không chắc chắn, góc pan-tilt

### Layer control
Toggle hiển thị từng lớp quỹ đạo độc lập để so sánh trực quan.

---

## API

### POST `/api/simulation/start`
Khởi động phiên mô phỏng mới.

```json
{
  "observer_lat": 10.762622,
  "observer_lon": 106.660172,
  "observer_alt": 10.0,
  "target_type": "motorcycle",
  "algorithm": "both",
  "duration_s": 120.0,
  "update_rate_hz": 10.0,
  "alpha": 0.4,
  "seed": null,
  "boundary_radius_m": 400.0
}
```

Trả về `session_id` và `ws_url` để kết nối WebSocket.

### WebSocket `/ws/tracking/{session_id}`
Stream dữ liệu JSON mỗi `1/update_rate_hz` giây:

```json
{
  "step": 42,
  "ground_truth": { "lat": 10.763, "lon": 106.661, "alt": 10.0 },
  "kalman":       { "lat": ..., "lon": ..., "up": ..., "speed": 9.8, "uncertainty_m": 3.2 },
  "alpha_beta":   { "lat": ..., "lon": ..., "speed": 9.5 },
  "pan_tilt":     { "azimuth": 45.2, "elevation": 1.8, "range": 312.0 },
  "metrics":      { "kalman_rmse": 2.1, "alpha_beta_rmse": 4.3, "raw_error": 6.7 }
}
```

### POST `/api/calculate`
Tính tọa độ đơn điểm từ GPS + góc ngắm + khoảng cách.

---

## Hạn chế kỹ thuật của mô phỏng

### Tại sao mục tiêu không chuyển động hoàn toàn như thực tế?

Hệ thống chưa kết nối được phần cứng thật (laser rangefinder + IMU + GPS), nên dữ liệu đầu vào của chuỗi xử lý là mô phỏng. Trong phạm vi đó, các nguồn thay thế đã được triển khai:

#### Những gì đã có
- **Dữ liệu đi bộ thực**: 252 phân đoạn từ bộ dữ liệu Geolife (Microsoft Research), nội suy PCHIP lên 10 Hz, replay hai chiều không nhảy vị trí.
- **Xe máy trên đường phố thực**: quỹ đạo random-walk trên mạng đường Hồ Chí Minh City (337K nút từ OSM), điều hướng theo tốc độ từng loại đường.
- **Ranh giới mềm**: lực đẩy thế năng thay cho phản xạ gương, tránh dao động bi-a tại mép vùng.
- **Drone đúng giới hạn khí động**: gia tốc/vận tốc bám thông số DJI Matrice 100.

#### Những gì còn hạn chế
1. **Chưa có hardware thật**: mọi đo lường đều là mô phỏng xấp xỉ; sai số cảm biến thực (drift IMU, multipath GPS) chỉ được xấp xỉ bằng nhiễu.
2. **Nhiễu Gaussian**: noise model dùng phân phối chuẩn, trong khi nhiễu thực tế có multipath (GPS phản xạ tòa nhà), scintillation (laser trong mưa), và bias drift theo nhiệt độ.
3. **Người đi bộ synthetic** vẫn là waypoint ngẫu nhiên tương đối vị trí hiện tại, thiếu yếu tố môi trường (tường, vỉa hè, đám đông).

#### Bước tiếp theo
Khi có phần cứng: thay module sinh dữ liệu bằng client thu thập thật (xem `raspberry_pi/`), giữ nguyên toàn bộ chuỗi xử lý phía sau.

---

## Kết quả đánh giá

Theo đặc tả đề tài (sai số < 5m ở cự ly < 1km), kết quả từ benchmark_rmse.py (seed=42, 120s, 10Hz, boundary=400m):

| Kịch bản | Đo thô | α-β RMSE | Kalman RMSE | Đạt spec |
|---|---|---|---|---|
| Người đi bộ | 0,48 m | 0,26 m | 0,86 m | ✅ |
| Xe máy | 1,89 m | 1,02 m | 1,80 m | ✅ |
| Drone (3D) | 1,94 m | 1,06 m | 2,10 m | ✅ |

---

## Công nghệ sử dụng

**Backend**
- Python 3.11 + FastAPI + Uvicorn
- NumPy, SciPy
- Pydantic v2
- pytest (162 tests)

**Frontend**
- React 19 + Vite 8
- Zustand (state management)
- React-Leaflet (bản đồ)
- Chart.js + react-chartjs-2 (biểu đồ)
- React Router v6

---

## Tác giả

Nhóm sinh viên thực hiện - Khoa Kỹ thuật Máy tính, HCMUT  
Giảng viên hướng dẫn: TS. Võ Tuấn Bình
