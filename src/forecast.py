"""
forecast.py
===========
Forecasts next-quarter bookings and reports HONEST out-of-sample accuracy — the
feature that separates this from a chart.

Two forecasts, quoted together (as a real revenue-ops team would):

1) Statistical forecast of monthly won revenue. We compare two transparent
   methods with a rolling-origin (walk-forward) backtest and keep the winner:
       * seasonal/level baseline  -> trailing 3-month average
       * linear-trend regression  -> degree-1 fit on the recent window
   The backtest MAPE becomes the forecast's confidence band.

2) Weighted-pipeline forecast: sum of currently-open opportunities x their
   stage win-probability — the pipeline-driven "commit" number.

No heavy time-series dependency: methods are intentionally simple and robust so
the backtest is trustworthy on ~2 years of monthly data.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from etl import build_warehouse, table

HORIZON = 3      # months (one quarter)
TREND_WINDOW = 9  # months used by the trend model


def _monthly_won(con) -> pd.Series:
    m = table(con, "kpi_monthly")
    m["activity_month"] = pd.to_datetime(m["activity_month"])
    s = m.set_index("activity_month")["revenue"].asfreq("MS").fillna(0.0)
    # Drop any leading/trailing months with zero bookings (outside the active
    # selling window); the interior is mature, so no ramp/censoring trim needed.
    nz = s[s > 0].index
    return s.loc[nz.min():nz.max()] if len(nz) else s


# ----- two transparent forecasters -------------------------------------------
def _f_naive(train: pd.Series, horizon: int) -> np.ndarray:
    level = train.iloc[-3:].mean()
    return np.repeat(level, horizon)


def _f_trend(train: pd.Series, horizon: int) -> np.ndarray:
    window = train.iloc[-TREND_WINDOW:]
    x = np.arange(len(window))
    slope, intercept = np.polyfit(x, window.values, 1)
    future_x = np.arange(len(window), len(window) + horizon)
    return np.clip(slope * future_x + intercept, 0, None)


METHODS = {"naive_3m": _f_naive, "linear_trend": _f_trend}


def _mape(actual: np.ndarray, pred: np.ndarray) -> float:
    mask = actual > 0
    if not mask.any():
        return np.nan
    return float(np.mean(np.abs((actual[mask] - pred[mask]) / actual[mask])))


def backtest(series: pd.Series, horizon: int = HORIZON,
             min_train: int = 9) -> dict:
    """Walk-forward backtest of each method. Returns {method: mean MAPE}."""
    scores = {name: [] for name in METHODS}
    for cut in range(min_train, len(series) - horizon + 1):
        train, test = series.iloc[:cut], series.iloc[cut:cut + horizon]
        for name, fn in METHODS.items():
            scores[name].append(_mape(test.values, fn(train, horizon)))
    return {name: float(np.nanmean(v)) if v else np.nan
            for name, v in scores.items()}


def statistical_forecast(series: pd.Series, horizon: int = HORIZON) -> dict:
    scores = backtest(series, horizon)
    best = min(scores, key=lambda k: scores[k])
    mape = scores[best]
    future_index = pd.date_range(series.index[-1] + pd.offsets.MonthBegin(),
                                 periods=horizon, freq="MS")
    yhat = METHODS[best](series, horizon)
    band = mape if not np.isnan(mape) else 0.15
    fc = pd.DataFrame({
        "month": future_index,
        "forecast_revenue": np.round(yhat, 0),
        "lower": np.round(yhat * (1 - band), 0),
        "upper": np.round(yhat * (1 + band), 0),
    })
    return {"forecast": fc, "best_method": best, "mape": mape,
            "method_scores": scores}


def weighted_pipeline_forecast(con) -> float:
    fct = table(con, "fct_pipeline")
    return float(fct.loc[fct["is_open"], "weighted_open_value"].sum())


def run(con=None) -> dict:
    con = con or build_warehouse()
    series = _monthly_won(con)
    sf = statistical_forecast(series)
    return {
        "series": series,
        "forecast": sf["forecast"],
        "best_method": sf["best_method"],
        "backtest_mape": sf["mape"],
        "method_scores": sf["method_scores"],
        "next_quarter_statistical": float(sf["forecast"]["forecast_revenue"].sum()),
        "weighted_pipeline_open": weighted_pipeline_forecast(con),
    }


def main() -> None:
    out = run()
    out["forecast"].to_csv("data/exports/forecast_next_quarter.csv", index=False)
    print("[forecast] backtest MAPE by method:")
    for name, s in out["method_scores"].items():
        star = "  <- selected" if name == out["best_method"] else ""
        print(f"           {name:14s} {s:6.1%}{star}")
    print(f"[forecast] next-quarter statistical forecast = "
          f"${out['next_quarter_statistical']:,.0f}")
    print(f"[forecast] weighted open pipeline           = "
          f"${out['weighted_pipeline_open']:,.0f}")
    print("[forecast] wrote data/exports/forecast_next_quarter.csv")


if __name__ == "__main__":
    main()
