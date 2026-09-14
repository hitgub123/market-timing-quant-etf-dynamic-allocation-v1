import pandas as pd
import pytest

from market_timing_quant.metrics import completed_holding_periods, performance_metrics, terminal_liquidation


def test_holding_period_uses_only_completed_position_episodes():
    index = pd.date_range("2024-01-01", periods=5)
    ledger = pd.DataFrame({"equity": 1000., "cash": [1000., 0., 0., 1000., 0.],
                           "shares": [0., 10., 10., 0., 5.], "daily_return": 0.}, index=index)
    episodes = completed_holding_periods(ledger)
    assert len(episodes) == 1
    assert episodes.iloc[0].trading_days == 2
    assert episodes.iloc[0].calendar_days == 2
    trades = pd.DataFrame({"date": [index[1], index[3], index[4]], "asset": "RISK",
                           "side": ["BUY", "SELL", "BUY"], "shares": [10., 10., 5.],
                           "notional": [1000., 1000., 1000.], "transaction_cost": 0.,
                           "realized_gain": 0.})
    metrics = performance_metrics(ledger, trades, 1000.)
    assert metrics["average_holding_period_days"] == 2
    assert metrics["mean_holding_period_days"] == 2
    assert metrics["median_holding_period_days"] == 2
    assert metrics["max_holding_period_days"] == 2
    assert metrics["mean_holding_trading_days"] == 2
    assert metrics["median_holding_trading_days"] == 2
    assert metrics["max_holding_trading_days"] == 2


def test_terminal_liquidation_taxes_unrealized_buy_and_hold_gain():
    index = pd.date_range("2024-01-01", periods=2)
    ledger = pd.DataFrame({"equity": [1000., 2000.], "cash": 0., "shares": 10.,
                           "daily_return": [0., 1.]}, index=index)
    trades = pd.DataFrame({"date": [index[0]], "asset": ["RISK"], "side": ["BUY"],
                           "shares": [10.], "notional": [1000.], "transaction_cost": [0.],
                           "realized_gain": [0.]})
    result = terminal_liquidation(ledger, trades, tax_rate=.20315, transaction_cost_rate=0.)
    assert result["terminal_liquidation_tax"] == pytest.approx(203.15)
    assert result["terminal_liquidation_wealth"] == pytest.approx(1796.85)


def test_buy_and_hold_turnover_excludes_initial_deployment():
    index = pd.date_range("2020-01-01", "2021-01-01", periods=3)
    ledger = pd.DataFrame({"equity": [1000., 1200., 1300.], "cash": 0., "shares": 10.,
                           "daily_return": [0., .2, 1/12]}, index=index)
    trades = pd.DataFrame({"date": [index[0]], "asset": "RISK", "side": "BUY",
                           "shares": 10., "notional": 1000., "transaction_cost": 0.,
                           "realized_gain": 0.}, index=[0])
    metrics = performance_metrics(ledger, trades, 1000.)
    assert metrics["annual_turnover"] == 0
    assert metrics["gross_traded_notional"] == 1000
    assert metrics["number_of_trades"] == 1
    for field in (
        "average_holding_period_days", "mean_holding_period_days",
        "median_holding_period_days", "max_holding_period_days",
    ):
        assert metrics[field] is None


def test_terminal_liquidation_applies_existing_loss_pool():
    index = pd.date_range("2024-01-01", periods=3)
    ledger = pd.DataFrame({"equity": [1000., 1600., 2100.], "cash": [0., 600., 600.],
                           "shares": [10., 0., 10.], "daily_return": [0., .6, .3125]}, index=index)
    trades = pd.DataFrame({
        "date": [index[0], index[1], index[1]], "asset": ["A", "A", "B"],
        "side": ["BUY", "SELL", "BUY"], "shares": [10., 10., 10.],
        "notional": [1000., 600., 1000.], "transaction_cost": 0.,
        "realized_gain": [0., -400., 0.],
    })
    result = terminal_liquidation(ledger, trades, tax_rate=.20315, transaction_cost_rate=0.)
    assert result["terminal_loss_pool_before_liquidation"] == 400
    assert result["terminal_liquidation_tax"] == pytest.approx(20.315)
    assert result["terminal_liquidation_wealth"] == pytest.approx(2079.685)


def test_terminal_liquidation_cost_and_tax_are_diagnostic_and_non_mutating():
    index = pd.date_range("2024-01-01", periods=2)
    ledger = pd.DataFrame({"equity": [1000., 2000.], "cash": 0., "shares": 10.,
                           "daily_return": [0., 1.]}, index=index)
    trades = pd.DataFrame({"date": [index[0]], "asset": ["RISK"], "side": ["BUY"],
                           "shares": [10.], "notional": [1000.], "transaction_cost": [0.],
                           "realized_gain": [0.]})
    ledger_before, trades_before = ledger.copy(deep=True), trades.copy(deep=True)
    metrics = performance_metrics(
        ledger, trades, 1000., terminal_tax_rate=.20315, terminal_cost_rate=.01,
    )
    assert metrics["terminal_liquidation_cost"] == pytest.approx(20.)
    assert metrics["terminal_unrealized_gain_after_cost"] == pytest.approx(980.)
    assert metrics["terminal_liquidation_tax"] == pytest.approx(980. * .20315)
    assert metrics["terminal_liquidation_wealth"] == pytest.approx(2000. - 20. - 980. * .20315)
    assert metrics["after_tax_wealth_tax_paid_to_date"] == 2000.
    assert metrics["after_tax_tax_paid_to_date"] == metrics["after_tax_wealth_tax_paid_to_date"]
    pd.testing.assert_frame_equal(ledger, ledger_before)
    pd.testing.assert_frame_equal(trades, trades_before)
