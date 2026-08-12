# Backend (FastAPI)

## Thiết lập

```bash
cd backend
uv sync --group dev          # Lần đầu: tạo venv + cài deps
uv run uvicorn app.main:app --reload --port 8000
```

Swagger UI: `http://localhost:8000/docs`

## Cấu trúc dự án

```
backend/
├── app/
│   ├── main.py              # Ứng dụng FastAPI, CORS, gắn router
│   ├── algorithms/
│   │   ├── kalman_filter.py     # KalmanFilter (2D) + KalmanFilter3D
│   │   ├── alpha_beta_filter.py # AlphaBetaFilter
│   │   ├── geodetics.py         # Chuyển đổi WGS84 ↔ ECEF ↔ ENU
│   │   └── sensor_fusion.py     # fuse_sensors() — kết hợp RSS
│   ├── models/
│   │   └── __init__.py          # Schema Pydantic v2
│   ├── routers/
│   │   ├── simulation.py        # REST + WebSocket endpoints
│   │   └── calculator.py        # Máy tính tĩnh đơn điểm
│   └── simulation/
│       ├── target_simulator.py  # Tạo quỹ đạo (3 loại)
│       ├── sensor_noise.py      # Mô hình nhiễu Gaussian
│       ├── data_loaders.py      # Geolife, AMIT, RoadNetwork loaders
│       └── boundary.py          # Ranh giới hình tròn
├── tests/                       # 163 test
├── scripts/                     # Script tiện ích
├── pyproject.toml               # Deps + cấu hình (nguồn gốc)
└── requirements.txt             # Chỉ tham khảo
```

## REST API Endpoints

| Phương thức | Đường dẫn | Mô tả |
|-------------|-----------|-------|
| POST | `/api/simulation/start` | Tạo phiên mới, trả về `session_id` + `ws_url` |
| POST | `/api/simulation/stop/{id}` | Dừng phiên, dọn dẹp |
| GET | `/api/simulation/sessions` | Liệt kê phiên đang hoạt động |
| GET | `/api/simulation/stats/{id}` | Thống kê RMSE/khung theo phiên |
| GET | `/api/simulation/export/{id}` | StreamingResponse CSV |
| POST | `/api/calculate` | Máy tính tĩnh đơn điểm |

## WebSocket

**Đường dẫn**: `/ws/tracking/{session_id}` (gắn tại gốc, KHÔNG phải `/api`)

**Tại sao ở gốc?** Middleware CORS của FastAPI không áp dụng cho WebSocket upgrade. Frontend proxy qua Vite thay thế.

**Giao thức**:
```json
// Client → Server (dữ liệu cảm biến)
{
  "timestamp": 1720000123.456,
  "gps": {"lat": 10.762622, "lon": 106.660172, "alt": 15.0},
  "imu": {"azimuth": 45.2, "elevation": 2.1},
  "laser": {"distance": 312.5}
}

// Server → Client (kết quả xử lý)
{
  "timestamp": 1720000123.456,
  "target": {"lat": 10.764150, "lon": 106.662830, "alt": 22.1},
  "kalman": {"lat": 10.764135, "lon": 106.662812, "alt": 22.0},
  "alphabeta": {"lat": 10.764142, "lon": 106.662821},
  "uncertainty_m": 3.2,
  "step": 142
}
```

## Quản lý phiên

- Phiên lưu trong dict `_sessions` (chỉ trong bộ nhớ)
- Trạng thái bộ lọc (x, P) được giữ trong bộ nhớ suốt phiên
- Vòng đệm `_frames` lưu các khung gần nhất cho `/stats` và `/export`
- Đóng WS kích hoạt dọn dẹp

## Các lớp chính

### SimulationEngine
- Quản lý vòng lặp mô phỏng (tạo quỹ đạo → nhiễu cảm biến → hợp nhất → lọc)
- Chạy trong async task, đẩy khung vào vòng đệm
- Tính RMSE so với ground truth

### Tạo quỹ đạo
- `PedestrianTrajectory`: Random walk với drift hướng, 0,8-1,5 m/s
- `MotorcycleTrajectory`: Máy trạng thái (điều khiển/rẽ), 5-15 m/s
- `DroneTrajectory`: 3D sinusoidal + hình tròn, độ cao thay đổi

### SensorNoiseModel
- Thêm nhiễu Gaussian cho GPS (5m), IMU azimuth (0,3°), elevation (0,2°), laser (0,5m)
- Sử dụng `np.random.default_rng(seed)` để tái tạo

### Boundary
- Ranh giới hình tròn tâm tại observer
- Bán kính bị ràng buộc [100, 1000] m qua Pydantic
- Quỹ đạo phản xạ tại ranh giới (xe máy) hoặc bị chặn (người đi bộ)
- Drone: ngang bị ràng buộc, độ cao tự do

## Phụ thuộc (pyproject.toml)

- FastAPI 0.115+
- NumPy, SciPy
- Pydantic v2 (model_config = ConfigDict)
- websockets
- osmnx, networkx (road network for motorcycle trajectories)
- pytest, pytest-asyncio (dev)
- ruff (dev, linter)

## Quy tắc

- Pydantic v2: `model_config = ConfigDict(...)` (KHÔNG dùng `class Config` cũ)
- Kalman `update()`: `np.linalg.solve` (KHÔNG dùng `np.linalg.inv`)
- `fuse_sensors()` là hàm cấp module, KHÔNG phải lớp
- Lớp `SensorFusion` trong models dùng cho schema, không phải tính toán
- Không có linter/formatter, không CI, không pre-commit hooks
