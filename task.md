# Task — StockInsight

Cập nhật 09/10/2026. Các yêu cầu chính đã có luồng chạy thực; không coi đề xuất mở rộng là điều kiện bắt buộc của đề gốc.

## Đã hoàn thành

- [x] Đọc đề PDF và đề xuất, phân biệt yêu cầu người dùng với nội dung tài liệu.
- [x] Tạo cây thư mục, context/task và repository GitHub.
- [x] UI nhận mã, khoảng ngày, ngày phân tích, mức chi tiết, phần PDF, P/B giả định.
- [x] Code tự lấy giá, tài chính năm, hồ sơ doanh nghiệp và tin công bố, không yêu cầu data nhập tay.
- [x] Tự tìm/tải PDF hợp nhất HPG; cache 24h kiểm tra checksum; đọc PDF scan bằng OCR.
- [x] Giữ raw sources, kỳ, đơn vị, ngày công bố/cập nhật, phạm vi và vị trí nguồn.
- [x] Kiểm tra OHLC, ngày trùng, tiền/volume, metadata bốn kỳ năm; chặn phản hồi kỳ mơ hồ.
- [x] Đối chiếu giá nguồn thứ hai và chỉ tiêu tài chính chọn từ tài liệu gốc; ghi rõ mức kiểm chứng.
- [x] Tính return/MA/drawdown/volatility, tăng trưởng, ROE bình quân, biên lợi nhuận, nợ/vốn, CFO/LNST khi phù hợp.
- [x] Không trộn hợp nhất/đơn lẻ, năm/quý lũy kế; giữ null và lý do cho chỉ tiêu thiếu.
- [x] P/B tham chiếu, ba kịch bản người dùng; chặn khi dữ liệu không đạt điều kiện.
- [x] Nhận định có dữ kiện và điều kiện theo dõi; tin có ngày/link, không suy diễn toàn văn.
- [x] Xuất PDF tiếng Việt có biểu đồ/bảng/nguồn; thực sự áp dụng summary/full và phần chọn.
- [x] UI/PDF dùng chung AnalysisResult; lưu request, validation, acquisition, sources, analysis, chart và PDF theo lượt.
- [x] Font Unicode có giấy phép, dependency có phiên bản kiểm thử, README và tài liệu phương pháp/demo cập nhật.
- [x] 26 kiểm thử offline đạt.
- [x] Streamlit HPG thật: 261 phiên, OCR bán niên hợp lệ, PDF tồn tại, không ngoại lệ.
- [x] Streamlit FPT thật: chọn summary/market/financial/risks, PDF bỏ phần khác, định giá bị chặn đúng.
- [x] Yêu cầu sai xóa kết quả/PDF lượt trước, không trả kết quả cũ.
- [x] Ba lượt dữ liệu thực HPG/FPT/VNM và ba PDF mẫu; xem acceptance.json.
- [x] Kiểm tra hiển thị tất cả trang PDF mẫu, chữ tiếng Việt, bảng và nguồn.

## Hạn chế đã công bố

FPT có hai phiên giá lệch nguồn, được ghi cảnh báo/chặn P/B. Baseline chỉ kiểm chứng một số chỉ tiêu đúng kỳ. Bộ tỷ số đầy đủ đã kiểm thử ở doanh nghiệp phi tài chính; ngân hàng/chứng khoán không nhận tỷ số phi tài chính và cần mô hình riêng nếu mở rộng. PDF scan bán niên hiện tự trích chỉ cho HPG. Thiếu nguồn/thiếu OCR được thông báo, không dùng dữ liệu giả.

## Mở rộng ngoài phạm vi bắt buộc

- [ ] Tự khám phá và kiểm tra PDF cho mọi doanh nghiệp.
- [ ] Mô hình chuyên ngành ngân hàng/chứng khoán.
- [ ] Adapter bốn quý độc lập đã xác minh để tính TTM/P/E.
- [ ] Phân tích toàn văn tin, dự báo hoặc DCF có giả định được thẩm định.
- [ ] Realtime/triển khai Internet nếu người dùng yêu cầu.

Bộ bàn giao: README, projectcontext/task, docs, outputs/pdf và submission. Minh chứng snapshot trong submission/evidence là kết quả cố định của lượt kiểm thử, không phải nguồn đầu vào bắt buộc của chương trình.
