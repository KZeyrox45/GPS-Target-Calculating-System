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
- **Tốc độ**: 5 - 15 m/s (synthetic) / Theo giới hạn tốc độ đường (20-90 km/h, real-world)
- **Nguồn dữ liệu real-world**: Đi ngẫu nhiên trên mạng đường bộ TP.HCM (OSMnx), tuân theo giới hạn tốc độ từng loại đường
- **Máy trạng thái**: Điều khiển | Rẽ | Giảm tốc (synthetic)
- **Rẽ**: Hình học cung với góc rẽ có thể cấu hình (synthetic)
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

## Phân tích tính thực tế của quỹ đạo

### Mô hình vi động (Micro-dynamics) — Hợp lệ

Các mô hình vận động cơ bản đều phù hợp với nghiên cứu học thuật:

- **Người đi bộ:** Quá trình Ornstein-Uhlenbeck cho hướng (τ=2.0s, σ=0.4 rad/s), điều chỉnh步态 tại 1.8 Hz, tạm dừng theo Poisson — tất cả đều phù hợp với Social Force Model (Helbing & Molnár 1995)
- **Xe máy:** Mô hình kinematic xe đạp với giới hạn gia tốc ngang 3.0 m/s² (synthetic); quỹ đạo đi ngẫu nhiên trên mạng đường bộ TP.HCM (real-world) — phù hợp với dữ liệu AMIT và OSMnx (Wen et al. 2023)
- **Drone:** Giới hạn kinematic phù hợp với thông số DJI Matrice 100 (Rodrigues et al. 2021): V_max=15 m/s, A_max=4 m/s²
- **KinematicDrone:** Mô hình thực tế nhất — enforced acceleration limits từ thông số khung thực tế

### Vấn đề điều hướng (Navigation) — Cần cải thiện

Ba vấn đề chính gây ra chuyển động "không thực tế":

1. **Điểm waypoint tương đối gốc** (`target_simulator.py:141-144`): Các điểm được tạo tuyệt đối quanh gốc (0,0), không phải từ vị trí hiện tại. Gây ra các đường đi U-turn bất tự nhiên.

2. **Phản xạ biên cứng** (`boundary.py:66-90`): Khi mục tiêu chạm biên, hướng bị phản xạ như bóng bi-a. Kết hợp với waypoint tương đối gốc, tạo ra mẫu di chuyểnzig-zag.

3. **Vòng lặp segment** (`target_simulator.py:457`): Khi chạy chế độ dataset, quỹ đạo nhảy ngay lập tức về điểm đầu khi kết thúc segment.

### Số liệu tham chiếu từ nghiên cứu

| Thông số | Giá trị hiện tại | Giá trị nghiên cứu | Nguồn |
|----------|----------------|-------------------|-------|
| Tốc độ người đi bộ | 0.3-2.0 m/s | 1.2-1.5 m/s (bình thường) | Campbell et al. 2022 |
| Tốc độ xe máy | 7-13 m/s | 5-20 m/s (giao thông đô thị) | Wen et al. 2023 |
| Tốc độ drone | 7-15 m/s | ≤17 m/s (DJI Matrice 100) | Rodrigues et al. 2021 |
| Gia tốc ngang drone | 4.0 m/s² | ~4 m/s² (DJI Matrice 100) | Rodrigues et al. 2021 |
| Thời gian phản ứng OU | τ=2.0s | 0.3-0.5s (Social Force) | Helbing & Molnár 1995 |

### Tài liệu tham khảo

- Helbing, D., & Molnár, P. (1995). Social force model for pedestrian dynamics. *Physical Review E*, 51(5), 4282-4286.
- Bongiorno, C., et al. (2021). Vector-based pedestrian navigation in cities. *Nature Computational Science*, 1, 656-667.
- Rodrigues, E., et al. (2021). In-flight positional and energy use data set of a DJI Matrice 100 quadcopter. *Scientific Data*, 8, 53.
- Wen, C., et al. (2023). Kinematic characterization of risky riding behavior of on-demand food-delivery motorcyclists in Taiwan. *Transportation Research Record*.
- Krajzewicz, D., et al. (2012). Road intersection model in SUMO. Springer.

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
