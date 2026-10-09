"""
analyzer.py
============
Module phân tích kỹ thuật và cơ bản cho cổ phiếu Việt Nam.
Tính toán: chỉ báo kỹ thuật, định giá, phân tích tài chính, khuyến nghị.
"""

import warnings
warnings.filterwarnings('ignore')

import pandas as pd
import numpy as np
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class TechnicalAnalyzer:
    """Phân tích kỹ thuật: Moving Averages, RSI, MACD, Bollinger Bands."""

    def __init__(self, price_df: pd.DataFrame):
        self.df = price_df.copy()
        if self.df.empty:
            raise ValueError("DataFrame giá rỗng, không thể phân tích kỹ thuật.")
        # Chuẩn hoá cột
        col_map = {}
        for c in self.df.columns:
            cl = c.lower()
            if cl in ["time", "date", "datetime"]:
                col_map[c] = "date"
            elif cl == "close":
                col_map[c] = "close"
            elif cl == "open":
                col_map[c] = "open"
            elif cl == "high":
                col_map[c] = "high"
            elif cl == "low":
                col_map[c] = "low"
            elif cl in ["volume", "vol"]:
                col_map[c] = "volume"
        self.df = self.df.rename(columns=col_map)
        if "date" in self.df.columns:
            self.df["date"] = pd.to_datetime(self.df["date"])
            self.df = self.df.sort_values("date").reset_index(drop=True)

    # ------------------------------------------------------------------
    # Moving Averages
    # ------------------------------------------------------------------
    def sma(self, window: int) -> pd.Series:
        """Simple Moving Average."""
        return self.df["close"].rolling(window=window).mean()

    def ema(self, window: int) -> pd.Series:
        """Exponential Moving Average."""
        return self.df["close"].ewm(span=window, adjust=False).mean()

    # ------------------------------------------------------------------
    # RSI
    # ------------------------------------------------------------------
    def rsi(self, window: int = 14) -> pd.Series:
        """Relative Strength Index."""
        delta = self.df["close"].diff()
        gain = delta.clip(lower=0).rolling(window=window).mean()
        loss = (-delta.clip(upper=0)).rolling(window=window).mean()
        rs = gain / loss.replace(0, np.nan)
        return 100 - (100 / (1 + rs))

    # ------------------------------------------------------------------
    # MACD
    # ------------------------------------------------------------------
    def macd(
        self, fast: int = 12, slow: int = 26, signal: int = 9
    ) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """MACD Line, Signal Line, Histogram."""
        ema_fast = self.ema(fast)
        ema_slow = self.ema(slow)
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal, adjust=False).mean()
        histogram = macd_line - signal_line
        return macd_line, signal_line, histogram

    # ------------------------------------------------------------------
    # Bollinger Bands
    # ------------------------------------------------------------------
    def bollinger_bands(
        self, window: int = 20, num_std: float = 2.0
    ) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """Upper, Middle, Lower Bollinger Bands."""
        middle = self.sma(window)
        std = self.df["close"].rolling(window=window).std()
        upper = middle + num_std * std
        lower = middle - num_std * std
        return upper, middle, lower

    # ------------------------------------------------------------------
    # Volume Analysis
    # ------------------------------------------------------------------
    def volume_sma(self, window: int = 20) -> pd.Series:
        if "volume" not in self.df.columns:
            return pd.Series(dtype=float)
        return self.df["volume"].rolling(window=window).mean()

    # ------------------------------------------------------------------
    # Hỗ trợ / Kháng cự
    # ------------------------------------------------------------------
    def support_resistance(self, window: int = 20) -> Dict[str, float]:
        prices = self.df["close"].dropna()
        if len(prices) < window:
            return {}
        recent = prices.tail(window)
        return {
            "support": float(recent.min()),
            "resistance": float(recent.max()),
            "pivot": float((recent.max() + recent.min() + prices.iloc[-1]) / 3),
        }

    # ------------------------------------------------------------------
    # Tổng hợp phân tích kỹ thuật
    # ------------------------------------------------------------------
    def full_analysis(self) -> Dict[str, Any]:
        """Tính toán tất cả chỉ báo kỹ thuật và sinh tín hiệu."""
        close = self.df["close"]
        result = {}

        # Moving Averages
        result["sma_20"] = self.sma(20)
        result["sma_50"] = self.sma(50)
        result["sma_200"] = self.sma(200)
        result["ema_12"] = self.ema(12)
        result["ema_26"] = self.ema(26)

        # RSI
        result["rsi_14"] = self.rsi(14)

        # MACD
        macd_line, signal_line, histogram = self.macd()
        result["macd_line"] = macd_line
        result["macd_signal"] = signal_line
        result["macd_hist"] = histogram

        # Bollinger Bands
        bb_upper, bb_mid, bb_lower = self.bollinger_bands()
        result["bb_upper"] = bb_upper
        result["bb_mid"] = bb_mid
        result["bb_lower"] = bb_lower

        # Volume
        result["vol_sma_20"] = self.volume_sma(20)

        # --- Tín hiệu tổng hợp ---
        latest_idx = len(close) - 1
        signals = {}

        # RSI signal
        rsi_val = result["rsi_14"].iloc[-1] if not result["rsi_14"].empty else np.nan
        if not np.isnan(rsi_val):
            if rsi_val < 30:
                signals["rsi"] = {"value": rsi_val, "signal": "MUA MẠNH", "note": "Quá bán (Oversold)"}
            elif rsi_val < 45:
                signals["rsi"] = {"value": rsi_val, "signal": "MUA", "note": "Vùng tích lũy"}
            elif rsi_val > 70:
                signals["rsi"] = {"value": rsi_val, "signal": "BÁN MẠNH", "note": "Quá mua (Overbought)"}
            elif rsi_val > 55:
                signals["rsi"] = {"value": rsi_val, "signal": "BÁN", "note": "Xu hướng tăng chậm lại"}
            else:
                signals["rsi"] = {"value": rsi_val, "signal": "TRUNG TÍNH", "note": "Vùng trung tính"}

        # MACD signal
        macd_v = result["macd_line"].iloc[-1]
        sig_v = result["macd_signal"].iloc[-1]
        hist_v = result["macd_hist"].iloc[-1]
        hist_prev = result["macd_hist"].iloc[-2] if len(result["macd_hist"]) > 1 else 0
        if macd_v > sig_v and hist_v > hist_prev:
            signals["macd"] = {"signal": "MUA", "note": "MACD cắt lên Signal, momentum tăng"}
        elif macd_v < sig_v and hist_v < hist_prev:
            signals["macd"] = {"signal": "BÁN", "note": "MACD cắt xuống Signal, momentum giảm"}
        else:
            signals["macd"] = {"signal": "TRUNG TÍNH", "note": "Chưa có tín hiệu rõ ràng"}

        # MA Cross signal
        sma20_v = result["sma_20"].iloc[-1]
        sma50_v = result["sma_50"].iloc[-1]
        sma200_v = result["sma_200"].iloc[-1] if not np.isnan(result["sma_200"].iloc[-1]) else None
        current_price = float(close.iloc[-1])

        if current_price > sma20_v > sma50_v:
            signals["trend"] = {"signal": "MUA", "note": "Giá > SMA20 > SMA50 → Uptrend"}
        elif current_price < sma20_v < sma50_v:
            signals["trend"] = {"signal": "BÁN", "note": "Giá < SMA20 < SMA50 → Downtrend"}
        else:
            signals["trend"] = {"signal": "TRUNG TÍNH", "note": "Đang trong vùng sideway"}

        # Bollinger Band signal
        bb_up_v = result["bb_upper"].iloc[-1]
        bb_low_v = result["bb_lower"].iloc[-1]
        if current_price >= bb_up_v:
            signals["bollinger"] = {"signal": "BÁN", "note": "Giá chạm dải trên BB → Quá mua"}
        elif current_price <= bb_low_v:
            signals["bollinger"] = {"signal": "MUA", "note": "Giá chạm dải dưới BB → Quá bán"}
        else:
            bb_pos = (current_price - bb_low_v) / (bb_up_v - bb_low_v) * 100
            signals["bollinger"] = {
                "signal": "TRUNG TÍNH",
                "note": f"Giá trong dải BB ({bb_pos:.0f}%)",
            }

        # Tổng hợp khuyến nghị kỹ thuật
        buy_signals = sum(1 for s in signals.values() if "MUA" in s.get("signal", ""))
        sell_signals = sum(1 for s in signals.values() if "BÁN" in s.get("signal", ""))
        if buy_signals >= 3:
            overall_technical = "MUA MẠNH"
        elif buy_signals >= 2:
            overall_technical = "MUA"
        elif sell_signals >= 3:
            overall_technical = "BÁN MẠNH"
        elif sell_signals >= 2:
            overall_technical = "BÁN"
        else:
            overall_technical = "TRUNG TÍNH"

        # Price performance
        perf = {}
        if len(close) >= 5:
            perf["1W"] = (close.iloc[-1] / close.iloc[-5] - 1) * 100
        if len(close) >= 22:
            perf["1M"] = (close.iloc[-1] / close.iloc[-22] - 1) * 100
        if len(close) >= 66:
            perf["3M"] = (close.iloc[-1] / close.iloc[-66] - 1) * 100
        if len(close) >= 252:
            perf["1Y"] = (close.iloc[-1] / close.iloc[-252] - 1) * 100

        # 52-week high/low
        w52 = close.tail(252)
        week52_high = float(w52.max())
        week52_low = float(w52.min())
        dist_from_high = (current_price / week52_high - 1) * 100
        dist_from_low = (current_price / week52_low - 1) * 100

        # Volatility (annualised)
        returns = close.pct_change().dropna()
        volatility = float(returns.std() * np.sqrt(252) * 100) if len(returns) > 0 else 0.0

        # Average True Range (ATR 14)
        if all(c in self.df.columns for c in ["high", "low", "close"]):
            high = self.df["high"]
            low = self.df["low"]
            tr = pd.concat(
                [
                    high - low,
                    (high - close.shift()).abs(),
                    (low - close.shift()).abs(),
                ],
                axis=1,
            ).max(axis=1)
            atr = tr.rolling(14).mean().iloc[-1]
        else:
            atr = np.nan

        result["summary"] = {
            "current_price": current_price,
            "price_performance": perf,
            "week52_high": week52_high,
            "week52_low": week52_low,
            "dist_from_52w_high_pct": dist_from_high,
            "dist_from_52w_low_pct": dist_from_low,
            "volatility_annual_pct": volatility,
            "atr_14": atr,
            "signals": signals,
            "overall_technical": overall_technical,
            "support_resistance": self.support_resistance(),
            "sma20": sma20_v,
            "sma50": sma50_v,
            "sma200": sma200_v,
            "rsi": rsi_val,
            "macd": macd_v,
            "macd_signal": sig_v,
        }

        return result


class FundamentalAnalyzer:
    """Phân tích cơ bản: BCTC, chỉ số định giá, sức khoẻ tài chính."""

    def __init__(self, ratios_df: pd.DataFrame, income_df: pd.DataFrame = None,
                 balance_sheet_df: pd.DataFrame = None, cash_flow_df: pd.DataFrame = None):
        self.ratios = ratios_df if ratios_df is not None else pd.DataFrame()
        self.income = income_df if income_df is not None else pd.DataFrame()
        self.balance = balance_sheet_df if balance_sheet_df is not None else pd.DataFrame()
        self.cash_flow = cash_flow_df if cash_flow_df is not None else pd.DataFrame()

    def _safe_get(self, df: pd.DataFrame, keyword: str, row_idx: int = 0) -> Optional[float]:
        """Lấy giá trị từ DataFrame theo keyword tìm trong tên cột/index."""
        if df is None or df.empty:
            return None
        # Tìm trong index (MultiIndex hoặc thường)
        try:
            if isinstance(df.index, pd.MultiIndex):
                for level_vals in zip(*df.index.levels):
                    pass
                idx_df = df.reset_index()
            else:
                idx_df = df.copy()
            # Tìm cột chứa keyword
            for col in idx_df.columns:
                if keyword.lower() in str(col).lower():
                    vals = idx_df[col].dropna()
                    if len(vals) > 0:
                        return float(vals.iloc[row_idx]) if row_idx < len(vals) else float(vals.iloc[-1])
        except Exception:
            pass
        return None

    def extract_key_ratios(self) -> Dict[str, Any]:
        """Trích xuất các chỉ số tài chính quan trọng nhất."""
        result = {}
        if self.ratios.empty:
            return result

        df = self.ratios
        # Xử lý MultiIndex (vnstock thường trả về MultiIndex)
        try:
            if isinstance(df.columns, pd.MultiIndex):
                # Flatten columns
                df.columns = [' '.join(map(str, c)).strip() for c in df.columns]
            if isinstance(df.index, pd.MultiIndex):
                df = df.reset_index()
        except Exception:
            pass

        # Chuyển về dạng có thể duyệt
        for col in df.columns:
            col_str = str(col).lower()
            val_series = df[col].dropna()
            if val_series.empty:
                continue
            val = val_series.iloc[-1]  # lấy mới nhất

            # P/E
            if "p/e" in col_str or "pe ratio" in col_str or "price_to_earning" in col_str:
                try:
                    result["PE"] = float(val)
                except Exception:
                    pass
            # P/B
            if "p/b" in col_str or "pb ratio" in col_str or "price_to_book" in col_str:
                try:
                    result["PB"] = float(val)
                except Exception:
                    pass
            # EPS
            if "eps" in col_str and "growth" not in col_str:
                try:
                    result["EPS"] = float(val)
                except Exception:
                    pass
            # ROE
            if "roe" in col_str:
                try:
                    result["ROE"] = float(val)
                except Exception:
                    pass
            # ROA
            if "roa" in col_str:
                try:
                    result["ROA"] = float(val)
                except Exception:
                    pass
            # Gross Margin
            if "gross" in col_str and "margin" in col_str:
                try:
                    result["GrossMargin"] = float(val)
                except Exception:
                    pass
            # Net Margin
            if "net" in col_str and "margin" in col_str:
                try:
                    result["NetMargin"] = float(val)
                except Exception:
                    pass
            # Dividend yield
            if "dividend" in col_str and "yield" in col_str:
                try:
                    result["DividendYield"] = float(val)
                except Exception:
                    pass
            # Debt ratio
            if "debt" in col_str and "equity" in col_str:
                try:
                    result["DebtToEquity"] = float(val)
                except Exception:
                    pass
            # Current ratio
            if "current ratio" in col_str or "current_ratio" in col_str:
                try:
                    result["CurrentRatio"] = float(val)
                except Exception:
                    pass
            # Revenue growth
            if "revenue" in col_str and "growth" in col_str:
                try:
                    result["RevenueGrowth"] = float(val)
                except Exception:
                    pass

        return result

    def score_fundamental(self, ratios: Dict[str, Any]) -> Dict[str, Any]:
        """
        Chấm điểm cơ bản từ 0-100 dựa trên các chỉ số.
        """
        scores = {}
        max_scores = {}

        # --- P/E ---
        pe = ratios.get("PE")
        if pe is not None and not np.isnan(pe):
            max_scores["PE"] = 20
            if 5 <= pe <= 15:
                scores["PE"] = 20  # Định giá hấp dẫn
            elif 15 < pe <= 20:
                scores["PE"] = 15
            elif 20 < pe <= 25:
                scores["PE"] = 10
            elif pe > 25:
                scores["PE"] = 5   # Định giá cao
            else:
                scores["PE"] = 3   # P/E âm hoặc quá thấp, rủi ro

        # --- ROE ---
        roe = ratios.get("ROE")
        if roe is not None and not np.isnan(roe):
            max_scores["ROE"] = 25
            roe_pct = roe * 100 if abs(roe) <= 1 else roe
            if roe_pct >= 20:
                scores["ROE"] = 25
            elif roe_pct >= 15:
                scores["ROE"] = 20
            elif roe_pct >= 10:
                scores["ROE"] = 15
            elif roe_pct >= 5:
                scores["ROE"] = 10
            else:
                scores["ROE"] = 3

        # --- Net Margin ---
        nm = ratios.get("NetMargin")
        if nm is not None and not np.isnan(nm):
            max_scores["NetMargin"] = 20
            nm_pct = nm * 100 if abs(nm) <= 1 else nm
            if nm_pct >= 20:
                scores["NetMargin"] = 20
            elif nm_pct >= 10:
                scores["NetMargin"] = 15
            elif nm_pct >= 5:
                scores["NetMargin"] = 10
            elif nm_pct > 0:
                scores["NetMargin"] = 5
            else:
                scores["NetMargin"] = 0

        # --- Debt/Equity ---
        de = ratios.get("DebtToEquity")
        if de is not None and not np.isnan(de):
            max_scores["DebtToEquity"] = 15
            if de < 0.3:
                scores["DebtToEquity"] = 15
            elif de < 0.5:
                scores["DebtToEquity"] = 12
            elif de < 1.0:
                scores["DebtToEquity"] = 8
            elif de < 2.0:
                scores["DebtToEquity"] = 4
            else:
                scores["DebtToEquity"] = 1

        # --- P/B ---
        pb = ratios.get("PB")
        if pb is not None and not np.isnan(pb):
            max_scores["PB"] = 10
            if 0.5 <= pb <= 1.5:
                scores["PB"] = 10
            elif 1.5 < pb <= 3:
                scores["PB"] = 7
            elif pb > 3:
                scores["PB"] = 4
            else:
                scores["PB"] = 2

        # --- Revenue Growth ---
        rg = ratios.get("RevenueGrowth")
        if rg is not None and not np.isnan(rg):
            max_scores["RevenueGrowth"] = 10
            rg_pct = rg * 100 if abs(rg) <= 1 else rg
            if rg_pct >= 20:
                scores["RevenueGrowth"] = 10
            elif rg_pct >= 10:
                scores["RevenueGrowth"] = 7
            elif rg_pct >= 0:
                scores["RevenueGrowth"] = 4
            else:
                scores["RevenueGrowth"] = 1

        total_score = sum(scores.values())
        total_max = sum(max_scores.values()) if max_scores else 100

        # Chuẩn hoá về 100
        normalized = (total_score / total_max * 100) if total_max > 0 else 0

        if normalized >= 80:
            recommendation = "MUA MẠNH"
        elif normalized >= 65:
            recommendation = "MUA"
        elif normalized >= 50:
            recommendation = "NẮM GIỮ"
        elif normalized >= 35:
            recommendation = "THEO DÕI"
        else:
            recommendation = "BÁN"

        return {
            "scores": scores,
            "total_score": total_score,
            "total_max": total_max,
            "normalized_score": normalized,
            "recommendation": recommendation,
        }

    def growth_analysis(self) -> Dict[str, Any]:
        """Phân tích tăng trưởng doanh thu, lợi nhuận qua các năm."""
        result = {}
        if self.income is None or self.income.empty:
            return result

        df = self.income.copy()
        try:
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = [' '.join(map(str, c)).strip() for c in df.columns]
            if isinstance(df.index, pd.MultiIndex):
                df = df.reset_index()

            # Tìm cột doanh thu và lợi nhuận
            revenue_col = None
            profit_col = None
            for col in df.columns:
                c = str(col).lower()
                if ("doanh thu" in c or "revenue" in c or "net revenue" in c) and revenue_col is None:
                    revenue_col = col
                if ("lợi nhuận" in c or "net profit" in c or "profit after" in c or "net income" in c) and profit_col is None:
                    profit_col = col

            if revenue_col:
                rev = df[revenue_col].dropna().apply(pd.to_numeric, errors="coerce").dropna()
                if len(rev) >= 2:
                    rev_growth = rev.pct_change().dropna() * 100
                    result["revenue"] = {
                        "values": rev.tail(5).tolist(),
                        "growth_pct": rev_growth.tail(4).tolist(),
                        "latest": float(rev.iloc[-1]),
                        "cagr": self._cagr(rev.tolist()),
                    }

            if profit_col:
                pnl = df[profit_col].dropna().apply(pd.to_numeric, errors="coerce").dropna()
                if len(pnl) >= 2:
                    pnl_growth = pnl.pct_change().dropna() * 100
                    result["net_profit"] = {
                        "values": pnl.tail(5).tolist(),
                        "growth_pct": pnl_growth.tail(4).tolist(),
                        "latest": float(pnl.iloc[-1]),
                        "cagr": self._cagr(pnl.tolist()),
                    }
        except Exception as e:
            logger.warning(f"Lỗi phân tích tăng trưởng: {e}")

        return result

    def _cagr(self, values: list, years: int = None) -> Optional[float]:
        """Tính CAGR từ danh sách giá trị."""
        try:
            vals = [v for v in values if v and not np.isnan(v) and v > 0]
            if len(vals) < 2:
                return None
            n = years or (len(vals) - 1)
            return (vals[-1] / vals[0]) ** (1 / n) - 1
        except Exception:
            return None


class InvestmentScorer:
    """
    Kết hợp phân tích kỹ thuật + cơ bản → Điểm đầu tư tổng hợp.
    """

    def __init__(self, technical_summary: Dict, fundamental_score: Dict, company_info: Dict = None):
        self.tech = technical_summary
        self.fund = fundamental_score
        self.company = company_info or {}

    def compute_final_score(self) -> Dict[str, Any]:
        """
        Tính điểm đầu tư tổng hợp từ 0–100.
        Trọng số: Cơ bản 60%, Kỹ thuật 40%.
        """
        # Technical score (0–100)
        tech_signal_map = {
            "MUA MẠNH": 100, "MUA": 75, "TRUNG TÍNH": 50, "THEO DÕI": 40, "BÁN": 25, "BÁN MẠNH": 0
        }
        overall_tech = self.tech.get("overall_technical", "TRUNG TÍNH")
        tech_score = tech_signal_map.get(overall_tech, 50)

        # Individual signal scores
        signals = self.tech.get("signals", {})
        signal_scores = []
        for sig_name, sig_data in signals.items():
            sig_val = tech_signal_map.get(sig_data.get("signal", "TRUNG TÍNH"), 50)
            signal_scores.append(sig_val)
        if signal_scores:
            tech_score = np.mean(signal_scores)

        # Fundamental score (0–100)
        fund_score = self.fund.get("normalized_score", 50)

        # Composite score
        composite = 0.40 * tech_score + 0.60 * fund_score

        # Risk assessment
        volatility = self.tech.get("volatility_annual_pct", 30)
        rsi = self.tech.get("rsi", 50)

        risk_level = "TRUNG BÌNH"
        if volatility > 50 or rsi > 75 or rsi < 25:
            risk_level = "CAO"
        elif volatility < 20 and 40 <= rsi <= 60:
            risk_level = "THẤP"

        # Final recommendation
        if composite >= 80:
            recommendation = "MUA MẠNH"
            target_upside = "+15% đến +25%"
        elif composite >= 65:
            recommendation = "MUA"
            target_upside = "+8% đến +15%"
        elif composite >= 50:
            recommendation = "NẮM GIỮ"
            target_upside = "+0% đến +8%"
        elif composite >= 35:
            recommendation = "THEO DÕI"
            target_upside = "-5% đến +5%"
        else:
            recommendation = "BÁN"
            target_upside = "< -5%"

        # Price targets (simple calculation)
        current_price = self.tech.get("current_price", 0)
        w52_high = self.tech.get("week52_high", current_price * 1.3)
        support = self.tech.get("support_resistance", {}).get("support", current_price * 0.9)
        resistance = self.tech.get("support_resistance", {}).get("resistance", current_price * 1.1)

        return {
            "composite_score": round(composite, 1),
            "technical_score": round(tech_score, 1),
            "fundamental_score": round(fund_score, 1),
            "overall_recommendation": recommendation,
            "target_upside": target_upside,
            "risk_level": risk_level,
            "price_target_1y": round(current_price * 1.15, 2) if current_price else None,
            "stop_loss": round(support * 0.95, 2) if support else None,
            "resistance_target": round(resistance, 2) if resistance else None,
            "investment_highlights": self._generate_highlights(composite, tech_score, fund_score, risk_level),
            "risk_factors": self._generate_risks(risk_level, volatility, rsi),
        }

    def _generate_highlights(self, composite, tech, fund, risk) -> List[str]:
        highlights = []
        if fund >= 70:
            highlights.append("✅ Nền tảng tài chính vững chắc với các chỉ số cơ bản tốt")
        if tech >= 70:
            highlights.append("📈 Xu hướng kỹ thuật tích cực, momentum tăng")
        if composite >= 70:
            highlights.append("⭐ Cơ hội đầu tư hấp dẫn với tỷ suất lợi nhuận tiềm năng cao")
        if 50 <= composite < 70:
            highlights.append("📊 Cổ phiếu có tiềm năng tăng trưởng ổn định")
        highlights.append("🇻🇳 Thị trường chứng khoán Việt Nam đang trong giai đoạn phát triển")
        return highlights

    def _generate_risks(self, risk_level, volatility, rsi) -> List[str]:
        risks = []
        if risk_level == "CAO":
            risks.append("⚠️ Biến động giá cao, đòi hỏi quản lý rủi ro chặt chẽ")
        if volatility > 40:
            risks.append(f"📊 Biến động giá năm hoá ~{volatility:.0f}%, cao hơn mức trung bình thị trường")
        if rsi > 70:
            risks.append("🔴 RSI ở vùng quá mua, cẩn thận với nguy cơ điều chỉnh ngắn hạn")
        risks.append("⚠️ Rủi ro thị trường chung và biến động vĩ mô")
        risks.append("📋 Thông tin trên mang tính tham khảo, không phải tư vấn đầu tư")
        return risks
