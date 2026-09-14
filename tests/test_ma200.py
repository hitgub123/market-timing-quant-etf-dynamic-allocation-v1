import numpy as np
import pandas as pd

from market_timing_quant.portfolio import single_asset_timed_backtest
from market_timing_quant.signals import ma_trend_decision, trend_target_next_open


def test_ma200_uses_strict_greater_than_and_requires_full_window():
    price = pd.Series([100.0] * 200 + [101.0], index=pd.bdate_range("2023-01-02", periods=201))
    decision = ma_trend_decision(price, 200)
    assert decision.iloc[:200].eq(0).all()
    assert decision.iloc[200] == 1.0


def test_ma_decision_at_t_cannot_affect_open_t():
    index = pd.bdate_range("2023-01-02", periods=205)
    price = pd.Series(np.arange(1.0, 206.0), index=index)
    targets = trend_target_next_open(price, "weekly", 200)
    changed = price.copy()
    changed.iloc[-1] = 1e9
    other = trend_target_next_open(changed, "weekly", 200)
    pd.testing.assert_series_equal(targets.iloc[:-1], other.iloc[:-1])


def test_bimonthly_changes_only_in_odd_months():
    index = pd.bdate_range("2022-01-03", "2023-02-03")
    price = pd.Series(np.arange(len(index), dtype=float) + 1, index=index)
    target = trend_target_next_open(price, "bimonthly", 2)
    changes = target.ne(target.shift()).fillna(False)
    assert set(index[changes].month) <= {1, 3, 5, 7, 9, 11}


def test_binary_ledger_realizes_gain_and_tax_on_exit():
    index = pd.DatetimeIndex(["2024-01-02", "2024-01-03", "2024-01-04"])
    prices = pd.DataFrame({"open": [100.0, 120.0, 120.0], "adjusted_close": [100.0, 120.0, 120.0]}, index=index)
    targets = pd.Series([1.0, 0.0, 0.0], index=index)
    ledger, _, trades, taxes = single_asset_timed_backtest(
        prices, targets, initial_capital=1000, commission_bps=0, slippage_bps=0, tax_rate=.20315
    )
    assert trades.side.tolist() == ["BUY", "SELL"]
    assert taxes.realized_gain.iloc[0] == 200.0
    assert taxes.tax_paid.iloc[0] == 40.63
    assert ledger.equity.iloc[-1] == 1159.37

