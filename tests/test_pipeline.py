import numpy as np
import pandas as pd
import pytest

import drivers
import forecast
import segmentation
from etl import table


# ---- warehouse / SQL layer --------------------------------------------------
def test_fact_table_keeps_every_opportunity(warehouse):
    raw = warehouse.execute("SELECT COUNT(*) FROM raw_sales_pipeline").fetchone()[0]
    fct = warehouse.execute("SELECT COUNT(*) FROM fct_pipeline").fetchone()[0]
    assert fct == raw > 0


def test_deal_status_flags_are_consistent(warehouse):
    fct = table(warehouse, "fct_pipeline")
    assert not (fct["is_open"] & fct["is_closed"]).any()
    assert (fct["is_open"] | fct["is_closed"]).all()
    assert not (fct["is_won"] & ~fct["is_closed"]).any()


def test_won_deals_have_positive_value(warehouse):
    fct = table(warehouse, "fct_pipeline")
    assert (fct.loc[fct["is_won"], "close_value"] > 0).all()


def test_segment_win_rates_are_probabilities(warehouse):
    seg = table(warehouse, "kpi_segment")
    assert seg["win_rate"].between(0, 1).all()


# ---- forecasting ------------------------------------------------------------
def test_mape_known_values():
    actual = np.array([100.0, 200.0, 0.0])
    pred = np.array([110.0, 180.0, 50.0])
    # zero actuals are excluded: mean(|10/100|, |20/200|) = 0.10
    assert forecast._mape(actual, pred) == pytest.approx(0.10)


def test_mape_all_zero_actuals_is_nan():
    assert np.isnan(forecast._mape(np.zeros(3), np.ones(3)))


def test_naive_forecast_is_trailing_three_month_mean():
    s = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0])
    np.testing.assert_allclose(forecast._f_naive(s, 3), [4.0, 4.0, 4.0])


def test_trend_forecast_extends_line_and_never_negative():
    up = pd.Series(np.arange(12, dtype=float))
    np.testing.assert_allclose(forecast._f_trend(up, 3), [12.0, 13.0, 14.0])
    down = pd.Series(np.arange(12, 0, -1, dtype=float))
    assert (forecast._f_trend(down, 24) >= 0).all()


def test_forecast_run_outputs(warehouse):
    fc = forecast.run(warehouse)
    assert fc["next_quarter_statistical"] >= 0
    assert fc["weighted_pipeline_open"] >= 0
    assert 0 <= fc["backtest_mape"] < 1


# ---- segmentation & win drivers --------------------------------------------
def test_every_account_gets_one_tier(warehouse):
    seg = segmentation.segment_accounts(warehouse)
    assert seg["account"].is_unique
    assert seg["tier"].notna().all()
    assert seg["rfm_score"].is_monotonic_decreasing


def test_driver_model_beats_random(warehouse):
    dr = drivers.fit_driver_model(warehouse)
    assert 0.5 < dr["auc"] <= 1.0
    assert len(dr["drivers"]) > 0
