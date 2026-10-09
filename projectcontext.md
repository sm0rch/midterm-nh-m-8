# Project context — StockInsight

Cập nhật 09/10/2026. Mục tiêu: ứng dụng nhận mã cổ phiếu và nhu cầu nội dung, tự lấy dữ liệu, phân tích cơ hội/rủi ro, tạo báo cáo PDF tiếng Việt có nguồn và phương pháp rõ ràng.

## Yêu cầu và phạm vi

Đề gốc một trang: `docs/references/261BFF401101_Dethigiuaky.pdf`. Yêu cầu thiết kế, xây dựng và chạy hệ thống phân tích cơ hội đầu tư cho một mã cổ phiếu bất kỳ; tự động tạo PDF theo nhu cầu người dùng; dữ liệu chính xác, phương pháp phù hợp, có tính sáng tạo. Đề không bắt buộc AI, DCF, realtime, triển khai Internet hay số trang cố định.

`docs/references/implementation_proposal.txt` là đề xuất kỹ thuật người dùng cung cấp, không phải mọi mục đều là yêu cầu bắt buộc của đề. Yêu cầu trực tiếp bổ sung: code phải tự lấy data, thử HPG trước, tạo context/task và đưa dự án lên repository `TranThanhPhu39/stock_report_pdf`. Repository đã được khởi tạo/push trong giai đoạn trước.

## Thiết kế đã thực hiện

Python + Streamlit + pandas + matplotlib + ReportLab + PyMuPDF; Tesseract vie/eng để đọc PDF scan. Mã là tham số; phạm vi nguồn hiện tại là cổ phiếu Việt Nam có Yahoo/KBS. Kiểm chứng HPG, FPT, VNM, trọng tâm doanh nghiệp phi tài chính. Những chỉ tiêu không phù hợp/thiếu dữ liệu được bỏ kèm lý do.

Luồng: AnalysisRequest → acquire giá/PDF → collect_research tài chính/hồ sơ/tin/giá đối chiếu → chuẩn hóa kỳ/đơn vị → phân tích → kiểm tra tài chính → kết luận → lưu analysis.json → giao diện và PDF từ cùng kết quả. UI/CLI tự gọi luồng, không cần file CSV có sẵn.

Nguồn: Yahoo chart cho giá; KBS cho báo cáo năm/hồ sơ/tin và giá đối chiếu; Hòa Phát cho PDF hợp nhất soát xét bán niên. Các giá trị đầu vào có source_id, kỳ, ngày công bố, đơn vị và vị trí nguồn; kết quả chỉ tiêu có công thức và inputs. Giá hiện tại luôn dùng phiên trước ngày hiện tại UTC+7. Financial publication và source revision sau ngày phân tích bị loại.

API KBS pageSize 1/2 có thể gắn dữ liệu cũ vào năm mới; dữ liệu quý có Head trùng ID. Chỉ nhận bốn kỳ năm có ánh xạ ID 1..4, năm riêng biệt và cùng phạm vi; không cộng quý lũy kế hoặc tuyên bố P/E TTM. ROE dùng LNST hợp nhất / VCSH hợp nhất bình quân. Định giá là kịch bản P/B có giả định vốn năm giữ nguyên trên số CP hiện tại, không phải dự báo giá.

## Kết quả kiểm chứng

26 kiểm thử offline đạt; giao diện thật tự lấy 261 phiên HPG và tạo PDF không lỗi. HPG/VNM khớp 20 phiên giá, FPT có hai phiên lệch và định giá bị chặn. Các tài chính năm chọn đối chiếu khớp tài liệu gốc; bán niên HPG có kiểm tra tài sản = nợ + vốn và cột đầu năm đối chiếu số liệu năm 2025. Ba PDF mẫu có nguồn và giới hạn. Chưa chứng nhận mọi cổ phiếu, mọi kỳ và mọi ngành.

## Quyết định phát triển

Không thay null bằng 0 hoặc dùng số liệu giả khi nguồn lỗi. Không dùng số CP hiện tại cho định giá quá khứ. Không coi số liệu OCR là hợp lệ khi thiếu kiểm tra bảng cân đối. Giá lệch nguồn thì chặn định giá. Người dùng chọn phần và mức chi tiết; nguồn, phương pháp và trạng thái dữ liệu luôn giữ trong PDF. PDF gốc được cache 24 giờ có SHA-256; OCR cache theo checksum nội dung. Font DejaVu có giấy phép phân phối đi kèm.

Các mở rộng không bắt buộc còn lại: mô hình ngân hàng/chứng khoán chuyên sâu; tự tìm PDF mọi doanh nghiệp; bốn quý đã xác minh để tính TTM/P/E; realtime; triển khai web; AI đọc toàn văn tin.
