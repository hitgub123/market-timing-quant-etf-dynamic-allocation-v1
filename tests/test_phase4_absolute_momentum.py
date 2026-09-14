from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from experiments.phase4_absolute_momentum import (
    FREQUENCIES,
    MOMENTUM_WINDOWS,
    STRATEGIES,
    _alignment_rows,
    _stability_rows,
    _warmup_rows,
    parameter_grid,
    strategy_identifier,
)
from market_timing_quant.metrics import performance_metrics
from market_timing_quant.portfolio import single_asset_timed_backtest
from market_timing_quant.signals import (
    absolute_momentum_decision,
    absolute_momentum_target_next_open,
    rebalance_mask,
)


ROOT = Path(__file__).resolve().parents[1]
CANONICAL_RUN = ROOT / "reports/runs/20260914_phase4_audit_final"
OLD_RUN = ROOT / "reports/runs/20260913_phase4_absolute_momentum_final"
NUMERIC_ATOL = 1e-8
EXECUTION_RATE = 5 / 10_000


def _assert_value_equal(left: object, right: object, field: str) -> None:
    if pd.isna(left) and pd.isna(right):
        return
    if field in {"start", "end", "date", "tax_mode", "strategy", "side", "asset"}:
        assert str(left) == str(right), field
    else:
        assert float(left) == pytest.approx(float(right), rel=0, abs=NUMERIC_ATOL), field


def _prices(index: pd.DatetimeIndex, opens: list[float], closes: list[float] | None = None) -> pd.DataFrame:
    adjusted_close = closes if closes is not None else opens
    return pd.DataFrame({"open": opens, "adjusted_close": adjusted_close}, index=index)


def test_phase4_exact_frozen_grid_and_combination_count():
    assert parameter_grid() == (126, 189, 252)
    assert MOMENTUM_WINDOWS == (126, 189, 252)
    assert len(STRATEGIES) * len(FREQUENCIES) * len(MOMENTUM_WINDOWS) == 24

    surface = pd.read_csv(CANONICAL_RUN / "absolute_momentum_results.csv")
    assert len(surface) == 48
    keys = ["rule", "frequency", "momentum_window", "tax_mode"]
    counts = surface.groupby(keys, dropna=False).size()
    assert len(counts) == 48
    assert counts.eq(1).all()
    assert set(surface.momentum_window) == set(MOMENTUM_WINDOWS)
    assert set(surface.tax_mode) == {"pre_tax", "after_tax"}


def test_phase4_parameter_results_enumerates_the_grid_without_selection():
    parameters = pd.read_csv(CANONICAL_RUN / "parameter_results.csv")
    assert len(parameters) == 24
    required = {
        "rule", "rule_family", "legacy_rule", "signal_asset", "held_asset", "frequency",
        "momentum_window", "searched_for_selection", "selection_performed",
    }
    assert required <= set(parameters.columns)
    assert parameters.searched_for_selection.eq(False).all()
    assert parameters.selection_performed.eq(False).all()
    assert parameters[["rule", "frequency", "momentum_window"]].drop_duplicates().shape[0] == 24
    assert set(parameters.momentum_window) == set(MOMENTUM_WINDOWS)


def test_phase4_artifact_completeness_counts_and_required_columns():
    required = {
        "config_snapshot.yaml", "metrics_pre_tax.csv", "metrics_after_tax.csv",
        "absolute_momentum_results.csv", "parameter_results.csv",
        "equity_curve.csv", "drawdown.csv", "positions.csv", "trades.csv", "tax_ledger.csv",
        "phase4_report.md", "absolute_momentum_heatmap.png", "absolute_momentum_heatmap_after_tax.png",
        "equity_curve.png", "drawdown.png", "rolling_returns.png", "rolling_maxdd.png",
        "cagr_maxdd_scatter.png",
    }
    missing = sorted(name for name in required if not (CANONICAL_RUN / name).exists())
    assert not missing, f"canonical Phase 4 run is missing: {missing}"

    pre = pd.read_csv(CANONICAL_RUN / "metrics_pre_tax.csv")
    after = pd.read_csv(CANONICAL_RUN / "metrics_after_tax.csv")
    surface = pd.read_csv(CANONICAL_RUN / "absolute_momentum_results.csv")
    parameters = pd.read_csv(CANONICAL_RUN / "parameter_results.csv")
    assert len(pre) == 24
    assert len(after) == 24
    assert len(surface) == 48
    assert len(parameters) == 24
    assert pre.tax_mode.eq("pre_tax").all()
    assert after.tax_mode.eq("after_tax").all()
    required_metric_fields = {
        "strategy", "tax_mode", "frequency", "rule", "rule_family", "momentum_window",
        "signal_asset", "held_asset", "ending_value", "cagr", "max_drawdown", "calmar",
        "annual_turnover", "number_of_trades", "mean_holding_period_days",
        "median_holding_period_days", "max_holding_period_days", "transaction_costs", "tax_paid",
        "terminal_liquidation_wealth", "terminal_liquidation_cagr", "terminal_liquidation_tax",
        "terminal_liquidation_cost", "terminal_unrealized_gain_after_cost", "cumulative_realized_tax_paid",
        "tax_semantics",
    }
    assert required_metric_fields <= set(surface.columns)
    assert after[
        [
            "terminal_liquidation_wealth", "terminal_liquidation_cagr", "terminal_liquidation_tax",
            "terminal_liquidation_cost", "terminal_unrealized_gain_after_cost",
            "cumulative_realized_tax_paid", "tax_semantics",
        ]
    ].notna().all().all()


def test_phase4_source_tables_survive_combined_surface_and_values_match():
    pre = pd.read_csv(CANONICAL_RUN / "metrics_pre_tax.csv")
    after = pd.read_csv(CANONICAL_RUN / "metrics_after_tax.csv")
    surface = pd.read_csv(CANONICAL_RUN / "absolute_momentum_results.csv")
    assert set(pre.columns) <= set(surface.columns)
    assert set(after.columns) <= set(surface.columns)
    assert surface.groupby(["strategy", "tax_mode"], dropna=False).size().eq(1).all()

    fields = [
        "ending_value", "total_return", "cagr", "max_drawdown", "calmar", "annual_turnover",
        "number_of_trades", "transaction_costs", "tax_paid", "mean_holding_period_days",
        "median_holding_period_days", "max_holding_period_days",
    ]
    for source in (pre, after):
        for _, row in source.iterrows():
            matches = surface[surface.strategy.eq(row.strategy) & surface.tax_mode.eq(row.tax_mode)]
            assert len(matches) == 1
            combined = matches.iloc[0]
            for field in fields:
                _assert_value_equal(row[field], combined[field], field)
            if row.tax_mode == "after_tax":
                for field in (
                    "terminal_liquidation_wealth", "terminal_liquidation_cagr", "terminal_liquidation_tax",
                    "terminal_liquidation_cost", "terminal_unrealized_gain_after_cost",
                ):
                    _assert_value_equal(row[field], combined[field], field)


@pytest.mark.parametrize("window", [126, 189, 252])
def test_phase4_absolute_momentum_formula_is_strict_positive_with_window_warmup(window: int):
    index = pd.bdate_range("2020-01-02", periods=window + 1)
    positive = pd.Series([100.0] * window + [110.0], index=index)
    negative = pd.Series([100.0] * window + [90.0], index=index)
    zero = pd.Series([100.0] * (window + 1), index=index)

    for price, expected in ((positive, 1.0), (negative, 0.0), (zero, 0.0)):
        decision = absolute_momentum_decision(price, window)
        assert decision.iloc[:window].eq(0.0).all()
        assert decision.iloc[window] == expected
        assert decision.iloc[window] == float(price.iloc[window] / price.iloc[0] - 1.0 > 0.0)
        assert decision.notna().all()


@pytest.mark.parametrize("window", [126, 252])
def test_phase4_parameterized_signal_path_preserves_close_to_next_open_no_lookahead(window: int):
    # Friday's close is the first positive momentum decision; Monday is the
    # next weekly open. The artificial Monday gap proves execution uses open.
    index = pd.bdate_range(end="2023-01-09", periods=window + 2)
    closes = [100.0] * window + [101.0, 101.0]
    opens = [100.0] * window + [77.0, 150.0]
    prices = _prices(index, opens, closes)
    target = absolute_momentum_target_next_open(prices.adjusted_close, "weekly", window)
    friday, monday = index[-2], index[-1]
    assert target.loc[friday] == 0.0
    assert target.loc[monday] == 1.0
    ledger, _, trades, _ = single_asset_timed_backtest(
        prices, target, initial_capital=1_000.0, commission_bps=0.0,
        slippage_bps=5.0, tax_rate=None,
    )
    assert trades.side.tolist() == ["BUY"]
    assert pd.Timestamp(trades.date.iloc[0]) == monday
    assert trades.price.iloc[0] == pytest.approx(150.0)
    assert trades.transaction_cost.iloc[0] == pytest.approx(trades.notional.iloc[0] * EXECUTION_RATE)
    assert ledger.loc[friday, "shares"] == 0.0
    assert ledger.loc[monday, "shares"] > 0.0

    changed = prices.adjusted_close.copy()
    changed.loc[index > friday] = changed.loc[index > friday] * 9.0
    original = absolute_momentum_target_next_open(prices.adjusted_close, "weekly", window)
    mutated = absolute_momentum_target_next_open(changed, "weekly", window)
    pd.testing.assert_series_equal(original.loc[:friday], mutated.loc[:friday])


def test_phase4_rebalance_schedules_use_first_available_session():
    weekly = pd.DatetimeIndex(["2024-01-02", "2024-01-03", "2024-01-08", "2024-01-09"])
    monthly = pd.DatetimeIndex(["2024-01-02", "2024-01-31", "2024-02-02", "2024-02-29", "2024-03-04"])
    bimonthly = pd.DatetimeIndex(["2024-01-03", "2024-01-31", "2024-02-01", "2024-03-04", "2024-03-29"])
    quarterly = pd.DatetimeIndex(["2024-01-02", "2024-03-28", "2024-04-03", "2024-06-28", "2024-07-02"])
    assert rebalance_mask(weekly, "weekly").loc["2024-01-02"]
    assert not rebalance_mask(weekly, "weekly").loc["2024-01-03"]
    assert rebalance_mask(monthly, "monthly").loc[["2024-01-02", "2024-02-02", "2024-03-04"]].all()
    assert not rebalance_mask(monthly, "monthly").loc[["2024-01-31", "2024-02-29"]].any()
    assert rebalance_mask(bimonthly, "bimonthly").loc[["2024-01-03", "2024-03-04"]].all()
    assert not rebalance_mask(bimonthly, "bimonthly").loc[["2024-01-31", "2024-02-01", "2024-03-29"]].any()
    assert rebalance_mask(quarterly, "quarterly").loc[["2024-01-02", "2024-04-03", "2024-07-02"]].all()
    assert not rebalance_mask(quarterly, "quarterly").loc[["2024-03-28", "2024-06-28"]].any()


def test_phase4_momentum_change_between_rebalances_waits_for_next_schedule():
    window = 126
    index = pd.bdate_range(end="2023-03-13", periods=window + 5)
    closes = [100.0] * window + [100.0, 101.0, 101.0, 101.0, 101.0]
    target = absolute_momentum_target_next_open(
        pd.Series(closes, index=index), "weekly", window,
    )
    wednesday, thursday, friday, monday = index[-4:]
    assert target.loc[wednesday] == 0.0
    assert target.loc[thursday] == 0.0
    assert target.loc[friday] == 0.0
    assert target.loc[monday] == 1.0


@pytest.mark.parametrize("signal_asset,held_asset", [("SPY", "SSO"), ("QQQ", "QLD")])
def test_phase4_signal_asset_is_separate_from_held_asset(signal_asset: str, held_asset: str):
    window = 126
    index = pd.bdate_range(end="2023-01-09", periods=window + 2)
    signal = pd.Series([100.0] * window + [101.0, 101.0], index=index)
    held = _prices(index, [50.0] * (window + 1) + [250.0])
    target = absolute_momentum_target_next_open(signal, "weekly", window)
    _, _, trades, _ = single_asset_timed_backtest(
        held, target, initial_capital=1_000.0, commission_bps=0.0, slippage_bps=5.0, tax_rate=None,
    )
    assert trades.asset.tolist() == ["RISK"]
    assert trades.price.iloc[-1] == pytest.approx(250.0)
    changed_held = held * 11.0
    pd.testing.assert_series_equal(target, absolute_momentum_target_next_open(signal, "weekly", window))
    _, _, changed_trades, _ = single_asset_timed_backtest(
        changed_held, target, initial_capital=1_000.0, commission_bps=0.0, slippage_bps=5.0, tax_rate=None,
    )
    assert changed_trades.price.iloc[-1] == pytest.approx(2_750.0)


def test_phase4_cash_state_has_zero_return_and_no_hidden_shares():
    index = pd.date_range("2024-01-02", periods=3, freq="B")
    prices = _prices(index, [100.0, 50.0, 200.0])
    target = pd.Series(0.0, index=index)
    ledger, _, trades, _ = single_asset_timed_backtest(
        prices, target, initial_capital=1_000.0, commission_bps=0.0, slippage_bps=5.0, tax_rate=None,
    )
    assert trades.empty
    assert ledger.shares.eq(0.0).all()
    assert ledger.cash.eq(1_000.0).all()
    assert ledger.equity.eq(1_000.0).all()


def test_phase4_window_specific_warmup_and_calendar_alignment_audit():
    prices = {
        asset: pd.read_parquet(ROOT / "data/processed" / f"{asset}.parquet")
        for asset in ("SPY", "QQQ", "SSO", "QLD")
    }
    start = pd.Timestamp("2006-06-21")
    end = pd.Timestamp("2026-08-31")
    warmups = _warmup_rows(prices, start, end)
    assert len(warmups) == 6
    assert {(row["signal_asset"], row["momentum_window"]) for row in warmups} == {
        (asset, window) for asset in ("SPY", "QQQ") for window in MOMENTUM_WINDOWS
    }
    for row in warmups:
        assert row["pre_start_warmup_rows"] > 0
        assert row["required_lookback_sessions"] == row["momentum_window"]
        assert row["lookback_observations_at_evaluation_start"] == row["momentum_window"] + 1
        assert row["first_valid_momentum_date"] < str(start.date())
        decision = absolute_momentum_decision(prices[row["signal_asset"]]["adjusted_close"], row["momentum_window"])
        assert decision.iloc[: row["momentum_window"]].eq(0.0).all()
        assert row["missing_aligned_targets"] == 0
    alignments = _alignment_rows(prices, start, end)
    assert len(alignments) == 2
    assert {row["common_evaluation_rows"] for row in alignments} == {5080}
    assert {row["missing_targets_after_reindex"] for row in alignments} == {0}
    curves = pd.read_csv(CANONICAL_RUN / "equity_curve.csv")
    positions = pd.read_csv(CANONICAL_RUN / "positions.csv")
    trades = pd.read_csv(CANONICAL_RUN / "trades.csv")
    assert curves.date.min() == str(start.date())
    assert positions.date.min() == str(start.date())
    assert pd.to_datetime(trades.date).min() >= start


def test_phase4_tax_terminal_diagnostics_are_non_mutating():
    after = pd.read_csv(CANONICAL_RUN / "metrics_after_tax.csv")
    assert after["tax_semantics"].str.contains("realized tax paid to date").all()
    assert after["cumulative_realized_tax_paid"].equals(after["tax_paid"])
    assert after[[
        "terminal_liquidation_wealth", "terminal_liquidation_cagr", "terminal_liquidation_tax",
        "terminal_liquidation_cost", "terminal_unrealized_gain_after_cost",
    ]].notna().all().all()

    index = pd.date_range("2024-01-02", periods=2, freq="B")
    prices = _prices(index, [100.0, 200.0])
    target = pd.Series([1.0, 1.0], index=index)
    ledger, _, trades, taxes = single_asset_timed_backtest(
        prices, target, initial_capital=1_000.0, commission_bps=0.0, slippage_bps=5.0, tax_rate=0.20315,
    )
    before = (ledger.copy(deep=True), trades.copy(deep=True), taxes.copy(deep=True))
    result = performance_metrics(
        ledger, trades, 1_000.0, terminal_tax_rate=0.20315, terminal_cost_rate=EXECUTION_RATE,
    )
    assert result["terminal_liquidation_wealth"] < result["after_tax_wealth_tax_paid_to_date"]
    assert not any(str(side).upper() == "SELL" for side in trades.side)
    pd.testing.assert_frame_equal(ledger, before[0])
    pd.testing.assert_frame_equal(trades, before[1])
    pd.testing.assert_frame_equal(taxes, before[2])


def test_phase4_stability_rows_are_descriptive_only():
    surface = pd.read_csv(CANONICAL_RUN / "absolute_momentum_results.csv")
    rows = _stability_rows(surface)
    assert len(rows) == len(STRATEGIES) * len(FREQUENCIES)
    for row in rows:
        assert row["pre_tax_cagr_min"] <= row["pre_tax_cagr_max"]
        assert row["cagr_spread"] == pytest.approx(
            row["pre_tax_cagr_max"] - row["pre_tax_cagr_min"], rel=0, abs=NUMERIC_ATOL,
        )
        assert row["maxdd_spread"] == pytest.approx(
            row["max_abs_maxdd"] - row["min_abs_maxdd"], rel=0, abs=NUMERIC_ATOL,
        )
        assert row["descriptive_min_cagr_window"] in MOMENTUM_WINDOWS
        assert row["descriptive_max_cagr_window"] in MOMENTUM_WINDOWS


def test_phase4_strategy_identifiers_make_lookback_explicit():
    surface = pd.read_csv(CANONICAL_RUN / "absolute_momentum_results.csv")
    for _, row in surface.iterrows():
        assert f"_{int(row.momentum_window)}D" in row.strategy
        assert row.rule_family in STRATEGIES
        assert row.legacy_rule == row.rule
        assert row.legacy_strategy == row.strategy


def test_phase4_old_to_new_economic_fields_are_unchanged():
    old = pd.concat(
        [pd.read_csv(OLD_RUN / "metrics_pre_tax.csv"), pd.read_csv(OLD_RUN / "metrics_after_tax.csv")],
        ignore_index=True,
    )
    new = pd.read_csv(CANONICAL_RUN / "absolute_momentum_results.csv")
    assert len(old) == len(new) == 48
    key = ["rule", "frequency", "momentum_window", "tax_mode"]
    economic_fields = [
        "ending_value", "total_return", "cagr", "max_drawdown", "sharpe", "sortino", "calmar",
        "ulcer_index", "number_of_trades",
        "transaction_costs", "tax_paid",
    ]
    for _, old_row in old.iterrows():
        matches = new[
            new.rule.eq(old_row.rule) & new.frequency.eq(old_row.frequency)
            & new.momentum_window.eq(old_row.momentum_window) & new.tax_mode.eq(old_row.tax_mode)
        ]
        assert len(matches) == 1
        new_row = matches.iloc[0]
        for field in economic_fields:
            _assert_value_equal(old_row[field], new_row[field], field)


def test_phase4_report_documents_audited_semantics_and_no_selection():
    report = (CANONICAL_RUN / "phase4_report.md").read_text(encoding="utf-8")
    required_phrases = [
        "exact frozen momentum grid is `(126, 189, 252)`",
        "momentum_t > 0",
        "next available session (*t+1*)",
        "Warm-up creates no pre-evaluation equity",
        "completed position episodes",
        "Terminal liquidation fields are hypothetical diagnostics",
        "contemporaneous_pretrade_equity",
        "no lookback was selected for deployment",
        "Phase 4 makes no OOS or Walk-Forward claim",
        "Walk-Forward parameter selection remains deferred",
        "parameter_results.csv` is the 24-row unique economic grid",
    ]
    for phrase in required_phrases:
        assert phrase in report
