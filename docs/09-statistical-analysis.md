# Phân tích thống kê — RMSE nhiều giá trị khởi tạo

## Mục đích

`tests/statistical_analysis.py` chạy mỗi loại mục tiêu qua 10 giá trị khởi tạo để tính toán RMSE có tính thống kê. Khác với `benchmark_rmse.py` (chỉ một giá trị khởi tạo=42), script này cho phép tính trung bình ± độ lệch chuẩn trên các giá trị khởi tạo từ 1 đến 10.

## Sử dụng

```bash
cd backend
uv run python tests/statistical_analysis.py
```

## Cấu hình

| Tham số | Giá trị |
|---------|---------|
| Hạt giống | Từ 1 đến 10 (10 lần chạy mỗi kịch bản) |
| Thời gian | 120 s |
| Tần số cập nhật | 10 Hz (1200 bước/lần chạy) |
| Bán kính biên | 400 m |
| Alpha (α-β) | 0,4 |
| Yêu cầu | RMSE < 5,0 m |

## Kết quả (đã xác thực 2026-07-21)

| Kịch bản | Phương pháp | Trung bình (m) | Độ lệch chuẩn (m) | Nhỏ nhất (m) | Lớn nhất (m) |
|----------|------------|----------------|-------------------|--------------|--------------|
| Người đi bộ | Thô | 0,45 | 0,06 | 0,37 | 0,55 |
| Người đi bộ | Alpha-beta | 0,24 | 0,03 | 0,21 | 0,30 |
| Người đi bộ | Kalman | 0,96 | 0,22 | 0,57 | 1,31 |
| Xe máy | Thô | 1,93 | 0,38 | 1,17 | 2,31 |
| Xe máy | Alpha-beta | 1,09 | 0,20 | 0,68 | 1,28 |
| Xe máy | Kalman | 2,24 | 0,37 | 1,74 | 2,93 |
| Drone | Thô | 1,29 | 0,08 | 1,11 | 1,35 |
| Drone | Alpha-beta | 0,77 | 0,03 | 0,71 | 0,82 |
| Drone | Kalman | 2,58 | 0,27 | 2,27 | 2,95 |

Cả 9 trường hợp ĐẠT yêu cầu (< 5,0 m).

## Các quan sát chính

- **Xe máy** có phương sai cao nhất (Kalman σ=0,37 m) do gia tốc ngẫu nhiên.
- **Drone** ổn định nhất (Thô σ=0,08 m) — nhiễu Gaussian đồng nhất trên cả ba trục.
- **Kalman người đi bộ** có phương sai tương đối cao nhất (σ/μ = 0,23) do giai đoạn hội tụ ban đầu.
- **Tất cả kịch bản** nằm trong yêu cầu với biên an toàn tối thiểu 2,05 m (lớn nhất Kalman drone = 2,95 m).

## Khác biệt với benchmark_rmse.py

| Khía cạnh | benchmark_rmse.py | statistical_analysis.py |
|-----------|-------------------|------------------------|
| Giá trị khởi tạo | Một (42) | 10 giá trị khởi tạo (từ 1 đến 10) |
| Đầu ra | RMSE mỗi lần chạy | Trung bình ± độ lệch chuẩn |
| Mục đích | Cơ sở có thẩm quyền | Tính ổn định thống kê |
| Sử dụng trong báo cáo | Bảng tuần 1-6 | Bảng tuần 7 nhiều giá trị khởi tạo |
