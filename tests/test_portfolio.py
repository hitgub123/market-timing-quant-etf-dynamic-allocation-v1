import pandas as pd
import pytest

from market_timing_quant.portfolio import buy_and_hold, validate_weights


def test_weight_sum_cannot_exceed_one():
    validate_weights(pd.DataFrame({"QQQ": [0.6], "QLD": [0.4]}))
    with pytest.raises(ValueError, match="exceeds"):
        validate_weights(pd.DataFrame({"QQQ": [0.6], "QLD": [0.4000001]}))


def test_buy_and_hold_cost_and_cash_are_exact():
    prices = pd.DataFrame({"open": [100.0, 100.0], "adjusted_close": [100.0, 110.0]}, index=pd.date_range("2024-01-01", periods=2))
    ledger, _, trades = buy_and_hold(prices, initial_capital=1000, commission_bps=0, slippage_bps=5)
    assert trades.transaction_cost.iloc[0] == pytest.approx(trades.notional.iloc[0] * 0.0005)
    assert ledger.cash.min() >= 0
    reconstructed = ledger.shares.iloc[-1] * prices.adjusted_close.iloc[-1] + ledger.cash.iloc[-1]
    assert ledger.equity.iloc[-1] == pytest.approx(reconstructed)


def test_turnover_is_normalized_by_contemporaneous_equity():
    from market_timing_quant.metrics import performance_metrics
    index = pd.date_range("2020-01-01", "2021-01-01", periods=3)
    ledger = pd.DataFrame({"equity": [1000., 2000., 2000.], "daily_return": [0., 1., 0.]}, index=index)
    trades = pd.DataFrame({"date": [index[0], index[1]], "side": ["BUY", "SELL"],
                           "notional": [1000., 2000.], "transaction_cost": [0., 0.],
                           "realized_gain": [0., 1000.]})
    metrics = performance_metrics(ledger, trades, 1000.)
    assert metrics["annual_turnover"] == pytest.approx(1.0, rel=.01)
    assert metrics["gross_traded_notional"] == 3000.0
