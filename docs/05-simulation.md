# Mô phỏng

## Tổng quan

Động cơ mô phỏng tạo dữ liệu cảm biến tổng hợp để xác thực thuật toán. Nó tạo quỹ đạo thực tế, thêm nhiễu cảm biến, hợp nhất phép đo, và chạy bộ lọc — tất cả mà không cần phần cứng vật lý.

## Các loại quỹ đạo

### Người đi bộ
- **Tốc độ**: 0,8 - 1,5 m/s (random walk)
- **Hướng**: Drift dần với nhiễu ngẫu nhiên
- **Độ cao**: Cố định 0 (theo dõi 2D)
- **Máy trạng thái**: Đi bộ | Tạm dừng (nghỉ ngẫu nhiên)
- **Ranh giới**: Bị chặn tại bán kính biên

### Xe máy
- **Tốc độ**: 5 - 15 m/s
- **Máy trạng thái**: Điều khiển | Rẽ | Giảm tốc
- **Rẽ**: Hình học cung với góc rẽ có thể cấu hình
- **Độ cao**: Cố định 0 (theo dõi 2D)
- **Ranh giới**: Phản xạ tại ranh giới (hướng ngược lại theo bán kính)

### Drone
- **Tốc độ**: Thay đổi (thành phần sinusoidal + hình tròn)
- **Độ cao**: Thay đổi (sinusoidal, 50-200 m)
- **Trục**: Đầy đủ 3D (Đông, Bắc, Lên)
- **Máy trạng thái**: Đi tăng | Tăng | Giảm
- **Ranh giới**: Ngang bị ràng buộc, độ cao tự do

## Mô hình nhiễu cảm biến

Nhiễu Gaussian được thêm vào mỗi phép đo:

| Cảm biến | Nhiễu (1σ) | Phân phối |
|----------|-----------|-----------|
| GPS vĩ độ/kinh độ | 5,0 m | Gaussian |
| GPS độ cao | 5,0 m | Gaussian |
| IMU azimuth | 0,3° | Gaussian |
| IMU elevation | 0,2° | Gaussian |
| Khoảng cách laser | 0,5 m | Gaussian |

Sử dụng `np.random.default_rng(seed)` để tái tạo kết quả.

## Luồng mô phỏng

```
Với mỗi bước thời gian k (từ 0 đến N-1):
  1. Tạo vị trí ground truth từ quỹ đạo
  2. Tính hình học observer → mục tiêu
  3. Tạo phép đo cảm biến có nhiễu:
     - GPS: observer_lla + nhiễu
     - IMU: true_azimuth + nhiễu, true_elevation + nhiễu
     - Laser: true_distance + nhiễu
  4. Hợp nhất cảm biến (RSS) → σ_pos
  5. Chuyển sang tọa độ ENU
  6. Chạy Kalman filter (dự báo + cập nhật với adaptive R)
  7. Chạy Alpha-Beta filter
  8. Tính sai số so với ground truth
  9. Lưu khung vào vòng đệm
```

## Ranh giới

- Ranh giới hình tròn tâm tại observer
- Bán kính ∈ [100, 1000] m (ràng buộc Pydantic)
- Người đi bộ: vị trí bị chặn tại ranh giới
- Xe máy: hướng phản xạ tại ranh giới
- Drone: ngang bị ràng buộc, độ cao tự do

## Tính RMSE

```
RMSE_k = sqrt( (1/k) * Σ[(e_i - ê_i)² + (n_i - n̂_i)²] )
```

- Chỉ RMSE nằm ngang (Đông + Bắc)
- Drone bao gồm trục Lên trong trạng thái nhưng RMSE chỉ nằm ngang
- RMSE cuối cùng được báo cáo sau tất cả N bước thời gian

## Kết quả đã xác thực (giá trị khởi tạo=42, 120s, 10Hz, bán kính 400m)

| Kịch bản | Thô | Alpha-Beta | Kalman | Yêu cầu (<5m) |
|----------|-----|-----------|--------|---------------|
| Người đi bộ | 0,46 m | 0,24 m | 0,84 m | ĐẠT |
| Xe máy | 1,79 m | 1,01 m | 2,18 m | ĐẠT |
| Drone | 1,28 m | 0,73 m | 2,33 m | ĐẠT |
