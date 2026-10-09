"""Explicit P/B scenarios, with dated equity and current share-count assumptions."""
from datetime import datetime
from src.data.providers import VN_TIME


def analyze_valuation(financial, market, company, quote_check, as_of, target_pb):
    unavailable={"available":False,"reason":"Chưa đủ giá đối chiếu, vốn cổ đông công ty mẹ hoặc số cổ phiếu phù hợp.","scenarios":[]}
    if not financial["periods"] or not market or quote_check.get("status")!="matched":
        return unavailable
    if as_of.isoformat()!=company.get("snapshot_at"):
        return {**unavailable,"reason":"Không dùng số cổ phiếu hiện tại để định giá tại ngày quá khứ."}
    latest=financial["periods"][0];fields=latest["fields"]
    equity=fields.get("equity",{}).get("value");nci=fields.get("non_controlling_equity",{}).get("value")
    shares=company.get("outstanding_shares")
    if equity is None or nci is None or equity-nci<=0 or not isinstance(shares,(int,float)) or shares<=0:
        return unavailable
    book_value=(equity-nci)/shares;price=market["latest_close_vnd"]
    scenarios=[]
    for label,multiple in [("Thận trọng",target_pb*0.8),("Cơ sở",target_pb),("Thuận lợi",target_pb*1.2)]:
        value=book_value*multiple
        scenarios.append({"label":label,"target_pb":multiple,"reference_price_vnd":value,"difference_pct":(value/price-1)*100})
    return {"available":True,"book_value_per_share":book_value,"reference_pb":price/book_value,
            "equity_period":str(latest["year"]),"shares":shares,"shares_snapshot":company["snapshot_at"],
            "assumption":"P/B cơ sở do người dùng chọn; hai kịch bản còn lại ±20%. Giả định vốn cuối năm không thay đổi khi quy đổi trên số cổ phiếu hiện tại. Không phải giá mục tiêu từ dự báo.",
            "formula":"BVPS = (VCSH hợp nhất - lợi ích cổ đông không kiểm soát) / số CP; giá trị kịch bản = BVPS × P/B giả định",
            "inputs":[fields["equity"],fields["non_controlling_equity"],{"source_id":company["source_id"],"value":shares,"unit":"shares","period":company["snapshot_at"]}],
            "scenarios":scenarios,"pe_status":"Không tính P/E TTM khi thiếu bốn quý độc lập và cơ sở EPS đã kiểm chứng."}
