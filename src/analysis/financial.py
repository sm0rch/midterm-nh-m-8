"""Financial calculations with matched periods/scopes and explicit missing values."""
import math


def ratio(numerator, denominator, positive_denominator=True):
    if numerator is None or denominator is None or denominator == 0:
        return None
    if positive_denominator and denominator < 0:
        return None
    return numerator / denominator


def growth(current, previous):
    return (current / previous - 1) * 100 if current is not None and previous is not None and previous > 0 and current >= 0 else None


def analyze_financials(records: list[dict]) -> dict:
    by_year, errors = {}, []
    for record in records:
        year = record["year"]
        grouped = by_year.setdefault(year, {"year": year, "fields": {}, "scopes": set(), "business_type": record["business_type"],"period_ends":set(),"business_types":set()})
        grouped["scopes"].add(record["scope"])
        grouped["period_ends"].add(record.get("period_end",f"{year}-12-31"))
        grouped["business_types"].add(record["business_type"])
        grouped["fields"].update(record["fields"])
    periods = []
    for year in sorted(by_year, reverse=True):
        period = by_year[year]
        if len(period["period_ends"])!=1 or len(period["business_types"])!=1:
            errors.append(f"{year}: ngày cuối kỳ hoặc nhóm ngành không nhất quán; chặn kỳ tài chính")
            continue
        period["period_end"]=period.pop("period_ends").pop()
        period.pop("business_types")
        if len(period["scopes"]) != 1 or "unknown" in period["scopes"]:
            errors.append(f"{year}: phạm vi báo cáo không nhất quán, chặn tính toán")
            continue
        period["scope"] = next(iter(period.pop("scopes")))
        fields = period["fields"]
        def value(key):
            return fields.get(key, {}).get("value")
        assets, equity, liabilities = value("assets"), value("equity"), value("liabilities")
        if all(v is not None for v in [assets, equity, liabilities]) and assets > 0:
            if abs(assets-equity-liabilities)/assets > 0.001:
                errors.append(f"{year}: tài sản khác tổng nợ và vốn, chặn kỳ tài chính")
                continue
        periods.append(period)
    metrics = []
    if not periods:
        return {"periods": [], "metrics": [], "errors": errors, "industry_group": "unknown"}
    latest = periods[0]
    previous = next((p for p in periods[1:] if p["year"] == latest["year"]-1 and p["scope"] == latest["scope"]), None)
    def get(period, key):
        return period["fields"].get(key, {}).get("value") if period else None
    fields = latest["fields"]
    def metric(key, label, value, unit, formula, dependencies, reason=None):
        refs = [fields[k] for k in dependencies if k in fields]
        metrics.append({"key": key, "label": label, "value": value, "unit": unit, "period": str(latest["year"]),
                        "formula": formula, "inputs": refs, "reason": reason if value is None else None})
    industry = "nonfinancial" if latest["business_type"] == 1 else "financial"
    for key, label in [("revenue", "Doanh thu thuần"), ("net_profit", "LNST hợp nhất"), ("parent_profit", "LNST cổ đông công ty mẹ"),
                       ("assets", "Tổng tài sản"), ("equity", "Vốn chủ sở hữu"), ("cfo", "Dòng tiền kinh doanh")]:
        metric(key, label, get(latest, key), "VND", "Số liệu báo cáo năm", [key], "Nguồn thiếu chỉ tiêu phù hợp")
    for key, label in [("revenue", "Tăng trưởng doanh thu"), ("net_profit", "Tăng trưởng LNST")]:
        value = growth(get(latest, key), get(previous, key))
        metric(key+"_growth", label, value, "%", "(Kỳ hiện tại / cùng kỳ năm trước - 1) × 100", [key], "Thiếu cùng kỳ hoặc kỳ gốc không phù hợp")
        if previous and key in previous["fields"]:
            metrics[-1]["inputs"].append(previous["fields"][key])
    average_equity = (get(latest,"equity")+get(previous,"equity"))/2 if get(latest,"equity") is not None and get(previous,"equity") is not None else None
    roe = ratio(get(latest,"net_profit"), average_equity)
    metric("roe", "ROE hợp nhất năm", roe*100 if roe is not None else None, "%", "LNST hợp nhất / VCSH hợp nhất bình quân × 100", ["net_profit","equity"], "Thiếu vốn bình quân hoặc vốn không dương")
    if previous and "equity" in previous["fields"]:
        metrics[-1]["inputs"].append(previous["fields"]["equity"])
    if industry == "nonfinancial":
        for key,label,numerator,denominator,unit in [
            ("gross_margin","Biên lợi nhuận gộp","gross_profit","revenue","%"),
            ("net_margin","Biên lợi nhuận ròng","net_profit","revenue","%"),
            ("cash_conversion","CFO / LNST","cfo","net_profit","lần")]:
            value=ratio(get(latest,numerator),get(latest,denominator))
            if unit=="%" and value is not None:value*=100
            metric(key,label,value,unit,f"{numerator} / {denominator}"+(" × 100" if unit=="%" else ""),[numerator,denominator],"Thiếu dữ liệu hoặc mẫu số không dương")
        debt = get(latest,"short_debt")+get(latest,"long_debt") if get(latest,"short_debt") is not None and get(latest,"long_debt") is not None else None
        metric("debt_equity","Nợ vay / vốn chủ",ratio(debt,get(latest,"equity")),"lần","(Nợ vay ngắn + dài hạn) / VCSH",["short_debt","long_debt","equity"],"Thiếu nợ vay hoặc vốn không dương")
    else:
        errors.append("Doanh nghiệp tài chính: chỉ hiển thị chỉ tiêu ánh xạ được; không áp biên lợi nhuận/CFO/nợ vay của doanh nghiệp phi tài chính.")
    return {"periods": periods, "metrics": metrics, "errors": errors, "industry_group": industry}
