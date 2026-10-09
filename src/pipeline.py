"""Application pipeline: hỗ trợ bất kỳ mã cổ phiếu nào, có real-time."""

import csv
from datetime import date
from pathlib import Path
import re

from src.data.acquisition import acquire, write_json
from src.data.providers import completed_day_cutoff
from src.data.research import collect_research
from src.data.quality import verify_financials
from src.models import AnalysisRequest
from src.analysis.market import analyze_market
from src.analysis.financial import analyze_financials
from src.analysis.valuation import analyze_valuation
from src.analysis.conclusion import build_conclusion


def run_analysis(ticker: str, start: date, as_of: date, root: Path | None = None, *,
                 mode="full", sections=None, target_pb=1.5) -> dict:
    ticker = ticker.strip().upper()
    if not re.fullmatch(r"[A-Z][A-Z0-9]{1,9}", ticker):
        raise ValueError("Mã cổ phiếu không hợp lệ.")
    if start > completed_day_cutoff(as_of):
        raise ValueError("Ngày bắt đầu phải nằm trước hoặc trong ngày giá đã hoàn tất.")
    root = root or Path(__file__).resolve().parents[1]
    request = AnalysisRequest(ticker, start, as_of, mode=mode, target_pb=target_pb,
                              **{"sections": sections} if sections is not None else {})

    # ── 1. Thu thập dữ liệu ──────────────────────────────────────────────────
    acquisition = acquire(ticker, start, as_of, root)

    # ── 2. Load rows từ CSV ──────────────────────────────────────────────────
    rows = []
    if acquisition["prices"]:
        with (root / acquisition["prices"]["csv"]).open(encoding="utf-8", newline="") as stream:
            for row in csv.DictReader(stream):
                rows.append({
                    **row,
                    **{key: float(row[key]) for key in ("open", "high", "low", "close")},
                    "adjusted_close": float(row["adjusted_close"]) if row.get("adjusted_close") else None,
                    "volume": int(float(row["volume"])),
                })

    # ── 3. Research: BCTC + tin tức + đối chiếu giá (KBS — hoạt động với mọi mã) ──
    research = collect_research(ticker, as_of, rows, root, acquisition["run_id"])

    # ── 4. Interim (chỉ HPG có trang công bố PDF riêng) ─────────────────────
    interim = None
    if ticker == "HPG":
        import subprocess
        from src.data.issuer_pdf import extract_hpg_interim
        reviewed = next(
            (d for d in acquisition["financial_documents"] if "soát xét" in d["title"].lower()), None
        )
        if reviewed:
            try:
                interim = extract_hpg_interim(reviewed, root)
                if not interim.get("valid"):
                    research["errors"].append({"stage": "issuer_ocr", "message": "OCR chưa đủ kiểm tra"})
            except (RuntimeError, OSError, ValueError, ImportError, subprocess.SubprocessError) as exc:
                research["errors"].append({"stage": "issuer_ocr", "message": str(exc)})

    # ── 5. Phân tích ─────────────────────────────────────────────────────────
    financial = analyze_financials(research["financial_records"])
    financial_check = verify_financials(ticker, financial, interim, root)
    if financial_check["status"] == "mismatch":
        research["errors"].append({
            "stage": "financial_check",
            "message": "Chỉ tiêu không khớp tài liệu gốc; chặn phân tích tài chính và định giá.",
        })
        financial = {**financial, "periods": [], "metrics": []}

    market = analyze_market(rows)

    # Thông tin công ty: ưu tiên real-time từ VCI, fallback về Yahoo meta
    realtime = acquisition.get("realtime") or {}
    company_name = (realtime.get("company_name")
                    or (acquisition["prices"].get("company_name") if acquisition["prices"] else None)
                    or ticker)
    company = {
        **research["company"],
        "name": company_name,
        "short_name": realtime.get("short_name", ticker),
        "sector": realtime.get("sector", research["company"].get("business_type", "")),
        "company_profile": realtime.get("company_profile", ""),
        "target_price": realtime.get("target_price"),
        "rating": realtime.get("rating"),
        "highest_1y": realtime.get("highest_1y"),
        "lowest_1y": realtime.get("lowest_1y"),
        "upside_pct": realtime.get("upside_pct"),
        "realtime_price": realtime.get("price"),
        "market_cap": realtime.get("market_cap"),
        "free_float_pct": realtime.get("free_float_pct"),
        "listing_date": realtime.get("listing_date"),
        "data_source": acquisition["prices"].get("data_source", "unknown") if acquisition["prices"] else "unknown",
    }

    valuation = analyze_valuation(financial, market, company, research["quote_check"], as_of, target_pb)
    conclusion = build_conclusion(financial, market, valuation, research["quote_check"], interim, company)

    # ── 6. Kết quả tổng hợp ──────────────────────────────────────────────────
    import json as _json
    existing_sources = root / "outputs/runs" / acquisition["run_id"] / "sources.json"
    all_sources = _json.loads(existing_sources.read_text(encoding="utf-8")) + research["sources"]

    if interim and interim.get("valid"):
        pages_by_source = {}
        for field in interim["fields"].values():
            pages_by_source.setdefault(field["source_id"], set()).add(field["page"])
        for source in all_sources:
            if source["source_id"] in pages_by_source:
                source["page_or_table"] = "OCR statement pages " + ", ".join(
                    map(str, sorted(pages_by_source[source["source_id"]]))
                )

    result = {
        "request": request.to_dict(),
        "acquisition": acquisition,
        "market": market,
        "price_rows": rows,
        "company": company,
        "financial": financial,
        "interim": interim,
        "valuation": valuation,
        "conclusion": conclusion,
        "news": research["news"],
        "quality": {
            "price_check": research["quote_check"],
            "financial_check": financial_check,
            "warnings": research["warnings"] + financial["errors"],
        },
        "errors": acquisition["errors"] + research["errors"],
        "financial_metrics_status": "analyzed" if financial["metrics"] else "unavailable",
        "sources": all_sources,
        "status": (
            "partial" if acquisition["errors"] or research["errors"]
            or research["quote_check"]["status"] != "matched"
            or not financial["metrics"]
            else "analyzed"
        ),
    }

    # Persist
    registry = root / "data/metadata/source_registry.csv"
    with registry.open("a", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=["source_id", "url_or_file", "retrieved_at", "page_or_table", "notes"])
        writer.writerows(research["sources"])
    write_json(existing_sources, result["sources"])
    write_json(root / "outputs/runs" / acquisition["run_id"] / "request.json", request.to_dict())
    write_json(root / "outputs/runs" / acquisition["run_id"] / "analysis.json", result)
    return result
