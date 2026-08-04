# Lịch sử phát triển

## Giai đoạn 1 (Má tính tĩnh)
- Máy tính điểm đơn JavaScript thuần
- Tính mục tiêu Haversine + trigonometric
- HTML/CSS tĩnh, không build
- Lưu trữ trong `phase1/`

## Giai đoạn 2 (Theo dõi thời gian thực)

### Tuần 1: Lập kế hoạch
- Xác định bài toán: theo dõi mục tiêu di chuyển
- Thiết kế kiến trúc: 4 tầng
- Lựa chọn công nghệ: FastAPI, React, WebSocket

### Tuần 2: Kiến trúc
- Thiết kế hệ thống chi tiết
- Kế hoạch tích hợp Raspberry Pi
- Sơ đồ lớp và sơ đồ hoạt động

### Tuần 3: Thuật toán
- Pipeline chuyển đổi tọa độ (WGS84 → ECEF → ENU)
- Phân tích lan truyền sai số (công thức RSS)
- Cài đặt Kalman filter (2D + 3D)
- Alpha-beta filter với công thức Benedict-Bordner
- Tính khoảng cách giao nhau (794 m)

### Tuần 4: Mô phỏng
- Động cơ mô phỏng Monte Carlo
- 3 loại quỹ đạo (người đi bộ, xe máy, drone)
- Đánh giá RMSE: tất cả kịch bản đạt yêu cầu <5m
- Alpha-beta tốt hơn Kalman trong mô phỏng CV

### Tuần 5: Pipeline thời gian thực
- Tích hợp WebSocket
- Quản lý phiên
- Vòng đệm (500 điểm)
- Tối ưu hiệu suất UI (pipeline 59 µs)
- Điều khiển lớp và hiển thị bất định

### Tuần 6: Xuất dữ liệu và Phân tích
- Endpoint xuất CSV (StreamingResponse)
- Phân tích hội tụ RMSE
- Trực quan hóa histogram sai số
- Xác thực trường hợp đặc biệt elevation âm

### Kiểm tra chất lượng code (Mới nhất)
- Quét Ruff đầy đủ: 0 lỗi còn lại
- Quét ESLint đầy đủ: 0 cảnh báo
- Xóa import không dùng trong 10 file
- Sửa pattern AI `--` trong docstring
- Sửa trộn tiếng Việt ("âm" → "negative")
- Xóa 105 dấu chấm phẩy (E702) trong scripts
- Xóa 8 f-string không có placeholder (F541)
- Tách 6 multi-imports (E401)
- Sửa 1 tên biến mơ hồ (E741)
- Sửa thứ tự import (E402) trong test_simulation_phase2.py
- Sửa ESLint: xóa `setFps` khỏi dependency useCallback

## Danh sách file

### Backend Python (27 file)
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
backend/scripts/ws_smoke.py
```

### Frontend JS/JSX (17 file)
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

### Report LaTeX (8 tuần)
```
report-weekly/Contents/week-1.tex đến week-8.tex
report-weekly/main.tex
```
