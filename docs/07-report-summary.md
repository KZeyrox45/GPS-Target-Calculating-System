# Nội dung báo cáo (Tuần 1-9)

## Tuần 1: Giới thiệu và bài toán

### Nội dung
- **Bài toán**: Theo dõi mục tiêu di chuyển bằng hợp nhất cảm biến Laser-IMU-GNSS
- **Máy tính điểm đơn tĩnh** (dựa trên Haversine)
- **Mở rộng**: Theo dõi thời gian thực với lọc và WebSocket

### Khái niệm giới thiệu
- Kiến trúc 4 tầng (Cảm biến → Nhúng → Server → Frontend)
- Đặc điểm cảm biến: GPS (độ chính xác 2-5m, 1-10 Hz), IMU (100-1000 Hz, bị drift), Laser (±1-2 cm, chỉLOS)
- Hệ tọa độ khung thiết bị và ma trận xoay
- Cơ sở Kalman filter (vector trạng thái, ma trận F)
- Cơ sở alpha-beta filter (tham số α, β)

### Hình ảnh
- Sơ đồ use-case (`Images/use-case-diagram.png`)

## Tuần 2: Kiến trúc hệ thống

### Nội dung
- Kiến trúc 4 tầng chi tiết với mô tả thành phần
- Luồng dữ liệu từ cảm biến đến frontend
- Thiết kế nhúng Raspberry Pi (kết nối UART/I2C/SPI)
- Thiết kế server FastAPI (REST + WebSocket)
- Thiết kế frontend React (bản đồ Leaflet)

### Khái niệm
- WebSocket so với HTTP polling (full-duplex, kết nối liên tục)
- Vòng đời phiên (bắt đầu → vòng lặp WS → dừng)
- Sơ đồ lớp của các thành phần phần mềm

### Hình ảnh
- Sơ đồ kiến trúc (TikZ)
- Sơ đồ lớp (`Images/class-diagram.png`)
- Sơ đồ hoạt động (xử lý + theo dõi)

## Tuần 3: Pipeline tọa độ và phân tích sai số

### Nội dung
- **Pipeline chuyển đổi tọa độ**: WGS84 → ECEF → ENU → mục tiêu → WGS84
- **Lan truyền sai số**: Công thức RSS cho σ_pos
- **Thông số nhiễu cảm biến** (giá trị 1-sigma)
- **Tính khoảng cách giao nhau** (794 m)
- **Cấu trúc Kalman filter**: F, Q (DWNA), adaptive R
- **Alpha-beta filter**: Công thức critically damped Benedict-Bordner

### Công thức chính
- RSS: `σ_pos² = σ_gps² + (R·sin(σ_az))² + σ_range² + (R·sin(σ_el))²`
- Giao nhau: `R_cross = σ_gps / √(sin²(σ_az) + sin²(σ_el))`
- Beta: `β = (2-α) - 2√(1-α)`

### Bảng
- Thông số nhiễu cảm biến
- Giá trị σ_a theo loại mục tiêu
- So sánh Kalman với alpha-beta

### Hình ảnh
- Sơ đồ luồng tọa độ (`Images/coord-flow.png`)
- Biểu đồ lan truyền sai số (`Images/error-prop.png`)
- Sơ đồ chi tiết Kalman (`Images/kalman-detail.png`)

## Tuần 4: Kết quả mô phỏng

### Nội dung
- **Thiết lập mô phỏng**: Biên 400m, 120s, 10 Hz, giá trị khởi tạo cố định để tái tạo
- **Kết quả RMSE**: Cả 3 kịch bản đạt yêu cầu <5m
- **Alpha-beta tốt hơn Kalman** trong mô phỏng CV này (dự kiến)
- **Ưu điểm Kalman**: Ước lượng bất định (ma trận P), adaptive R
- **Phân tích sai số theo khoảng cách**: Đường cong σ_pos(R)

### Kết quả chính
| Kịch bản | Thô | Alpha-Beta | Kalman |
|----------|-----|-----------|--------|
| Người đi bộ | 0,46 m | 0,24 m | 0,84 m |
| Xe máy | 1,79 m | 1,01 m | 2,18 m |
| Drone | 1,28 m | 0,73 m | 2,33 m |

### Hình ảnh
- Biểu đồ cột RMSE (`figures/rmse_bar_comparison.png`)
- Đường cong sigma theo khoảng cách (`figures/error_vs_range.png`)

## Tuần 5: Pipeline thời gian thực và Giao diện

### Nội dung
- **Luồng dữ liệu thời gian thực**: Cảm biến → WS → Server → Lọc → WS → Frontend
- **Giao thức WebSocket**: Định dạng JSON (lên + xuống)
- **Quản lý phiên**: Trong bộ nhớ, vòng đệm N_max=500
- **Hiệu suất UI**: ~3ms độ trễ WS, ~8ms render, ~4% CPU
- **Điều khiển lớp**: 3 lớp quỹ đạo (thô/kalman/alphabeta) + vòng tròn bất định
- **Thời gian pipeline**: Tổng 59 µs, Kalman chiếm phần lớn

### Số liệu chính
- Độ trễ WebSocket: ~3 ms (server → trình duyệt)
- Thời gian render: ~8 ms/khung
- Tổng điểm quỹ đạo: 3 × 500 = 1500
- Bộ nhớ Leaflet: ~2,1 MB
- Sử dụng CPU: ~4%

### Bảng
- So sánh WebSocket với HTTP
- Vòng đời phiên
- Chỉ số hiệu suất UI
- Phân tích thời gian pipeline

### Hình ảnh
- Pipeline dữ liệu thời gian thực (`Images/real-time-data-pipeline.png`)
- Sai số theo thời gian (`figures/error_timeseries.png`)

## Tuần 6: Xuất dữ liệu và Phân tích sau phiên

### Nội dung
- **Xuất CSV**: StreamingResponse, 19 cột, ~120 KB mỗi phiên
- **Đường cong hội tụ RMSE**: Cho thấy giai đoạn khởi tạo bộ lọc
- **Phân tích sai số theo trục**: Đối xứng Đông-Bắc
- **Histogram sai số**: Alpha-beta tập trung gần 0, Kalman rộng hơn (đuôi hội tụ)
- **Xử lý elevation âm**: Bằng chứng toán học + bảng xác thực

### Kết quả quan trọng
- Hội tụ Kalman mất khoảng 50-100 bước thời gian (5-10 giây)
- Alpha-beta: 93% sai số trong khoảng 0-0,4 m
- Kalman: phân phối rộng hơn do bất định ma trận P ban đầu
- Chuyển đổi cực sang ENU xử lý elevation âm đúng cách mà không cần phân nhánh

### Bảng
- Schema CSV (19 cột)
- Sai số theo trục (σ_E, σ_N)
- Kết quả kiểm tra elevation âm

### Hình ảnh
- Hội tụ RMSE (`figures/rmse_convergence.png`)
- Histogram sai số (`figures/error_histogram_pedestrian.png`)

## Tuần 7: Phân tích thống kê và Độ nhạy tham số

### Nội dung
- **Phân tích nhiều giá trị khởi tạo**: 10 giá trị khởi tạo (từ 1 đến 10), cùng cấu hình
- **Thống kê RMSE**: Trung bình, độ lệch chuẩn, nhỏ nhất, lớn nhất cho cả 3 kịch bản × 3 phương pháp
- **Cả 9 trường hợp đạt yêu cầu <5m** ở mọi giá trị khởi tạo
- **Phân tích độ nhạy α**: α=0,2, 0,4, 0,7 với Benedict-Bordner β
- **So sánh bộ lọc**: Ưu nhược điểm Kalman so với alpha-beta

### Kết quả chính (Trung bình ± Độ lệch chuẩn nhiều giá trị khởi tạo)
| Kịch bản | Alpha-Beta | Kalman |
|----------|-----------|--------|
| Người đi bộ | 0,24 ± 0,03 m | 0,96 ± 0,22 m |
| Xe máy | 1,09 ± 0,20 m | 2,24 ± 0,37 m |
| Drone | 0,77 ± 0,03 m | 2,58 ± 0,27 m |

### Độ nhạy α
| α | β | RMSE (m) | Ghi chú |
|---|---|----------|---------|
| 0,2 | 0,011 | 0,21 | Lọc mạnh, chậm bám khi đổi hướng |
| 0,4 | 0,051 | 0,24 | Cân bằng tối ưu (mặc định) |
| 0,7 | 0,205 | 0,34 | Bám nhanh, nhạy với nhiễu |

### Hình ảnh
- Biểu đồ cột RMSE nhiều giá trị khởi tạo với thanh lỗi (`figures/multi_seed_rmse_spec.png`)
- Biểu đồ độ nhạy α (`figures/alpha_sensitivity.png`)

## Tuần 8: Kiểm tra hồi quy và Tổng kết

### Nội dung
- **Kiểm tra hồi quy**: 163 test đạt tất cả, 0 lỗi
- **Đánh giá kiến trúc**: Các tầng tính toán, giao tiếp, giao diện được xác nhận
- **Danh sách endpoint**: 5 REST + 1 WebSocket
- **Chuẩn bị demo**: Hướng dẫn demo từng bước cho đánh giá giữa kỳ
- **Còn lại**: Viết báo cáo, trường hợp đặc biệt, triển khai RPi

### Tóm tắt kiểm thử
| Hạng mục | Số test | Nội dung |
|----------|---------|----------|
| Bộ lọc alpha-beta | 10 | Khởi tạo, bước tính, reset |
| Chuyển đổi tọa độ | 25 | Haversine, bearing, ECEF/ENU khứ hồi |
| Kalman filter | 17 | Khởi tạo, predict, update, hội tụ |
| Hợp nhất cảm biến | 6 | Hướng, sigma, đầu ra LLA |
| Mô phỏng simulation | 50 | Quỹ đạo, biên, Kalman3D |
| Endpoint thống kê và xuất | 17 | Stats engine, endpoint |
| Nạp dữ liệu thực tế | 38 | Geolife, AMIT, drone, routing |
| **Tổng** | **163** | **Đạt tất cả** |

### Hạng mục còn lại
| Hạng mục | Tuần | Mô tả |
|----------|------|-------|
| Báo cáo phần lý thuyết | 11 | Kalman 3D, adaptive R, tham chiếu |
| Báo cáo phần thực nghiệm | 12 | Kết quả đầy đủ, figures, screenshots |
| Trường hợp đặc biệt: khoảng cách về 0 | 10 | Xử lý khi mục tiêu trở về observer |
| Kết luận và hướng phát triển | 13 | Đóng góp, hạn chế, hướng mở |
| Review và proofread | 14 | Format, mục lục, tham chiếu |

## Cấu trúc báo cáo tổng thể

```
main.tex (master)
├── week-1.tex  — Giới thiệu, bài toán, lý thuyết
├── week-2.tex  — Kiến trúc, luồng dữ liệu, Raspberry Pi
├── week-3.tex  — Pipeline tọa độ, phân tích sai số, bộ lọc
├── week-4.tex  — Kết quả mô phỏng, đánh giá RMSE
├── week-5.tex  — Pipeline thời gian thực, WebSocket, UI
├── week-6.tex  — Xuất dữ liệu, phân tích sau, trường hợp đặc biệt
├── week-7.tex  — Phân tích thống kê, độ nhạy tham số
└── week-8.tex  — Kiểm tra hồi quy, tổng kết, chuẩn bị demo
```

Compiler: pdfLaTeX (tương thích Overleaf). BibTeX cho tham chiếu. 5 lần biên dịch để ổn định tham chiếu chéo.

## Tuần 9: Dữ liệu quỹ đạo thực tế

### Nội dung
- **Tập dữ liệu Geolife**: 252 đoạn đi bộ hợp lệ (60-180 giây, GPS WGS-84, 182 người dùng)
- **Tập dữ liệu AMIT**: 25.757 đoạn xe máy hợp lệ (tậa độ mét từ camera UAV)
- **So sánh Geolife và AMIT**: GPS vệ tinh vs. camera UAV, PCHIP vs. nội suy tuyến tính
- **Bộ nạp dữ liệu (data loader)**: GeolifeWalkLoader, AMITMotorcycleLoader, RoadNetworkMotorcycleLoader
- **Toggle thực tế**: `use_realistic_sim` kết nối từ giao diện đến engine
- **Kiểm thử**: 38 test cases mới cho các bộ nạp dữ liệu

### Lý do dùng Geolife cho người đi bộ
- GPS vệ tinh thực, không phải đường cảnh quan ngẫu nhiên
- Chứa hành vi thực: dừng chờ, tăng từ từ, rẽ
- Lọc đoạn: 60-180 giây, khoảng trống GPS dưới 3 giây, phạm vi dưới 400 m
- Nội suy PCHIP giữ được điểm dừng (không tạo velocity hump như cubic spline)

### Kết quả bộ nạp dữ liệu
| Bộ nạp | Nguồn | Đoạn hợp lệ | Tần số đầu ra |
|----------|--------|--------------|---------------|
| GeolifeWalkLoader | GPS vệ tinh, WGS-84 | 252 | 10 Hz (PCHIP) |
| AMITMotorcycleLoader | Camera UAV, tọa độ mét | 25.757 | 10 Hz (tuyến tính) |
| RoadNetworkMotorcycleLoader | OSM TP.HCM | Vô hạn (random walk) | 10 Hz |

### Cấu trúc file
```
main.tex (master)
├── week-1.tex  — Giới thiệu, bài toán, lý thuyết
├── week-2.tex  — Kiến trúc, luồng dữ liệu, Raspberry Pi
├── week-3.tex  — Pipeline tọa độ, phân tích sai số, bộ lọc
├── week-4.tex  — Kết quả mô phỏng, đánh giá RMSE
├── week-5.tex  — Pipeline thời gian thực, WebSocket, UI
├── week-6.tex  — Xuất dữ liệu, phân tích sau, trường hợp đặc biệt
├── week-7.tex  — Phân tích thống kê, độ nhạy tham số
├── week-8.tex  — Kiểm tra hồi quy, tổng kết, chuẩn bị demo
└── week-9.tex  — Dữ liệu quỹ đạo thực tế (Geolife, AMIT, Road network toggle)
```
