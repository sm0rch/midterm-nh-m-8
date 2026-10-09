"""Market statistics from one provider-defined adjusted-close series."""
import math
import statistics


def analyze_market(rows):
    if not rows:
        return None
    closes = [row["close"] for row in rows]
    adjusted = [row.get("adjusted_close") for row in rows]
    usable = all(isinstance(v,(int,float)) and math.isfinite(v) and v > 0 for v in adjusted)
    series = adjusted if usable else closes
    # Normalize chart/MA to the latest close while retaining provider-adjusted relative changes.
    factor = closes[-1]/series[-1]
    normalized = [v*factor for v in series]
    peak, drawdown = series[0], 0
    for value in series:
        peak=max(peak,value);drawdown=min(drawdown,value/peak-1)
    returns = [math.log(series[i]/series[i-1]) for i in range(1,len(series))]
    return {"latest_close_vnd": closes[-1],"latest_date": rows[-1]["date"],"latest_volume": rows[-1]["volume"],
            "ma20_vnd":sum(normalized[-20:])/20 if len(rows)>=20 else None,
            "ma50_vnd":sum(normalized[-50:])/50 if len(rows)>=50 else None,
            "return_pct":(series[-1]/series[0]-1)*100 if usable else None,
            "max_drawdown_pct":drawdown*100 if usable else None,
            "annualized_volatility_pct":statistics.stdev(returns)*math.sqrt(252)*100 if usable and len(returns)>1 else None,
            "average_volume_20":sum(r["volume"] for r in rows[-20:])/20 if len(rows)>=20 else None,
            "chart_prices": normalized, "series_basis":"Yahoo adjusted_close" if usable else "Yahoo close; adjustment unverified",
            "return_note":"Biến động theo chuỗi Adj Close do Yahoo điều chỉnh cổ tức/chia tách; không phải lợi nhuận thực nhận sau thuế/phí." if usable else "Thiếu chuỗi Adj Close đầy đủ; không tính lợi suất/drawdown."}
