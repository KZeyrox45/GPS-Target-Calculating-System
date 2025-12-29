# GPS Target Calculating System - Hệ thống tính toán tọa độ mục tiêu

Dự án nghiên cứu và xây dựng thuật toán xác định tọa độ địa lý (Kinh độ, Vĩ độ) của mục tiêu dựa trên dữ liệu vị trí GPS của người quan sát, góc phương vị (Azimuth) và khoảng cách đo từ cảm biến.

## 📌 Giới thiệu dự án

Đây là đồ án kỹ thuật thuộc ngành Kỹ Thuật Máy Tính - Trường Đại học Bách Khoa TP.HCM. Hệ thống cung cấp một công cụ tính toán và trực quan hóa (WebGIS) giúp người dùng xác định vị trí mục tiêu một cách nhanh chóng và chính xác trong không gian thực.

## ✨ Tính năng chính

- **Tính toán tọa độ mục tiêu**: Sử dụng thuật toán Haversine để tính tọa độ dựa trên mô hình cầu của Trái Đất.
- **Chuyển đổi định dạng**: Hỗ trợ linh hoạt giữa định dạng thập phân (Decimal Degrees) và Độ-Phút Giây (DMS).
- **Trực quan hóa WebGIS**: Hiển thị vị trí người quan sát, mục tiêu và đường ngắm trực quan trên nền bản đồ OpenStreetMap (sử dụng Leaflet.js).
- **Ước lượng sai số**: Tính toán sai số tổng hợp (RSS) dựa trên độ chính xác của cảm biến đầu vào (GPS, Compass, Laser).
- **Trải nghiệm người dùng**: Giao diện responsive, hỗ trợ phím tắt, copy tọa độ nhanh và thông báo lỗi chi tiết.

## 🛠 Công nghệ sử dụng

- **Frontend**: HTML5, Vanilla CSS3 (Modern design, Dark mode optimized).
- **Logic**: Vanilla JavaScript (ES6+), được thiết kế theo module hóa.
- **Bản đồ**: Leaflet.js v1.9.4.
- **Dữ liệu**: OpenStreetMap Tiles.

## 📐 Thuật toán cốt lõi

Hệ thống sử dụng các công thức lượng giác cầu (Spherical Trigonometry) để giải bài toán Geodesic thuận:
- **Tính vĩ độ (φ₂)**: `asin(sin φ₁ ⋅ cos δ + cos φ₁ ⋅ sin δ ⋅ cos θ)`
- **Tính kinh độ (λ₂)**: `λ₁ + atan2(sin θ ⋅ sin δ ⋅ cos φ₁, cos δ − sin φ₁ ⋅ sin φ₂)`
- **Ước lượng sai số**: `sqrt(σ_GPS² + (d × sin(σ_Azimuth))² + σ_Distance²)`

## 📂 Cấu trúc thư mục

```text
GPS-Target-Calculating-System/
├── index.html          # Giao diện chính và khởi tạo ứng dụng
├── css/
│   └── style.css       # Toàn bộ định dạng giao diện (Modern UI)
├── js/
│   ├── coordinateCalculator.js # Logic tính toán và validation
│   └── mapViewer.js            # Quản lý bản đồ và tương tác UI
└── README.md           # Hướng dẫn này
```

## 🚀 Hướng dẫn cài đặt và chạy

Vì dự án sử dụng Vanilla JavaScript, bạn không cần cài đặt môi trường phức tạp:

1. Tải toàn bộ mã nguồn về máy.
2. Mở file `index.html` bằng trình duyệt web bất kỳ (Chrome, Firefox, Safari, Edge).
3. Đảm bảo máy tính có kết nối Internet để tải dữ liệu bản đồ từ OpenStreetMap.

## 👥 Thành viên thực hiện (Nhóm 072)

1. **Huỳnh Gia Qui** - 2112138
2. **Nguyễn Trung Hiếu** - 2113357
3. **Bùi Nguyễn Thành Luân** - 2111700

**Giảng viên hướng dẫn**: TS. Võ Tuấn Bình

---
*Dự án thuộc học phần Đồ án Kỹ thuật Máy tính - HK1/2025-2026.*