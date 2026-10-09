"""Financial period/unit guards, independent checks and selective PDF behavior."""
from copy import deepcopy
from datetime import date
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from src.data.normalize import parse_annual_financials
from src.data.providers import DataSourceError
from src.data.research import compare_prices
from src.data.issuer_pdf import parse_interim_text
from src.analysis.financial import analyze_financials, ratio, growth
from src.analysis.market import analyze_market
from src.analysis.valuation import analyze_valuation
from src.reporting.pdf_exporter import generate_report

def payload():
    return {"Head":[{"ID":i,"YearPeriod":2026-i,"TermCode":"N","United":"HN","BusinessType":1,
                     "DatePubDepartment":f"{2027-i}-03-01T00:00:00","LastUpdate":f"{2027-i}-03-02T00:00:00"} for i in range(1,5)],
            "Content":{"income":[{"ReportNormID":2216,"Name":"Doanh thu thuần",**{f"Value{i}":10000/i for i in range(1,5)}},
                                  {"ReportNormID":2215,"Name":"EPS",**{f"Value{i}":1973 for i in range(1,5)}}]}}

def period(year,profit,equity,scope="consolidated"):
    values={"net_profit":profit,"equity":equity,"assets":equity*2,"liabilities":equity,"revenue":profit*10,
            "non_controlling_equity":0,"cfo":profit*1.2,"short_debt":10,"long_debt":10}
    return {"year":year,"business_type":1,"scope":scope,"fields":{k:{"value":v,"source_id":"fixture","period":str(year)} for k,v in values.items()}}

class FinancialGuardTests(unittest.TestCase):
    def test_unit_conversion_does_not_multiply_eps(self):
        r=parse_annual_financials(payload(),"income",date(2026,10,9),"test")
        self.assertEqual(r[0]["fields"]["revenue"]["value"],10000000)
        self.assertEqual(r[0]["fields"]["eps"]["value"],1973)
    def test_ambiguous_and_duplicate_periods_rejected(self):
        for ids in [[1],[1,2,1,2]]:
            p=payload();p["Head"]=[dict(p["Head"][i],ID=v) for i,v in enumerate(ids)]
            with self.assertRaises(DataSourceError):parse_annual_financials(p,"income",date(2026,10,9),"test")
    def test_quarter_not_treated_as_independent_annual(self):
        p=payload();p["Head"][0]["TermCode"]="Q2"
        with self.assertRaises(DataSourceError):parse_annual_financials(p,"income",date(2026,10,9),"test")
    def test_future_publication_and_revision_excluded(self):
        p=payload();p["Head"][0]["DatePubDepartment"]="2026-11-01"
        p["Head"][1]["LastUpdate"]="2026-11-01"
        self.assertEqual([r["year"] for r in parse_annual_financials(p,"income",date(2026,10,9),"test")],[2023,2022])
    def test_average_equity_and_growth(self):
        f=analyze_financials([period(2025,20,120),period(2024,10,80)])
        m={r["key"]:r for r in f["metrics"]}
        self.assertEqual(m["roe"]["value"],20)
        self.assertEqual(m["net_profit_growth"]["value"],100)
        self.assertEqual(len(m["roe"]["inputs"]),3)
    def test_scope_mismatch_and_accounting_identity_blocked(self):
        a=period(2025,10,100);b=period(2025,10,100,"parent")
        self.assertFalse(analyze_financials([a,b])["periods"])
        a["fields"]["assets"]["value"]=999
        self.assertFalse(analyze_financials([a])["periods"])
    def test_financial_statement_end_dates_must_match(self):
        a=period(2025,10,100);b=period(2025,10,100)
        a["period_end"]="2025-12-31";b["period_end"]="2025-09-30"
        self.assertFalse(analyze_financials([a,b])["periods"])
    def test_source_fiscal_end_is_preserved(self):
        p=payload();p["Head"][0].update({"PeriodEnd":"202509","PeriodBegin":"202410"})
        r=parse_annual_financials(p,"income",date(2026,10,9),"test")
        self.assertEqual(r[0]["period_end"],"2025-09-30")
    def test_invalid_denominators_and_negative_base_not_misleading_growth(self):
        self.assertIsNone(ratio(10,0));self.assertIsNone(ratio(10,-10))
        self.assertIsNone(growth(10,-10));self.assertIsNone(growth(-10,10))
    def test_bank_does_not_receive_nonfinancial_ratios(self):
        a=period(2025,10,100);a["business_type"]=3
        keys={m["key"] for m in analyze_financials([a])["metrics"]}
        self.assertNotIn("debt_equity",keys);self.assertNotIn("cash_conversion",keys)
    def test_missing_adjusted_series_suppresses_return(self):
        rows=[{"close":100,"date":"2026-10-08","volume":1}]
        self.assertIsNone(analyze_market(rows)["return_pct"])
    def test_drawdown_uses_previous_peak(self):
        rows=[{"close":v,"adjusted_close":v,"date":f"2026-10-0{i+1}","volume":1} for i,v in enumerate([100,120,90,110])]
        self.assertAlmostEqual(analyze_market(rows)["max_drawdown_pct"],-25)
    def test_price_mismatch_and_stale_quote_not_accepted(self):
        rows=[{"date":"2026-10-07","close":100},{"date":"2026-10-08","close":110}]
        q=compare_prices(rows,{"data_day":[{"t":"2026-10-07 07:00","c":100}]},date(2026,10,8))
        self.assertFalse(q["latest_match"])
        q=compare_prices(rows,{"data_day":[{"t":"2026-10-07","c":90},{"t":"2026-10-08","c":110}]},date(2026,10,8))
        self.assertEqual(q["status"],"unverified")
    def test_valuation_rejects_historical_current_shares_and_unverified_prices(self):
        f=analyze_financials([period(2025,20,120)])
        company={"snapshot_at":"2026-10-09","outstanding_shares":10,"source_id":"test"}
        m={"latest_close_vnd":20}
        self.assertFalse(analyze_valuation(f,m,company,{"status":"matched","latest_match":True},date(2026,10,8),1.5)["available"])
        self.assertFalse(analyze_valuation(f,m,company,{"status":"unverified","latest_match":True},date(2026,10,9),1.5)["available"])
        self.assertTrue(analyze_valuation(f,m,company,{"status":"matched","latest_match":True},date(2026,10,9),1.5)["available"])
    def test_ocr_requires_balance_identity_and_rejects_wrong_unit(self):
        text="""BÁO CÁO hợp nhất Đơn vị: VND kết thúc ngày 30 tháng 6 năm 2026
TỔNG CỘNG TÀI SẢN 200.000.000 180.000.000
C. NỢ PHẢI TRẢ 100.000.000 90.000.000
D. VỐN CHỦ SỞ HỮU 100.000.000 90.000.000
Doanh thu thuần về bán hàng 120.000.000 100.000.000
18. Lợi nhuận sau thuế thu nhập 20.000.000 10.000.000
Lưu chuyển tiền thuần từ hoạt động kinh doanh 22.000.000 11.000.000"""
        self.assertTrue(parse_interim_text([{"page":1,"text":text}],"test","2026-08-28")["valid"])
        self.assertFalse(parse_interim_text([{"page":1,"text":text.replace("VND","USD")}],"test","2026-08-28")["valid"])
        self.assertFalse(parse_interim_text([{"page":1,"text":text.replace("200.000.000","300.000.000")}],"test","2026-08-28")["valid"])

class ReportTests(unittest.TestCase):
    def test_selected_pdf_contains_same_number_and_excludes_other_sections(self):
        import pymupdf
        result={"request":{"ticker":"HPG","as_of":"2026-10-09","start":"2025-10-09","mode":"summary","sections":["financial"]},
                "acquisition":{"run_id":"fixture"},"company":{"name":"Hòa Phát"},"market":None,"price_rows":[],"financial":analyze_financials([period(2025,20e9,120e9),period(2024,10e9,80e9)]),
                "interim":None,"valuation":{"available":False},"conclusion":{"summary":"Kiểm tra tiếng Việt","opportunities":[],"risks":[]},"news":[],
                "quality":{"price_check":{"status":"unverified"},"financial_check":{"status":"not_independently_checked","checks":[]},"warnings":[]},"errors":[],"status":"partial","sources":[]}
        with TemporaryDirectory() as folder:
            path=generate_report(result,Path(folder)/"report.pdf")
            with pymupdf.open(path) as doc:text="\n".join(p.get_text() for p in doc)
        self.assertIn("20.00 tỷ VND",text);self.assertIn("Kiểm tra tiếng Việt",text)
        self.assertNotIn("Tin tức",text);self.assertNotIn("Giá và giao dịch",text)
        self.assertIn("Phương pháp",text);self.assertIn("Nguồn và khả năng truy vết",text)

if __name__=="__main__":unittest.main()
