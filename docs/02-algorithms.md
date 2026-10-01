# Thuật toán

## Kalman Filter

### Vector trạng thái

**2D (Người đi bộ, Xe máy)** — lớp `KalmanFilter`:
```
x = [e, n, ė, ṅ]^T    (Đông, Bắc, vận tốc-Đông, vận tốc-Bắc)
```

**3D (Drone)** — lớp `KalmanFilter3D`:
```
x = [e, n, u, ė, ṅ, u̇]^T    (+ trục Lên và vận tốc của nó)
```

### Ma trận chuyển trạng thái F

Mô hình vận tốc không đổi (CV) với bước thời gian Δt:

```
F_2D = [1  0  Δt  0 ]    F_3D = F_2D mở rộng với
       [0  1   0  Δt ]         hàng/cột trục Lên
       [0  0   1   0 ]
       [0  0   0   1 ]
```

### Nhiễu quá trình Q (mô hình DWNA)

Nhiễu gia tốc trắng rời rạc:
```
Q = σ_a² · [Δt⁴/4    0      Δt³/2    0     ]
            [0      Δt⁴/4    0      Δt³/2   ]
            [Δt³/2    0      Δt²      0     ]
            [0      Δt³/2    0      Δt²     ]
```

Giá trị σ_a:
| Loại mục tiêu | σ_a (m/s²) | Lý do |
|---------------|------------|-------|
| Người đi bộ | 0,5 | Gia tốc thấp, chuyển động chậm |
| Xe máy | 5,0 | Gia tốc cao, đổi hướng đột ngột |
| Drone | 5,0 | Gia tốc cao trên cả ba trục |

### Nhiễu đo lường thích ứng R

Cập nhật mỗi bước thời gian từ độ bất định hợp nhất cảm biến:
```
R_k = σ_pos,k² · I
```
Trong đó σ_pos,k đến từ công thức lan truyền sai số RSS. Khi mục tiêu ở xa (>794 m điểm giao nhau), R tăng, giảm Kalman gain và dựa nhiều hơn vào mô hình dự báo.

### Phương pháp giải

Sử dụng `np.linalg.solve` thay vì `np.linalg.inv` để ổn định số học:
```
K = P H^T (H P H^T + R)^{-1}   ← tính qua solve()
```

## Alpha-Beta Filter

### Công thức

```
Dự báo:      x_p[k] = x[k-1] + Δt · ẋ[k-1]
Cập nhật vt: x[k]   = x_p[k] + α · (z[k] - x_p[k])
Cập nhật vc: ẋ[k]   = ẋ[k-1] + (β/Δt) · (z[k] - x_p[k])
```

### Benedict-Bordner critically damped

β được suy ra từ α để đảm bảo phản hồi critically damped (không overshoot):
```
β = (2 - α) - 2√(1 - α)
```
Tại α = 0,4 → β ≈ 0,051

### Hạn chế
- Chỉ 2D (Đông-Bắc) — không theo dõi độ cao
- Không có ước lượng bất định (không ma trận P)
- Tham số cố định — không thích ứng với điều kiện nhiễu thay đổi

## Hợp nhất cảm biến (Lan truyền sai số RSS)

### Công thức

```
σ_pos² = σ_gps² + σ_laser² + R² · (sin²(σ_az) + sin²(σ_el))
```

### Thông số nhiễu cảm biến (1-sigma)

| Cảm biến | Ký hiệu | Giá trị |
|----------|---------|--------|
| GPS (nằm ngang) | σ_gps | 5,0 m |
| IMU (azimuth) | σ_az | 0,3° (0,00524 rad) |
| IMU (elevation) | σ_el | 0,2° (0,00349 rad) |
| Đo xa laser | σ_range | 0,5 m |

### Khoảng cách giao nhau

Khoảng cách mà sai số GPS = sai số góc IMU:
```
R_cross = σ_gps / √(sin²(σ_az) + sin²(σ_el))
        = 5,0 / √(0,00002745 + 0,00001219)
        ≈ 794 m
```

- Dưới 794 m: GPS chiếm ưu thế → cải thiện GPS giúp chính xác hơn
- Trên 794 m: IMU chiếm ưu thế → cải thiện IMU giúp chính xác hơn

### Sai số ở các khoảng cách quan trọng

| Khoảng cách | σ_pos | Đóng góp GPS | Đóng góp IMU |
|-------------|-------|--------------|--------------|
| 50 m | 5,0 m | ~98% | ~2% |
| 500 m | 5,9 m | ~72% | ~28% |
| 1000 m | 8,1 m | ~39% | ~61% |

## Pipeline chuyển đổi tọa độ

```
WGS84 → ECEF → ENU (tại observer) + vector hướng × khoảng cách → ENU mục tiêu → WGS84
```

Các bước chi tiết:
1. WGS84 → ECEF: Công thức ellipsoid (vĩ độ/kinh độ/độ cao → X/Y/Z)
2. ECEF → ENU: Ma trận xoay từ kinh độ/vĩ độ tại observer
3. Cực → vector ENU: `v = [cos(el)·sin(az), cos(el)·cos(az), sin(el)]`
4. ENU mục tiêu = ENU observer + khoảng cách × v
5. ENU → ECEF → WGS84: Nghịch đảo của bước 1-2

## Thời gian pipeline (Benchmark)

| Bước | Thời gian | Tỷ lệ |
|------|-----------|-------|
| LLA → ECEF | 2,1 µs | 4% |
| ECEF → ENU | 3,8 µs | 6% |
| Hợp nhất cảm biến (RSS) | 1,2 µs | 2% |
| Kalman Filter | 48,5 µs | 82% |
| ENU → LLA | 3,4 µs | 6% |
| **Tổng** | **59,0 µs** | 100% |

Kalman filter chiếm phần lớn thời gian xử lý do các phép toán ma trận. Tổng 59 µs nằm trong giới hạn 100 ms ở tần số 10 Hz.
