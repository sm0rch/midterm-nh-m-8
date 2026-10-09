"""Selectable Vietnamese PDF from the saved analysis result."""
from pathlib import Path
import sys
from xml.sax.saxutils import escape
from src.models import SECTION_LABELS
from src.reporting.charts import market_chart

ROOT=Path(__file__).resolve().parents[2]
try:
    import reportlab
except ImportError:
    sys.path.insert(0,str(ROOT/".vendor"))
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, KeepTogether

def formatted(value, unit=""):
    if value is None:return "Chưa đủ dữ liệu"
    if unit=="VND":return f"{value/1e9:,.2f} tỷ VND"
    if unit=="VND/share":return f"{value:,.0f} VND"
    return f"{value:,.2f}"+(f" {unit}" if unit else "")

def generate_report(result: dict, path: Path | None=None) -> Path:
    request=result["request"];run_id=result["acquisition"]["run_id"]
    path=Path(path) if path else ROOT/"outputs/runs"/run_id/f"{request['ticker']}_report.pdf"
    path.parent.mkdir(parents=True,exist_ok=True)
    for name,file in [("DV","DejaVuSans.ttf"),("DV-Bold","DejaVuSans-Bold.ttf")]:
        if name not in pdfmetrics.getRegisteredFontNames():pdfmetrics.registerFont(TTFont(name,str(ROOT/"assets/fonts"/file)))
    pdfmetrics.registerFontFamily("DV",normal="DV",bold="DV-Bold",italic="DV",boldItalic="DV-Bold")
    styles=getSampleStyleSheet()
    styles.add(ParagraphStyle(name="BodyVN",fontName="DV",fontSize=9,leading=14,spaceAfter=6,textColor=colors.HexColor("#263640")))
    styles.add(ParagraphStyle(name="SmallVN",parent=styles["BodyVN"],fontSize=7.2,leading=11,spaceAfter=3,wordWrap="CJK"))
    styles.add(ParagraphStyle(name="HeadingVN",parent=styles["BodyVN"],fontName="DV-Bold",fontSize=14,leading=19,spaceBefore=14,spaceAfter=9,keepWithNext=True,textColor=colors.HexColor("#14566e")))
    styles.add(ParagraphStyle(name="TitleVN",parent=styles["HeadingVN"],fontSize=26,leading=32,spaceBefore=0))
    story=[]
    def p(value,small=False):
        safe=str(value).translate(str.maketrans({"—":"-","–":"-","‑":"-","−":"-"}))
        return Paragraph(escape(safe).replace("\n","<br/>"),styles["SmallVN" if small else "BodyVN"])
    def text(value,small=False):story.append(p(value,small))
    def heading(value):story.append(Paragraph(escape(value),styles["HeadingVN"]))
    def table(headers,rows,widths=None):
        if not rows:return
        cells=[[p(h,True) for h in headers]]+[[p(v,True) for v in row] for row in rows]
        t=Table(cells,colWidths=widths or [174*mm/len(headers)]*len(headers),repeatRows=1,hAlign="LEFT")
        t.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),colors.HexColor("#e3eef2")),("VALIGN",(0,0),(-1,-1),"TOP"),
            ("LEFTPADDING",(0,0),(-1,-1),7),("RIGHTPADDING",(0,0),(-1,-1),7),("TOPPADDING",(0,0),(-1,-1),5),("BOTTOMPADDING",(0,0),(-1,-1),5),
            ("LINEBELOW",(0,0),(-1,0),.7,colors.HexColor("#14566e")),("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white,colors.HexColor("#f5f7f8")])]))
        if len(rows)<=4:story.append(KeepTogether([t,Spacer(1,6)]))
        else:story.extend([t,Spacer(1,6)])
    selected=set(request["sections"]);full=request["mode"]=="full"
    heading("STOCKINSIGHT")
    story.append(Paragraph(f"{escape(request['ticker'])} | Báo cáo phân tích",styles["TitleVN"]))
    text(f"{result['company'].get('name') or request['ticker']} · Ngày phân tích {request['as_of']}")
    text(f"Dữ liệu giá: {request['start']} đến {result['market']['latest_date'] if result['market'] else 'chưa có'} · {'Đầy đủ' if full else 'Tóm tắt'}")
    text("Nội dung đã chọn: "+", ".join(SECTION_LABELS[k] for k in request["sections"]),True)
    text(result["conclusion"]["summary"])
    quality=result["quality"]
    labels={"matched":"Đã khớp nguồn thứ hai","unverified":"Chưa xác minh đầy đủ","matched_selected_fields":"Khớp các chỉ tiêu đã chọn","mismatch":"Có sai lệch — đã chặn","not_independently_checked":"Chưa đối chiếu độc lập","analyzed":"Đã phân tích","partial":"Thiếu một phần dữ liệu"}
    table(["Kiểm tra giá","Kiểm tra tài chính","Trạng thái"],[[labels.get(quality["price_check"]["status"],quality["price_check"]["status"]),labels.get(quality["financial_check"]["status"],quality["financial_check"]["status"]),labels.get(result["status"],result["status"])]])
    text("Các kiểm tra chỉ áp dụng cho số liệu và kỳ được nêu; không xác nhận toàn bộ lịch sử. Báo cáo dùng dữ liệu công khai và các giả định công bố bên dưới.",True)
    if "overview" in selected:
        heading(SECTION_LABELS["overview"])
        text(f"Sàn: {result['company'].get('exchange') or 'chưa có'} · Website: {result['company'].get('website') or 'chưa có'}")
        business=result["company"].get("business") or "Nguồn chưa cung cấp mô tả doanh nghiệp."
        limit=1000 if full else 500
        text(business if len(business)<=limit else business[:limit].rsplit(" ",1)[0]+"… (mô tả rút gọn từ nguồn)")
        for item in result["conclusion"]["opportunities"][:(8 if full else 3)]:text("• "+item)
    if "market" in selected:
        heading(SECTION_LABELS["market"]);market=result.get("market")
        if market:
            table(["Chỉ tiêu","Giá trị"],[["Đóng cửa / ngày",formatted(market["latest_close_vnd"],"VND/share")+" / "+market["latest_date"]],
                ["Biến động trong khoảng chọn",formatted(market["return_pct"],"%")],["Sụt giảm tối đa",formatted(market["max_drawdown_pct"],"%")],
                ["Biến động năm hóa",formatted(market["annualized_volatility_pct"],"%")],["MA20 / MA50",formatted(market["ma20_vnd"],"VND/share")+" / "+formatted(market["ma50_vnd"],"VND/share")],
                ["Khối lượng bình quân 20 phiên",formatted(market["average_volume_20"],"CP")]], [70*mm,104*mm])
            chart=market_chart(result,path.parent/"charts")
            if chart:story.append(Image(str(chart),width=174*mm,height=87*mm))
            text(market["return_note"],True);text(quality["price_check"].get("note","Không có đối chiếu giá."),True)
            differences=[c for c in quality["price_check"].get("checks",[]) if not c["match"]]
            if differences:table(["Ngày lệch nguồn","Yahoo (VND)","KBS (VND)","Sai lệch"],[[c["date"],formatted(c["yahoo_close"]),formatted(c["kbs_close"]),formatted(c["relative_difference"]*100,"%")] for c in differences])
        else:text("Chưa có chuỗi giá hợp lệ; không tính các chỉ tiêu thị trường.")
    if "financial" in selected:
        heading(SECTION_LABELS["financial"]);metrics=result["financial"]["metrics"]
        if metrics:
            text(f"Báo cáo năm {metrics[0]['period']}; tăng trưởng so với năm trước cùng phạm vi. Tiền quy đổi: tỷ VND.")
            chosen=metrics if full else [m for m in metrics if m["key"] in {"revenue","net_profit","revenue_growth","net_profit_growth","roe","cash_conversion"}]
            table(["Chỉ tiêu","Giá trị"],[[m["label"],formatted(m["value"],m["unit"])] for m in chosen],[100*mm,74*mm])
            if full:table(["Năm","Doanh thu thuần (tỷ)","LNST hợp nhất (tỷ)","CFO (tỷ)"],[[str(year["year"])]+[formatted(year["fields"].get(k,{}).get("value"),"VND").replace(" tỷ VND","") for k in ["revenue","net_profit","cfo"]] for year in result["financial"]["periods"]])
        else:text("Chưa đủ dữ liệu tài chính có kỳ và phạm vi hợp lệ.")
        interim=result.get("interim")
        if interim and interim["valid"]:
            text(f"Cập nhật bán niên kết thúc {interim['period_end']} — OCR báo cáo hợp nhất soát xét HPG.")
            table(["Chỉ tiêu","6 tháng hiện tại (tỷ)","6 tháng cùng kỳ (tỷ)","Trang PDF"],[[label,formatted(interim["fields"][k]["value"],"VND").replace(" tỷ VND",""),formatted(interim["fields"][k]["previous"],"VND").replace(" tỷ VND",""),str(interim["fields"][k]["page"])] for k,label in [("revenue","Doanh thu thuần"),("net_profit","LNST hợp nhất"),("cfo","Dòng tiền kinh doanh")] if k in interim["fields"]])
            text(interim["note"],True)
        if full:
            names={"revenue":"Doanh thu thuần","net_profit":"LNST","assets":"Tài sản","equity":"Vốn chủ","liabilities":"Nợ phải trả"}
            table(["Đối chiếu / kỳ","Nguồn API (tỷ)","Tài liệu gốc (tỷ)","Kết quả"],[[names.get(c["metric"],c["metric"])+" / "+c["period"],formatted(c["actual_billion_vnd"]),formatted(c["reference_billion_vnd"]),"Khớp" if c["match"] else "Sai lệch"] for c in quality["financial_check"].get("checks",[])])
    if "valuation" in selected:
        heading(SECTION_LABELS["valuation"]);val=result["valuation"]
        if val["available"]:
            text(f"BVPS tham chiếu: {formatted(val['book_value_per_share'],'VND/share')} · P/B tham chiếu: {val['reference_pb']:.2f} lần.")
            text(f"Vốn cuối năm {val['equity_period']}; số CP tại {val['shares_snapshot']}: {val['shares']:,.0f}.")
            table(["Kịch bản","P/B giả định","Giá trị quy đổi","Chênh lệch với giá"],[[s["label"],f"{s['target_pb']:.2f}",formatted(s["reference_price_vnd"],"VND/share"),formatted(s["difference_pct"],"%")] for s in val["scenarios"]])
            text(val["assumption"]);text(val["pe_status"],True)
        else:text(val["reason"])
    if "news" in selected:
        heading(SECTION_LABELS["news"])
        if not result["news"]:text("Nguồn chưa cung cấp tin phù hợp trước ngày phân tích.")
        for item in result["news"][:(12 if full else 3)]:text(item["published_at"]+" | "+item["title"]);text(item["url"],True)
        text("Danh sách công bố/sự kiện dùng để tra cứu. Chưa đọc toàn văn nên không suy diễn tác động đầu tư.",True)
    if "risks" in selected:
        heading(SECTION_LABELS["risks"])
        if "overview" not in selected:
            for item in result["conclusion"]["opportunities"]:text("• "+item)
        for item in result["conclusion"]["risks"]:text("• "+item)
    heading("Phương pháp và giới hạn dữ liệu")
    if "market" in selected:text("Giá dùng phiên trước ngày hiện tại để tránh phiên chưa kết thúc. Biến động = (Adj Close cuối / đầu − 1) × 100; MA dùng chuỗi điều chỉnh chuẩn hóa về giá đóng cửa cuối. Drawdown = mức giảm lớn nhất từ đỉnh trước đó; biến động năm hóa = độ lệch chuẩn lợi suất log ngày × √252 × 100.",True)
    if "financial" in selected:
        for metric in result["financial"]["metrics"]:
            if metric["key"] not in {"revenue","net_profit","parent_profit","assets","equity","cfo"}:text(metric["label"]+": "+metric["formula"]+(". "+metric["reason"] if metric["reason"] else ""),True)
    if "valuation" in selected and result["valuation"]["available"]:text(result["valuation"]["formula"],True)
    for warning in quality["warnings"]:text("• "+warning,True)
    for error in result["errors"]:text(f"Thiếu dữ liệu ({error['stage']}): {error['message']}",True)
    heading("Nguồn và khả năng truy vết")
    for source in result["sources"]:
        story.append(KeepTogether([p(source["source_id"],True),p(source.get("url_or_file") or source.get("url") or "",True),p(f"Truy xuất: {source.get('retrieved_at','')} · Vị trí: {source.get('page_or_table','')} · {source.get('notes','')}",True)]))
    seen=set()
    for check in quality["financial_check"].get("checks",[]):
        ref=check.get("url")
        if ref and ref not in seen:
            story.append(KeepTogether([p("Tài liệu đối chiếu: "+ref,True),p("Vị trí: "+check["locator"],True)]));seen.add(ref)
    text(f"Mã lượt chạy: {run_id}. Tệp analysis.json lưu giá trị, công thức và đầu vào nguồn cho từng chỉ tiêu.",True)
    def footer(canvas,doc):
        canvas.saveState();canvas.setStrokeColor(colors.HexColor("#cedde3"));canvas.line(18*mm,17*mm,192*mm,17*mm)
        canvas.setFont("DV",7);canvas.setFillColor(colors.HexColor("#50646d"));canvas.drawString(18*mm,12*mm,f"StockInsight · {request['ticker']} · {request['as_of']}")
        canvas.drawRightString(192*mm,12*mm,f"Trang {doc.page}");canvas.restoreState()
    document=SimpleDocTemplate(str(path),pagesize=(210*mm,297*mm),leftMargin=18*mm,rightMargin=18*mm,topMargin=18*mm,bottomMargin=23*mm,title=f"{request['ticker']} - Báo cáo phân tích",author="StockInsight")
    document.build(story,onFirstPage=footer,onLaterPages=footer)
    return path
