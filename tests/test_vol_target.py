import numpy as np
import pandas as pd
import pytest

from experiments.phase6_vol_target import TARGET_VOLS, VOL_WINDOWS, parameter_grid
from market_timing_quant.portfolio import continuous_weight_backtest
from market_timing_quant.signals import realized_volatility, volatility_target_decision, volatility_target_next_open


def test_volatility_grid_is_exactly_frozen():
    assert VOL_WINDOWS == (20, 40, 60)
    assert TARGET_VOLS == (.10, .15, .20, .25, .30)
    assert len(parameter_grid()) == 15


def test_realized_volatility_uses_daily_returns_and_sqrt_252():
    returns = np.array([.01, -.01] * 11)
    price = pd.Series(100 * np.cumprod(1 + returns))
    actual = realized_volatility(price, 20).iloc[-1]
    expected = pd.Series(returns[1:]).iloc[-20:].std(ddof=1) * np.sqrt(252)
    assert actual == pytest.approx(expected)


def test_target_weight_is_capped_at_one_and_unready_is_cash():
    price = pd.Series(np.linspace(100, 101, 30))
    weight = volatility_target_decision(price, 20, .30)
    assert weight.iloc[:20].eq(0).all()
    assert weight.iloc[-1] == 1.0


def test_future_close_cannot_change_prior_volatility_targets():
    index = pd.bdate_range("2022-01-03", periods=100)
    price = pd.Series(100 * np.cumprod(1 + .01 * np.sin(np.arange(100))), index=index)
    target = volatility_target_next_open(price, "monthly", 20, .15)
    changed = price.copy(); changed.iloc[-1] *= 2
    other = volatility_target_next_open(changed, "monthly", 20, .15)
    pd.testing.assert_series_equal(target.iloc[:-1], other.iloc[:-1])


def test_continuous_ledger_trades_only_on_schedule():
    index = pd.DatetimeIndex(["2024-01-02", "2024-01-03", "2024-02-01"])
    prices = pd.DataFrame({"open": [100., 110., 120.], "adjusted_close": [100., 110., 120.]}, index=index)
    target = pd.Series([.5, .5, .5], index=index)
    schedule = pd.Series([True, False, True], index=index)
    ledger, _, trades, _ = continuous_weight_backtest(prices, target, schedule, initial_capital=1000,
                                                        commission_bps=0, slippage_bps=0, tax_rate=None)
    assert ledger.trade_notional.iloc[1] == 0
    assert trades.date.tolist() == [index[0], index[2]]
    assert (ledger.risk_weight <= 1 + 1e-12).all()

