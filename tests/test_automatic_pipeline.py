"""Verify automatic acquisition from an empty workspace and safe partial failures."""

from datetime import date, datetime, timedelta
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from src.data.providers import DataSourceError, VN_TIME
from src.data.acquisition import recent_document_cache
from src.pipeline import run_analysis


def price_response():
    rows = [{"ticker": "HPG", "date": "2026-10-08", "open": 20000, "high": 20500,
             "low": 19800, "close": 20150, "volume": 100,
             "price_basis": "yahoo_chart_ohlc_unverified", "unit": "VND_per_share"}]
    return {"url": "https://example.test/price", "raw": b'{}', "rows": rows,
            "meta": {"longName": "HPG"}, "cutoff": "2026-10-08", "retrieved_at": "2026-10-09T10:00:00+07:00"}


class AutomaticPipelineTests(unittest.TestCase):
    def setUp(self):
        mock=patch("src.pipeline.collect_research",return_value={"company":{},"financial_records":[],"news":[],"quote_check":{"status":"unverified"},"sources":[],"errors":[],"warnings":[]})
        mock.start()
        self.addCleanup(mock.stop)
    def test_empty_workspace_fetches_sources_and_persists_result(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            with patch("src.data.acquisition.fetch_daily_prices", return_value=price_response()) as prices, \
                 patch("src.data.acquisition.discover_hpg_reports", return_value=([], b"<html></html>")) as reports:
                result = run_analysis("hpg", date(2025, 10, 9), date(2026, 10, 9), root)
            prices.assert_called_once()
            reports.assert_called_once()
            self.assertEqual(result["market"]["latest_close_vnd"], 20150)
            self.assertEqual(result["status"], "partial")
            self.assertEqual(result["acquisition"]["errors"][0]["stage"], "financial_listing")
            saved = root / "outputs/runs" / result["acquisition"]["run_id"] / "analysis.json"
            self.assertEqual(json.loads(saved.read_text(encoding="utf-8"))["request"]["ticker"], "HPG")

    def test_price_failure_does_not_reuse_previous_result(self):
        with TemporaryDirectory() as directory, \
             patch("src.data.acquisition.fetch_daily_prices", side_effect=DataSourceError("Source offline")), \
             patch("src.data.acquisition.discover_hpg_reports", return_value=([], b"")):
            result = run_analysis("HPG", date(2025, 10, 9), date(2026, 10, 9), Path(directory))
        self.assertIsNone(result["market"])
        self.assertEqual(result["price_rows"], [])
        self.assertEqual(result["status"], "partial")

    def test_invalid_request_does_not_fetch(self):
        with patch("src.pipeline.acquire") as fetch:
            with self.assertRaises(ValueError):
                run_analysis("../HPG", date(2025, 10, 9), date(2026, 10, 9))
            fetch.assert_not_called()

    def test_repeated_requests_refresh_prices_and_reuse_checked_pdf(self):
        report = {"ticker": "HPG", "title": "Test report", "published_at": "2026-08-28",
                  "statement_scope": "consolidated", "url": "https://file.hoaphat.com.vn/test.pdf"}
        with TemporaryDirectory() as directory, \
             patch("src.data.acquisition.fetch_daily_prices", side_effect=lambda *args: price_response()) as prices, \
             patch("src.data.acquisition.discover_hpg_reports", return_value=([report], b"")) as listing, \
             patch("src.data.acquisition.download", return_value=b"%PDF-test-fixture") as document:
            root = Path(directory)
            first = run_analysis("HPG", date(2025, 10, 9), date(2026, 10, 9), root)
            second = run_analysis("HPG", date(2025, 10, 9), date(2026, 10, 9), root)
            self.assertEqual(prices.call_count, 2)
            self.assertEqual(listing.call_count, 2)
            self.assertEqual(document.call_count, 1)
            self.assertEqual(second["acquisition"]["financial_documents"][0]["retrieval_mode"], "local_cache_checked_sha256")
            self.assertEqual(first["acquisition"]["financial_documents"][0]["downloaded_at"], second["acquisition"]["financial_documents"][0]["downloaded_at"])
            # A corrupt cached PDF must trigger a new source download.
            (root / first["acquisition"]["financial_documents"][0]["file"]).write_bytes(b"broken")
            third = run_analysis("HPG", date(2025, 10, 9), date(2026, 10, 9), root)
            self.assertEqual(document.call_count, 2)
            self.assertEqual(third["acquisition"]["financial_documents"][0]["retrieval_mode"], "downloaded")

    def test_recent_log_does_not_renew_expired_download(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            log = root / "outputs/runs/test/acquisition.json"
            log.parent.mkdir(parents=True)
            old = (datetime.now(VN_TIME) - timedelta(days=2)).isoformat()
            log.write_text(json.dumps({"financial_documents": [{"url": "https://example.test/report.pdf", "downloaded_at": old}]}), encoding="utf-8")
            self.assertEqual(recent_document_cache(root), {})


if __name__ == "__main__":
    unittest.main()
