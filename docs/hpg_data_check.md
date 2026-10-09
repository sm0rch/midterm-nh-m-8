# Kiểm chứng dữ liệu thực — 09/10/2026

HPG: 261 phiên 2025-10-09 → 2026-10-08; giá đóng cửa cuối 20.150 VND. Hai nguồn Yahoo/KBS khớp 20/20 phiên đối chiếu. Bộ lấy tự động tải hai PDF hợp nhất từ Hòa Phát; bản soát xét bán niên được OCR và kiểm tra bảng cân đối.

| Chỉ tiêu HPG | Giá trị |
|---|---:|
| Doanh thu thuần 2025 | 156.116,09 tỷ VND |
| LNST hợp nhất 2025 | 15.514,93 tỷ VND |
| Doanh thu thuần 6T2026 | 108.059,75 tỷ VND |
| LNST hợp nhất 6T2026 | 15.480,39 tỷ VND |
| CFO 6T2026 | 12.641,70 tỷ VND |

Doanh thu và LNST năm đối chiếu phần tóm tắt tài chính báo cáo thường niên HPG 2025 (dung sai 1 tỷ do làm tròn). Tài sản/nợ/vốn cuối 2025 đối chiếu cột đầu kỳ của PDF bán niên, có vị trí và dòng OCR. Năm/6 tháng không cộng để tính TTM. Giá trị tiền nguồn KBS là nghìn VND; tiền PDF là VND. Doanh thu thuần không thay bằng tổng doanh thu từ bài tin.

FPT: các chỉ tiêu năm 2025 chọn đối chiếu khớp báo cáo thường niên, nhưng giá ngày 21/09 lệch khoảng 1,83%, ngày 22/09 lệch khoảng 0,30%; **chặn định giá**, giữ nhận định thị trường có cảnh báo.

VNM: 20/20 phiên đóng cửa khớp; LNST 2025 khớp giá trị làm tròn 9.414 tỷ trong báo cáo thường niên. Doanh thu thuần 63.645,89 tỷ không đồng nhất tổng doanh thu 63.724 tỷ, nên không lấy con số tổng doanh thu làm baseline doanh thu thuần.

Đối chiếu chỉ xác nhận những chỉ tiêu/kỳ được liệt kê. `submission/acceptance.json` lưu mã lượt chạy, số kiểm tra, sai lệch và trạng thái; PDF mẫu chứa nguồn chi tiết. Nút Streamlit với HPG đã chạy thật, không ngoại lệ, tự lấy dữ liệu và xuất PDF. 26 kiểm thử offline đạt.
