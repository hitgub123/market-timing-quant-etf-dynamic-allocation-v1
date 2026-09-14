import numpy as np
import pandas as pd
import pytest

from experiments.phase1_static_frontier import candidate_allocations, mark_pareto
from market_timing_quant.portfolio import rebalance_schedule, static_allocation_backtest


def _prices(index, first, second):
    return pd.DataFrame({"open": [first, second], "adjusted_close": [first, second]}, index=index)


def test_frozen_candidate_grid_has_exact_size_and_steps():
    candidates = candidate_allocations()
    assert len(candidates) == 8 * 21 + 5 * 66
    pairs = [x for x in candidates if x["kind"] == "pair"]
    triples = [x for x in candidates if x["kind"] == "triple"]
    assert all(np.isclose(sum(x["weights"].values()), 1.0) for x in candidates)
    assert {round(value, 10) for x in pairs for value in x["weights"].values()} == {i / 20 for i in range(21)}
    assert {round(value, 10) for x in triples for value in x["weights"].values()} == {i / 10 for i in range(11)}


def test_rebalance_is_first_trading_day_of_month_or_quarter():
    index = pd.DatetimeIndex(["2024-01-02", "2024-01-03", "2024-02-01", "2024-03-01", "2024-04-01"])
    assert rebalance_schedule(index, "monthly").tolist() == [True, False, True, True, True]
    assert rebalance_schedule(index, "quarterly").tolist() == [True, False, False, False, True]


def test_static_ledger_charges_costs_and_realized_tax_without_negative_cash():
    index = pd.DatetimeIndex(["2024-01-02", "2024-02-01"])
    prices = {"A": _prices(index, 100, 200), "B": _prices(index, 100, 100)}
    pre, _, pre_trades, _ = static_allocation_backtest(
        prices, {"A": .5, "B": .5}, initial_capital=1000,
        commission_bps=0, slippage_bps=5, frequency="monthly", tax_rate=None,
    )
    after, _, after_trades, taxes = static_allocation_backtest(
        prices, {"A": .5, "B": .5}, initial_capital=1000,
        commission_bps=0, slippage_bps=5, frequency="monthly", tax_rate=.20315,
    )
    assert pre_trades.transaction_cost.sum() > 0
    assert taxes.tax_paid.sum() > 0
    assert after.equity.iloc[-1] < pre.equity.iloc[-1]
    assert (after.cash >= -1e-10).all()


def test_pareto_marks_only_improving_cagr_as_risk_increases():
    frame = pd.DataFrame({"max_drawdown": [-.1, -.2, -.3], "cagr": [.05, .04, .08]})
    assert mark_pareto(frame).tolist() == [True, False, True]

