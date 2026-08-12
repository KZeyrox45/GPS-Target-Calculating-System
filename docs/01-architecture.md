# Kiến trúc hệ thống

## Tổng quan

Hệ thống tính toán tọa độ mục tiêu GPS theo thời gian thực, kết hợp ba cảm biến Laser-IMU-GNSS. Đây là đồ án tốt nghiệp tại Trường Đại học Bách Khoa Thành phố Hồ Chí Minh (HCMUT).

## Phát triển

### Máy tính điểm đơn tĩnh
- **Vị trí**: `index.html` + `js/` + `css/` (gốc repo), bản sao lưu trong `phase1/`
- **Mục đích**: Tính tọa độ mục tiêu từ một phép đo đơn (GPS observer + góc IMU + khoảng cách laser)
- **Công nghệ**: JavaScript thuần, CDN Leaflet, không cần build
- **Thuật toán**: Tính trigonometric trực tiếp, không lọc

### Mô phỏng theo dõi 3D thời gian thực
- **Vị trí**: `backend/` (FastAPI) + `frontend/` (React 19 + Vite)
- **Mục đích**: Theo dõi liên tục mục tiêu di chuyển với hợp nhất cảm biến và lọc
- **Công nghệ**: Python 3.11+, FastAPI, NumPy, SciPy, React 19, Zustand, Leaflet
- **Thuật toán**: Kalman filter (2D/3D), Alpha-Beta filter, hợp nhất RSS

## Kiến trúc phân lớp (4 tầng)

```
┌─────────────────────────────────────────────┐
│  Tầng giao diện (React + Leaflet)           │
│  - TrackingMap, TargetMarker, Polyline      │
│  - Zustand store (vòng đệm 500 khung)       │
│  - WebSocket client qua useWebSocket hook   │
├─────────────────────────────────────────────┤
│  Tầng server (FastAPI + WebSocket)          │
│  - REST API: /api/simulation/*              │
│  - WebSocket: /ws/tracking/{session_id}     │
│  - SimulationEngine (phiên trong bộ nhớ)    │
├─────────────────────────────────────────────┤
│  Tầng nhúng (Raspberry Pi stub)             │
│  - sensor_client.py (WebSocket client)      │
│  - Đọc cảm biến UART/I2C                    │
├─────────────────────────────────────────────┤
│  Tầng cảm biến (Phần cứng)                  │
│  - GPS/GNSS (U-Blox, UART)                 │
│  - IMU (MPU6050/BNO055, I2C)               │
│  - Đo xa laser (LIDAR-Lite, I2C)           │
└─────────────────────────────────────────────┘
```

## Luồng dữ liệu

```
GPS/IMU/Laser → RPi → WebSocket → FastAPI Server
                                      ↓
                              Chuyển đổi tọa độ
                              (WGS84 → ECEF → ENU)
                                      ↓
                              Hợp nhất cảm biến (RSS)
                                      ↓
                              Kalman/Alpha-Beta filter
                                      ↓
                              ENU → ECEF → WGS84
                                      ↓
                              WebSocket → React Frontend
                                      ↓
                              Bản đồ Leaflet + Biểu đồ
```

## Hệ tọa độ

| Hệ tọa độ | Mục đích | Sử dụng |
|------------|----------|---------|
| WGS84 | Vĩ độ/kinh độ/độ cao toàn cầu | Đầu vào GPS, đầu ra cuối |
| ECEF | Tâm Trái Đất, cố định với Trái Đất | Biến đổi trung gian |
| ENU | Đông-Bắc-Lên địa phương | Tính toán bộ lọc, vector |
| Khung thiết bị | Tương đối với thiết bị | Góc IMU (azimuth, elevation) |

## Các quyết định thiết kế quan trọng

1. **WebSocket thay vì HTTP polling**: Kết nối full-duplex, liên tục cho cập nhật 10 Hz
2. **Phiên trong bộ nhớ**: Không có cơ sở dữ liệu, trạng thái được dọn khi ngắt WS
3. **Vite proxy**: Frontend proxy `/ws` → `ws://localhost:8000` (middleware CORS không áp dụng cho WebSocket upgrade)
4. **Vòng đệm 500 điểm**: Bộ nhớ cố định, 50 giây quỹ đạo ở 10 Hz
5. **Ma trận Adaptive R**: Nhiễu đo lường Kalman được cập nhật động từ σ_pos của hợp nhất cảm biến
