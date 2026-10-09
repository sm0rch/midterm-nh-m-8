"""
chart_generator.py
===================
Module vẽ biểu đồ phân tích cổ phiếu bằng matplotlib.
Xuất hình ảnh PNG để nhúng vào báo cáo PDF.
"""

import warnings
warnings.filterwarnings('ignore')

import matplotlib
matplotlib.use('Agg')  # Non-interactive backend

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.gridspec as gridspec
from matplotlib.patches import FancyBboxPatch
import matplotlib.ticker as mticker
import pandas as pd
import numpy as np
from typing import Dict, Any, Optional, List, Tuple
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

# Vietnamese-compatible font (dùng font system)
plt.rcParams.update({
    'font.family': ['DejaVu Sans', 'sans-serif'],
    'font.size': 10,
    'axes.titlesize': 12,
    'axes.titleweight': 'bold',
    'figure.facecolor': 'white',
    'axes.facecolor': '#f8f9fa',
    'axes.grid': True,
    'grid.alpha': 0.3,
    'axes.spines.top': False,
    'axes.spines.right': False,
})

# Color palette
COLORS = {
    'primary': '#1565C0',
    'secondary': '#2E7D32',
    'accent': '#F57F17',
    'danger': '#C62828',
    'neutral': '#546E7A',
    'positive': '#2E7D32',
    'negative': '#C62828',
    'candle_up': '#26A69A',
    'candle_down': '#EF5350',
    'sma20': '#FF9800',
    'sma50': '#2196F3',
    'sma200': '#9C27B0',
    'volume': '#78909C',
    'rsi': '#00BCD4',
    'macd': '#1565C0',
    'signal': '#FF7043',
    'bb_upper': '#E91E63',
    'bb_lower': '#E91E63',
    'bb_fill': '#FCE4EC',
    'bg_dark': '#1a1a2e',
}


class ChartGenerator:
    """Tạo tất cả biểu đồ cần thiết cho báo cáo phân tích."""

    def __init__(self, output_dir: str = "output"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # 1. CANDLESTICK + TECHNICAL CHART (MAIN CHART)
    # ------------------------------------------------------------------
    def plot_price_technical(
        self,
        price_df: pd.DataFrame,
        tech_data: Dict[str, Any],
        symbol: str,
        filename: str = "price_technical.png",
    ) -> str:
        """
        Biểu đồ giá + MA + Bollinger + Volume + RSI + MACD.
        Trả về đường dẫn file PNG.
        """
        fig = plt.figure(figsize=(16, 12), facecolor='white')
        fig.suptitle(
            f"Phân Tích Kỹ Thuật - {symbol}",
            fontsize=16, fontweight='bold', y=0.98, color=COLORS['primary']
        )

        gs = gridspec.GridSpec(4, 1, figure=fig, hspace=0.08,
                               height_ratios=[4, 1.5, 1.2, 1.2])

        # Chuẩn hoá dữ liệu
        df = price_df.copy()
        col_map = {}
        for c in df.columns:
            cl = c.lower()
            if cl in ["time", "date"]:
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
        df = df.rename(columns=col_map)
        if "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"])
        df = df.tail(250)  # 1 năm gần nhất
        x = np.arange(len(df))

        # ---- Panel 1: Price + MA + Bollinger ----
        ax1 = fig.add_subplot(gs[0])
        
        # Vẽ candlestick
        width = 0.5
        for i, row in df.iterrows():
            xi = x[df.index.get_loc(i)]
            color = COLORS['candle_up'] if row.get('close', 0) >= row.get('open', 0) else COLORS['candle_down']
            # Body
            body_low = min(row.get('open', row.get('close', 0)), row.get('close', 0))
            body_high = max(row.get('open', row.get('close', 0)), row.get('close', 0))
            ax1.bar(xi, body_high - body_low, bottom=body_low, color=color, width=width * 0.8, alpha=0.85)
            # Wick
            ax1.plot([xi, xi], [row.get('low', body_low), row.get('high', body_high)],
                     color=color, linewidth=0.6, alpha=0.7)

        # Moving Averages
        if "sma_20" in tech_data:
            sma20 = tech_data["sma_20"].iloc[-len(df):]
            ax1.plot(x, sma20.values, color=COLORS['sma20'], linewidth=1.5,
                    label='SMA 20', alpha=0.9)
        if "sma_50" in tech_data:
            sma50 = tech_data["sma_50"].iloc[-len(df):]
            ax1.plot(x, sma50.values, color=COLORS['sma50'], linewidth=1.5,
                    label='SMA 50', alpha=0.9)
        if "sma_200" in tech_data:
            sma200 = tech_data["sma_200"].iloc[-len(df):]
            ax1.plot(x, sma200.values, color=COLORS['sma200'], linewidth=1.5,
                    label='SMA 200', linestyle='--', alpha=0.8)

        # Bollinger Bands
        if all(k in tech_data for k in ["bb_upper", "bb_lower", "bb_mid"]):
            bb_up = tech_data["bb_upper"].iloc[-len(df):].values
            bb_lo = tech_data["bb_lower"].iloc[-len(df):].values
            bb_md = tech_data["bb_mid"].iloc[-len(df):].values
            ax1.fill_between(x, bb_up, bb_lo, color=COLORS['bb_fill'], alpha=0.3, label='Bollinger Bands')
            ax1.plot(x, bb_up, color=COLORS['bb_upper'], linewidth=0.8, linestyle=':', alpha=0.8)
            ax1.plot(x, bb_lo, color=COLORS['bb_lower'], linewidth=0.8, linestyle=':', alpha=0.8)
            ax1.plot(x, bb_md, color='gray', linewidth=0.8, linestyle='--', alpha=0.5)

        ax1.set_ylabel('Giá (VNĐ)', fontsize=10)
        ax1.legend(loc='upper left', fontsize=8, framealpha=0.8)
        ax1.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, p: f'{x:,.0f}'))
        ax1.set_xlim(-1, len(x))
        ax1.tick_params(labelbottom=False)

        # Annotation: current price
        summary = tech_data.get("summary", {})
        cur_price = summary.get("current_price", 0)
        ax1.axhline(y=cur_price, color=COLORS['primary'], linewidth=1.5, linestyle='-', alpha=0.5)
        ax1.text(len(x) - 1, cur_price, f'  {cur_price:,.0f}',
                va='center', ha='left', color=COLORS['primary'], fontsize=9, fontweight='bold')

        # ---- Panel 2: Volume ----
        ax2 = fig.add_subplot(gs[1], sharex=ax1)
        if "volume" in df.columns:
            colors_vol = [
                COLORS['candle_up'] if row.get('close', 0) >= row.get('open', 0)
                else COLORS['candle_down']
                for _, row in df.iterrows()
            ]
            ax2.bar(x, df['volume'].values, color=colors_vol, alpha=0.7, width=0.8)
            if "vol_sma_20" in tech_data:
                vol_sma = tech_data["vol_sma_20"].iloc[-len(df):]
                ax2.plot(x, vol_sma.values, color=COLORS['accent'], linewidth=1.2, label='Vol SMA 20')
        ax2.set_ylabel('Khối lượng', fontsize=9)
        ax2.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, p: f'{x/1e6:.1f}M'))
        ax2.tick_params(labelbottom=False)
        ax2.set_facecolor('#f0f4f8')

        # ---- Panel 3: RSI ----
        ax3 = fig.add_subplot(gs[2], sharex=ax1)
        if "rsi_14" in tech_data:
            rsi_vals = tech_data["rsi_14"].iloc[-len(df):].values
            ax3.plot(x, rsi_vals, color=COLORS['rsi'], linewidth=1.5)
            ax3.axhline(y=70, color=COLORS['danger'], linewidth=1, linestyle='--', alpha=0.7)
            ax3.axhline(y=30, color=COLORS['secondary'], linewidth=1, linestyle='--', alpha=0.7)
            ax3.axhline(y=50, color='gray', linewidth=0.8, linestyle='-', alpha=0.4)
            ax3.fill_between(x, rsi_vals, 70, where=(rsi_vals >= 70), color=COLORS['danger'], alpha=0.2)
            ax3.fill_between(x, rsi_vals, 30, where=(rsi_vals <= 30), color=COLORS['secondary'], alpha=0.2)
            ax3.set_ylim(0, 100)
            ax3.text(-8, 70, 'OB', color=COLORS['danger'], fontsize=7, va='center')
            ax3.text(-8, 30, 'OS', color=COLORS['secondary'], fontsize=7, va='center')
        ax3.set_ylabel('RSI (14)', fontsize=9)
        ax3.tick_params(labelbottom=False)
        ax3.set_facecolor('#f0f8f4')

        # ---- Panel 4: MACD ----
        ax4 = fig.add_subplot(gs[3], sharex=ax1)
        if all(k in tech_data for k in ["macd_line", "macd_signal", "macd_hist"]):
            macd_l = tech_data["macd_line"].iloc[-len(df):].values
            macd_s = tech_data["macd_signal"].iloc[-len(df):].values
            macd_h = tech_data["macd_hist"].iloc[-len(df):].values
            
            colors_hist = [COLORS['candle_up'] if v >= 0 else COLORS['candle_down'] for v in macd_h]
            ax4.bar(x, macd_h, color=colors_hist, alpha=0.6, width=0.8)
            ax4.plot(x, macd_l, color=COLORS['macd'], linewidth=1.3, label='MACD')
            ax4.plot(x, macd_s, color=COLORS['signal'], linewidth=1.3, label='Signal')
            ax4.axhline(y=0, color='gray', linewidth=0.8, alpha=0.5)
            ax4.legend(loc='upper left', fontsize=7, framealpha=0.8)
        ax4.set_ylabel('MACD', fontsize=9)
        ax4.set_facecolor('#f8f0f0')

        # X-axis dates
        n_ticks = 10
        step = max(1, len(df) // n_ticks)
        tick_positions = x[::step]
        if "date" in df.columns:
            tick_labels = df['date'].iloc[::step].dt.strftime('%d/%m/%y')
        else:
            tick_labels = [str(i) for i in x[::step]]
        ax4.set_xticks(tick_positions)
        ax4.set_xticklabels(tick_labels, rotation=30, ha='right', fontsize=8)
        ax4.set_xlabel('Ngày', fontsize=9)

        plt.tight_layout()
        output_path = self.output_dir / filename
        plt.savefig(output_path, dpi=150, bbox_inches='tight', facecolor='white')
        plt.close()
        logger.info(f"Đã lưu biểu đồ kỹ thuật: {output_path}")
        return str(output_path)

    # ------------------------------------------------------------------
    # 2. FINANCIAL PERFORMANCE CHART
    # ------------------------------------------------------------------
    def plot_financial_performance(
        self,
        ratios_df: pd.DataFrame,
        symbol: str,
        filename: str = "financial_performance.png",
    ) -> str:
        """Biểu đồ các chỉ số tài chính quan trọng qua các kỳ."""
        fig, axes = plt.subplots(2, 3, figsize=(15, 9))
        fig.suptitle(f"Chỉ Số Tài Chính - {symbol}", fontsize=14,
                     fontweight='bold', color=COLORS['primary'])

        if ratios_df is None or ratios_df.empty:
            fig.text(0.5, 0.5, 'Không có dữ liệu tài chính',
                    ha='center', va='center', fontsize=14)
            output_path = self.output_dir / filename
            plt.savefig(output_path, dpi=130, bbox_inches='tight')
            plt.close()
            return str(output_path)

        # Chuẩn hoá dữ liệu
        df = ratios_df.copy()
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [' '.join(map(str, c)).strip() for c in df.columns]
        if isinstance(df.index, pd.MultiIndex):
            df = df.reset_index()

        # Map item_id → metric
        metrics_map = {
            'pe_ratio': ('P/E Ratio', COLORS['primary'], 'lần'),
            'pb_ratio': ('P/B Ratio', COLORS['secondary'], 'lần'),
            'gross_margin': ('Biên LN Gộp (%)', COLORS['accent'], '%'),
            'net_margin': ('Biên LN Ròng (%)', COLORS['danger'], '%'),
            'roe': ('ROE (%)', '#7B1FA2', '%'),
            'roa': ('ROA (%)', '#00838F', '%'),
        }

        ax_flat = axes.flatten()
        plotted = 0
        period_cols = [c for c in df.columns if c not in ['item', 'item_id']]
        period_cols = period_cols[:6]  # Tối đa 6 kỳ

        for ax_idx, (metric_id, (metric_name, color, unit)) in enumerate(metrics_map.items()):
            if ax_idx >= len(ax_flat):
                break
            ax = ax_flat[ax_idx]

            # Tìm row tương ứng
            row_data = df[df.get('item_id', pd.Series([], dtype=str)).str.lower().str.strip() == metric_id.lower()]
            if row_data.empty:
                # Thử tìm theo tên
                row_data = df[df.get('item', pd.Series([], dtype=str)).str.lower().str.contains(
                    metric_id.replace('_', ' ').lower()[:8], na=False)]

            if row_data.empty:
                ax.text(0.5, 0.5, f'Không có\n{metric_name}',
                       ha='center', va='center', transform=ax.transAxes, fontsize=10, color='gray')
                ax.set_title(metric_name)
                plotted += 1
                continue

            vals = []
            labels = []
            for pc in period_cols:
                if pc in row_data.columns:
                    v = pd.to_numeric(row_data[pc].values[0], errors='coerce')
                    if not np.isnan(v):
                        vals.append(v)
                        labels.append(str(pc))

            if not vals:
                ax.text(0.5, 0.5, f'Không có\n{metric_name}',
                       ha='center', va='center', transform=ax.transAxes, fontsize=10, color='gray')
                ax.set_title(metric_name)
                plotted += 1
                continue

            # Vẽ bar chart
            bars = ax.bar(range(len(vals)), vals, color=color, alpha=0.8, width=0.6, edgecolor='white')
            ax.set_title(metric_name, fontsize=11, fontweight='bold', color=color)
            ax.set_xticks(range(len(labels)))
            ax.set_xticklabels(labels, rotation=45, ha='right', fontsize=7)
            ax.set_ylabel(unit, fontsize=9)

            # Value labels on bars
            for bar, val in zip(bars, vals):
                ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + max(vals) * 0.02,
                       f'{val:.2f}', ha='center', va='bottom', fontsize=7.5, fontweight='bold')

            # Add trend line
            if len(vals) > 1:
                z = np.polyfit(range(len(vals)), vals, 1)
                p = np.poly1d(z)
                trend_color = COLORS['positive'] if z[0] >= 0 else COLORS['negative']
                ax.plot(range(len(vals)), [p(i) for i in range(len(vals))],
                       'r--', linewidth=1.2, alpha=0.6, color=trend_color)

            plotted += 1

        plt.tight_layout()
        output_path = self.output_dir / filename
        plt.savefig(output_path, dpi=130, bbox_inches='tight', facecolor='white')
        plt.close()
        return str(output_path)

    # ------------------------------------------------------------------
    # 3. INVESTMENT SCORE RADAR CHART
    # ------------------------------------------------------------------
    def plot_score_radar(
        self,
        scores: Dict[str, float],
        symbol: str,
        filename: str = "score_radar.png",
    ) -> str:
        """Biểu đồ radar thể hiện điểm đầu tư đa chiều."""
        categories = list(scores.keys())
        values = list(scores.values())

        if len(categories) < 3:
            # Tạo biểu đồ đơn giản thay thế
            return self._plot_score_bar(scores, symbol, filename)

        N = len(categories)
        angles = [n / float(N) * 2 * np.pi for n in range(N)]
        angles += angles[:1]
        values_plot = values + values[:1]

        fig, ax = plt.subplots(1, 1, figsize=(8, 8), subplot_kw=dict(polar=True))
        fig.patch.set_facecolor('white')

        ax.set_theta_offset(np.pi / 2)
        ax.set_theta_direction(-1)

        plt.xticks(angles[:-1], categories, size=11, fontweight='bold')
        ax.set_rlabel_position(0)
        plt.yticks([20, 40, 60, 80, 100], ['20', '40', '60', '80', '100'], color='grey', size=8)
        plt.ylim(0, 100)

        ax.plot(angles, values_plot, linewidth=2.5, linestyle='solid', color=COLORS['primary'])
        ax.fill(angles, values_plot, alpha=0.3, color=COLORS['primary'])

        # Add value labels
        for angle, val, cat in zip(angles[:-1], values, categories):
            ax.text(angle, val + 8, f'{val:.0f}', ha='center', va='center',
                   fontsize=9, fontweight='bold', color=COLORS['primary'])

        ax.set_title(f'Phân Tích Đa Chiều - {symbol}',
                    size=13, fontweight='bold', y=1.08, color=COLORS['primary'])

        output_path = self.output_dir / filename
        plt.savefig(output_path, dpi=130, bbox_inches='tight', facecolor='white')
        plt.close()
        return str(output_path)

    def _plot_score_bar(self, scores: Dict[str, float], symbol: str, filename: str) -> str:
        """Fallback: bar chart thay cho radar."""
        fig, ax = plt.subplots(figsize=(10, 5))
        categories = list(scores.keys())
        values = list(scores.values())
        colors = [COLORS['positive'] if v >= 60 else COLORS['accent'] if v >= 40 else COLORS['danger'] for v in values]
        bars = ax.barh(categories, values, color=colors, alpha=0.8, height=0.6)
        ax.set_xlim(0, 100)
        ax.axvline(x=60, color='gray', linestyle='--', alpha=0.5)
        for bar, val in zip(bars, values):
            ax.text(val + 1, bar.get_y() + bar.get_height() / 2,
                   f'{val:.1f}', va='center', fontweight='bold')
        ax.set_title(f'Điểm Phân Tích - {symbol}', fontweight='bold', color=COLORS['primary'])
        ax.set_xlabel('Điểm (0-100)')
        plt.tight_layout()
        output_path = self.output_dir / filename
        plt.savefig(output_path, dpi=130, bbox_inches='tight')
        plt.close()
        return str(output_path)

    # ------------------------------------------------------------------
    # 4. PRICE PERFORMANCE COMPARISON
    # ------------------------------------------------------------------
    def plot_price_performance(
        self,
        price_df: pd.DataFrame,
        symbol: str,
        filename: str = "price_performance.png",
    ) -> str:
        """Biểu đồ hiệu suất giá chuẩn hoá (% return)."""
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))
        fig.suptitle(f"Hiệu Suất Giá - {symbol}", fontsize=14,
                     fontweight='bold', color=COLORS['primary'])

        df = price_df.copy()
        col_map = {}
        for c in df.columns:
            cl = c.lower()
            if cl in ["time", "date"]:
                col_map[c] = "date"
            elif cl == "close":
                col_map[c] = "close"
            elif cl in ["volume", "vol"]:
                col_map[c] = "volume"
        df = df.rename(columns=col_map)
        if "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"])

        close = df["close"]

        # ---- Normalized return ----
        base_price = close.iloc[0]
        pct_return = (close / base_price - 1) * 100

        colors = [COLORS['positive'] if v >= 0 else COLORS['negative'] for v in pct_return]
        if "date" in df.columns:
            ax1.plot(df["date"], pct_return, color=COLORS['primary'], linewidth=1.5)
            ax1.fill_between(df["date"], pct_return, 0,
                            where=(pct_return >= 0), color=COLORS['positive'], alpha=0.2)
            ax1.fill_between(df["date"], pct_return, 0,
                            where=(pct_return < 0), color=COLORS['negative'], alpha=0.2)
        ax1.axhline(y=0, color='gray', linewidth=1, alpha=0.7)
        ax1.set_title('% Lợi Nhuận Tích Lũy', fontsize=11)
        ax1.set_ylabel('% Return')
        ax1.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, p: f'{x:.1f}%'))
        ax1.tick_params(axis='x', rotation=30)

        # ---- Monthly returns heatmap (simplified) ----
        periods = {
            '1W': 5, '2W': 10, '1M': 22, '3M': 66, '6M': 132, '1Y': 252
        }
        period_returns = []
        period_labels = []
        for label, days in periods.items():
            if len(close) >= days:
                ret = (close.iloc[-1] / close.iloc[-days] - 1) * 100
                period_returns.append(ret)
                period_labels.append(label)

        if period_returns:
            bar_colors = [COLORS['positive'] if v >= 0 else COLORS['negative'] for v in period_returns]
            bars = ax2.bar(period_labels, period_returns, color=bar_colors, alpha=0.85, width=0.6)
            ax2.axhline(y=0, color='gray', linewidth=1, alpha=0.7)
            ax2.set_title('Lợi Nhuận Theo Giai Đoạn', fontsize=11)
            ax2.set_ylabel('% Return')
            ax2.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, p: f'{x:.1f}%'))
            for bar, val in zip(bars, period_returns):
                ypos = val + 0.5 if val >= 0 else val - 1.5
                ax2.text(bar.get_x() + bar.get_width() / 2, ypos,
                        f'{val:.1f}%', ha='center', va='bottom', fontsize=9, fontweight='bold')

        plt.tight_layout()
        output_path = self.output_dir / filename
        plt.savefig(output_path, dpi=130, bbox_inches='tight', facecolor='white')
        plt.close()
        return str(output_path)

    # ------------------------------------------------------------------
    # 5. COMPOSITE SCORE GAUGE
    # ------------------------------------------------------------------
    def plot_score_gauge(
        self,
        score: float,
        recommendation: str,
        symbol: str,
        filename: str = "score_gauge.png",
    ) -> str:
        """Đồng hồ đo điểm đầu tư tổng hợp."""
        fig, ax = plt.subplots(1, 1, figsize=(8, 5), subplot_kw=dict(aspect='equal'))
        fig.patch.set_facecolor('white')
        ax.set_xlim(-1.5, 1.5)
        ax.set_ylim(-0.8, 1.5)
        ax.axis('off')

        # Gauge arcs
        segments = [
            (0, 20, COLORS['danger'], 'BÁN\nMẠNH'),
            (20, 40, '#EF6C00', 'BÁN'),
            (40, 60, COLORS['accent'], 'TRUNG\nTÍNH'),
            (60, 80, '#66BB6A', 'MUA'),
            (80, 100, COLORS['secondary'], 'MUA\nMẠNH'),
        ]

        for start, end, color, label in segments:
            theta1 = 180 - end * 1.8
            theta2 = 180 - start * 1.8
            arc = mpatches.Wedge(
                (0, 0), 1.3, theta1, theta2,
                width=0.3, color=color, alpha=0.8
            )
            ax.add_patch(arc)
            # Label
            mid_angle = np.radians((theta1 + theta2) / 2)
            lx = 1.0 * np.cos(mid_angle)
            ly = 1.0 * np.sin(mid_angle)
            ax.text(lx, ly, label, ha='center', va='center',
                   fontsize=7.5, fontweight='bold', color='white')

        # Needle
        needle_angle = np.radians(180 - score * 1.8)
        nx = 1.0 * np.cos(needle_angle)
        ny = 1.0 * np.sin(needle_angle)
        ax.annotate('', xy=(nx, ny), xytext=(0, 0),
                   arrowprops=dict(arrowstyle='->', color='black', lw=2.5))

        # Center circle
        center_circle = plt.Circle((0, 0), 0.1, color='white', zorder=5)
        ax.add_patch(center_circle)

        # Score text
        ax.text(0, -0.4, f'{score:.1f}', ha='center', va='center',
               fontsize=28, fontweight='bold', color=COLORS['primary'])
        ax.text(0, -0.65, recommendation, ha='center', va='center',
               fontsize=14, fontweight='bold',
               color=COLORS['positive'] if 'MUA' in recommendation else
               COLORS['danger'] if 'BÁN' in recommendation else COLORS['neutral'])

        ax.set_title(f'Điểm Đầu Tư Tổng Hợp - {symbol}',
                    fontsize=13, fontweight='bold', color=COLORS['primary'], y=1.05)

        output_path = self.output_dir / filename
        plt.savefig(output_path, dpi=130, bbox_inches='tight', facecolor='white')
        plt.close()
        return str(output_path)

    def generate_all_charts(
        self,
        price_df: pd.DataFrame,
        tech_data: Dict,
        ratios_df: pd.DataFrame,
        final_score: Dict,
        symbol: str,
    ) -> Dict[str, str]:
        """Tạo tất cả biểu đồ. Trả về dict {tên: đường dẫn}."""
        charts = {}
        print(f"  📊 Vẽ biểu đồ kỹ thuật...")
        try:
            charts["price_technical"] = self.plot_price_technical(
                price_df, tech_data, symbol, f"{symbol}_technical.png"
            )
        except Exception as e:
            logger.warning(f"Lỗi vẽ biểu đồ kỹ thuật: {e}")

        print(f"  📊 Vẽ biểu đồ hiệu suất...")
        try:
            charts["price_performance"] = self.plot_price_performance(
                price_df, symbol, f"{symbol}_performance.png"
            )
        except Exception as e:
            logger.warning(f"Lỗi vẽ biểu đồ hiệu suất: {e}")

        print(f"  📊 Vẽ biểu đồ chỉ số tài chính...")
        try:
            charts["financial_performance"] = self.plot_financial_performance(
                ratios_df, symbol, f"{symbol}_financials.png"
            )
        except Exception as e:
            logger.warning(f"Lỗi vẽ biểu đồ tài chính: {e}")

        print(f"  📊 Vẽ đồng hồ điểm đầu tư...")
        try:
            charts["score_gauge"] = self.plot_score_gauge(
                final_score.get("composite_score", 50),
                final_score.get("overall_recommendation", "TRUNG TÍNH"),
                symbol,
                f"{symbol}_gauge.png",
            )
        except Exception as e:
            logger.warning(f"Lỗi vẽ gauge: {e}")

        print(f"  📊 Vẽ biểu đồ radar đa chiều...")
        try:
            score_dict = {
                "Cơ Bản": final_score.get("fundamental_score", 50),
                "Kỹ Thuật": final_score.get("technical_score", 50),
                "Tăng Trưởng": 60,  # placeholder
                "Định Giá": 55,     # placeholder
                "Rủi Ro": 50,       # placeholder (inverted)
            }
            charts["radar"] = self.plot_score_radar(
                score_dict, symbol, f"{symbol}_radar.png"
            )
        except Exception as e:
            logger.warning(f"Lỗi vẽ radar: {e}")

        return charts
