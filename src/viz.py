"""Render the PNG charts used in the README and the memo (matplotlib only).
Shared colors and styling so the charts look consistent."""
from __future__ import annotations

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd

ASSETS = "assets"
INK = "#152230"
MUTED = "#5C6B7E"
ACCENT = "#0E7C82"
ACCENT_LT = "#8FC7CB"
COPPER = "#B5632A"
GRID = "#E1E6EC"

plt.rcParams.update({
    "figure.dpi": 130,
    "savefig.dpi": 130,
    "font.family": "DejaVu Sans",
    "font.size": 11,
    "axes.edgecolor": GRID,
    "axes.labelcolor": INK,
    "axes.titlecolor": INK,
    "text.color": INK,
    "xtick.color": MUTED,
    "ytick.color": MUTED,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "figure.facecolor": "white",
    "axes.facecolor": "white",
})


def _dollars(ax, axis="y"):
    fmt = mticker.FuncFormatter(lambda x, _: f"${x/1e3:,.0f}K" if abs(x) < 1e6
                                else f"${x/1e6:,.1f}M")
    (ax.yaxis if axis == "y" else ax.xaxis).set_major_formatter(fmt)


def _save(fig, name):
    fig.tight_layout()
    path = f"{ASSETS}/{name}"
    fig.savefig(path, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return path


def chart_revenue_forecast(monthly: pd.DataFrame, forecast: pd.DataFrame,
                           mape: float):
    monthly = monthly.copy()
    monthly["activity_month"] = pd.to_datetime(monthly["activity_month"])
    forecast = forecast.copy()
    forecast["month"] = pd.to_datetime(forecast["month"])

    fig, ax = plt.subplots(figsize=(9, 4.2))
    ax.plot(monthly["activity_month"], monthly["revenue"], color=ACCENT,
            lw=2.2, label="Actual bookings")
    ax.plot(monthly["activity_month"], monthly["revenue_ma3"], color=MUTED,
            lw=1.2, ls="--", label="3-mo moving avg")
    # Forecast
    fx = forecast["month"]
    ax.plot(fx, forecast["forecast_revenue"], color=COPPER, lw=2.2,
            marker="o", ms=4, label="Forecast (next quarter)")
    ax.fill_between(fx, forecast["lower"], forecast["upper"], color=COPPER,
                    alpha=0.15, label=f"±{mape:.0%} backtest band")
    _dollars(ax)
    ax.set_title("Monthly bookings with backtested next-quarter forecast",
                 fontsize=13, fontweight="bold", loc="left")
    ax.grid(axis="y", color=GRID, lw=0.8)
    ax.legend(frameon=False, fontsize=9, ncol=2)
    return _save(fig, "01_revenue_forecast.png")


def chart_funnel(funnel: pd.DataFrame):
    order = ["Prospecting", "Engaging", "Won", "Lost"]
    f = funnel.set_index("deal_stage").reindex(order)
    colors = [ACCENT_LT, ACCENT, "#2E7D5B", "#B0453A"]
    fig, ax = plt.subplots(figsize=(8, 4))
    bars = ax.barh(f.index[::-1], f["opportunities"][::-1],
                   color=colors[::-1], edgecolor="white")
    for b, v in zip(bars, f["opportunities"][::-1]):
        ax.text(b.get_width() + max(f["opportunities"]) * 0.01,
                b.get_y() + b.get_height() / 2, f"{int(v):,}",
                va="center", fontsize=10, color=INK)
    ax.set_title("Opportunity funnel by deal stage", fontsize=13,
                 fontweight="bold", loc="left")
    ax.set_xlabel("Opportunities")
    ax.grid(axis="x", color=GRID, lw=0.8)
    return _save(fig, "02_pipeline_funnel.png")


def chart_segment(seg_kpi: pd.DataFrame):
    s = seg_kpi.sort_values("win_rate", ascending=True)
    fig, ax = plt.subplots(figsize=(8.5, 4.6))
    bars = ax.barh(s["sector"], s["win_rate"] * 100, color=ACCENT,
                   edgecolor="white")
    avg = (seg_kpi["won"].sum() / seg_kpi["opportunities"].sum()) * 100
    ax.axvline(avg, color=COPPER, ls="--", lw=1.4)
    ax.text(avg, len(s) - 0.4, f" avg {avg:.0f}%", color=COPPER, fontsize=9)
    for b, v in zip(bars, s["win_rate"] * 100):
        ax.text(b.get_width() - 2, b.get_y() + b.get_height() / 2,
                f"{v:.0f}%", va="center", ha="right", color="white",
                fontsize=9, fontweight="bold")
    ax.set_title("Win rate by sector (vs. company average)", fontsize=13,
                 fontweight="bold", loc="left")
    ax.xaxis.set_major_formatter(mticker.PercentFormatter())
    ax.grid(axis="x", color=GRID, lw=0.8)
    return _save(fig, "03_segment_winrate.png")


def chart_agent_leaderboard(agent_kpi: pd.DataFrame, top: int = 12):
    a = agent_kpi.nlargest(top, "revenue").sort_values("revenue")
    fig, ax = plt.subplots(figsize=(8.5, 5))
    ax.barh(a["sales_agent"], a["revenue"], color=ACCENT, edgecolor="white")
    _dollars(ax, axis="x")
    ax.set_title(f"Top {top} agents by closed-won revenue", fontsize=13,
                 fontweight="bold", loc="left")
    ax.grid(axis="x", color=GRID, lw=0.8)
    return _save(fig, "04_agent_leaderboard.png")


def chart_segments_scatter(seg: pd.DataFrame):
    tiers = ["Strategic", "Growth", "Maintain", "At-Risk", "Dormant", "Marginal"]
    palette = {"Strategic": "#0E7C82", "Growth": "#2E7D5B", "Maintain": "#B7791F",
               "At-Risk": "#B5632A", "Dormant": "#B0453A", "Marginal": "#8494A7"}
    fig, ax = plt.subplots(figsize=(8.5, 5))
    for tier in tiers:
        d = seg[seg["tier"] == tier]
        if d.empty:
            continue
        ax.scatter(d["frequency"], d["monetary"], s=40 + d["rfm_score"] * 6,
                   c=palette.get(tier, MUTED), alpha=0.8, label=tier,
                   edgecolor="white", linewidth=0.6)
    ax.set_xlabel("Opportunity frequency")
    ax.set_ylabel("Total won revenue")
    _dollars(ax)
    ax.set_title("Account segments (RFM + K-means)", fontsize=13,
                 fontweight="bold", loc="left")
    ax.grid(color=GRID, lw=0.8)
    ax.legend(frameon=False, fontsize=9, title="Tier", title_fontsize=9)
    return _save(fig, "05_account_segments.png")


def chart_drivers(drivers: pd.DataFrame, top: int = 10):
    d = drivers.head(top).iloc[::-1]
    labels = (d["feature"].str.replace("cat__", "", regex=False)
              .str.replace("num__", "", regex=False)
              .str.replace("_", " "))
    colors = [ACCENT if c > 0 else COPPER for c in d["coef"]]
    fig, ax = plt.subplots(figsize=(8.5, 5))
    ax.barh(labels, d["coef"], color=colors, edgecolor="white")
    ax.axvline(0, color=INK, lw=0.8)
    ax.set_title("Win-rate drivers (logistic coefficients)", fontsize=13,
                 fontweight="bold", loc="left")
    ax.text(0.99, -0.14, "teal = raises win odds   ·   copper = lowers",
            transform=ax.transAxes, ha="right", fontsize=8.5, color=MUTED)
    ax.grid(axis="x", color=GRID, lw=0.8)
    return _save(fig, "06_win_drivers.png")
