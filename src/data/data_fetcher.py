"""
data_fetcher.py
================
Module thu thập dữ liệu từ vnstock và các nguồn bổ sung.
Hỗ trợ: giá cổ phiếu, BCTC, chỉ số tài chính, thông tin doanh nghiệp.
"""

import warnings
warnings.filterwarnings('ignore')

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Tuple
import logging

logger = logging.getLogger(__name__)


class StockDataFetcher:
    """Thu thập toàn bộ dữ liệu cần thiết cho phân tích một mã cổ phiếu."""

    DEFAULT_SOURCE = "VCI"

    def __init__(self, symbol: str, source: str = None):
        self.symbol = symbol.upper().strip()
        self.source = source or self.DEFAULT_SOURCE
        self._stock = None
        self._init_vnstock()

    def _init_vnstock(self):
        """Khởi tạo Vnstock client."""
        try:
            from vnstock import Vnstock
            self._stock = Vnstock().stock(symbol=self.symbol, source=self.source)
            logger.info(f"Khởi tạo Vnstock thành công cho {self.symbol}")
        except Exception as e:
            logger.error(f"Lỗi khởi tạo Vnstock: {e}")
            raise

    # ------------------------------------------------------------------
    # 1. GIÁ & GIAO DỊCH
    # ------------------------------------------------------------------
    def get_price_history(
        self,
        start: str = None,
        end: str = None,
        interval: str = "1D",
    ) -> pd.DataFrame:
        """
        Lấy lịch sử giá OHLCV.
        Mặc định: 2 năm gần nhất, chu kỳ 1 ngày.
        """
        if end is None:
            end = datetime.today().strftime("%Y-%m-%d")
        if start is None:
            start = (datetime.today() - timedelta(days=730)).strftime("%Y-%m-%d")

        try:
            df = self._stock.quote.history(
                start=start, end=end, interval=interval
            )
            if df is None or df.empty:
                logger.warning("Không có dữ liệu giá.")
                return pd.DataFrame()
            df = df.reset_index(drop=True)
            # Chuẩn hoá cột tên
            df.columns = [c.lower() for c in df.columns]
            if "time" in df.columns:
                df["time"] = pd.to_datetime(df["time"])
            return df
        except Exception as e:
            logger.error(f"Lỗi lấy giá: {e}")
            return pd.DataFrame()

    def get_intraday(self, page_size: int = 100) -> pd.DataFrame:
        """Lấy dữ liệu khớp lệnh trong phiên."""
        try:
            df = self._stock.quote.intraday(page_size=page_size)
            if df is None or df.empty:
                return pd.DataFrame()
            df.columns = [c.lower() for c in df.columns]
            return df
        except Exception as e:
            logger.warning(f"Không lấy được intraday: {e}")
            return pd.DataFrame()

    # ------------------------------------------------------------------
    # 2. THÔNG TIN DOANH NGHIỆP
    # ------------------------------------------------------------------
    def get_company_info(self) -> Dict[str, Any]:
        """Thông tin tổng quan doanh nghiệp."""
        result = {}
        try:
            overview = self._stock.company.overview()
            if overview is not None and not (
                isinstance(overview, pd.DataFrame) and overview.empty
            ):
                if isinstance(overview, pd.DataFrame):
                    result["overview"] = overview.iloc[0].to_dict()
                else:
                    result["overview"] = overview
        except Exception as e:
            logger.warning(f"Lỗi lấy company overview: {e}")

        try:
            profile = self._stock.company.profile()
            if profile is not None and not (
                isinstance(profile, pd.DataFrame) and profile.empty
            ):
                if isinstance(profile, pd.DataFrame):
                    result["profile"] = profile.iloc[0].to_dict()
                else:
                    result["profile"] = profile
        except Exception as e:
            logger.warning(f"Lỗi lấy company profile: {e}")

        try:
            officers = self._stock.company.officers()
            if officers is not None and isinstance(officers, pd.DataFrame):
                result["officers"] = officers.head(10).to_dict("records")
        except Exception as e:
            logger.warning(f"Lỗi lấy company officers: {e}")

        try:
            shareholders = self._stock.company.shareholders()
            if shareholders is not None and isinstance(shareholders, pd.DataFrame):
                result["shareholders"] = shareholders.head(10).to_dict("records")
        except Exception as e:
            logger.warning(f"Lỗi lấy shareholders: {e}")

        try:
            subsidiaries = self._stock.company.subsidiaries()
            if subsidiaries is not None and isinstance(subsidiaries, pd.DataFrame):
                result["subsidiaries"] = subsidiaries.head(10).to_dict("records")
        except Exception as e:
            logger.warning(f"Lỗi lấy subsidiaries: {e}")

        return result

    # ------------------------------------------------------------------
    # 3. BÁO CÁO TÀI CHÍNH
    # ------------------------------------------------------------------
    def get_financial_reports(self, period: str = "annual", lang: str = "vi") -> Dict[str, pd.DataFrame]:
        """
        Lấy BCTC: Balance Sheet, P&L, Cash Flow.
        period: 'annual' | 'quarter'
        """
        reports = {}
        try:
            bs = self._stock.finance.balance_sheet(period=period, lang=lang, dropna=True)
            if bs is not None and not bs.empty:
                reports["balance_sheet"] = bs
        except Exception as e:
            logger.warning(f"Lỗi lấy Balance Sheet: {e}")

        try:
            pl = self._stock.finance.income_statement(period=period, lang=lang, dropna=True)
            if pl is not None and not pl.empty:
                reports["income_statement"] = pl
        except Exception as e:
            logger.warning(f"Lỗi lấy Income Statement: {e}")

        try:
            cf = self._stock.finance.cash_flow(period=period, dropna=True)
            if cf is not None and not cf.empty:
                reports["cash_flow"] = cf
        except Exception as e:
            logger.warning(f"Lỗi lấy Cash Flow: {e}")

        return reports

    # ------------------------------------------------------------------
    # 4. CHỈ SỐ TÀI CHÍNH
    # ------------------------------------------------------------------
    def get_financial_ratios(self, period: str = "annual", lang: str = "vi") -> pd.DataFrame:
        """Lấy các chỉ số tài chính."""
        try:
            ratios = self._stock.finance.ratio(period=period, lang=lang, dropna=True)
            if ratios is not None and not ratios.empty:
                return ratios
        except Exception as e:
            logger.warning(f"Lỗi lấy financial ratios: {e}")
        return pd.DataFrame()

    # ------------------------------------------------------------------
    # 5. DỮ LIỆU THỊ TRƯỜNG & ĐỊNH GIÁ
    # ------------------------------------------------------------------
    def get_valuation_data(self) -> Dict[str, Any]:
        """Lấy thông tin định giá: P/E, P/B, EPS, v.v."""
        result = {}
        try:
            from vnstock import Quote
            qt = Quote(symbol=self.symbol, source=self.source)
            # Thử lấy price board
            board = qt.price_board([self.symbol])
            if board is not None and not board.empty:
                result["price_board"] = board.to_dict("records")[0] if len(board) else {}
        except Exception as e:
            logger.warning(f"Lỗi lấy price board: {e}")

        return result

    # ------------------------------------------------------------------
    # 6. SỰ KIỆN & TIN TỨC
    # ------------------------------------------------------------------
    def get_events(self) -> pd.DataFrame:
        """Các sự kiện doanh nghiệp (cổ tức, phát hành, v.v.)."""
        try:
            events = self._stock.company.events()
            if events is not None and isinstance(events, pd.DataFrame):
                return events.head(20)
        except Exception as e:
            logger.warning(f"Lỗi lấy events: {e}")
        return pd.DataFrame()

    def get_news(self, page_size: int = 10) -> pd.DataFrame:
        """Tin tức mới nhất liên quan đến doanh nghiệp."""
        try:
            news = self._stock.company.news(page_size=page_size)
            if news is not None and isinstance(news, pd.DataFrame):
                return news
        except Exception as e:
            logger.warning(f"Lỗi lấy news: {e}")
        return pd.DataFrame()

    # ------------------------------------------------------------------
    # 7. THU THẬP TOÀN BỘ
    # ------------------------------------------------------------------
    def fetch_all(self) -> Dict[str, Any]:
        """
        Thu thập toàn bộ dữ liệu cần thiết cho phân tích.
        Trả về dict gồm tất cả dữ liệu.
        """
        logger.info(f"⏳ Đang thu thập dữ liệu cho {self.symbol}...")
        data = {
            "symbol": self.symbol,
            "source": self.source,
            "fetched_at": datetime.now().isoformat(),
        }

        print(f"  📈 Lấy lịch sử giá 2 năm...")
        data["price_history"] = self.get_price_history()

        print(f"  🏢 Lấy thông tin doanh nghiệp...")
        data["company"] = self.get_company_info()

        print(f"  📋 Lấy báo cáo tài chính (năm)...")
        data["financials_annual"] = self.get_financial_reports(period="annual")

        print(f"  📋 Lấy báo cáo tài chính (quý)...")
        data["financials_quarter"] = self.get_financial_reports(period="quarter")

        print(f"  📊 Lấy chỉ số tài chính...")
        data["ratios_annual"] = self.get_financial_ratios(period="annual")
        data["ratios_quarter"] = self.get_financial_ratios(period="quarter")

        print(f"  📰 Lấy sự kiện & tin tức...")
        data["events"] = self.get_events()
        data["news"] = self.get_news()

        print(f"  ✅ Hoàn thành thu thập dữ liệu!")
        return data
