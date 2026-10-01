# Cut List: report-phase2 consolidation (15 → 9 chapters, ~255 → ~140 pp)

Trạng thái: ĐÃ DUYỆT (2026-09-10). Thực thi theo kế hoạch 9 chương. Số dòng (line) là số dòng trong file .tex nguồn hiện tại.

> **KẾT QUẢ THỰC THI (2026-09-10, cập nhật sau round trim 2):** main.pdf = **126 trang** (dưới trần 150). Các bảng trùng lặp và các tiểu mục chỉ còn lý thuyết/thuyết minh không có bằng chứng (mutation testing, TCO, GUM, Erlang, Weibull, GLR, watchdog, Allan, DMA, RMS, HMM, CTMC, Pareto, gradient descent…) đã bị cắt theo tiêu chí của danh sách này; mỗi số liệu chuẩn (canonical) chỉ còn ở một bảng duy nhất. Biên tập chi tiết xem SESSION_LOG.md Round 7.

Quy tắc chung:
- Mỗi số liệu xác minh chỉ xuất hiện ở MỘT bảng duy nhất (bảng "canonical"); các bản lặp ở chương khác đều CUT.
- Toàn bộ bảng ước lượng lý thuyết/ datasheet (công suất, TCO, MTBF, GUM, PCRLB, vi kiến trúc ARM...) bị CUT: không có phần cứng nào được chế tạo.
- Ảnh (includegraphics) và ảnh chụp giao diện: GIỮ HẾT trừ khi trùng lặp.
- Chỉ CUT bảng; văn bản mô tả giữ lại ở mức tối thiểu cần thiết, viết lại liền mạch khi gộp chương.

## C1: Giới thiệu đề tài (từ introduction.tex)
Trước: 15 pp, 10 bảng, 9 ảnh. Dự kiến sau: ~7 pp.

Bảng:
- KEEP 313 (chỉ số hiệu suất thiết kế), 674 (so sánh hai chế độ tạo quỹ đạo), 698 (tham số cảm biến mô phỏng: canonical).
- CUT 17 (so sánh giai đoạn 1/2 → viết thành 1 đoạn văn), 136+262 (trùng bảng nhiễu C3), 365 (trùng so sánh bộ lọc C3), 490 (trùng tham số mô phỏng C7), 530/552/562 (trùng bảng RMSE C7), 593 (trùng cross-over C7), 628 (trùng phân rã thời gian C6).

Ảnh/TikZ:
- KEEP 114 (kiến trúc 4 tầng), 394 (use-case).
- CUT 440 (chuỗi tọa độ: trùng sơ đồ C3), các ảnh kết quả (606/617/643/652) chuyển sang C7 nếu chưa có.
- Giữ 9 ảnh gốc trừ trùng; ảnh giao diện chuyển về C6.

Subsection: gộp 1.3–1.5 thành một mục "Tổng quan hệ thống"; giữ nguyên 1.1, 1.2, 1.9 (ví dụ tính toán số liệu), 1.10.

## C2: Thiết kế tổng thể hệ thống (từ system-design.tex)
Trước: 15 pp, 8 bảng, 5 ảnh, 1 TikZ. Dự kiến sau: ~11 pp.

Bảng:
- KEEP 59 (kiến trúc phân lớp: canonical), 428 (tĩnh vs thời gian thực), 457 (mô hình nhiễu cảm biến: canonical), 501 (chức năng quản lý phiên REST: canonical), 618 (mảng động vs bộ đệm vòng), 648 (Exponential Backoff).
- MERGE 123 + 584 (trường JSON: gộp thành một bảng).
- CUT: không có bảng nào cắt hoàn toàn.

Ảnh/TikZ: KEEP tất cả (209 sơ đồ lớp, 238/257 quy trình, 373/384 giao diện).

Subsection: giữ hầu hết; gộp các subsubsection mô tả JSON thành một mục.

## C3: Chuỗi xử lý tọa độ và hợp nhất cảm biến (từ coordinate-pipeline.tex)
Trước: 15 pp, 7 bảng, 4 ảnh. Dự kiến sau: ~13 pp.

Bảng:
- KEEP 22 (chuỗi LLA-ECEF-ENU: canonical), 168 (1-sigma từng cảm biến: canonical), 227 (tổng hợp đóng góp sai số theo cự ly: canonical), 347 (σa theo loại mục tiêu: canonical), 490 (chu trình Kalman), 591 (thời gian thực thi mỗi bước), 618 (Kalman vs alpha-beta: canonical), 737 (tóm tắt tham số thiết kế).
- MERGE 218 vào 227.
- CUT 694, 719 (độ nhạy α: trùng C4).

Ảnh: KEEP cả 4.

Subsection: giữ nguyên toàn bộ (chương lõi, ít cắt).

## C4: Thuật toán lọc và thích nghi (từ adaptive-filtering.tex)
Trước: 15 pp, 25 bảng, 2 TikZ. Dự kiến sau: ~11 pp.

Bảng:
- KEEP 61 (đặc tuyến độ lợi K: chuyển thành hình nếu là bảng số), 163 (nghiệm xác lập Riccati), 290 (so sánh chiến lược R: canonical), 429 (độ nhạy R_cross: canonical cho phân tích cross-over), 609 (độ nhạy α: canonical cho bảng α), 762 (Joseph vs chuẩn), 792 (Kalman vs vi phân trực tiếp khi GNSS nhảy bước), 864 (ước lượng thời gian nhúng: GIỮ, đã gán nhãn ước lượng giải tích), 902 (cổng χ² và tỷ lệ loại nhiễu: canonical).

- CUT 119 (dump độ bất định theo R), 218 (điểm cực miền Z), 258 (đáp ứng quá độ), 318+365 (phân rã thời gian: trùng C6), 383 (đặc tính cảm biến: trùng C3), 409 (IID vs nhiễu màu → 1 đoạn văn), 463 (biên cứng vs mềm: trùng C5), 497 (trùng 347), 524 (drone gió: trùng C7), 547 (162 ca kiểm thử: trùng C8), 654 (khứ hồi 10.000 chu kỳ: trùng C8), 685 (RAM: cắt), 723 (confusion matrix), 925 (UKF/PF → 1 đoạn văn), 968 (Gramian), 1007 (PCRLB), 1047 (tiến trình P_k).

TikZ: KEEP 2 (đặc tuyến/biểu đồ phân phối).

Subsection: gộp các mục phân tích lý thuyết (ổn định Z-domain, PCRLB, Gramian, UKF/PF) thành một mục "Phân tích ổn định và vị trí trong họ bộ lọc" ngắn.

## C5: Dữ liệu thực và tính chân thực quỹ đạo (real-world-data + trajectory-realism)
Trước: 15 + 17 = 32 pp, 22 + 18 = 40 bảng. Dự kiến sau: ~13 pp.

Bảng real-world-data:
- KEEP 33 (Geolife 252 phân đoạn: canonical), 80 (AMIT), 130 (giới hạn DJI Matrice 100: canonical), 326 (phân cấp đường HCMC), 480 (38 ca kiểm thử dữ liệu thực: canonical).
- CUT 176, 227 (RMSE thực nghiệm → chỉ giữ ở C7), 274, 304, 355, 391, 427, 456, 512, 583 (trùng bảng 6 khiếm khuyết của trajectory-realism 14), 608, 644, 671, 698, 727, 756, 784, 812.

Bảng trajectory-realism:
- KEEP 14 (phân loại 6 khiếm khuyết + giải pháp: canonical), 276 (hội tụ khởi tạo vận tốc: minh chứng fix #6), 469 (động học quay vòng xe máy).
- CUT 376 (quét α-β: trùng C7), 405, 431, 507 (trùng 130), 541, 573, 596 (trùng C8), 623 (trùng C7), 687 (trùng C6), 753, 783, 811, 846, 874.

Subsection: gộp 22 bảng "đo đạc lý thuyết" thành văn bản tóm tắt; mỗi fix giữ đúng một bằng chứng định lượng.

## C6: Chuỗi thời gian thực, tối ưu và xuất dữ liệu (realtime-pipeline + performance-optimization + data-export-analysis)
Trước: ~21 + 32 + 24 = 77 bảng. Dự kiến sau: ~14 pp.

Bảng realtime-pipeline:
- KEEP 718 (vòng đời phiên: canonical).
- CUT còn lại; caption của các bảng này nằm xa vị trí begin{table} nên khi thực thi sẽ kiểm tra lại: nếu bảng nào mang số canonical (59 µs, 82 %, 6 %) thì chuyển sang C7 thay vì cắt.

Bảng performance-optimization:
- KEEP 42 (phân rã thời gian 59 µs / 82 % / 6 %: canonical), 166 (trước/sau 3 tối ưu), 325 (REST vs WebSocket băng thông/độ trễ), 654 (KD-tree vs quét tuyến tính), 680 (tile caching), 872 (TCP_NODELAY), 1126 (ổn định số học 1.000.000 chu kỳ: thí nghiệm phần mềm đo được).
- CUT 71, 218, 295, 349, 384, 411, 484, 568, 600, 633, 703, 755, 790, 818, 845, 899, 941, 964, 1002, 1027, 1057, 1090, 1156, 1186, 1216, 1242 (trùng 872), 1266 (trùng 872).

Bảng data-export-analysis:
- KEEP 11 (cấu trúc cột CSV), 839 (trường hợp đặc biệt khi xuất), 962 (dung lượng dữ liệu phiên 120 s).
- CUT 126, 151, 401, 482, 512, 545, 575, 616, 644, 670, 713, 747, 773, 803, 862, 887, 912, 936, 989, 1014, 1045 (đa số trùng bảng RMSE của C7).

Subsection: cắt toàn bộ tiểu mục ước lượng vi kiến trúc (AoS/SoA, branch prediction, SIMD, Slab/Heap, BER, công suất pin): không có phần cứng chế tạo.

## C7: Kết quả, thống kê và so sánh (performance-evaluation + statistical-analysis + comparative-ablation)
Trước: 13 + 21 + 34 = 68 bảng. Dự kiến sau: ~16 pp.

Bảng performance-evaluation:
- KEEP 43 (tham số mô phỏng chuẩn: canonical cho tham số; thay thế bảng 698 của C1 đã chuyển sang CUT), 72 (nhiễu cảm biến: canonical), 234 (RMSE seed=42: canonical), 444 (tóm tắt phát hiện chính), 467 (đa seed trung bình ± độ lệch chuẩn: canonical).
- MERGE 123 + 176 + 210 thành một bảng "tham số động học ba loại mục tiêu".
- CUT 523, 545, 579, 650, 678 (trùng bảng thời gian C6).

Bảng statistical-analysis:
- KEEP 114 (thống kê mô tả đa seed: canonical), 209 (kiểm định Student), 325 (độ nhạy α: canonical), 413 (ảnh hưởng bán kính biên), 616 (xe máy động học vs mạng đường OSM), 710 (độ nhạy tần số trích mẫu), 747 (EKF trực tiếp vs phân tầng ENU).
- CUT 26 (trùng 43), 86 (dump theo từng seed), 154 (gộp vào 114), 244, 474, 515, 543, 590, 658, 686, 780, 872, 917, 953.

Bảng comparative-ablation:
- KEEP 67 (ma trận cắt bỏ đa tầng: canonical), 437 (ANOVA), 457 (Tukey HSD), 979 (Shapiro-Wilk chuỗi đổi mới), 1256 (nhiễu trắng vs OU: minh chứng fix #5).
- CUT 13, 232, 287, 192, 213, 484, 546, 571, 606, 669, 698, 722, 750, 785, 823, 858, 887, 912, 946, 1015, 1049, 1085, 1116, 1155, 1192, 1225, 1290, 1324, 1358.

## C8: Độ tin cậy, kiểm thử và trường hợp biên (integration-testing + reliability-edge-cases)
Trước: 31 + 32 = 63 bảng. Dự kiến sau: ~12 pp.

Bảng integration-testing:
- KEEP 78 (REST vs kênh hai chiều), 207 (cấu trúc 163 ca kiểm thử: canonical), 317 (khứ hồi trắc địa), 446 (thời gian thao tác đồ thị 337K nút), 470 (ma trận an ninh đa lớp), 631 (toàn vẹn CSV theo thời gian), 703 (10 phiên bất đồng bộ), 839 (hiệu năng giao diện trước/sau tối ưu).
- CUT 261, 361, 394, 417 (trùng C6), 527 (trùng 317), 554, 581, 611, 655, 680, 751 (trùng C5), 792, 861, 899, 962 (trùng C6), 998, 1030, 1053, 1081, 1133 (trùng 207), 1162, 1191, 1222, 1257.

Bảng reliability-edge-cases:
- KEEP 11 (phân loại trường hợp biên: canonical), 88 (trọng số thích nghi khi suy giảm cảm biến), 708 (cổng loại trừ nhiễu đột biến), 847 (phát hiện/cô lập cảm biến lỗi).
- CUT 149, 179, 359, 565, 631, 736, 782, 816, 871, 907, 937, 967, 991, 1017, 1067, 1096 (trùng C4), 1124, 1156, 1185, 1225, 1260, 1298, 1329 (trùng C7), 1361, 1390, 1425, 1455, 1483.

## C9: Kết luận và hướng phát triển (conclusion-future)
Trước: 17 pp, ~35 bảng. Dự kiến sau: ~10 pp.

Bảng:
- KEEP 54 (thống kê tổng quan hệ thống: canonical), 364 (đối chiếu với các phương pháp định vị hiện có), 909 (đặc tả HAL: thiết kế tương lai, ghi rõ là đặc tả), 1180 (chuẩn giao tiếp nhúng: thiết kế tương lai, ghi rõ là đặc tả).
- CUT toàn bộ còn lại (86, 312, 453, 488, 520, 553, 576, 604, 628, 657, 687, 718, 747, 772, 803, 832, 857, 884, 945, 979, 1015, 1044, 1079, 1111, 1150, 1211, 1308, 1338, 1371, 1399, 1428): phần lớn là bảng ước lượng lý thuyết (GUM, TCO, công suất, nhiệt, vô tuyến) không có phần cứng chứng minh.

## Tổng hợp

| Chương | Bảng trước | Bảng sau | Trang trước | Trang dự kiến |
|---|---|---|---|---|
| C1 | 10 | 3 | 15 | ~7 |
| C2 | 8 | 7 | 15 | ~11 |
| C3 | 7 | 8 | 15 | ~13 |
| C4 | 25 | 9 | 15 | ~11 |
| C5 | 40 | 8 | 32 | ~13 |
| C6 | 77 | 12 | ~45 | ~14 |
| C7 | 68 | 18 | ~60 | ~16 |
| C8 | 63 | 12 | ~50 | ~12 |
| C9 | 35 | 4 | 17 | ~10 |
| Tổng | ~333 | ~81 | 251 (nội dung) | ~107 + front/back ≈ 130–140 |

Ghi chú thực thi:
- Ảnh (includegraphics): giữ toàn bộ; chỉ cắt TikZ trùng ảnh.
- Khi gộp chương, mọi `\ref`/`\label`/`\cite` được ánh xạ lại; số canonical mỗi chủ đề chỉ xuất hiện ở một bảng duy nhất.
- Bảng realtime-pipeline có caption xa vị trí begin{table}: kiểm tra lại từng bảng lúc thực thi.
- defense-prep tác động: các Q&A nhắc tới TCO, MTBF, GUM, nhiệt, vô tuyến, watchdog → điều chỉnh hoặc bỏ vì bằng chứng đã cắt; Q&A về 1M chu kỳ, cross-over 794 m, 59 µs, đa seed → giữ (bảng canonical còn lại).

