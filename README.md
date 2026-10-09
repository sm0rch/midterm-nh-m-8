# StockInsight

Ứng dụng phân tích cổ phiếu Việt Nam và tự tạo PDF theo nhu cầu người dùng. **Không cần chuẩn bị data**: mỗi lần bấm Phân tích, chương trình tự lấy giá, tài chính, hồ sơ doanh nghiệp, tin công bố và đối chiếu nguồn.

## Chạy ứng dụng

Python 3.11+; máy kiểm thử dùng Python 3.12.10. Chạy trong thư mục dự án:

```powershell
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

Nhập HPG (hoặc mã Việt Nam có dữ liệu Yahoo/KBS), chọn khoảng ngày, bản đầy đủ/tóm tắt, phần cần xuất và P/B giả định. Bấm **Phân tích**, sau đó **Tải báo cáo phân tích PDF**. Luồng chính không yêu cầu chạy script lấy dữ liệu riêng.

Để đọc PDF scan bán niên HPG tự động, cài Tesseract OCR có gói `vie` và `eng`, thêm `tesseract` vào PATH. Windows cũng nhận đường dẫn `C:/Program Files/Tesseract-OCR/tesseract.exe`. Thiếu OCR: hệ thống báo thiếu phần bán niên và vẫn dùng số liệu năm hợp lệ. Tệp PDF gốc tải lần đầu có thể mất vài phút; bản lưu được kiểm tra SHA-256 và thời hạn 24 giờ trước khi dùng lại. Giá, tài chính và danh sách công bố vẫn được truy cập mới mỗi lượt.

## Dùng dòng lệnh (tùy chọn)

```powershell
python -m scripts.analyze HPG --start 2025-10-09 --as-of 2026-10-09
python -m scripts.analyze VNM --mode summary --sections market financial risks --target-pb 2.0
python -m unittest discover -s tests -v
```

Tệp theo lượt chạy nằm tại `outputs/runs/<run_id>/`: request.json, validation.json, acquisition.json, sources.json, analysis.json, charts/, và `<ticker>_report.pdf`. Dữ liệu gốc và bảng chuẩn nằm tại `data/`. PDF và số liệu giao diện dùng chung một kết quả tính toán. PDF tiếng Việt dùng font DejaVu có giấy phép trong `assets/fonts/LICENSE.txt`.

## Phân tích và nguồn

- Giá cuối ngày Yahoo Finance; giá đóng cửa tối đa 20 phiên gần nhất được đối chiếu KBS. Luôn bỏ ngày hiện tại theo UTC+7, kể cả sau giờ giao dịch.
- Lợi suất theo Yahoo Adj Close, MA20/MA50, drawdown, biến động năm hóa và khối lượng. Chuỗi điều chỉnh không đồng nghĩa lợi nhuận thực nhận sau phí/thuế.
- Báo cáo năm qua KBS: doanh thu thuần, LNST, tài sản, vốn, CFO, tăng trưởng, ROE hợp nhất, biên lợi nhuận và nợ vay/vốn khi phù hợp. Bán niên HPG được đọc trực tiếp từ PDF soát xét của doanh nghiệp bằng OCR.
- P/B tham chiếu và ba kịch bản theo giả định người dùng. Chặn khi giá lệch nguồn, thiếu vốn/số CP, hoặc phân tích quá khứ với số CP hiện tại. Không tính P/E TTM từ API quý có kỳ không rõ ràng.
- Tin công bố có ngày và liên kết. Nhận định được tạo bằng quy tắc từ dữ liệu; không tự suy diễn tác động từ tiêu đề tin.

## Kiểm chứng ngày 09/10/2026

26 kiểm thử offline đạt. Nút Phân tích thật trên Streamlit đã tự lấy 261 phiên HPG, đọc bán niên và tạo PDF, không có ngoại lệ. HPG và VNM khớp 20/20 giá đóng cửa được đối chiếu. FPT lệch 2/20 phiên (21–22/09/2026), vì vậy định giá bị chặn và báo cáo ghi trạng thái thiếu một phần. Số liệu năm 2025 khớp **các chỉ tiêu chọn đối chiếu**, không phải chứng nhận toàn bộ dữ liệu. Xem `submission/acceptance.json` và `docs/hpg_data_check.md`.

Báo cáo mẫu: `outputs/pdf/HPG_report.pdf`, `FPT_report.pdf`, `VNM_report.pdf`. Các mẫu đã được kiểm tra chữ tiếng Việt và bố cục trang.

## Giới hạn

Mã cổ phiếu là tham số, không cố định HPG; khả năng có số liệu phụ thuộc nguồn. Đã kiểm chứng ba doanh nghiệp phi tài chính. Ngân hàng/chứng khoán chỉ nhận các chỉ tiêu ánh xạ được; không áp tỷ số phi tài chính và chưa có mô hình chuyên ngành hoàn chỉnh. API công khai có thể thay đổi hoặc giới hạn truy cập. Baseline trong `config/verification_baselines.json` là số tham chiếu đã đọc từ tài liệu gốc, **không thay dữ liệu tự lấy** và chỉ áp dụng đúng kỳ. Không dùng dữ liệu giả khi nguồn lỗi.

`projectcontext.md` ghi phạm vi đề gốc; `task.md` ghi hạng mục đã làm. Đề gốc và đề xuất triển khai trong `docs/references/` được giữ riêng.
