import numpy as np
import pandas as pd
import pytest

from experiments.phase1_static_frontier import FREQUENCIES, PAIRS, TRIPLES, candidate_allocations, mark_pareto
from market_timing_quant.metrics import performance_metrics
from market_timing_quant.portfolio import buy_and_hold, rebalance_schedule, static_allocation_backtest


def _prices(index, first, second):
    return pd.DataFrame({"open": [first, second], "adjusted_close": [first, second]}, index=index)


def test_frozen_candidate_grid_has_exact_size_and_steps():
    candidates = candidate_allocations()
    assert len(PAIRS) == 8
    assert len(TRIPLES) == 5
    assert len(candidates) == 8 * 21 + 5 * 66 == 498
    pairs = [x for x in candidates if x["kind"] == "pair"]
    triples = [x for x in candidates if x["kind"] == "triple"]
    assert len(pairs) == 168
    assert len(triples) == 330
    assert len(FREQUENCIES) * len(candidates) == 996
    assert len(FREQUENCIES) * len(candidates) * 2 == 1992
    for candidate in candidates:
        weights = np.asarray(list(candidate["weights"].values()), dtype=float)
        assert np.isfinite(weights).all()
        assert (weights >= 0).all()
        assert weights.sum() == pytest.approx(1.0, abs=1e-12)
    assert {round(value, 10) for x in pairs for value in x["weights"].values()} == {i / 20 for i in range(21)}
    assert {round(value, 10) for x in triples for value in x["weights"].values()} == {i / 10 for i in range(11)}
    assert all(sum(1 for x in triples if x["assets"] == assets) == 66 for assets in TRIPLES)


def test_rebalance_is_first_trading_day_of_month_or_quarter():
    # Jan 1 is a holiday, Jan 2 is the first available session; Jan 31 and
    # Feb 29 ensure this is not a last-day-of-period schedule.
    index = pd.DatetimeIndex([
        "2024-01-02", "2024-01-31", "2024-02-01", "2024-02-29",
        "2024-04-01", "2024-04-30", "2024-07-01", "2024-07-31",
    ])
    assert rebalance_schedule(index, "monthly").tolist() == [True, False, True, False, True, False, True, False]
    assert rebalance_schedule(index, "quarterly").tolist() == [True, False, False, False, True, False, True, False]


def test_static_ledger_matches_hand_calculation_for_50_50_rebalance():
    index = pd.DatetimeIndex(["2024-01-02", "2024-02-01"])
    prices = {
        "A": _prices(index, 100, 120),
        "B": _prices(index, 100, 100),
    }
    ledger, positions, trades, taxes = static_allocation_backtest(
        prices, {"A": .5, "B": .5}, initial_capital=1000,
        commission_bps=0, slippage_bps=5, frequency="monthly", tax_rate=None,
    )
    rate = .0005
    first_equity_after_cost = 1000 / (1 + rate)
    first_notional_each = first_equity_after_cost / 2
    first_shares_each = first_notional_each / 100
    first_cost = first_equity_after_cost * rate
    before_a = first_shares_each * 120
    before_b = first_shares_each * 100
    pretrade = before_a + before_b
    second_cost = (before_a - before_b) * rate
    second_equity = pretrade - second_cost
    expected_a_sell = before_a - second_equity / 2
    expected_b_buy = second_equity / 2 - before_b
    second_trades = trades.loc[trades.date.eq(index[1])].set_index("asset")

    assert trades.loc[trades.date.eq(index[0]), "transaction_cost"].sum() == pytest.approx(first_cost)
    assert ledger.loc[index[1], "pretrade_equity"] == pytest.approx(pretrade)
    assert ledger.loc[index[1], "trade_notional"] == pytest.approx(expected_a_sell + expected_b_buy)
    assert ledger.loc[index[1], "transaction_cost"] == pytest.approx(second_cost)
    assert second_trades.loc["A", "side"] == "SELL"
    assert second_trades.loc["B", "side"] == "BUY"
    assert second_trades.loc["A", "notional"] == pytest.approx(expected_a_sell)
    assert second_trades.loc["B", "notional"] == pytest.approx(expected_b_buy)
    assert positions.loc[positions.date.eq(index[1]) & positions.asset.eq("A"), "shares"].iloc[0] == pytest.approx(second_equity / 2 / 120)
    assert positions.loc[positions.date.eq(index[1]) & positions.asset.eq("B"), "shares"].iloc[0] == pytest.approx(second_equity / 2 / 100)
    assert ledger.loc[index[1], "cash"] == pytest.approx(0.0)
    assert ledger.loc[index[1], "equity"] == pytest.approx(second_equity)
    assert taxes.empty


def test_static_cash_allocation_hits_requested_post_cost_risk_weight():
    index = pd.DatetimeIndex(["2024-01-02", "2024-02-01"])
    prices = {"QQQ": _prices(index, 100, 100)}
    ledger, _, trades, taxes = static_allocation_backtest(
        prices, {"QQQ": .5}, initial_capital=1000,
        commission_bps=0, slippage_bps=5, frequency="monthly", tax_rate=None,
    )
    assert ledger.loc[index[0], "QQQ_weight"] == pytest.approx(.5)
    expected_notional = 500 / (1 + .5 * .0005)
    assert ledger.loc[index[0], "cash"] == pytest.approx(expected_notional)
    assert ledger.loc[index[0], "cash"] >= 0
    assert (ledger.cash >= -1e-10).all()
    assert trades.loc[0, "notional"] == pytest.approx(expected_notional)
    assert taxes.empty


def test_pure_single_asset_endpoint_matches_phase0_buy_and_hold():
    index = pd.DatetimeIndex(["2024-01-02", "2024-01-31", "2024-02-01", "2024-02-29"])
    prices = pd.DataFrame({"open": [100., 120., 90., 130.], "adjusted_close": [100., 120., 90., 130.]}, index=index)
    phase0_ledger, _, phase0_trades = buy_and_hold(
        prices, initial_capital=1000, commission_bps=0, slippage_bps=5,
    )
    phase1_ledger, _, phase1_trades, _ = static_allocation_backtest(
        {"SPY": prices}, {"SPY": 1.0}, initial_capital=1000,
        commission_bps=0, slippage_bps=5, frequency="monthly", tax_rate=None,
    )
    assert np.allclose(phase1_ledger.equity.to_numpy(), phase0_ledger.equity.to_numpy())
    phase0_metrics = performance_metrics(phase0_ledger, phase0_trades, 1000)
    phase1_metrics = performance_metrics(phase1_ledger, phase1_trades, 1000)
    for field in ("ending_value", "cagr", "max_drawdown", "calmar"):
        assert phase1_metrics[field] == pytest.approx(phase0_metrics[field])


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
    assert after.tax_paid.sum() == pytest.approx(taxes.tax_paid.sum())
    assert (after.equity <= pre.equity + 1e-9).all()


def test_pareto_marks_only_improving_cagr_as_risk_increases():
    frame = pd.DataFrame({"max_drawdown": [-.1, -.2, -.3], "cagr": [.05, .04, .08]})
    assert mark_pareto(frame).tolist() == [True, False, True]


def test_pareto_same_risk_higher_cagr_is_strictly_dominant():
    frame = pd.DataFrame({"max_drawdown": [-.2, -.2], "cagr": [.05, .06]})
    assert mark_pareto(frame).tolist() == [False, True]


def test_pareto_same_cagr_lower_risk_is_strictly_dominant():
    frame = pd.DataFrame({"max_drawdown": [-.2, -.1], "cagr": [.05, .05]})
    assert mark_pareto(frame).tolist() == [False, True]


def test_pareto_equal_economic_points_all_remain_nondominated():
    frame = pd.DataFrame({"max_drawdown": [-.2, -.2], "cagr": [.05, .05]})
    assert mark_pareto(frame).tolist() == [True, True]


def test_pareto_tolerance_equality_is_not_treated_as_dominance():
    frame = pd.DataFrame({"max_drawdown": [-.2, -.2 - 5e-13], "cagr": [.05, .05 + 5e-13]})
    assert mark_pareto(frame).tolist() == [True, True]
