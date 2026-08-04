# Frontend (React 19 + Vite)

## Thiết lập

```bash
cd frontend
npm install          # Lần đầu
npm run dev          # Server dev trên cổng 5173
npm run build        # Build production
npm run lint         # Kiểm tra ESLint
```

## Cấu trúc dự án

```
frontend/
├── src/
│   ├── main.jsx                 # Điểm vào
│   ├── App.jsx                  # Cài đặt router
│   ├── App.css                  # Style toàn cục
│   ├── index.css                # Reset + style cơ bản
│   ├── pages/
│   │   ├── HomePage.jsx         # Trang chủ
│   │   ├── TrackingPage.jsx     # Giao diện theo dõi thời gian thực
│   │   ├── StaticCalcPage.jsx   # Máy tính giai đoạn 1
│   │   └── ComparisonPage.jsx   # So sánh bộ lọc
│   ├── components/
│   │   ├── charts/
│   │   │   ├── AltitudeChart.jsx
│   │   │   └── ErrorMetricsChart.jsx
│   │   ├── controls/
│   │   │   ├── SimulationPanel.jsx
│   │   │   └── LayerControl.jsx
│   │   ├── map/
│   │   │   ├── TrackingMap.jsx
│   │   │   ├── TargetMarker.jsx
│   │   │   └── TrajectoryPolyline.jsx
│   │   └── ui/
│   │       ├── CoordDisplay.jsx
│   │       └── StatusBar.jsx
│   ├── store/
│   │   └── trackingStore.js    # Zustand store
│   └── hooks/
│       └── useWebSocket.js     # Hook kết nối WebSocket
├── vite.config.js              # Cấu hình proxy + build
├── eslint.config.js            # ESLint flat config
├── package.json
└── index.html
```

## Tech Stack

| Thư viện | Mục đích |
|----------|----------|
| React 19 | Framework UI |
| Vite 8 | Công cụ build + server dev |
| Zustand | Quản lý trạng thái (nhẹ) |
| Leaflet | Hiển thị bản đồ (OpenStreetMap) |
| Recharts | Biểu đồ (độ cao, sai số) |
| React Router | Định tuyến trang |

## Các thành phần chính

### TrackingMap (Leaflet)
- Lớp tile OpenStreetMap
- Marker observer (xanh lá)
- Marker mục tiêu (đỏ cho thô, xanh lam cho Kalman, tím cho alpha-beta)
- Polyline quỹ đạo (3 lớp, có thể tắt/bật độc lập)
- Vòng tròn bất định xung quanh ước lượng Kalman

### Hook useWebSocket
- Kết nối đến `/ws/tracking/{session_id}` (qua Vite proxy đến ws://localhost:8000)
- Parse JSON đầu vào, cập nhật Zustand store
- Xử lý kết nối lại và dọn dẹp

### trackingStore (Zustand)
- Vòng đệm: `MAX_HISTORY = 500` điểm mỗi lớp
- Trạng thái: vị trí observer, vị trí mục tiêu (thô/kalman/alphabeta), bất định, FPS
- Hành động: addFrame, clearHistory, setFps

### LayerControl
- Bật/tắt hiển thị lớp thô/kalman/alphabeta
- Bật/tắt vòng tròn bất định
- Bật/tắt marker observer

## Cấu hình Vite Proxy

```js
// vite.config.js
export default defineConfig({
  server: {
    proxy: {
      '/api': 'http://localhost:8000',
      '/ws': {
        target: 'ws://localhost:8000',
        ws: true
      }
    }
  }
})
```

## Kiểm tra code

- ESLint flat config (`eslint.config.js`)
- `no-unused-vars` bỏ qua tên bắt đầu bằng chữ hoa/dấu gạch dưới
- Chạy: `npm run lint`

## Build

```bash
npm run build  # Đầu ra: frontend/dist/
```

Cảnh báo về kích thước chunk (588 kB) là bình thường do Leaflet + Recharts.

## Tất cả đều là .jsx (KHÔNG phải TypeScript)

Mặc dù `@types/react` là dev dependency, dự án dùng JSX thuần không có TypeScript compilation. Không có `tsconfig.json`.
