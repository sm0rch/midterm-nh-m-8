# Demo 4–5 phút

1. Chạy `python -m streamlit run app.py`. Để mã HPG, từ 2025-10-09, ngày phân tích 2026-10-09, đầy đủ, tất cả các phần. Bấm **Phân tích**. Không nhập file/data. Lần đầu cần Internet và có thể chờ tải PDF/OCR.
2. Chỉ giá cuối ngày 08/10, 261 phiên và kết quả đối chiếu hai nguồn. Mở Tài chính để xem năm 2025 và 6 tháng 2026 riêng kỳ.
3. Mở Nguồn dữ liệu, chỉ công thức ROE và đầu vào; chỉ trang 12/13 của PDF gốc HPG cho doanh thu/LNST/CFO.
4. Mở kịch bản P/B: giải thích giả định người dùng và số CP hiện tại, thay P/B cơ sở rồi phân tích lại để thấy độ nhạy.
5. Tải PDF phân tích, đối chiếu số giá/LNST với UI. Chọn Tóm tắt và chỉ market/financial/risks, chạy lại: PDF bỏ các phần khác nhưng giữ phương pháp/nguồn.
6. Đổi VNM: dữ liệu và nhận định khác HPG. Đổi FPT: hai phiên giá không khớp nguồn, báo cáo ghi thiếu một phần và chặn P/B.
7. Nhập mã sai hoặc ngắt nguồn: ứng dụng báo lỗi, không dùng kết quả lượt trước làm kết quả mới.

Mẫu đã tạo trong `outputs/pdf/`; minh chứng kết quả chạy trong `submission/acceptance.json`, `submission/ui_check.json`. Danh sách hạn chế nằm trong README; không tuyên bố mọi ngành đã được kiểm chứng.
