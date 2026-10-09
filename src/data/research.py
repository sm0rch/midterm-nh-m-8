"""Acquire financial tables, company profile, news and an independent price check."""
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timedelta
import json
from pathlib import Path
from urllib.parse import urlencode, urljoin

from bs4 import BeautifulSoup

from src.data.providers import DataSourceError, VN_TIME, completed_day_cutoff, download
from src.data.normalize import parse_annual_financials

KBS_BASE = "https://kbbuddywts.kbsec.com.vn/iis-server/investment"


def compare_prices(primary: list[dict], payload: dict, cutoff: date) -> dict:
    observed = {r["t"][:10]: r for r in payload.get("data_day", []) if r.get("t", "")[:10] <= cutoff.isoformat()}
    checks = []
    for row in primary[-20:]:
        other = observed.get(row["date"])
        if other and other.get("c") is not None:
            deviation = abs(float(row["close"]) - float(other["c"])) / float(other["c"]) if float(other["c"]) > 0 else None
            checks.append({"date": row["date"], "yahoo_close": row["close"], "kbs_close": other["c"],
                           "relative_difference": deviation, "match": deviation is not None and deviation <= 0.001})
    latest_match = bool(checks and primary and checks[-1]["date"] == primary[-1]["date"] and checks[-1]["match"])
    return {"status": "matched" if latest_match and all(r["match"] for r in checks) else "unverified",
            "checks": checks, "latest_match": latest_match,
            "note": "Đối chiếu giá đóng cửa tối đa 20 ngày gần nhất, sai lệch cho phép 0,1%; không xác nhận toàn bộ lịch sử điều chỉnh."}


def collect_research(ticker: str, as_of: date, primary: list[dict], root: Path, run_id: str) -> dict:
    cutoff = completed_day_cutoff(as_of)
    common = {"page": 1, "pageSize": 4, "unit": 1000, "termtype": 1}
    jobs = {"profile": f"{KBS_BASE}/stockinfo/profile/{ticker}?l=1",
            "news": f"{KBS_BASE}/stockinfo/news/{ticker}?l=1&p=1&s=12",
            "price_check": f"{KBS_BASE}/stocks/{ticker}/data_day?{urlencode({'sdate': (cutoff-timedelta(days=45)).strftime('%d-%m-%Y'), 'edate':cutoff.strftime('%d-%m-%Y')})}"}
    for kind, code in [("income", "KQKD"), ("balance", "CDKT"), ("cashflow", "LCTT")]:
        params = {**common, "type": code}
        params.update({"termType": 1, "code": ticker} if code == "LCTT" else {"languageid": 1})
        jobs[kind] = f"{KBS_BASE}/stock/finance-info/{ticker}?{urlencode(params)}"
    result = {"company": {}, "financial_records": [], "news": [], "quote_check": {"status": "unverified"},
              "sources": [], "errors": [], "warnings": ["Phân tích tài chính dùng báo cáo năm đã công bố; không sử dụng API quý có ánh xạ kỳ không rõ ràng."]}
    folder = root / "data/raw/financials"
    folder.mkdir(parents=True, exist_ok=True)
    def retrieve(kind, url):
        raw = download(url, timeout=20)
        return kind, url, raw, json.loads(raw)
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {executor.submit(retrieve, kind, url): kind for kind, url in jobs.items()}
        for future in as_completed(futures):
            kind = futures[future]
            try:
                kind, url, raw, data = future.result()
                source_id = f"KBS_{kind}_{run_id}"
                (folder / f"{run_id}_{kind}.json").write_bytes(raw)
                result["sources"].append({"source_id": source_id, "url_or_file": url,
                    "retrieved_at": datetime.now(VN_TIME).isoformat(), "page_or_table": kind,
                    "notes": "Financial monetary values requested in thousand VND; EPS in VND/share" if kind in {"income", "balance", "cashflow"} else "Public source snapshot"})
                if kind in {"income", "balance", "cashflow"}:
                    parsed = parse_annual_financials(data, kind, as_of, source_id)
                    result["financial_records"].extend({**period, "kind": kind} for period in parsed)
                elif kind == "profile":
                    if data.get("SB") != ticker:
                        raise DataSourceError("Company symbol mismatch")
                    result["company"] = {"ticker": ticker, "website": data.get("URL"), "exchange": data.get("EX"),
                        "business": BeautifulSoup(data.get("SM") or "", "html.parser").get_text(" ", strip=True),
                        "outstanding_shares": data.get("KLCPLH"), "source_id": source_id,
                        "snapshot_at": datetime.now(VN_TIME).date().isoformat()}
                elif kind == "price_check":
                    if data.get("symbol") != ticker:
                        raise DataSourceError("Cross-check symbol mismatch")
                    result["quote_check"] = {**compare_prices(primary, data, cutoff), "source_id": source_id}
                elif kind == "news":
                    for item in data if isinstance(data, list) else []:
                        published = item.get("PublishTime", "")[:10]
                        if not published:
                            continue
                        if date.fromisoformat(published) <= as_of:
                            # KBS company news uses Vietstock article paths.
                            link = item.get("URL", "")
                            result["news"].append({"title": item.get("Title", ""), "published_at": published,
                                "url": urljoin("https://vietstock.vn", link), "source_id": source_id,
                                "summary": "Sự kiện/công bố từ danh sách tin của nguồn; cần đọc tài liệu gốc để xác định tác động."})
            except (DataSourceError, ValueError, KeyError, TypeError) as exc:
                result["errors"].append({"stage": kind, "message": str(exc)})
    # Deterministic output regardless of request completion order.
    result["financial_records"].sort(key=lambda record: (record["year"], record["kind"]), reverse=True)
    result["sources"].sort(key=lambda source: source["source_id"])
    return result
