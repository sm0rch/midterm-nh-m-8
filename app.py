"""StockInsight: request → automatic acquisition → analysis → selected PDF."""
from datetime import datetime, timedelta
from pathlib import Path
import pandas as pd
import streamlit as st
from src.data.providers import VN_TIME
from src.models import SECTION_LABELS
from src.pipeline import run_analysis
from src.reporting.pdf_exporter import generate_report, formatted

ROOT=Path(__file__).resolve().parent
today=datetime.now(VN_TIME).date()
st.set_page_config(page_title="StockInsight",layout="wide")
st.title("StockInsight")
st.caption("Nhập mã cổ phiếu. Hệ thống tự lấy dữ liệu cuối ngày, phân tích và tạo báo cáo PDF theo nội dung bạn chọn.")
with st.form("analysis_request"):
    cols=st.columns(3)
    ticker=cols[0].text_input("Mã cổ phiếu",value="HPG",help="Ví dụ: HPG, FPT, VNM. Nguồn hiện hỗ trợ cổ phiếu Việt Nam có dữ liệu Yahoo/KBS.")
    start=cols[1].date_input("Từ ngày",value=today-timedelta(days=365),max_value=today-timedelta(days=1))
    as_of=cols[2].date_input("Ngày phân tích",value=today,max_value=today)
    mode=st.radio("Độ chi tiết",["Đầy đủ","Tóm tắt"],horizontal=True)
    sections=st.multiselect("Nội dung PDF",list(SECTION_LABELS),default=list(SECTION_LABELS),format_func=SECTION_LABELS.get)
    target_pb=st.number_input("P/B cơ sở giả định",min_value=0.1,max_value=20.0,value=1.5,step=0.1,help="Giả định của bạn cho kịch bản tham chiếu; không phải mức P/B tối ưu được hệ thống ước lượng.")
    submitted=st.form_submit_button("Phân tích",type="primary")
if submitted:
    st.session_state.pop("analysis_result",None)
    st.session_state.pop("report_path",None)
    try:
        with st.spinner("Đang lấy dữ liệu, đối chiếu nguồn, phân tích và tạo PDF… Lần đầu đọc PDF scan có thể mất vài phút."):
            result=run_analysis(ticker,start,as_of,mode="full" if mode=="Đầy đủ" else "summary",sections=sections,target_pb=target_pb)
            if not result["market"] and not result["financial"]["metrics"]:
                st.error("Không lấy được dữ liệu hợp lệ. Kiểm tra mã cổ phiếu hoặc thử lại khi nguồn truy cập được.")
                for error in result["errors"]:st.warning(error["message"])
            else:
                st.session_state["analysis_result"]=result
                st.session_state["report_path"]=str(generate_report(result))
    except (ValueError,OSError,RuntimeError) as exc:
        st.error(f"Không thể hoàn tất yêu cầu: {exc}")
result=st.session_state.get("analysis_result")
if result:
    request=result["request"];acquisition=result["acquisition"]
    st.subheader(f"Kết quả {request['ticker']}")
    st.caption(f"Ngày phân tích {request['as_of']} · Dữ liệu giá đến {result['market']['latest_date'] if result['market'] else 'chưa có'}")
    if st.session_state.get("report_path"):
        path=Path(st.session_state["report_path"])
        st.download_button("Tải báo cáo phân tích PDF",path.read_bytes(),file_name=path.name,mime="application/pdf",type="primary")
    for error in result["errors"]:st.warning(f"Dữ liệu chưa đủ ({error['stage']}): {error['message']}")
    market=result.get("market")
    if market:
        cols=st.columns(4)
        for col,label,key,unit in zip(cols,["Giá đóng cửa","Biến động khoảng chọn","Sụt giảm tối đa","MA20"],["latest_close_vnd","return_pct","max_drawdown_pct","ma20_vnd"],["VND/share","%","%","VND/share"]):
            col.metric(label,formatted(market[key],unit))
        price_check=result["quality"]["price_check"]
        if price_check["status"]=="matched":st.success(f"Giá đóng cửa đã khớp hai nguồn trong {len(price_check['checks'])} phiên được đối chiếu.")
        else:st.warning("Giá chưa được đối chiếu đầy đủ với nguồn thứ hai.")
        prices=pd.DataFrame(result["price_rows"])
        chart=pd.DataFrame({"Ngày":pd.to_datetime(prices["date"]),"Giá điều chỉnh chuẩn hóa":market["chart_prices"]}).set_index("Ngày")
        st.line_chart(chart)
        st.caption(market["return_note"])
    tabs=st.tabs(["Tài chính","Kịch bản P/B","Cơ hội và rủi ro","Tin tức","Nguồn dữ liệu"])
    with tabs[0]:
        if result["financial"]["metrics"]:
            st.caption(f"Báo cáo năm {result['financial']['metrics'][0]['period']}; không phải số liệu TTM.")
            st.dataframe(pd.DataFrame([{"Chỉ tiêu":m["label"],"Giá trị":formatted(m["value"],m["unit"])} for m in result["financial"]["metrics"]]),hide_index=True,width="stretch")
        else:st.info("Chưa có chỉ tiêu tài chính đủ điều kiện tính toán.")
        interim=result.get("interim")
        if interim and interim["valid"]:
            st.write(f"**Bán niên HPG đến {interim['period_end']}**")
            st.dataframe(pd.DataFrame([{"Chỉ tiêu":label,"Hiện tại":formatted(interim["fields"][key]["value"],"VND"),"6 tháng cùng kỳ":formatted(interim["fields"][key]["previous"],"VND"),"Trang PDF":interim["fields"][key]["page"]} for key,label in [("revenue","Doanh thu thuần"),("net_profit","LNST"),("cfo","Dòng tiền kinh doanh")]]),hide_index=True,width="stretch")
    with tabs[1]:
        val=result["valuation"]
        if val["available"]:
            st.caption(f"BVPS tham chiếu {formatted(val['book_value_per_share'],'VND/share')} · P/B tham chiếu {val['reference_pb']:.2f} lần")
            st.dataframe(pd.DataFrame([{"Kịch bản":s["label"],"P/B giả định":s["target_pb"],"Giá trị quy đổi":formatted(s["reference_price_vnd"],"VND/share"),"Chênh lệch":formatted(s["difference_pct"],"%")} for s in val["scenarios"]]),hide_index=True,width="stretch")
            st.info(val["assumption"])
        else:st.info(val["reason"])
    with tabs[2]:
        st.write("**Cơ hội / điều kiện theo dõi**")
        for item in result["conclusion"]["opportunities"]:st.write("• "+item)
        st.write("**Rủi ro**")
        for item in result["conclusion"]["risks"]:st.write("• "+item)
    with tabs[3]:
        for item in result["news"]:st.markdown(f"{item['published_at']} · [{item['title']}]({item['url']})")
        if not result["news"]:st.info("Chưa có tin phù hợp từ nguồn.")
        st.caption("Danh sách công bố/sự kiện để tra cứu. Chưa suy diễn tác động từ tiêu đề tin.")
    with tabs[4]:
        st.write(result["quality"]["financial_check"]["note"])
        checks=result["quality"]["financial_check"]["checks"]
        if checks:st.dataframe(pd.DataFrame(checks),hide_index=True,width="stretch")
        for warning in result["quality"]["warnings"]:st.caption(warning)
        for source in result["sources"]:
            st.markdown(f"[{source['source_id']}]({source.get('url_or_file','')})")
        with st.expander("Công thức và đầu vào chỉ tiêu"):
            st.json(result["financial"]["metrics"])
        if acquisition["prices"]:
            st.download_button("Tải dữ liệu giá CSV",(ROOT/acquisition["prices"]["csv"]).read_bytes(),file_name=f"{request['ticker']}_prices.csv",mime="text/csv")
        for i,report in enumerate(acquisition["financial_documents"]):
            st.download_button("Tải PDF gốc: "+report["title"],(ROOT/report["file"]).read_bytes(),file_name=Path(report["file"]).name,mime="application/pdf",key=f"raw_pdf_{i}")
else:
    st.info("Không cần chuẩn bị CSV hoặc nhập số liệu tài chính. Bấm Phân tích để hệ thống tự lấy dữ liệu.")
