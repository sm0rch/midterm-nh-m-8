# Từ điển dữ liệu

| Đối tượng | Trường chính / đơn vị |
|---|---|
| Request | ticker, start/as_of ISO date, mode summary/full, sections, target_pb |
| Price | date, open/high/low/close VND/CP, adjusted_close do Yahoo cung cấp, volume CP, price_basis |
| Company | name, exchange, website, business, outstanding_shares CP, snapshot_at, source_id |
| Financial field | value VND (EPS VND_per_share), source_field/source_label/source_value, unit_multiplier, period, published_at, statement_scope, source_id |
| Financial metric | key, label, value, unit, period, formula, inputs, reason |
| Interim field | value/previous VND, period, published_at, source_id, page, ocr_line |
| News | title, published_at, url, source_id, summary |
| Source | source_id, url_or_file, retrieved_at có timezone, page_or_table, notes |
| Quality | price_check.status/checks, financial_check.status/checks, warnings |
| Result | status analyzed/partial; errors gồm stage và message |

Thiếu là null; không gán 0. Kỳ báo cáo năm là năm dương lịch theo metadata nguồn. Phạm vi consolidated/parent/separate/unknown; không trộn phạm vi. `published_at` là ngày công bố, `retrieved_at` là thời điểm lấy; hai trường không thay thế nhau.

`interim.fields.previous`: revenue/net_profit/gross_profit/parent_profit/cfo là 6 tháng cùng kỳ; assets/equity/liabilities/debt là số đầu năm. Chỉ bảng 6 tháng có các dòng kết quả kinh doanh và CFO, không đặt cột đầu năm dưới nhãn cùng kỳ.

`market.chart_prices`: Adj Close chuẩn hóa về close cuối, dùng MA và biểu đồ. `market.latest_close_vnd` là OHLC close nguồn, không phải Adj Close. `valuation.reference_price_vnd` là quy đổi giả định P/B, không được ghi thành dự báo giá.
