"""Public-source acquisition. No promise of real-time or verified adjustment basis."""

from datetime import date, datetime, time, timedelta, timezone
import json
import re
from urllib.parse import urlencode, urljoin, urlparse
from urllib.request import Request, urlopen

from bs4 import BeautifulSoup

VN_TIME = timezone(timedelta(hours=7), name="Asia/Saigon")
HPG_REPORTS_URL = "https://www.hoaphat.com.vn/quan-he-co-dong/bao-cao-tai-chinh"


class DataSourceError(RuntimeError):
    """A source could not provide usable data; callers must not invent a fallback."""


def download(url: str, timeout: int = 30) -> bytes:
    request = Request(url, headers={"User-Agent": "Mozilla/5.0 StockInsight/0.1"})
    try:
        with urlopen(request, timeout=timeout) as response:
            return response.read()
    except (OSError, ValueError) as exc:
        raise DataSourceError(f"Unable to retrieve {url}: {exc}") from exc


def completed_day_cutoff(as_of: date, now: datetime | None = None) -> date:
    """Conservative rule: use only dates strictly before today's local date.

    Does not assume the market is closed or a daily bar is finalized today.
    A future requested date never permits future observations.
    """
    now = now or datetime.now(VN_TIME)
    if now.tzinfo is None:
        raise ValueError("now must be timezone-aware")
    return min(as_of, now.astimezone(VN_TIME).date() - timedelta(days=1))


def parse_yahoo_chart(payload: dict, ticker: str, start: date, end: date) -> tuple[list[dict], dict]:
    try:
        chart = payload["chart"]
        if chart.get("error"):
            raise DataSourceError(f"Yahoo source error: {chart['error']}")
        result = chart["result"][0]
        meta = result["meta"]
        if meta.get("symbol", "").upper() != f"{ticker}.VN" or meta.get("currency") != "VND":
            raise DataSourceError("Unexpected source symbol or currency")
        timestamps = result["timestamp"]
        quotes = result["indicators"]["quote"][0]
        adjusted = result["indicators"].get("adjclose", [{}])[0].get("adjclose", [])
        fields = ("open", "high", "low", "close", "volume")
        if any(len(quotes[f]) != len(timestamps) for f in fields):
            raise DataSourceError("Source arrays have inconsistent lengths")
        rows = []
        for i, timestamp in enumerate(timestamps):
            session_date = datetime.fromtimestamp(timestamp, VN_TIME).date()
            if start <= session_date <= end:
                rows.append({"ticker": ticker, "date": session_date.isoformat(),
                             **{f: quotes[f][i] for f in fields},
                             "adjusted_close": adjusted[i] if i < len(adjusted) else None,
                             "price_basis": "yahoo_chart_ohlc_unverified", "unit": "VND_per_share"})
        return sorted(rows, key=lambda row: row["date"]), meta
    except (KeyError, IndexError, TypeError, ValueError) as exc:
        raise DataSourceError(f"Unrecognized Yahoo response: {exc}") from exc


def fetch_daily_prices(ticker: str, start: date, as_of: date, now: datetime | None = None) -> dict:
    ticker = ticker.strip().upper()
    if not re.fullmatch(r"[A-Z][A-Z0-9]{1,9}", ticker):
        raise ValueError("Invalid ticker")
    cutoff = completed_day_cutoff(as_of, now)
    if start > cutoff:
        raise ValueError("start must be on or before the completed-day cutoff")
    parameters = {"period1": int(datetime.combine(start, time.min, VN_TIME).timestamp()),
                  "period2": int(datetime.combine(cutoff + timedelta(days=1), time.min, VN_TIME).timestamp()),
                  "interval": "1d", "events": "div,splits"}
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}.VN?{urlencode(parameters)}"
    raw = download(url)
    try:
        payload = json.loads(raw)
    except ValueError as exc:
        raise DataSourceError("Source returned non-JSON data") from exc
    rows, meta = parse_yahoo_chart(payload, ticker, start, cutoff)
    return {"url": url, "raw": raw, "rows": rows, "meta": meta,
            "cutoff": cutoff.isoformat(), "retrieved_at": datetime.now(VN_TIME).isoformat()}


def parse_hpg_reports(html: bytes, as_of: date) -> list[dict]:
    """Read publication dates from the issuer's listing, not from download times."""
    soup = BeautifulSoup(html, "html.parser")
    reports, seen = [], set()
    for item in soup.select("div.item"):
        anchor = item.select_one("div.name a[href]")
        published = item.select_one("div.time")
        if anchor is None or published is None:
            continue
        title = anchor.get_text(" ", strip=True)
        url = urljoin(HPG_REPORTS_URL, anchor["href"])
        if "hợp nhất" not in title.lower() or not urlparse(url).path.lower().endswith(".pdf"):
            continue
        if urlparse(url).hostname != "file.hoaphat.com.vn" or url in seen:
            continue
        try:
            publication_date = datetime.strptime(published.get_text(strip=True), "%d/%m/%Y").date()
        except ValueError:
            continue
        if publication_date <= as_of:
            reports.append({"ticker": "HPG", "title": title, "url": url,
                            "published_at": publication_date.isoformat(), "statement_scope": "consolidated"})
            seen.add(url)
    return sorted(reports, key=lambda report: report["published_at"], reverse=True)


def discover_hpg_reports(as_of: date) -> tuple[list[dict], bytes]:
    html = download(HPG_REPORTS_URL)
    return parse_hpg_reports(html, as_of), html
