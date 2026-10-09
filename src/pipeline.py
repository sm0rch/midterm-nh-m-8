"""Application pipeline: always acquire source data before displaying a new result."""

import csv
from datetime import date
from pathlib import Path
import re
import subprocess

from src.data.acquisition import acquire, write_json
from src.data.providers import completed_day_cutoff
from src.data.research import collect_research
from src.data.issuer_pdf import extract_hpg_interim
from src.data.quality import verify_financials
from src.models import AnalysisRequest
from src.analysis.market import analyze_market
from src.analysis.financial import analyze_financials
from src.analysis.valuation import analyze_valuation
from src.analysis.conclusion import build_conclusion


def run_analysis(ticker: str, start: date, as_of: date, root: Path | None = None, *, mode="full", sections=None, target_pb=1.5) -> dict:
    ticker = ticker.strip().upper()
    if not re.fullmatch(r"[A-Z][A-Z0-9]{1,9}", ticker):
        raise ValueError("Mã cổ phiếu không hợp lệ.")
    if start > completed_day_cutoff(as_of):
        raise ValueError("Ngày bắt đầu phải nằm trước hoặc trong ngày giá đã hoàn tất.")
    root = root or Path(__file__).resolve().parents[1]
    request = AnalysisRequest(ticker, start, as_of, mode=mode, target_pb=target_pb, **({"sections":sections} if sections is not None else {}))
    # No pre-existing CSV and no manual fetch step required. This calls the network providers.
    acquisition = acquire(ticker, start, as_of, root)
    rows = []
    if acquisition["prices"]:
        with (root / acquisition["prices"]["csv"]).open(encoding="utf-8", newline="") as stream:
            for row in csv.DictReader(stream):
                rows.append({**row, **{key: float(row[key]) for key in ("open", "high", "low", "close")},
                             "adjusted_close":float(row["adjusted_close"]) if row.get("adjusted_close") else None,
                             "volume": int(float(row["volume"]))})
    research = collect_research(ticker, as_of, rows, root, acquisition["run_id"])
    interim=None
    if ticker=="HPG":
        reviewed=next((d for d in acquisition["financial_documents"] if "soát xét" in d["title"].lower()),None)
        if reviewed:
            try:
                interim=extract_hpg_interim(reviewed,root)
                if not interim.get("valid"):
                    research["errors"].append({"stage":"issuer_ocr","message":"OCR chưa đủ kiểm tra; không dùng để kết luận"})
            except (RuntimeError,OSError,ValueError,ImportError,subprocess.SubprocessError) as exc:
                research["errors"].append({"stage":"issuer_ocr","message":str(exc)})
    financial=analyze_financials(research["financial_records"])
    financial_check=verify_financials(ticker,financial,interim,root)
    if financial_check["status"]=="mismatch":
        research["errors"].append({"stage":"financial_check","message":"Chỉ tiêu không khớp tài liệu gốc; chặn phân tích tài chính và định giá."})
        financial={**financial,"periods":[],"metrics":[]}
    market=analyze_market(rows)
    company={**research["company"],"name":acquisition["prices"].get("company_name") if acquisition["prices"] else ticker}
    valuation=analyze_valuation(financial,market,company,research["quote_check"],as_of,target_pb)
    conclusion=build_conclusion(financial,market,valuation,research["quote_check"],interim)
    result = {"request": request.to_dict(),
              "acquisition": acquisition, "market": market, "price_rows": rows,
              "company":company,"financial":financial,"interim":interim,"valuation":valuation,"conclusion":conclusion,"news":research["news"],
              "quality":{"price_check":research["quote_check"],"financial_check":financial_check,"warnings":research["warnings"]+financial["errors"]},
              "errors":acquisition["errors"]+research["errors"],"financial_metrics_status":"analyzed" if financial["metrics"] else "unavailable",
              "sources":research["sources"],"status":"partial" if acquisition["errors"] or research["errors"] or research["quote_check"]["status"]!="matched" or not financial["metrics"] else "analyzed"}
    import json
    existing_sources = root / "outputs/runs" / acquisition["run_id"] / "sources.json"
    result["sources"] = json.loads(existing_sources.read_text(encoding="utf-8")) + research["sources"]
    if interim and interim.get("valid"):
        pages_by_source={}
        for field in interim["fields"].values():
            pages_by_source.setdefault(field["source_id"],set()).add(field["page"])
        for source in result["sources"]:
            if source["source_id"] in pages_by_source:
                source["page_or_table"]="OCR statement pages "+", ".join(map(str,sorted(pages_by_source[source["source_id"]])))
    registry=root/"data/metadata/source_registry.csv"
    with registry.open("a",encoding="utf-8",newline="") as stream:
        writer=csv.DictWriter(stream,fieldnames=["source_id","url_or_file","retrieved_at","page_or_table","notes"])
        writer.writerows(research["sources"])
    write_json(existing_sources,result["sources"])
    write_json(root / "outputs/runs" / acquisition["run_id"] / "request.json",request.to_dict())
    write_json(root / "outputs/runs" / acquisition["run_id"] / "analysis.json", result)
    return result
