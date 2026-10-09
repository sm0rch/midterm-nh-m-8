"""Offline regression tests for completed-session filtering and source parsing."""

from datetime import date, datetime, timezone
import unittest

from src.data.providers import DataSourceError, completed_day_cutoff, parse_hpg_reports, parse_yahoo_chart
from src.data.validate import validate_prices


class AcquisitionTests(unittest.TestCase):
    def test_cutoff_uses_vietnam_date_and_excludes_current_day(self):
        now = datetime(2026, 10, 8, 20, tzinfo=timezone.utc)  # 03:00 Oct 9 in Vietnam
        self.assertEqual(completed_day_cutoff(date(2026, 10, 9), now), date(2026, 10, 8))
        self.assertEqual(completed_day_cutoff(date(2026, 10, 7), now), date(2026, 10, 7))
        self.assertEqual(completed_day_cutoff(date(2026, 10, 10), now), date(2026, 10, 8))

    def test_today_is_excluded_even_after_close(self):
        now = datetime(2026, 10, 9, 15, tzinfo=timezone.utc)
        self.assertEqual(completed_day_cutoff(date(2026, 10, 9), now), date(2026, 10, 8))

    def test_daily_parser_filters_live_bar_and_rejects_wrong_currency(self):
        payload = {"chart": {"error": None, "result": [{"meta": {"symbol": "HPG.VN", "currency": "VND"},
            "timestamp": [1791421200, 1791507600], "indicators": {"quote": [{
                "open": [20, 21], "high": [22, 23], "low": [19, 20], "close": [21, 22], "volume": [100, 200]}]}}]}}
        rows, _ = parse_yahoo_chart(payload, "HPG", date(2026, 10, 8), date(2026, 10, 8))
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["date"], "2026-10-08")
        payload["chart"]["result"][0]["meta"]["currency"] = "USD"
        with self.assertRaises(DataSourceError):
            parse_yahoo_chart(payload, "HPG", date(2026, 10, 8), date(2026, 10, 8))

    def test_validation_rejects_missing_values_duplicates_and_bad_range(self):
        row = {"ticker": "HPG", "date": "2026-10-08", "open": 20, "high": 22, "low": 19, "close": 21, "volume": 100}
        check = lambda rows: validate_prices(rows, "HPG", date(2026, 10, 1), date(2026, 10, 8))
        self.assertTrue(check([row])["valid"])
        self.assertFalse(check([row, row])["valid"])
        self.assertFalse(check([{**row, "close": None}])["valid"])
        self.assertFalse(check([{**row, "high": 18}])["valid"])
        self.assertFalse(check([{**row, "volume": -1}])["valid"])

    def test_issuer_parser_filters_future_and_separate_reports(self):
        def item(title, stamp, filename):
            return f'<div class="item"><div class="name"><a href="https://file.hoaphat.com.vn/{filename}.pdf">{title}</a></div><div class="time">{stamp}</div></div>'
        html = (item("Báo cáo tài chính hợp nhất", "28/08/2026", "valid") +
                item("Báo cáo tài chính hợp nhất", "29/10/2026", "future") +
                item("Báo cáo tài chính riêng", "28/08/2026", "separate")).encode("utf-8")
        reports = parse_hpg_reports(html, date(2026, 10, 9))
        self.assertEqual(len(reports), 1)
        self.assertEqual(reports[0]["published_at"], "2026-08-28")


if __name__ == "__main__":
    unittest.main()
