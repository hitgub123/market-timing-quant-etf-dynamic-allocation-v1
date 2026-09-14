from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from experiments.phase2_ma200 import FREQUENCIES, STRATEGIES
from experiments.phase3_ma_stability import (
    MA_WINDOWS,
    _alignment_rows,
    _warmup_rows,
    parameter_grid,
    strategy_identifier,
)
from market_timing_quant.metrics import performance_metrics
from market_timing_quant.portfolio import single_asset_timed_backtest
from market_timing_quant.signals import ma_trend_decision, trend_target_next_open


ROOT = Path(__file__).resolve().parents[1]
CANONICAL_RUN = ROOT / "reports/runs/20260914_phase3_audit_final_v3"
PHASE2_RUN = ROOT / "reports/runs/20260914_phase2_audit_final"
NUMERIC_ATOL = 1e-8
EXECUTION_RATE = 5 / 10_000


def _read_metrics(path: Path) -> pd.DataFrame:
    return pd.read_csv(path)


def _assert_value_equal(left: object, right: object, field: str) -> None:
    if field in {"start", "end"}:
        assert str(left) == str(right), field
    elif pd.isna(left) and pd.isna(right):
        return
    else:
        assert float(left) == pytest.approx(float(right), rel=0, abs=NUMERIC_ATOL), field


def _phase3_to_phase2_name(row: pd.Series) -> str:
    return f"{row.legacy_rule}_{row.frequency}"


def _phase2_row_for_phase3(row: pd.Series, phase2: pd.DataFrame) -> pd.Series:
    matches = phase2[
        phase2.tax_mode.eq(row.tax_mode)
        & phase2.frequency.eq(row.frequency)
        & phase2.signal_asset.eq(row.signal_asset)
        & phase2.held_asset.eq(row.held_asset)
    ]
    assert len(matches) == 1, (row.strategy, row.tax_mode)
    return matches.iloc[0]


def test_phase3_exact_frozen_grid_and_combination_count():
    assert parameter_grid() == (150, 175, 200, 225, 250)
    assert MA_WINDOWS == (150, 175, 200, 225, 250)
    assert len(STRATEGIES) * len(FREQUENCIES) * len(MA_WINDOWS) == 60

    surface = pd.read_csv(CANONICAL_RUN / "ma_parameter_surface.csv")
    assert len(surface) == 120
    keys = ["rule_family", "frequency", "ma_window", "tax_mode"]
    counts = surface.groupby(keys, dropna=False).size()
    assert len(counts) == 120
    assert counts.eq(1).all()
    assert set(surface.ma_window) == set(MA_WINDOWS)
    assert set(surface.tax_mode) == {"pre_tax", "after_tax"}


def test_phase3_parameter_results_enumerates_without_selection():
    parameters = pd.read_csv(CANONICAL_RUN / "parameter_results.csv")
    assert len(parameters) == 60
    assert {
        "rule", "rule_family", "legacy_rule", "signal_asset", "held_asset", "frequency",
        "ma_window", "searched_for_selection", "selection_performed",
    } <= set(parameters.columns)
    assert parameters.searched_for_selection.eq(False).all()
    assert parameters.selection_performed.eq(False).all()
    keys = ["rule_family", "frequency", "ma_window"]
    assert parameters[keys].drop_duplicates().shape[0] == 60
    assert set(parameters.ma_window) == set(MA_WINDOWS)


def test_phase3_artifact_completeness_and_counts():
    required = {
        "config_snapshot.yaml", "metrics_pre_tax.csv", "metrics_after_tax.csv",
        "ma_parameter_surface.csv", "parameter_results.csv", "equity_curve.csv",
        "drawdown.csv", "positions.csv", "trades.csv", "tax_ledger.csv", "phase3_report.md",
        "ma_stability_heatmap.png", "ma_stability_heatmap_after_tax.png", "equity_curve.png",
        "drawdown.png", "rolling_returns.png", "rolling_maxdd.png", "cagr_maxdd_scatter.png",
    }
    missing = sorted(name for name in required if not (CANONICAL_RUN / name).exists())
    assert not missing, f"canonical Phase 3 run is missing: {missing}"

    pre = pd.read_csv(CANONICAL_RUN / "metrics_pre_tax.csv")
    after = pd.read_csv(CANONICAL_RUN / "metrics_after_tax.csv")
    surface = pd.read_csv(CANONICAL_RUN / "ma_parameter_surface.csv")
    parameters = pd.read_csv(CANONICAL_RUN / "parameter_results.csv")
    assert len(pre) == 60
    assert len(after) == 60
    assert len(surface) == 120
    assert len(parameters) == 60
    assert pre.tax_mode.eq("pre_tax").all()
    assert after.tax_mode.eq("after_tax").all()

    required_metric_fields = {
        "strategy", "tax_mode", "frequency", "rule_family", "ma_window", "signal_asset", "held_asset",
        "cagr", "max_drawdown", "calmar", "annual_turnover", "ending_value", "number_of_trades",
        "mean_holding_period_days", "median_holding_period_days", "max_holding_period_days", "pareto",
        "terminal_liquidation_wealth", "terminal_liquidation_cagr", "terminal_liquidation_tax",
        "terminal_liquidation_cost", "terminal_unrealized_gain_after_cost", "pareto_terminal_liquidation",
        "cumulative_realized_tax_paid", "tax_semantics",
    }
    # Pareto fields are optional in this Phase 3 implementation; every other
    # requested metric/diagnostic must be present in the finalized surface.
    assert (required_metric_fields - {"pareto", "pareto_terminal_liquidation"}) <= set(surface.columns)
    assert {"pareto", "pareto_terminal_liquidation"}.isdisjoint(set(surface.columns)) or \
        {"pareto", "pareto_terminal_liquidation"} <= set(surface.columns)
    assert after[
        [
            "terminal_liquidation_wealth", "terminal_liquidation_cagr", "terminal_liquidation_tax",
            "terminal_liquidation_cost", "terminal_unrealized_gain_after_cost",
            "cumulative_realized_tax_paid", "tax_semantics",
        ]
    ].notna().all().all()


def test_phase3_source_tables_survive_in_surface_and_cross_file_values_match():
    pre = pd.read_csv(CANONICAL_RUN / "metrics_pre_tax.csv")
    after = pd.read_csv(CANONICAL_RUN / "metrics_after_tax.csv")
    surface = pd.read_csv(CANONICAL_RUN / "ma_parameter_surface.csv")
    assert set(pre.columns) <= set(surface.columns)
    assert set(after.columns) <= set(surface.columns)

    key = ["strategy", "tax_mode"]
    assert surface.groupby(key, dropna=False).size().eq(1).all()
    fields = ["ending_value", "cagr", "max_drawdown", "calmar", "annual_turnover", "pareto"]
    fields = [field for field in fields if field in pre.columns and field in surface.columns]
    for source in (pre, after):
        for _, row in source.iterrows():
            match = surface[surface.strategy.eq(row.strategy) & surface.tax_mode.eq(row.tax_mode)]
            assert len(match) == 1
            combined = match.iloc[0]
            for field in fields:
                _assert_value_equal(row[field], combined[field], field)
            if row.tax_mode == "after_tax":
                for field in (
                    "terminal_liquidation_wealth", "terminal_liquidation_cagr",
                    "terminal_liquidation_tax", "terminal_liquidation_cost",
                    "terminal_unrealized_gain_after_cost", "pareto_terminal_liquidation",
                ):
                    if field in source.columns and field in surface.columns:
                        _assert_value_equal(row[field], combined[field], field)


def test_phase3_strategy_identifiers_make_window_explicit():
    surface = pd.read_csv(CANONICAL_RUN / "ma_parameter_surface.csv")
    for _, row in surface.iterrows():
        assert f"_MA{int(row.ma_window)}" in row.strategy
        assert row.rule_family in {"QQQ_MA_QQQ", "QQQ_MA_QLD", "SPY_MA_SSO"}
        assert row.legacy_rule in {"QQQ_MA200_QQQ", "QQQ_MA200_QLD", "SPY_MA200_SSO"}
        assert "MA200" not in row.rule_family


def test_phase3_ma200_matches_phase2_metrics_for_all_24_rows():
    phase3 = pd.concat(
        [
            pd.read_csv(CANONICAL_RUN / "metrics_pre_tax.csv"),
            pd.read_csv(CANONICAL_RUN / "metrics_after_tax.csv"),
        ],
        ignore_index=True,
    )
    phase2 = pd.concat(
        [
            pd.read_csv(PHASE2_RUN / "metrics_pre_tax.csv"),
            pd.read_csv(PHASE2_RUN / "metrics_after_tax.csv"),
        ],
        ignore_index=True,
    )
    metric_fields = [
        "start", "end", "ending_value", "total_return", "cagr", "max_drawdown", "sharpe", "sortino",
        "calmar", "ulcer_index", "number_of_trades", "annual_turnover", "mean_holding_period_days",
        "median_holding_period_days", "max_holding_period_days", "transaction_costs", "tax_paid",
    ]
    terminal_fields = [
        "terminal_liquidation_wealth", "terminal_liquidation_cagr", "terminal_liquidation_tax",
        "terminal_liquidation_cost",
    ]
    p3_ma200 = phase3[phase3.ma_window.eq(200)]
    assert len(p3_ma200) == 24
    comparisons = 0
    for _, p3_row in p3_ma200.iterrows():
        p2_row = _phase2_row_for_phase3(p3_row, phase2)
        for field in metric_fields:
            _assert_value_equal(p3_row[field], p2_row[field], field)
        if p3_row.tax_mode == "after_tax":
            for field in terminal_fields:
                _assert_value_equal(p3_row[field], p2_row[field], field)
        comparisons += 1
    assert comparisons == 24


@pytest.mark.parametrize("table_name,fields", [
    ("equity_curve.csv", ["date", "equity", "tax_mode"]),
    ("positions.csv", ["date", "shares", "target_weight", "actual_weight", "tax_mode"]),
    ("trades.csv", ["date", "asset", "side", "shares", "price", "notional", "transaction_cost", "realized_gain", "tax_mode"]),
    ("tax_ledger.csv", ["date", "realized_gain", "loss_pool", "tax_paid", "cumulative_tax_paid", "tax_mode"]),
])
def test_phase3_ma200_paths_match_phase2(table_name: str, fields: list[str]):
    phase3 = pd.read_csv(CANONICAL_RUN / table_name)
    phase2 = pd.read_csv(PHASE2_RUN / table_name)
    metrics = pd.read_csv(CANONICAL_RUN / "metrics_pre_tax.csv")
    metrics = pd.concat([metrics, pd.read_csv(CANONICAL_RUN / "metrics_after_tax.csv")], ignore_index=True)
    p3_ma200 = metrics[metrics.ma_window.eq(200)]
    comparisons = 0
    for _, row in p3_ma200.iterrows():
        p2_name = _phase3_to_phase2_name(row)
        left = phase3[phase3.strategy.eq(row.strategy) & phase3.tax_mode.eq(row.tax_mode)].reset_index(drop=True)
        right = phase2[phase2.strategy.eq(p2_name) & phase2.tax_mode.eq(row.tax_mode)].reset_index(drop=True)
        assert len(left) == len(right), (table_name, row.strategy, row.tax_mode)
        assert list(left.columns)  # guard against an accidentally empty schema
        for field in fields:
            assert field in left.columns and field in right.columns, (table_name, field)
            if field in {"date", "tax_mode", "asset", "side"}:
                assert left[field].astype(str).tolist() == right[field].astype(str).tolist(), (
                    table_name, row.strategy, row.tax_mode, field,
                )
            elif len(left):
                np.testing.assert_allclose(
                    left[field].to_numpy(dtype=float), right[field].to_numpy(dtype=float),
                    rtol=0, atol=NUMERIC_ATOL,
                    err_msg=f"{table_name} {row.strategy} {row.tax_mode} {field}",
                )
        comparisons += 1
    assert comparisons == 24


@pytest.mark.parametrize("window", [150, 250])
def test_phase3_parameterized_signal_path_preserves_next_open_no_lookahead(window: int):
    # The final two sessions are Friday and Monday. The Friday close is the
    # first close above the MA, so the weekly target can only change at the
    # following Monday open.
    index = pd.bdate_range(end="2023-01-09", periods=window + 1)
    closes = [100.0] * (window - 1) + [101.0, 101.0]
    opens = [100.0] * (window - 1) + [77.0, 150.0]
    prices = pd.DataFrame({"open": opens, "adjusted_close": closes}, index=index)
    targets = trend_target_next_open(prices.adjusted_close, "weekly", lookback=window)
    friday, monday = index[-2], index[-1]
    assert targets.loc[friday] == 0.0
    assert targets.loc[monday] == 1.0
    ledger, _, trades, _ = single_asset_timed_backtest(
        prices, targets, initial_capital=1_000.0, commission_bps=0.0,
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
    original_target = trend_target_next_open(prices.adjusted_close, "weekly", lookback=window)
    changed_target = trend_target_next_open(changed, "weekly", lookback=window)
    pd.testing.assert_series_equal(original_target.loc[:friday], changed_target.loc[:friday])


def test_phase3_window_specific_warmup_and_calendar_alignment_audit():
    prices = {
        asset: pd.read_parquet(ROOT / "data/processed" / f"{asset}.parquet")
        for asset in ("SPY", "QQQ", "SSO", "QLD")
    }
    start = pd.Timestamp("2006-06-21")
    end = pd.Timestamp("2026-08-31")
    warmups = _warmup_rows(prices, start, end)
    assert len(warmups) == 10
    assert {(row["signal_asset"], row["ma_window"]) for row in warmups} == {
        (asset, window) for asset in ("QQQ", "SPY") for window in MA_WINDOWS
    }
    for row in warmups:
        assert row["pre_start_warmup_rows"] > 0
        assert row["lookback_observations_at_start"] == row["ma_window"]
        assert row["first_valid_ma_date"] < str(start.date())
        decision = ma_trend_decision(prices[row["signal_asset"]]["adjusted_close"], row["ma_window"])
        assert decision.iloc[: row["ma_window"] - 1].eq(0.0).all()
        assert row["missing_aligned_targets"] == 0
    alignments = _alignment_rows(prices, start, end)
    assert len(alignments) == 3
    assert {row["common_evaluation_rows"] for row in alignments} == {5080}
    assert {row["missing_targets_after_reindex"] for row in alignments} == {0}


def test_phase3_tax_terminal_diagnostics_are_present_and_non_mutating():
    after = pd.read_csv(CANONICAL_RUN / "metrics_after_tax.csv")
    assert after["tax_semantics"].str.contains("realized tax paid to date").all()
    assert after["cumulative_realized_tax_paid"].equals(after["tax_paid"])
    assert after["terminal_liquidation_wealth"].notna().all()
    assert after["terminal_liquidation_cagr"].notna().all()
    assert after["terminal_liquidation_tax"].notna().all()
    assert after["terminal_liquidation_cost"].notna().all()

    index = pd.date_range("2024-01-02", periods=2, freq="B")
    prices = pd.DataFrame({"open": [100.0, 200.0], "adjusted_close": [100.0, 200.0]}, index=index)
    targets = pd.Series([1.0, 1.0], index=index)
    ledger, _, trades, taxes = single_asset_timed_backtest(
        prices, targets, initial_capital=1_000.0, commission_bps=0.0,
        slippage_bps=5.0, tax_rate=0.20315,
    )
    before = (ledger.copy(deep=True), trades.copy(deep=True), taxes.copy(deep=True))
    result = performance_metrics(
        ledger, trades, 1_000.0, terminal_tax_rate=0.20315, terminal_cost_rate=EXECUTION_RATE,
    )
    assert result["terminal_liquidation_wealth"] < result["after_tax_wealth_tax_paid_to_date"]
    pd.testing.assert_frame_equal(ledger, before[0])
    pd.testing.assert_frame_equal(trades, before[1])
    pd.testing.assert_frame_equal(taxes, before[2])


def test_phase3_report_states_descriptive_full_sample_study():
    report = (CANONICAL_RUN / "phase3_report.md").read_text(encoding="utf-8")
    required_phrases = [
        "frozen MA grid",
        "no window was selected for deployment",
        "Phase 3 is not OOS evidence",
        "Walk-Forward parameter selection remains deferred",
        "All 24 (rule, frequency, tax-mode) comparisons",
        "CAGR spread",
        "completed position episodes",
        "terminal liquidation",
    ]
    for phrase in required_phrases:
        assert phrase in report

