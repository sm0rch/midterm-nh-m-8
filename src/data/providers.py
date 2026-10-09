"""
providers.py — Data providers: vnstock (KBS/VCI) + DNSE fallback + Yahoo fallback.
Hỗ trợ mọi mã cổ phiếu niêm yết trên HOSE/HNX/UPCOM.
"""

from datetime import date, datetime, time, timedelta, timezone
import json
import re
import sys
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

VN_TIME = timezone(timedelta(hours=7), name="Asia/Saigon")

# Legacy HPG URL (kept for backward compat, no longer mandatory)
HPG_REPORTS_URL = "https://www.hoaphat.com.vn/quan-he-co-dong/bao-cao-tai-chinh"


class DataSourceError(RuntimeError):
    """A source could not provide usable data."""


# ── Helpers ──────────────────────────────────────────────────────────────────

def download(url: str, timeout: int = 30) -> bytes:
    request = Request(url, headers={"User-Agent": "Mozilla/5.0 StockInsight/0.1"})
    try:
        with urlopen(request, timeout=timeout) as response:
            return response.read()
    except (OSError, ValueError) as exc:
        raise DataSourceError(f"Unable to retrieve {url}: {exc}") from exc


def completed_day_cutoff(as_of: date, now: datetime | None = None) -> date:
    now = now or datetime.now(VN_TIME)
    if now.tzinfo is None:
        raise ValueError("now must be timezone-aware")
    return min(as_of, now.astimezone(VN_TIME).date() - timedelta(days=1))


# ── Provider 1: vnstock KBS (primary — works for any ticker) ─────────────────

def fetch_daily_prices_vnstock(ticker: str, start: date, as_of: date, now: datetime | None = None) -> dict:
    """
    Lấy giá lịch sử từ vnstock (source=KBS).
    Hoạt động với bất kỳ mã nào trên HOSE/HNX/UPCOM.
    """
    ticker = ticker.strip().upper()
    cutoff = completed_day_cutoff(as_of, now)
    try:
        from vnstock.api.quote import Quote
        q = Quote(symbol=ticker, source="KBS")
        df = q.history(start=start.isoformat(), end=cutoff.isoformat(), interval="1D")
        if df is None or df.empty:
            raise DataSourceError(f"vnstock KBS trả về rỗng cho {ticker}")
        # Chuẩn hoá cột
        df.columns = [c.lower() for c in df.columns]
        date_col = next((c for c in df.columns if c in ("time", "date", "datetime")), None)
        if date_col:
            df[date_col] = df[date_col].astype(str).str[:10]
        rows = []
        for _, row in df.iterrows():
            d = str(row.get(date_col, ""))[:10]
            if not d or d < start.isoformat() or d > cutoff.isoformat():
                continue
            rows.append({
                "ticker": ticker,
                "date": d,
                "open": float(row.get("open", 0) or 0),
                "high": float(row.get("high", 0) or 0),
                "low": float(row.get("low", 0) or 0),
                "close": float(row.get("close", 0) or 0),
                "volume": int(float(row.get("volume", 0) or 0)),
                "adjusted_close": float(row.get("close", 0) or 0),
                "price_basis": "vnstock_kbs_ohlcv",
                "unit": "VND_per_share",
            })
        if not rows:
            raise DataSourceError(f"vnstock KBS: không có hàng dữ liệu hợp lệ cho {ticker}")
        rows = sorted(rows, key=lambda r: r["date"])
        return {
            "url": f"vnstock://KBS/{ticker}",
            "raw": json.dumps(rows).encode(),
            "rows": rows,
            "meta": {"symbol": ticker, "currency": "VND", "longName": ticker, "source": "vnstock_kbs"},
            "cutoff": cutoff.isoformat(),
            "retrieved_at": datetime.now(VN_TIME).isoformat(),
        }
    except DataSourceError:
        raise
    except Exception as exc:
        raise DataSourceError(f"vnstock KBS error ({ticker}): {exc}") from exc


# ── Provider 2: vnstock VCI ───────────────────────────────────────────────────

def fetch_daily_prices_vnstock_vci(ticker: str, start: date, as_of: date, now: datetime | None = None) -> dict:
    """Lấy giá từ vnstock VCI (fallback cho KBS)."""
    ticker = ticker.strip().upper()
    cutoff = completed_day_cutoff(as_of, now)
    try:
        from vnstock.api.quote import Quote
        q = Quote(symbol=ticker, source="VCI")
        df = q.history(start=start.isoformat(), end=cutoff.isoformat(), interval="1D")
        if df is None or df.empty:
            raise DataSourceError(f"vnstock VCI trả về rỗng cho {ticker}")
        df.columns = [c.lower() for c in df.columns]
        date_col = next((c for c in df.columns if c in ("time", "date", "datetime")), None)
        if date_col:
            df[date_col] = df[date_col].astype(str).str[:10]
        rows = []
        for _, row in df.iterrows():
            d = str(row.get(date_col, ""))[:10]
            if not d or d < start.isoformat() or d > cutoff.isoformat():
                continue
            rows.append({
                "ticker": ticker,
                "date": d,
                "open": float(row.get("open", 0) or 0),
                "high": float(row.get("high", 0) or 0),
                "low": float(row.get("low", 0) or 0),
                "close": float(row.get("close", 0) or 0),
                "volume": int(float(row.get("volume", 0) or 0)),
                "adjusted_close": float(row.get("close", 0) or 0),
                "price_basis": "vnstock_vci_ohlcv",
                "unit": "VND_per_share",
            })
        if not rows:
            raise DataSourceError(f"vnstock VCI: không có hàng dữ liệu hợp lệ cho {ticker}")
        rows = sorted(rows, key=lambda r: r["date"])
        return {
            "url": f"vnstock://VCI/{ticker}",
            "raw": json.dumps(rows).encode(),
            "rows": rows,
            "meta": {"symbol": ticker, "currency": "VND", "longName": ticker, "source": "vnstock_vci"},
            "cutoff": cutoff.isoformat(),
            "retrieved_at": datetime.now(VN_TIME).isoformat(),
        }
    except DataSourceError:
        raise
    except Exception as exc:
        raise DataSourceError(f"vnstock VCI error ({ticker}): {exc}") from exc


# ── Provider 3: DNSE real-time ────────────────────────────────────────────────

def fetch_daily_prices_dnse(ticker: str, start: date, as_of: date, now: datetime | None = None) -> dict:
    """
    Lấy giá từ DNSE LightSpeed API.
    Đặc biệt hữu ích cho real-time và các mã nhỏ.
    """
    ticker = ticker.strip().upper()
    cutoff = completed_day_cutoff(as_of, now)
    try:
        # Import DNSE client từ thư mục dự án
        _root = Path(__file__).resolve().parents[2]
        if str(_root) not in sys.path:
            sys.path.insert(0, str(_root))
        import importlib.util, os
        dnse_path = _root / "src" / "data" / "dnse_client.py"
        if not dnse_path.exists():
            raise DataSourceError("DNSE client không tìm thấy")

        # Load credentials từ .env
        env_path = _root / ".env"
        username, password = "", ""
        if env_path.exists():
            for line in env_path.read_text().splitlines():
                if line.startswith("DNSE_USERNAME="):
                    username = line.split("=", 1)[1].strip().strip('"')
                elif line.startswith("DNSE_PASSWORD="):
                    password = line.split("=", 1)[1].strip().strip('"')

        if not username or not password:
            raise DataSourceError("DNSE credentials không tìm thấy trong .env")

        # Dùng DNSE REST API trực tiếp (không cần import module phức tạp)
        import requests as req_lib

        # Login
        login_resp = req_lib.post(
            "https://services.entrade.com.vn/dnse-user-service/api/auth",
            json={"username": username, "password": password},
            timeout=15
        )
        if login_resp.status_code != 200:
            raise DataSourceError(f"DNSE login failed: {login_resp.status_code}")
        token = login_resp.json().get("token", "")
        if not token:
            raise DataSourceError("DNSE token rỗng")

        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

        # Lấy lịch sử giá
        params = {
            "resolution": "D",
            "from": int(datetime.combine(start, time.min, VN_TIME).timestamp()),
            "to": int(datetime.combine(cutoff + timedelta(days=1), time.min, VN_TIME).timestamp()),
        }
        price_url = f"https://services.entrade.com.vn/chart-service/v2/history?symbol={ticker}&{urlencode(params)}"
        hist_resp = req_lib.get(price_url, headers=headers, timeout=20)
        if hist_resp.status_code != 200:
            raise DataSourceError(f"DNSE history failed: {hist_resp.status_code}")
        data = hist_resp.json()

        timestamps = data.get("t", [])
        opens = data.get("o", [])
        highs = data.get("h", [])
        lows = data.get("l", [])
        closes = data.get("c", [])
        volumes = data.get("v", [])

        rows = []
        for i, ts in enumerate(timestamps):
            d = datetime.fromtimestamp(ts, VN_TIME).date()
            if d < start or d > cutoff:
                continue
            rows.append({
                "ticker": ticker,
                "date": d.isoformat(),
                "open": float(opens[i]) if i < len(opens) else 0.0,
                "high": float(highs[i]) if i < len(highs) else 0.0,
                "low": float(lows[i]) if i < len(lows) else 0.0,
                "close": float(closes[i]) if i < len(closes) else 0.0,
                "volume": int(float(volumes[i])) if i < len(volumes) else 0,
                "adjusted_close": float(closes[i]) if i < len(closes) else 0.0,
                "price_basis": "dnse_lightspeed_ohlcv",
                "unit": "VND_per_share",
            })

        if not rows:
            raise DataSourceError(f"DNSE: không có dữ liệu cho {ticker}")
        rows = sorted(rows, key=lambda r: r["date"])
        return {
            "url": price_url,
            "raw": json.dumps(rows).encode(),
            "rows": rows,
            "meta": {"symbol": ticker, "currency": "VND", "longName": ticker, "source": "dnse"},
            "cutoff": cutoff.isoformat(),
            "retrieved_at": datetime.now(VN_TIME).isoformat(),
        }
    except DataSourceError:
        raise
    except Exception as exc:
        raise DataSourceError(f"DNSE error ({ticker}): {exc}") from exc


# ── Provider 4: Yahoo Finance (fallback cuối) ─────────────────────────────────

def parse_yahoo_chart(payload: dict, ticker: str, start: date, end: date) -> tuple[list[dict], dict]:
    try:
        chart = payload["chart"]
        if chart.get("error"):
            raise DataSourceError(f"Yahoo source error: {chart['error']}")
        result = chart["result"][0]
        meta = result["meta"]
        timestamps = result["timestamp"]
        quotes = result["indicators"]["quote"][0]
        adjusted = result["indicators"].get("adjclose", [{}])[0].get("adjclose", [])
        fields = ("open", "high", "low", "close", "volume")
        rows = []
        for i, timestamp in enumerate(timestamps):
            session_date = datetime.fromtimestamp(timestamp, VN_TIME).date()
            if start <= session_date <= end:
                rows.append({
                    "ticker": ticker, "date": session_date.isoformat(),
                    **{f: quotes[f][i] for f in fields},
                    "adjusted_close": adjusted[i] if i < len(adjusted) else None,
                    "price_basis": "yahoo_chart_ohlc_unverified", "unit": "VND_per_share",
                })
        return sorted(rows, key=lambda row: row["date"]), meta
    except (KeyError, IndexError, TypeError, ValueError) as exc:
        raise DataSourceError(f"Unrecognized Yahoo response: {exc}") from exc


def fetch_daily_prices_yahoo(ticker: str, start: date, as_of: date, now: datetime | None = None) -> dict:
    ticker = ticker.strip().upper()
    cutoff = completed_day_cutoff(as_of, now)
    parameters = {
        "period1": int(datetime.combine(start, time.min, VN_TIME).timestamp()),
        "period2": int(datetime.combine(cutoff + timedelta(days=1), time.min, VN_TIME).timestamp()),
        "interval": "1d", "events": "div,splits",
    }
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}.VN?{urlencode(parameters)}"
    raw = download(url)
    try:
        payload = json.loads(raw)
    except ValueError as exc:
        raise DataSourceError("Source returned non-JSON data") from exc
    rows, meta = parse_yahoo_chart(payload, ticker, start, cutoff)
    return {
        "url": url, "raw": raw, "rows": rows, "meta": meta,
        "cutoff": cutoff.isoformat(), "retrieved_at": datetime.now(VN_TIME).isoformat(),
    }


# ── Main entry point: thử lần lượt các nguồn ─────────────────────────────────

def fetch_daily_prices(ticker: str, start: date, as_of: date, now: datetime | None = None) -> dict:
    """
    Thử lần lượt: vnstock KBS → vnstock VCI → DNSE → Yahoo.
    Trả về dữ liệu từ nguồn đầu tiên thành công.
    """
    providers = [
        ("vnstock_kbs", fetch_daily_prices_vnstock),
        ("vnstock_vci", fetch_daily_prices_vnstock_vci),
        ("dnse", fetch_daily_prices_dnse),
        ("yahoo", fetch_daily_prices_yahoo),
    ]
    last_error = None
    for name, fn in providers:
        try:
            result = fn(ticker, start, as_of, now)
            if result["rows"]:
                return result
        except Exception as exc:
            last_error = exc
            continue
    raise DataSourceError(f"Tất cả nguồn dữ liệu giá đều thất bại cho {ticker}. Lỗi cuối: {last_error}")


# ── Real-time price ───────────────────────────────────────────────────────────

def fetch_realtime_price(ticker: str) -> dict | None:
    """
    Lấy giá real-time từ vnstock Company overview (VCI).
    Trả về dict gồm: price, change_pct, volume, market_cap, target_price, rating.
    """
    try:
        from vnstock.api.company import Company
        c = Company(symbol=ticker.upper(), source="VCI")
        ov = c.overview()
        if ov is None or (hasattr(ov, "empty") and ov.empty):
            return None
        if hasattr(ov, "iloc"):
            row = ov.iloc[0].to_dict()
        else:
            row = ov if isinstance(ov, dict) else {}
        return {
            "price": row.get("current_price"),
            "market_cap": row.get("market_cap"),
            "target_price": row.get("target_price"),
            "rating": row.get("rating"),
            "highest_1y": row.get("highest_price1_year"),
            "lowest_1y": row.get("lowest_price1_year"),
            "foreign_pct": row.get("foreigner_percentage"),
            "upside_pct": row.get("upside_to_target_percent"),
            "sector": row.get("sector"),
            "company_name": row.get("organ_name"),
            "short_name": row.get("organ_short_name"),
            "company_profile": row.get("company_profile", ""),
            "issue_share": row.get("issue_share"),
            "free_float_pct": row.get("free_float_percentage"),
            "listing_date": row.get("listing_date"),
            "source": "vnstock_vci_realtime",
        }
    except Exception:
        return None


# ── HPG report discovery (legacy, kept for compatibility) ────────────────────

def parse_hpg_reports(html: bytes, as_of: date) -> list[dict]:
    from bs4 import BeautifulSoup
    from urllib.parse import urljoin, urlparse
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
    return sorted(reports, key=lambda r: r["published_at"], reverse=True)


def discover_hpg_reports(as_of: date) -> tuple[list[dict], bytes]:
    html = download(HPG_REPORTS_URL)
    return parse_hpg_reports(html, as_of), html
