# Phương pháp đã triển khai

## Giá

Dùng Yahoo OHLC (VND/cổ phiếu) và Adj Close riêng. Giá ngày hiện tại theo UTC+7 bị loại. Kiểm tra ngày trùng, giá hữu hạn/dương, high/low, volume nguyên không âm. Đối chiếu tối đa 20 phiên đóng cửa mới nhất với KBS, dung sai 0,1%; các phiên lệch được ghi trong PDF.

Biến động khoảng chọn = (Adj Close cuối / đầu − 1) × 100. Drawdown = min(Adj Close / đỉnh lũy kế − 1) × 100. Biến động năm hóa = std mẫu(lợi suất log ngày) × sqrt(252) × 100. MA20/MA50 tính trên Adj Close nhân hệ số close cuối / Adj Close cuối; chỉ tính khi đủ phiên. Thiếu Adj Close thì không hiển thị return/drawdown/volatility; không tự xác nhận lịch sử điều chỉnh của nguồn.

## Tài chính

Chỉ nhận API KBS bốn kỳ năm riêng biệt với Head ID 1..4; metadata công bố/cập nhật không sau ngày phân tích. Đơn vị tiền gốc là nghìn VND → VND ×1000; EPS là VND/CP giữ nguyên. Hợp nhất/đơn lẻ/công ty mẹ phải nhất quán. Tài sản phải khớp nợ + vốn với dung sai 0,1%.

| Chỉ tiêu | Công thức |
|---|---|
| Tăng trưởng | (Giá trị năm hiện tại / năm trước cùng phạm vi − 1) ×100; kỳ gốc phải dương |
| ROE hợp nhất | LNST hợp nhất / ((VCSH cuối năm + VCSH đầu năm)/2) ×100 |
| Biên gộp / ròng | Lợi nhuận gộp / doanh thu thuần; LNST / doanh thu thuần; ×100 |
| CFO/LNST | Dòng tiền kinh doanh / LNST dương |
| Nợ vay/vốn | (Nợ vay ngắn + dài hạn) / VCSH dương |

Ba tỷ số biên/CFO/nợ vay chỉ áp dụng doanh nghiệp phi tài chính. Chỉ tiêu thiếu, không cùng kỳ hoặc mẫu số không phù hợp là null và có lý do, không phải 0.

PDF hợp nhất soát xét HPG được OCR tự động. Tiền ghi bằng VND; giữ dòng nhận dạng và trang PDF. Kiểm tra assets = liabilities + equity (0,01%) và đối chiếu cột đầu năm với tài chính năm trước. Bán niên kết quả kinh doanh/CFO so với 6 tháng cùng kỳ; bảng cân đối so với đầu năm. Không cộng bán niên với Q2 để tính TTM.

## Kịch bản P/B

BVPS tham chiếu = (VCSH hợp nhất − lợi ích cổ đông không kiểm soát) / số CP hiện tại. P/B tham chiếu = giá đóng cửa / BVPS. Giá trị kịch bản = BVPS × P/B do người dùng giả định; thận trọng/cơ sở/thuận lợi tương ứng 80%/100%/120% giả định cơ sở. Đây là phân tích độ nhạy; giả định vốn cuối năm giữ nguyên trên số CP hiện tại, không phải dự báo giá trị nội tại. Chặn nếu giá không khớp nguồn, số CP/vốn thiếu hoặc dùng ngày quá khứ với số CP hiện tại. Không tính P/E TTM vì API quý chưa có ánh xạ đủ tin cậy.

## Nhận định và đối chiếu

Quy tắc dùng tăng trưởng, CFO/LNST, vị trí so với MA, drawdown và HPG bán niên để trình bày dữ kiện → điều kiện theo dõi. Không áp ngưỡng mua/bán chung. Tin chỉ là danh sách công bố có ngày/liên kết; chưa suy diễn nội dung toàn văn.

Baseline tài chính là tham chiếu đã đọc từ báo cáo thường niên gốc, riêng đúng mã/năm/chỉ tiêu. Sai lệch quá dung sai chặn tài chính/định giá. Không có baseline thì trạng thái chưa đối chiếu độc lập, không tuyên bố khớp. Các phép kiểm tra không chứng nhận toàn bộ số liệu.
