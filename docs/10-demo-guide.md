# Hướng dẫn Demo

## Yêu cầu trước khi demo

Backend và frontend phải chạy đồng thời:

```bash
# Cửa sổ 1 — Backend
cd backend
uv run uvicorn app.main:app --reload --port 8000

# Cửa sổ 2 — Frontend
cd frontend
npm run dev
```

Mở trình duyệt tại `http://localhost:5173`.

## Luồng demo đề xuất (15 phút)

### 1. Máy tính tĩnh (2 phút)

Trang: **Static Calc**

Mục tiêu: Minh họa tính toán tọa độ điểm đơn từ đầu vào GPS + IMU + Laser.

Nhập thử:
- Observer: vĩ độ=10,762622, kinh độ=106,660172, độ cao=10,0
- Azimuth: 45,0°, Elevation: 5,0°, Khoảng cách: 200,0 m

Kết quả: tọa độ mục tiêu + `sigma_pos` hiển thị trên bản đồ.

### 2. Theo dõi trực tiếp — Xe máy (8 phút)

Trang: **Tracking**

Cấu hình:
- Loại mục tiêu: **xe máy** (thấy sự khác biệt rõ nhất)
- Bán kính biên: **400 m**
- Thời gian: **60 s**
- Hạt giống: **42** (kết quả nhất quán)

Giải thích trong khi chạy:
- Đường **cam**: đo thô từ cảm biến (có nhiễu)
- Đường **xanh lam**: ước lượng alpha-beta (mượt hơn, RMSE ~1,01 m)
- Đường **đỏ**: ước lượng Kalman (hội tụ sau ~10 s, RMSE ~2,18 m)
- Vòng tròn bất định: thể hiện độ tin cậy của Kalman

Sau 60 s: nhấn **Dừng**.

### 3. So sánh (3 phút)

Trang: **Comparison**

So sánh RMSE của 3 phương pháp trên 3 kịch bản. Chỉ ra:
- Alpha-beta luôn có RMSE thấp nhất
- Kalman có thông tin bất định (ma trận P) mà alpha-beta không có

### 4. Xuất CSV (2 phút)

Dùng endpoint trực tiếp hoặc nút Export CSV trong TrackingPage.

Xác nhận:
- 600 hàng (60 s × 10 Hz)
- Header đầy đủ: bước, thời gian, vị trí thực, vị trí ước lượng...

## Câu hỏi thường gặp

**Tại sao Kalman RMSE cao hơn alpha-beta?**
Giai đoạn hội tụ ban đầu (khoảng 50 bước đầu). Sau khi ma trận P ổn định, sai số tức thời tương đương (khoảng 0,3-0,5 m).

**Khoảng cách giao nhau 794 m nghĩa là gì?**
Khoảng cách mà sai số GPS (5 m) bằng sai số góc IMU × khoảng cách. Dưới 794 m: GPS chi phối. Trên 794 m: IMU chi phối độ chính xác.

**Tại sao không dùng EKF/UKF?**
Mô hình Constant Velocity là tuyến tính nên Kalman filter tuyến tính là lựa chọn tối ưu. EKF/UKF cần thiết khi mô hình phi tuyến.

**Phần cứng RPi đâu?**
Hiện tại dùng mô phỏng trên máy tính. Kiến trúc: RPi → GPS/IMU/Laser → WebSocket → server. Chờ phần cứng thực tế để triển khai.

**Tính nhất quán kết quả thế nào?**
Phân tích 10 giá trị khởi tạo: tất cả RMSE < 5 m. Xe máy có phương sai cao nhất (σ=0,37 m) do gia tốc ngẫu nhiên. Drone ổn định nhất (σ=0,08 m).
