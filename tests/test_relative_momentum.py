import numpy as np
import pandas as pd
import pytest

from market_timing_quant.portfolio import rotation_backtest
from market_timing_quant.signals import relative_momentum_decision, relative_momentum_target_next_open


def test_relative_momentum_selects_stronger_positive_or_cash():
    spy = pd.Series([100.0] * 126 + [110.0, 90.0])
    qqq = pd.Series([100.0] * 126 + [120.0, 80.0])
    decision = relative_momentum_decision(spy, qqq, 126)
    assert decision.iloc[126].to_dict() == {"SPY": 0.0, "QQQ": 1.0}
    assert decision.iloc[127].sum() == 0.0


def test_exact_positive_tie_uses_deterministic_spy_rule():
    spy = pd.Series([100.0] * 126 + [110.0])
    qqq = spy.copy()
    assert relative_momentum_decision(spy, qqq, 126).iloc[-1].to_dict() == {"SPY": 1.0, "QQQ": 0.0}


def test_relative_signal_never_uses_future_close():
    index = pd.bdate_range("2022-01-03", periods=300)
    spy = pd.Series(np.arange(1.0, 301.0), index=index)
    qqq = pd.Series(np.arange(1.0, 301.0) * 1.1, index=index)
    target = relative_momentum_target_next_open(spy, qqq, "monthly", 126)
    changed = qqq.copy(); changed.iloc[-1] = 1e9
    other = relative_momentum_target_next_open(spy, changed, "monthly", 126)
    pd.testing.assert_frame_equal(target.iloc[:-1], other.iloc[:-1])


def test_rotation_charges_two_legs_and_immediate_tax():
    index = pd.DatetimeIndex(["2024-01-02", "2024-01-03"])
    prices = {
        "SPY": pd.DataFrame({"open": [100.0, 120.0], "adjusted_close": [100.0, 120.0]}, index=index),
        "QQQ": pd.DataFrame({"open": [100.0, 100.0], "adjusted_close": [100.0, 100.0]}, index=index),
    }
    targets = pd.DataFrame({"SPY": [1.0, 0.0], "QQQ": [0.0, 1.0]}, index=index)
    ledger, _, trades, taxes = rotation_backtest(prices, targets, initial_capital=1000,
                                                  commission_bps=0, slippage_bps=0, tax_rate=.20315)
    assert trades.side.tolist() == ["BUY", "SELL", "BUY"]
    assert taxes.tax_paid.iloc[0] == pytest.approx(40.63)
    assert ledger.equity.iloc[-1] == pytest.approx(1159.37)

