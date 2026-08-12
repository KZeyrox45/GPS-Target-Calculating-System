# Kiểm thử và xác thực

## Bộ kiểm thử

**Vị trí**: `backend/tests/`
**Framework**: pytest + pytest-asyncio
**Số lượng**: 163 test (đạt tất cả)
**Chạy**:
```bash
cd backend
uv run pytest tests/ -v
```

## Các file test

| Hạng mục | Số test | Nội dung |
|----------|---------|----------|
| Bộ lọc alpha-beta | 10 | Khởi tạo, bước tính, reset, tốc độ |
| Chuyển đổi tọa độ | 14 | Haversine, bearing, ECEF/ENU khứ hồi, elevation âm |
| Kalman filter | 15 | Khởi tạo, predict, update, hội tụ, RMSE tiêu chuẩn |
| Hợp nhất cảm biến | 6 | Hướng, sigma, đầu ra LLA |
| Mô phỏng simulation | 49 | Quỹ đạo, biên, Kalman3D, adaptive R, motorcycle, drone |
| Endpoint thống kê và xuất | 15 | Stats engine, stats endpoint, export endpoint |
| Benchmark RMSE | (script) | RMSE cơ sở có thẩm quyền cho số liệu báo cáo |

## Các hạng mục test chính

### Đúng đắn thuật toán
- Hội tụ Kalman cho cả 3 loại mục tiêu
- Hành vi làm mượt alpha-beta
- Sigma hợp nhất cảm biến tăng theo khoảng cách
- Độ chính xác khứ hồi ECEF/ENU

### Ranh giới
- Người đi bộ ở trong ranh giới
- Xe máy phản xạ đúng
- Drone ngang bị ràng buộc, độ cao tự do
- Bán kính không hợp lệ gây lỗi xác thực

### Trường hợp đặc biệt
- Elevation âm (observer nhìn xuống)
- Khoảng cách bằng 0 (mục tiêu tại vị trí observer)
- Khởi tạo bước đầu tiên của bộ lọc
- Góc rẽ xe máy (kiểm tra hồi quy: không crash)

### API Endpoints
- Stats trả 404 cho phiên không tồn tại
- Stats trả 200 cho phiên hoạt động
- Export trả CSV với header/số hàng đúng
- Export trả 204 khi không có khung

## Tái tạo

Tất cả test dùng giá trị khởi tạo RNG cố định qua `np.random.default_rng(seed)`. Trường `seed` trong request API kiểm soát tính tái tạo. Giá trị khởi tạo mặc định trong test: 42.

## Script (Xác thực không phải test)

### benchmark_rmse.py
```bash
cd backend
uv run python tests/benchmark_rmse.py
```
Số RMSE có thẩm quyền cho báo cáo. Dùng động cơ mô phỏng thực tế, không cần server.

### statistical_analysis.py
```bash
cd backend
uv run python tests/statistical_analysis.py
```
Phân tích nhiều giá trị khởi tạo (từ 1 đến 10), cho phép tính trung bình ± độ lệch chuẩn. Dùng để xác nhận tính ổn định thống kê.

### ws_smoke.py
```bash
cd backend
uv run python scripts/ws_smoke.py
```
Kiểm tra toàn bộ pipeline REST→WS. **Yêu cầu backend đã chạy trên cổng 8000.**

## Kiểm tra code

### Python (Ruff)
```bash
cd backend
uv run ruff check .
```
Quy tắc mặc định: 0 lỗi còn lại.

### JavaScript (ESLint)
```bash
cd frontend
npm run lint
```
Kết quả: 0 cảnh báo.

## Build Frontend
```bash
cd frontend
npm run build
```
Đầu ra: `frontend/dist/`. Build thành công với cảnh báo kích thước chunk bình thường.

## CI/CD

Không có. Không có pre-commit hooks. Không có GitHub Actions.
