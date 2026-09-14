from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from market_timing_quant.metrics import performance_metrics
from market_timing_quant.portfolio import single_asset_timed_backtest
from market_timing_quant.signals import (
    ma_trend_decision,
    rebalance_mask,
    scheduled_target_next_open,
    trend_target_next_open,
)

from experiments.phase2_ma200 import _alignment_rows, _warmup_rows


ROOT = Path(__file__).resolve().parents[1]
CANONICAL_RUN = ROOT / "reports/runs/20260914_phase2_audit_final"
RATE = 5 / 10_000


def _prices(index: pd.DatetimeIndex, opens: list[float], closes: list[float] | None = None) -> pd.DataFrame:
    close = closes if closes is not None else opens
    return pd.DataFrame({"open": opens, "adjusted_close": close}, index=index)


def test_phase2_exact_ma200_window_and_strict_crossing():
    index = pd.bdate_range("2023-01-02", periods=201)
    price = pd.Series([100.0] * 200 + [101.0], index=index)
    decision = ma_trend_decision(price, lookback=200)
    assert decision.iloc[:200].eq(0.0).all()
    assert decision.iloc[200] == 1.0
    # The 200-session mean at the final date includes the final close only;
    # no future row is available to the calculation.
    assert price.iloc[200] > price.iloc[1:201].mean() - 1e-12


def test_phase2_ma200_future_mutation_cannot_change_prior_signals():
    index = pd.bdate_range("2020-01-02", periods=260)
    price = pd.Series(np.linspace(100.0, 130.0, len(index)), index=index)
    cutoff = index[220]
    changed = price.copy()
    changed.loc[index > cutoff] = changed.loc[index > cutoff] * 9.0
    before = ma_trend_decision(price, 200)
    after = ma_trend_decision(changed, 200)
    pd.testing.assert_series_equal(before.loc[:cutoff], after.loc[:cutoff])


def test_phase2_close_t_signal_executes_at_next_open_and_uses_gap_price():
    # The second-last session is Friday, followed by Monday. The close on
    # Friday crosses MA200; weekly scheduling makes Monday the next eligible
    # execution session.
    index = pd.bdate_range(end="2023-01-09", periods=201)
    closes = [100.0] * 199 + [101.0, 101.0]
    opens = [100.0] * 199 + [77.0, 150.0]
    prices = _prices(index, opens, closes)
    targets = trend_target_next_open(prices.adjusted_close, "weekly", 200)
    friday, monday = index[-2], index[-1]
    assert targets.loc[friday] == 0.0
    assert targets.loc[monday] == 1.0
    ledger, _, trades, _ = single_asset_timed_backtest(
        prices,
        targets,
        initial_capital=1_000.0,
        commission_bps=0.0,
        slippage_bps=5.0,
        tax_rate=None,
    )
    assert trades.side.tolist() == ["BUY"]
    assert pd.Timestamp(trades.date.iloc[0]) == monday
    assert trades.price.iloc[0] == pytest.approx(150.0)
    assert trades.transaction_cost.iloc[0] == pytest.approx(trades.notional.iloc[0] * RATE)
    assert ledger.loc[friday, "shares"] == 0.0
    assert ledger.loc[monday, "shares"] > 0.0
    assert ledger.cash.min() >= -1e-9


def test_phase2_rebalance_schedules_use_first_available_session_not_period_end():
    # Missing first calendar days model holidays/weekends.
    weekly_index = pd.DatetimeIndex(["2024-01-02", "2024-01-03", "2024-01-08", "2024-01-09"])
    monthly_index = pd.DatetimeIndex(["2024-01-02", "2024-01-31", "2024-02-02", "2024-02-29", "2024-03-04"])
    bimonthly_index = pd.DatetimeIndex(["2024-01-03", "2024-01-31", "2024-02-01", "2024-03-04", "2024-03-29"])
    quarterly_index = pd.DatetimeIndex(["2024-01-02", "2024-03-28", "2024-04-03", "2024-06-28", "2024-07-02"])
    assert rebalance_mask(weekly_index, "weekly").loc["2024-01-02"]
    assert not rebalance_mask(weekly_index, "weekly").loc["2024-01-03"]
    assert rebalance_mask(monthly_index, "monthly").loc[["2024-01-02", "2024-02-02", "2024-03-04"]].all()
    assert not rebalance_mask(monthly_index, "monthly").loc[["2024-01-31", "2024-02-29"]].any()
    assert rebalance_mask(bimonthly_index, "bimonthly").loc[["2024-01-03", "2024-03-04"]].all()
    assert not rebalance_mask(bimonthly_index, "bimonthly").loc[["2024-01-31", "2024-02-01", "2024-03-29"]].any()
    assert rebalance_mask(quarterly_index, "quarterly").loc[["2024-01-02", "2024-04-03", "2024-07-02"]].all()
    assert not rebalance_mask(quarterly_index, "quarterly").loc[["2024-03-28", "2024-06-28"]].any()


def test_phase2_non_rebalance_signal_change_waits_for_next_schedule():
    index = pd.bdate_range(end="2023-03-13", periods=205)
    closes = np.full(len(index), 100.0)
    # Wednesday crosses the MA; the following Thursday and Friday are not
    # weekly rebalance sessions, so the target remains unchanged until Monday.
    wednesday = index[-4]
    closes[index.get_loc(wednesday):] = 101.0
    target = trend_target_next_open(pd.Series(closes, index=index), "weekly", 200)
    assert target.loc[wednesday] == 0.0
    assert target.loc[index[-3]] == 0.0
    assert target.loc[index[-2]] == 0.0
    assert target.loc[index[-1]] == 1.0


def test_phase2_signal_asset_is_separate_from_held_asset():
    index = pd.bdate_range(end="2023-01-09", periods=201)
    qqq = pd.Series([100.0] * 199 + [101.0, 101.0], index=index)
    qld = _prices(index, [50.0] * 200 + [250.0], [50.0] * 200 + [250.0])
    changed_qld = qld.copy()
    changed_qld[["open", "adjusted_close"]] *= 11.0
    qqq_target = trend_target_next_open(qqq, "weekly", 200)
    # QLD is the held asset, never an input to the QQQ MA signal. Mutating its
    # history therefore cannot change the signal state, but it does change the
    # execution price/notional when it is actually held.
    pd.testing.assert_series_equal(qqq_target, trend_target_next_open(qqq, "weekly", 200))
    ledger, _, trades, _ = single_asset_timed_backtest(
        qld, qqq_target, initial_capital=1_000.0, commission_bps=0, slippage_bps=5, tax_rate=None,
    )
    _, _, changed_trades, _ = single_asset_timed_backtest(
        changed_qld, qqq_target, initial_capital=1_000.0, commission_bps=0, slippage_bps=5, tax_rate=None,
    )
    assert trades.price.iloc[-1] == pytest.approx(250.0)
    assert changed_trades.price.iloc[-1] == pytest.approx(2_750.0)
    assert ledger.shares.iloc[-1] > 0
    assert changed_qld.open.iloc[-1] != qld.open.iloc[-1]


def test_phase2_cash_state_is_zero_return_and_has_no_hidden_shares():
    index = pd.date_range("2024-01-02", periods=3, freq="B")
    prices = _prices(index, [100.0, 50.0, 200.0], [100.0, 50.0, 200.0])
    targets = pd.Series(0.0, index=index)
    ledger, _, trades, _ = single_asset_timed_backtest(
        prices, targets, initial_capital=1_000.0, commission_bps=0, slippage_bps=5, tax_rate=None,
    )
    assert trades.empty
    assert ledger.shares.eq(0.0).all()
    assert ledger.cash.eq(1_000.0).all()
    assert ledger.equity.eq(1_000.0).all()


def test_phase2_cost_is_exactly_five_basis_points_on_each_transition():
    index = pd.date_range("2024-01-02", periods=4, freq="B")
    prices = _prices(index, [100.0, 120.0, 80.0, 90.0], [100.0, 120.0, 80.0, 90.0])
    targets = pd.Series([1.0, 0.0, 1.0, 0.0], index=index)
    ledger, _, trades, _ = single_asset_timed_backtest(
        prices, targets, initial_capital=1_000.0, commission_bps=0, slippage_bps=5, tax_rate=None,
    )
    assert len(trades) == 4
    np.testing.assert_allclose(trades.transaction_cost, trades.notional * RATE, rtol=0, atol=1e-10)
    assert ledger.cash.min() >= -1e-9


def test_phase2_tax_is_immediate_average_cost_and_loss_pool_aware():
    index = pd.date_range("2024-01-02", periods=6, freq="B")
    prices = _prices(index, [100.0, 90.0, 80.0, 130.0, 120.0, 120.0])
    targets = pd.Series([1.0, 0.0, 1.0, 0.0, 1.0, 0.0], index=index)
    pre_ledger, _, pre_trades, pre_taxes = single_asset_timed_backtest(
        prices, targets, initial_capital=1_000.0, commission_bps=0, slippage_bps=5, tax_rate=None,
    )
    after_ledger, _, after_trades, after_taxes = single_asset_timed_backtest(
        prices, targets, initial_capital=1_000.0, commission_bps=0, slippage_bps=5, tax_rate=.20315,
    )
    assert pre_taxes.empty
    pd.testing.assert_series_equal(pre_ledger.equity.iloc[:2], after_ledger.equity.iloc[:2])
    assert len(after_taxes) == 3
    assert after_taxes.tax_paid.iloc[0] == 0.0  # realized loss creates a pool
    assert after_taxes.loss_pool.iloc[0] > 0.0
    # The loss pool offsets the first part of the next gain; only the net gain
    # is taxed, and the later near-flat realization creates a new small pool.
    assert after_taxes.tax_paid.iloc[1] == pytest.approx(
        (after_taxes.realized_gain.iloc[1] - after_taxes.loss_pool.iloc[0]) * .20315,
    )
    assert after_taxes.tax_paid.iloc[1] < after_taxes.realized_gain.iloc[1] * .20315
    assert after_taxes.tax_paid.iloc[2] == pytest.approx(0.0)
    assert after_ledger.equity.iloc[-1] <= pre_ledger.equity.iloc[-1]
    # No tax is charged merely for the unrealized position before the final sell.
    assert after_ledger.tax_paid.iloc[4] == 0.0
    assert len(after_trades) == len(pre_trades)


def test_phase2_warmup_and_calendar_alignment_audit():
    prices = {
        asset: pd.read_parquet(ROOT / "data/processed" / f"{asset}.parquet")
        for asset in ("SPY", "QQQ", "SSO", "QLD")
    }
    start = pd.Timestamp("2006-06-21")
    end = pd.Timestamp("2026-08-31")
    warmups = _warmup_rows(prices, start, end)
    assert {row["signal_asset"] for row in warmups} == {"QQQ", "SPY"}
    for row in warmups:
        assert row["pre_start_warmup_rows"] > 0
        assert row["lookback_observations_at_start"] == 200
        assert row["lookback_start_at_start"] == "2005-09-06"
        assert row["first_valid_ma200_date"] < "2006-06-21"
    alignments = _alignment_rows(prices, start, end)
    assert len(alignments) == 3
    assert {row["common_evaluation_rows"] for row in alignments} == {5080}
    assert {row["missing_targets_after_reindex"] for row in alignments} == {0}


def test_phase2_terminal_diagnostics_are_non_mutating():
    index = pd.date_range("2024-01-02", periods=2, freq="B")
    prices = _prices(index, [100.0, 200.0])
    targets = pd.Series([1.0, 1.0], index=index)
    ledger, _, trades, taxes = single_asset_timed_backtest(
        prices, targets, initial_capital=1_000.0, commission_bps=0, slippage_bps=5, tax_rate=.20315,
    )
    ledger_before, trades_before, taxes_before = ledger.copy(), trades.copy(), taxes.copy()
    result = performance_metrics(ledger, trades, 1_000.0, terminal_tax_rate=.20315, terminal_cost_rate=RATE)
    for field in (
        "after_tax_wealth_tax_paid_to_date", "after_tax_cagr_tax_paid_to_date",
        "terminal_liquidation_wealth", "terminal_liquidation_cagr", "terminal_liquidation_tax",
        "terminal_liquidation_cost", "terminal_unrealized_gain_after_cost",
    ):
        assert field in result
    assert result["terminal_liquidation_wealth"] < result["after_tax_wealth_tax_paid_to_date"]
    pd.testing.assert_frame_equal(ledger, ledger_before)
    pd.testing.assert_frame_equal(trades, trades_before)
    pd.testing.assert_frame_equal(taxes, taxes_before)


def test_phase2_artifact_completeness_and_counts():
    required = {
        "config_snapshot.yaml", "metrics_pre_tax.csv", "metrics_after_tax.csv", "ma200_results.csv",
        "parameter_results.csv", "equity_curve.csv", "drawdown.csv", "positions.csv", "trades.csv",
        "tax_ledger.csv", "phase2_report.md", "equity_curve.png", "drawdown.png", "rolling_returns.png",
        "rolling_maxdd.png", "cagr_maxdd_scatter.png",
    }
    missing = sorted(name for name in required if not (CANONICAL_RUN / name).exists())
    assert not missing, f"canonical Phase 2 run is missing: {missing}"
    pre = pd.read_csv(CANONICAL_RUN / "metrics_pre_tax.csv")
    after = pd.read_csv(CANONICAL_RUN / "metrics_after_tax.csv")
    combined = pd.read_csv(CANONICAL_RUN / "ma200_results.csv")
    parameters = pd.read_csv(CANONICAL_RUN / "parameter_results.csv")
    assert len(pre) == 12
    assert len(after) == 12
    assert len(combined) == 24
    assert len(parameters) == 12
    assert set(parameters.ma_window) == {200}
    assert set(parameters.searched) == {False}
    assert set(pre.tax_mode) == {"pre_tax"}
    assert set(after.tax_mode) == {"after_tax"}
    for field in (
        "terminal_liquidation_wealth", "terminal_liquidation_cagr", "terminal_liquidation_tax",
        "terminal_liquidation_cost", "terminal_unrealized_gain_after_cost",
        "after_tax_wealth_tax_paid_to_date", "after_tax_cagr_tax_paid_to_date",
        "cumulative_realized_tax_paid", "tax_semantics",
    ):
        assert field in after
        assert after[field].notna().all()
