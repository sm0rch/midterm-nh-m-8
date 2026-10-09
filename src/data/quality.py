"""Compare selected provider figures with documented issuer baselines and OCR evidence."""
import json


def verify_financials(ticker, financial, interim, root):
    path=root / "config/verification_baselines.json"
    baseline=json.loads(path.read_text(encoding="utf-8")).get(ticker) if path.exists() else None
    checks=[]
    if baseline:
        period=next((p for p in financial["periods"] if p["year"]==baseline["year"]),None)
        if period:
            for key,expected in baseline["values_billion_vnd"].items():
                actual=period["fields"].get(key,{}).get("value")
                matches=actual is not None and abs(actual/1e9-expected)<=baseline["tolerance_billion_vnd"]
                checks.append({"metric":key,"period":str(baseline["year"]),"actual_billion_vnd":actual/1e9 if actual is not None else None,
                               "reference_billion_vnd":expected,"match":matches,"url":baseline["url"],"locator":baseline["locator"]})
    if interim and interim.get("valid"):
        previous_year=int(interim["period_end"][:4])-1
        period=next((p for p in financial["periods"] if p["year"]==previous_year),None)
        if period:
            for key in ["assets","equity","liabilities"]:
                reference=interim["fields"].get(key,{}).get("previous")
                actual=period["fields"].get(key,{}).get("value")
                if reference is not None and actual is not None:
                    checks.append({"metric":key,"period":str(previous_year),"actual_billion_vnd":actual/1e9,
                                   "reference_billion_vnd":reference/1e9,"match":abs(actual-reference)<=max(2000,abs(reference)*0.0001),
                                   "source_id":interim["fields"][key]["source_id"],"locator":f"BCTC bán niên, cột đầu kỳ, trang PDF {interim['fields'][key]['page']}"})
    return {"status":"matched_selected_fields" if checks and all(c["match"] for c in checks) else "mismatch" if checks else "not_independently_checked",
            "checks":checks,"note":"Chỉ đối chiếu các chỉ tiêu được liệt kê; không chứng nhận mọi số liệu hay toàn bộ lịch sử."}
