"""Acquire and persist source data for application and CLI workflows."""

import csv
from datetime import date, datetime, timedelta
import hashlib
import json
from pathlib import Path
from urllib.parse import urlparse

from src.data.providers import (DataSourceError, HPG_REPORTS_URL, VN_TIME,
                                discover_hpg_reports, download, fetch_daily_prices)
from src.data.validate import validate_prices


def write_json(path: Path, value: dict | list) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")


def recent_document_cache(root: Path) -> dict:
    """Only reuse downloads recorded with a checksum in a run within 24 hours."""
    documents = {}
    cutoff = datetime.now(VN_TIME).timestamp() - timedelta(hours=24).total_seconds()
    for log in sorted((root / "outputs/runs").glob("*/acquisition.json")):
        if log.stat().st_mtime < cutoff:
            continue
        try:
            saved = json.loads(log.read_text(encoding="utf-8"))
            for document in saved.get("financial_documents", []):
                downloaded_at = document.get("downloaded_at")
                if downloaded_at is None:
                    downloaded_at = datetime.fromtimestamp(log.stat().st_mtime, VN_TIME).isoformat()
                if datetime.fromisoformat(downloaded_at).timestamp() >= cutoff:
                    documents[document["url"]] = {**document, "downloaded_at": downloaded_at}
        except (OSError, ValueError, KeyError):
            continue
    return documents


def acquire(ticker: str, start: date, as_of: date, root: Path, report_limit: int = 2) -> dict:
    ticker = ticker.upper().strip()
    stamp = datetime.now(VN_TIME).strftime("%Y%m%d_%H%M%S_%f")
    run_id = f"{ticker}_{stamp}"
    run_dir = root / "outputs/runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    write_json(run_dir / "request.json", {"ticker": ticker, "start": start.isoformat(),
                                          "as_of": as_of.isoformat(), "mode": "completed_daily",
                                          "report_limit": report_limit})
    sources, errors = [], []
    summary = {"ticker": ticker, "run_id": run_id, "prices": None, "financial_documents": [],
               "financial_metrics_status": "not_extracted", "errors": errors}
    try:
        prices = fetch_daily_prices(ticker, start, as_of)
        source_id = f"YAHOO_{run_id}"
        raw_path = root / "data/raw/prices" / f"{run_id}.json"
        raw_path.parent.mkdir(parents=True, exist_ok=True)
        raw_path.write_bytes(prices["raw"])
        validation = validate_prices(prices["rows"], ticker, start, date.fromisoformat(prices["cutoff"]))
        write_json(run_dir / "validation.json", validation)
        sources.append({"source_id": source_id, "url_or_file": prices["url"],
                        "retrieved_at": prices["retrieved_at"], "page_or_table": "chart.indicators.quote",
                        "notes": f"Raw snapshot: {raw_path.relative_to(root).as_posix()}; VND; adjustment basis unverified"})
        if not validation["valid"]:
            raise DataSourceError(f"Daily price validation failed: {validation['errors'][:5]}")
        output = root / "data/processed" / f"{run_id}_prices.csv"
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(prices["rows"][0]) + ["source_id"])
            writer.writeheader()
            writer.writerows({**row, "source_id": source_id} for row in prices["rows"])
        summary["prices"] = {"row_count": len(prices["rows"]), "first": prices["rows"][0]["date"],
                             "last": prices["rows"][-1]["date"], "last_close_vnd": prices["rows"][-1]["close"],
                             "cutoff": prices["cutoff"], "csv": output.relative_to(root).as_posix(),
                             "company_name": prices["meta"].get("longName"), "validation": validation}
    except (DataSourceError, ValueError) as exc:
        errors.append({"stage": "prices", "message": str(exc)})
    if ticker == "HPG" and report_limit:
        try:
            cached_documents = recent_document_cache(root)
            reports, html = discover_hpg_reports(min(as_of, datetime.now(VN_TIME).date()))
            listing_path = root / "data/raw/documents" / f"{run_id}_listing.html"
            listing_path.parent.mkdir(parents=True, exist_ok=True)
            listing_path.write_bytes(html)
            write_json(run_dir / "financial_document_candidates.json", reports)
            if not reports:
                raise DataSourceError("No eligible consolidated reports discovered on issuer listing page 1")
            for report in reports[:report_limit]:
                try:
                    cached = cached_documents.get(report["url"])
                    content = None
                    if cached:
                        cached_path = (root / cached["file"]).resolve()
                        if cached_path.is_relative_to(root.resolve()) and cached_path.exists():
                            candidate = cached_path.read_bytes()
                            if hashlib.sha256(candidate).hexdigest() == cached["sha256"]:
                                content = candidate
                    retrieval_mode = "local_cache_checked_sha256" if content is not None else "downloaded"
                    if content is None:
                        content = download(report["url"])
                    if not content.startswith(b"%PDF-"):
                        raise DataSourceError("Download is not a PDF")
                    filename = Path(urlparse(report["url"]).path).name
                    target = root / "data/raw/documents" / filename
                    if retrieval_mode == "downloaded":
                        target.write_bytes(content)
                    source_id = f"HPG_{hashlib.sha256(content).hexdigest()[:16]}"
                    summary["financial_documents"].append({**report, "file": target.relative_to(root).as_posix(),
                                                           "bytes": len(content), "sha256": hashlib.sha256(content).hexdigest(),
                                                           "source_id": source_id, "retrieval_mode": retrieval_mode,
                                                           "downloaded_at": cached["downloaded_at"] if retrieval_mode != "downloaded" else datetime.now(VN_TIME).isoformat()})
                    sources.append({"source_id": source_id, "url_or_file": report["url"] if retrieval_mode == "downloaded" else target.relative_to(root).as_posix(),
                                    "retrieved_at": datetime.now(VN_TIME).isoformat(), "page_or_table": "whole PDF; metrics not extracted",
                                    "notes": f"{report['title']}; published_at={report['published_at']}; mode={retrieval_mode}; source_url={report['url']}; listing={HPG_REPORTS_URL}"})
                except DataSourceError as exc:
                    errors.append({"stage": "financial_document", "url": report["url"], "message": str(exc)})
        except DataSourceError as exc:
            errors.append({"stage": "financial_listing", "message": str(exc)})
    elif ticker != "HPG":
        summary["financial_metrics_status"] = "issuer_provider_not_implemented_for_this_ticker"
    registry = root / "data/metadata/source_registry.csv"
    registry.parent.mkdir(parents=True, exist_ok=True)
    needs_header = not registry.exists() or not registry.stat().st_size
    with registry.open("a", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=["source_id", "url_or_file", "retrieved_at", "page_or_table", "notes"])
        if needs_header:
            writer.writeheader()
        writer.writerows(sources)
    write_json(run_dir / "acquisition.json", summary)
    write_json(run_dir / "sources.json", sources)
    return summary

