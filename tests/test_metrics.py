import pandas as pd
import pytest

from market_timing_quant.metrics import drawdown_series, performance_metrics


def test_drawdown_frozen_example():
    equity = pd.Series([100.0, 120.0, 60.0, 90.0], index=pd.date_range("2024-01-01", periods=4))
    assert drawdown_series(equity, 100.0).min() == pytest.approx(-0.5)


def test_initial_capital_peak_controls_drawdown_start_and_recovery():
    index = pd.date_range("2024-01-02", periods=4)
    equity = pd.Series([90.0, 80.0, 100.0, 110.0], index=index)
    ledger = pd.DataFrame({"equity": equity, "daily_return": equity.pct_change().fillna(-.1)})
    trades = pd.DataFrame(columns=["date", "side", "notional", "transaction_cost"])
    metrics = performance_metrics(ledger, trades, 100.0)
    assert metrics["max_drawdown"] == pytest.approx(-.2)
    assert metrics["max_drawdown_start"] == "2024-01-01"
    assert metrics["max_drawdown_trough"] == "2024-01-03"
    assert metrics["recovery_date"] == "2024-01-04"
    assert metrics["recovery_trading_days"] == 1


def test_cagr_and_calmar_match_hand_calculation():
    index = pd.DatetimeIndex(["2020-01-01", "2020-07-01", "2020-12-31"])
    equity = pd.Series([120.0, 60.0, 121.0], index=index)
    ledger = pd.DataFrame({"equity": equity, "daily_return": equity.pct_change().fillna(.2)})
    trades = pd.DataFrame(columns=["date", "side", "notional", "transaction_cost"])
    metrics = performance_metrics(ledger, trades, 100.0)
    expected_cagr = (121.0 / 100.0) ** (365.25 / 365.0) - 1.0
    assert metrics["cagr"] == pytest.approx(expected_cagr)
    assert metrics["max_drawdown"] == pytest.approx(-.5)
    assert metrics["calmar"] == pytest.approx(expected_cagr / .5)
