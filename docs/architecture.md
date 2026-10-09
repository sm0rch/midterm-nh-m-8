# Kiến trúc

`app.py` và `scripts/analyze.py` nhận yêu cầu, gọi `src/pipeline.py`, rồi gọi `generate_report`. Dữ liệu được lấy trong mỗi yêu cầu; file có sẵn không phải điều kiện đầu vào.

| Thành phần | Trách nhiệm |
|---|---|
| models.py | Mã, ngày, mode, sections, P/B giả định |
| data/acquisition.py, providers.py | Giá Yahoo, khám phá/tải PDF HPG, source registry, SHA-256 |
| data/research.py | GET song song hồ sơ, tin, giá đối chiếu và ba báo cáo năm KBS |
| data/normalize.py, validate.py | Metadata kỳ/phạm vi, đơn vị và kiểm tra OHLC |
| data/issuer_pdf.py | Đọc text hoặc OCR PDF soát xét HPG; lưu bằng chứng theo checksum |
| data/quality.py | Đối chiếu chỉ tiêu với tài liệu gốc; không dùng baseline làm số liệu phân tích |
| analysis/* | Thị trường, tài chính, kịch bản định giá và kết luận có điều kiện |
| reporting/* | Biểu đồ, bảng, PDF tiếng Việt có phần tùy chọn và nguồn bắt buộc |

`analysis.json` là kết quả chung cho UI/PDF: request, acquisition, price_rows, market, company, financial, interim, valuation, conclusion, news, quality, errors, sources, status. Mỗi metric tài chính gồm giá trị, đơn vị, kỳ, formula, inputs và reason khi thiếu. JSON/CSV/raw sources theo run_id cho phép tái kiểm tra.

Lỗi từng nguồn được giữ như dữ liệu thiếu một phần. Giao diện xóa kết quả cũ khi gửi yêu cầu mới; nếu mọi dữ liệu phân tích đều thiếu thì không cấp PDF mới. Không tự lấy giá cũ thay giá mới khi mạng lỗi. Font Unicode nằm trong repository; dependency có phiên bản đã chạy kiểm chứng.
