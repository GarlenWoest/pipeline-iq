"""
run_all.py
==========
One command to reproduce the whole project:

    python src/run_all.py

Steps:
  1. (re)generate synthetic data if the raw CSVs are missing
  2. build the DuckDB warehouse (staging -> marts)
  3. run segmentation, forecasting, and the win-driver model
  4. render all chart assets
  5. export Power BI-ready star-schema CSVs
  6. write reports/metrics.json (single source of truth for the README numbers)
"""
from __future__ import annotations

import json
import os

import pandas as pd

import drivers as drivers_mod
import forecast as forecast_mod
import segmentation as seg_mod
import viz
from etl import build_warehouse, table


def ensure_data():
    if not os.path.exists("data/raw/sales_pipeline.csv"):
        print("[run_all] raw data missing -> generating synthetic dataset")
        import generate_data
        generate_data.main()


def export_powerbi(con):
    """Flat star-schema exports Power BI can import with zero transformation."""
    os.makedirs("data/exports/powerbi", exist_ok=True)
    table(con, "fct_pipeline").to_csv(
        "data/exports/powerbi/fct_pipeline.csv", index=False)
    table(con, "dim_account").to_csv(
        "data/exports/powerbi/dim_account.csv", index=False)
    table(con, "kpi_monthly").to_csv(
        "data/exports/powerbi/kpi_monthly.csv", index=False)
    print("[run_all] exported Power BI star-schema CSVs -> data/exports/powerbi/")


def main():
    os.makedirs("data/exports", exist_ok=True)
    os.makedirs("reports", exist_ok=True)
    ensure_data()

    con = build_warehouse()

    # ---- core marts ----
    fct = table(con, "fct_pipeline")
    seg_kpi = table(con, "kpi_segment")
    agent_kpi = table(con, "kpi_agent")
    monthly = table(con, "kpi_monthly")
    funnel = table(con, "kpi_funnel")

    # ---- models ----
    seg = seg_mod.segment_accounts(con)
    seg.to_csv("data/exports/account_segments.csv", index=False)
    fc = forecast_mod.run(con)
    fc["forecast"].to_csv("data/exports/forecast_next_quarter.csv", index=False)
    dr = drivers_mod.fit_driver_model(con)
    dr["drivers"].to_csv("data/exports/win_drivers.csv", index=False)

    # ---- headline metrics ----
    closed = fct[fct["is_closed"]]
    total_rev = float(closed.loc[closed["is_won"], "close_value"].sum())
    win_rate = float(closed["is_won"].mean())
    avg_cycle = float(closed["cycle_days"].mean())
    open_deals = int(fct["is_open"].sum())

    # Revenue concentration: share from top 20% of accounts by won revenue.
    acct_rev = (closed[closed["is_won"]].groupby("account")["close_value"]
                .sum().sort_values(ascending=False))
    top20 = acct_rev.head(max(1, int(len(acct_rev) * 0.2))).sum()
    concentration = float(top20 / acct_rev.sum()) if acct_rev.sum() else 0.0

    best_sector = seg_kpi.iloc[seg_kpi["win_rate"].idxmax()]
    worst_sector = seg_kpi.iloc[seg_kpi["win_rate"].idxmin()]

    metrics = {
        "opportunities_total": int(len(fct)),
        "closed_deals": int(len(closed)),
        "open_deals": open_deals,
        "accounts": int(fct["account"].nunique()),
        "agents": int(fct["sales_agent"].nunique()),
        "total_won_revenue": round(total_rev),
        "overall_win_rate": round(win_rate, 4),
        "avg_cycle_days": round(avg_cycle, 1),
        "revenue_concentration_top20pct": round(concentration, 4),
        "best_sector": {"sector": best_sector["sector"],
                        "win_rate": round(float(best_sector["win_rate"]), 4)},
        "worst_sector": {"sector": worst_sector["sector"],
                         "win_rate": round(float(worst_sector["win_rate"]), 4)},
        "forecast_backtest_mape": round(fc["backtest_mape"], 4),
        "next_quarter_forecast": round(fc["next_quarter_statistical"]),
        "weighted_open_pipeline": round(fc["weighted_pipeline_open"]),
        "driver_model_auc": round(dr["auc"], 3),
        "segments": seg["tier"].value_counts().to_dict(),
    }
    with open("reports/metrics.json", "w") as fh:
        json.dump(metrics, fh, indent=2)

    # ---- charts ----
    viz.chart_revenue_forecast(monthly, fc["forecast"], fc["backtest_mape"])
    viz.chart_funnel(funnel)
    viz.chart_segment(seg_kpi)
    viz.chart_agent_leaderboard(agent_kpi)
    viz.chart_segments_scatter(seg)
    viz.chart_drivers(dr["drivers"])

    export_powerbi(con)

    print("\n===== PIPELINE IQ — HEADLINE METRICS =====")
    print(json.dumps(metrics, indent=2))
    print("\n[run_all] done. Charts -> assets/  Metrics -> reports/metrics.json")


if __name__ == "__main__":
    main()
