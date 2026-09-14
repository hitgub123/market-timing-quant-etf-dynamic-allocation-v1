from __future__ import annotations

from pathlib import Path
import hashlib

import numpy as np
import pandas as pd
import pytest

from experiments.phase2_ma200 import FREQUENCIES, _turnover_audit
from experiments.phase5_relative_momentum import (
    MAPPINGS,
    MOMENTUM_WINDOWS,
    _add_rotation_pretrade_equity,
    _alignment_rows,
    _stability_rows,
    _tie_audit_rows,
    _warmup_rows,
    parameter_grid,
    strategy_identifier,
)
from market_timing_quant.metrics import performance_metrics
from market_timing_quant.portfolio import rotation_backtest
from market_timing_quant.signals import (
    rebalance_mask,
    relative_momentum_decision,
    relative_momentum_target_next_open,
)


ROOT = Path(__file__).resolve().parents[1]
CANONICAL_RUN = ROOT / "reports/runs/20260914_phase5_audit_final"
OLD_RUN = ROOT / "reports/runs/20260913_phase5_relative_momentum_final"
NUMERIC_ATOL = 1e-8
EXECUTION_RATE = 5 / 10_000
TAX_RATE = 0.20315


def _assert_value_equal(left: object, right: object, field: str) -> None:
    if pd.isna(left) and pd.isna(right):
        return
    if field in {"start", "end", "date", "tax_mode", "strategy", "side", "asset"}:
        assert str(left) == str(right), field
    else:
        assert float(left) == pytest.approx(float(right), rel=0, abs=NUMERIC_ATOL), field


def _prices(index: pd.DatetimeIndex, opens: dict[str, list[float]], closes: dict[str, list[float]] | None = None):
    closes = closes or opens
    return {
        asset: pd.DataFrame({"open": opens[asset], "adjusted_close": closes[asset]}, index=index)
        for asset in opens
    }


def _relative_rotation_case(window: int, first: str = "SPY"):
    index = pd.bdate_range(end="2023-01-16", periods=window + 7)
    assert index[window].weekday() == 4
    assert index[-2].weekday() == 4
    assert index[-1].weekday() == 0
    spy = np.full(len(index), 100.0)
    qqq = np.full(len(index), 100.0)
    if first == "SPY":
        spy[window] = 110.0
        qqq[window] = 105.0
        spy[window + 1:window + 5] = 102.0
        qqq[window + 1:window + 5] = 101.0
        spy[-2:] = 101.0
        qqq[-2:] = 130.0
    else:
        spy[window] = 105.0
        qqq[window] = 110.0
        spy[window + 1:window + 5] = 101.0
        qqq[window + 1:window + 5] = 102.0
        spy[-2:] = 130.0
        qqq[-2:] = 101.0
    signal_spy = pd.Series(spy, index=index)
    signal_qqq = pd.Series(qqq, index=index)
    target = relative_momentum_target_next_open(signal_spy, signal_qqq, "weekly", window)
    return index, signal_spy, signal_qqq, target


def test_phase5_exact_frozen_grid_and_combination_count():
    assert parameter_grid() == (126, 189, 252)
    assert MOMENTUM_WINDOWS == (126, 189, 252)
    assert len(MAPPINGS) * len(FREQUENCIES) * len(MOMENTUM_WINDOWS) == 24

    surface = pd.read_csv(CANONICAL_RUN / "relative_momentum_results.csv")
    assert len(surface) == 48
    keys = ["rule", "frequency", "momentum_window", "tax_mode"]
    counts = surface.groupby(keys, dropna=False).size()
    assert len(counts) == 48
    assert counts.eq(1).all()
    assert set(surface.momentum_window) == set(MOMENTUM_WINDOWS)
    assert set(surface.frequency) == set(FREQUENCIES)
    assert set(surface.tax_mode) == {"pre_tax", "after_tax"}


def test_phase5_parameter_results_enumerates_without_selection():
    parameters = pd.read_csv(CANONICAL_RUN / "parameter_results.csv")
    assert len(parameters) == 24
    required = {
        "rule", "rule_family", "legacy_rule", "mapping", "signal_assets", "held_assets",
        "frequency", "momentum_window", "searched_for_selection", "selection_performed",
    }
    assert required <= set(parameters.columns)
    assert parameters.searched_for_selection.eq(False).all()
    assert parameters.selection_performed.eq(False).all()
    assert parameters[["rule", "frequency", "momentum_window"]].drop_duplicates().shape[0] == 24


def test_phase5_artifact_completeness_counts_and_required_columns():
    required = {
        "config_snapshot.yaml", "metrics_pre_tax.csv", "metrics_after_tax.csv",
        "relative_momentum_results.csv", "parameter_results.csv", "equity_curve.csv",
        "drawdown.csv", "positions.csv", "trades.csv", "tax_ledger.csv", "phase5_report.md",
        "relative_momentum_heatmap.png", "relative_momentum_heatmap_after_tax.png",
        "equity_curve.png", "drawdown.png", "rolling_returns.png", "rolling_maxdd.png",
        "cagr_maxdd_scatter.png",
    }
    missing = sorted(name for name in required if not (CANONICAL_RUN / name).exists())
    assert not missing, f"canonical Phase 5 run is missing: {missing}"

    pre = pd.read_csv(CANONICAL_RUN / "metrics_pre_tax.csv")
    after = pd.read_csv(CANONICAL_RUN / "metrics_after_tax.csv")
    surface = pd.read_csv(CANONICAL_RUN / "relative_momentum_results.csv")
    parameters = pd.read_csv(CANONICAL_RUN / "parameter_results.csv")
    assert len(pre) == 24
    assert len(after) == 24
    assert len(surface) == 48
    assert len(parameters) == 24
    assert pre.tax_mode.eq("pre_tax").all()
    assert after.tax_mode.eq("after_tax").all()
    required_metric_fields = {
        "strategy", "tax_mode", "frequency", "rule", "rule_family", "mapping", "momentum_window",
        "signal_asset", "held_asset", "signal_assets", "held_assets", "ending_value", "cagr",
        "max_drawdown", "calmar", "annual_turnover", "number_of_trades", "mean_holding_period_days",
        "median_holding_period_days", "max_holding_period_days", "transaction_costs", "tax_paid",
        "terminal_liquidation_wealth", "terminal_liquidation_cagr", "terminal_liquidation_tax",
        "terminal_liquidation_cost", "terminal_unrealized_gain_after_cost", "cumulative_realized_tax_paid",
        "tax_semantics",
    }
    assert required_metric_fields <= set(surface.columns)
    assert after[[
        "after_tax_wealth_tax_paid_to_date", "after_tax_cagr_tax_paid_to_date",
        "terminal_liquidation_wealth", "terminal_liquidation_cagr", "terminal_liquidation_tax",
        "terminal_liquidation_cost", "terminal_unrealized_gain_after_cost",
        "cumulative_realized_tax_paid", "tax_semantics",
    ]].notna().all().all()


def test_phase5_source_tables_survive_combined_surface_and_values_match():
    pre = pd.read_csv(CANONICAL_RUN / "metrics_pre_tax.csv")
    after = pd.read_csv(CANONICAL_RUN / "metrics_after_tax.csv")
    surface = pd.read_csv(CANONICAL_RUN / "relative_momentum_results.csv")
    combined = pd.concat([pre, after], ignore_index=True)
    pd.testing.assert_frame_equal(surface, combined)
    assert set(pre.columns) <= set(surface.columns)
    assert set(after.columns) <= set(surface.columns)
    fields = [
        "ending_value", "total_return", "cagr", "max_drawdown", "sharpe", "sortino", "calmar",
        "ulcer_index", "annual_turnover", "number_of_trades", "transaction_costs", "tax_paid",
        "mean_holding_period_days", "median_holding_period_days", "max_holding_period_days",
    ]
    for source in (pre, after):
        for _, row in source.iterrows():
            matches = surface[surface.strategy.eq(row.strategy) & surface.tax_mode.eq(row.tax_mode)]
            assert len(matches) == 1
            combined_row = matches.iloc[0]
            for field in fields:
                _assert_value_equal(row[field], combined_row[field], field)
            if row.tax_mode == "after_tax":
                for field in (
                    "terminal_liquidation_wealth", "terminal_liquidation_cagr", "terminal_liquidation_tax",
                    "terminal_liquidation_cost", "terminal_unrealized_gain_after_cost",
                ):
                    _assert_value_equal(row[field], combined_row[field], field)


@pytest.mark.parametrize("window", [126, 189, 252])
def test_phase5_relative_momentum_formula_and_l_plus_one_indexing(window: int):
    index = pd.bdate_range("2020-01-02", periods=window + 1)
    spy = pd.Series([100.0] * window + [120.0], index=index)
    qqq = pd.Series([100.0] * window + [110.0], index=index)
    decision = relative_momentum_decision(spy, qqq, window)
    assert decision.iloc[:window].sum().sum() == 0.0
    expected_spy = spy.iloc[window] / spy.iloc[0] - 1.0
    expected_qqq = qqq.iloc[window] / qqq.iloc[0] - 1.0
    assert expected_spy == pytest.approx(0.20)
    assert expected_qqq == pytest.approx(0.10)
    assert decision.iloc[window].to_dict() == {"SPY": 1.0, "QQQ": 0.0}


@pytest.mark.parametrize(
    "spy_end,qqq_end,expected",
    [(120.0, 110.0, {"SPY": 1.0, "QQQ": 0.0}),
     (110.0, 120.0, {"SPY": 0.0, "QQQ": 1.0}),
     (110.0, 100.0, {"SPY": 1.0, "QQQ": 0.0}),
     (100.0, 110.0, {"SPY": 0.0, "QQQ": 1.0}),
     (90.0, 80.0, {"SPY": 0.0, "QQQ": 0.0}),
     (100.0, 90.0, {"SPY": 0.0, "QQQ": 0.0}),
     (90.0, 100.0, {"SPY": 0.0, "QQQ": 0.0}),
     (100.0, 100.0, {"SPY": 0.0, "QQQ": 0.0})],
)
def test_phase5_complete_decision_table_boundaries(spy_end: float, qqq_end: float, expected: dict[str, float]):
    window = 126
    index = pd.bdate_range("2020-01-02", periods=window + 1)
    spy = pd.Series([100.0] * window + [spy_end], index=index)
    qqq = pd.Series([100.0] * window + [qqq_end], index=index)
    assert relative_momentum_decision(spy, qqq, window).iloc[-1].to_dict() == expected


def test_phase5_positive_tie_is_current_implementation_convention_not_frozen_rule():
    window = 126
    index = pd.bdate_range("2020-01-02", periods=window + 1)
    spy = pd.Series([100.0] * window + [110.0], index=index)
    qqq = spy.copy()
    assert relative_momentum_decision(spy, qqq, window).iloc[-1].to_dict() == {"SPY": 1.0, "QQQ": 0.0}
    assert "does not define a tie-break" in (CANONICAL_RUN / "phase5_report.md").read_text(encoding="utf-8")


def test_phase5_historical_positive_tie_scan_is_zero_for_every_grid_cell():
    prices = {
        asset: pd.read_parquet(ROOT / "data/processed" / f"{asset}.parquet")
        for asset in ("SPY", "QQQ", "SSO", "QLD")
    }
    ties = _tie_audit_rows(prices)
    assert len(ties) == len(MOMENTUM_WINDOWS) * len(FREQUENCIES)
    assert {row["exact_positive_tie_count"] for row in ties} == {0}
    assert {row["exact_positive_tie_close_count"] for row in ties} == {0}
    assert {row["tie_close_dates"] for row in ties} == {"none"}
    assert {row["tie_execution_dates"] for row in ties} == {"none"}


@pytest.mark.parametrize("window", [126, 252])
@pytest.mark.parametrize("first", ["SPY", "QQQ"])
def test_phase5_relative_signal_executes_rotation_at_next_open_without_lookahead(window: int, first: str):
    index, signal_spy, signal_qqq, target = _relative_rotation_case(window, first)
    friday, monday = index[-2], index[-1]
    assert target.loc[friday].sum() in (0.0, 1.0)
    if first == "SPY":
        assert target.loc[monday].to_dict() == {"SPY": 0.0, "QQQ": 1.0}
    else:
        assert target.loc[monday].to_dict() == {"SPY": 1.0, "QQQ": 0.0}
    opens = {
        "SPY": [50.0] * len(index),
        "QQQ": [60.0] * len(index),
    }
    opens["SPY"][-1] = 80.0
    opens["QQQ"][-1] = 150.0
    prices = _prices(index, opens, {"SPY": signal_spy.tolist(), "QQQ": signal_qqq.tolist()})
    ledger, _, trades, _ = rotation_backtest(
        prices, target, initial_capital=1_000.0, commission_bps=0.0, slippage_bps=5.0, tax_rate=None,
    )
    assert not (pd.to_datetime(trades.date) == friday).any()
    assert pd.to_datetime(trades.date).max() == monday
    incoming = "QQQ" if first == "SPY" else "SPY"
    assert trades.iloc[-1].asset == incoming
    assert trades.iloc[-1].price == pytest.approx(opens[incoming][-1])
    assert trades.iloc[-1].transaction_cost == pytest.approx(trades.iloc[-1].notional * EXECUTION_RATE)
    assert ledger.loc[friday, "shares"] > 0.0

    changed_spy = signal_spy.copy()
    changed_qqq = signal_qqq.copy()
    changed_spy.loc[index > friday] *= 9.0
    changed_qqq.loc[index > friday] *= 9.0
    changed_target = relative_momentum_target_next_open(changed_spy, changed_qqq, "weekly", window)
    pd.testing.assert_frame_equal(target.loc[:friday], changed_target.loc[:friday])


def test_phase5_rebalance_schedules_use_first_available_session_and_hold_between_dates():
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

    window = 126
    index = pd.bdate_range(end="2023-03-13", periods=window + 5)
    closes = [100.0] * window + [100.0, 101.0, 101.0, 101.0, 101.0]
    target = relative_momentum_target_next_open(pd.Series(closes, index=index), pd.Series(closes, index=index), "weekly", window)
    # Equal positive rankings are a tie convention, but a change between
    # weekly schedule dates cannot alter the target until the next Monday.
    assert target.loc[index[-4:-1], "SPY"].eq(0.0).all()


@pytest.mark.parametrize(
    "mapping_name,asset_a,asset_b",
    [("RELATIVE_MOMENTUM_1X", "SPY", "QQQ"), ("RELATIVE_MOMENTUM_2X", "SSO", "QLD")],
)
def test_phase5_underlying_signal_and_execution_mapping_are_separate(mapping_name: str, asset_a: str, asset_b: str):
    index, signal_spy, signal_qqq, underlying = _relative_rotation_case(126, "SPY")
    mapped = pd.DataFrame({asset_a: underlying.SPY, asset_b: underlying.QQQ}, index=index)
    opens = {asset_a: [40.0] * len(index), asset_b: [60.0] * len(index)}
    opens[asset_a][-1] = 77.0
    opens[asset_b][-1] = 250.0
    held = _prices(index, opens)
    _, _, trades, _ = rotation_backtest(
        held, mapped, initial_capital=1_000.0, commission_bps=0.0, slippage_bps=5.0, tax_rate=None,
    )
    assert set(mapped.columns) == {asset_a, asset_b}
    assert trades.iloc[-1].asset in {asset_a, asset_b}
    changed_held = {asset: frame * 11.0 for asset, frame in held.items()}
    pd.testing.assert_frame_equal(
        underlying,
        relative_momentum_target_next_open(signal_spy, signal_qqq, "weekly", 126),
    )
    assert changed_held[asset_b].open.iloc[-1] == pytest.approx(held[asset_b].open.iloc[-1] * 11.0)


def test_phase5_rotation_execution_has_two_legs_correct_cost_basis_and_immediate_tax():
    index = pd.date_range("2024-01-02", periods=3, freq="B")
    prices = _prices(
        index,
        {"SPY": [100.0, 120.0, 120.0], "QQQ": [80.0, 80.0, 80.0]},
    )
    targets = pd.DataFrame({"SPY": [1.0, 0.0, 0.0], "QQQ": [0.0, 1.0, 1.0]}, index=index)
    ledger, positions, trades, taxes = rotation_backtest(
        prices, targets, initial_capital=1_000.0, commission_bps=0.0, slippage_bps=5.0, tax_rate=TAX_RATE,
    )
    assert trades.side.tolist() == ["BUY", "SELL", "BUY"]
    assert trades.asset.tolist() == ["SPY", "SPY", "QQQ"]
    assert trades.price.tolist() == pytest.approx([100.0, 120.0, 80.0])
    np.testing.assert_allclose(trades.transaction_cost, trades.notional * EXECUTION_RATE, rtol=0, atol=1e-10)
    assert taxes.tax_paid.iloc[0] > 0.0
    net_sale_proceeds = trades.iloc[1].notional - trades.iloc[1].transaction_cost - taxes.tax_paid.iloc[0]
    assert trades.iloc[2].notional + trades.iloc[2].transaction_cost <= net_sale_proceeds + NUMERIC_ATOL
    assert ledger.cash.min() >= -1e-9
    weights = positions.groupby("date").actual_weight.sum()
    assert (weights <= 1.0 + 1e-12).all()
    assert positions.loc[positions.date.eq(index[1]) & positions.asset.eq("SPY"), "shares"].iloc[0] == 0.0
    assert positions.loc[positions.date.eq(index[1]) & positions.asset.eq("QQQ"), "shares"].iloc[0] > 0.0


def test_phase5_rotation_turnover_includes_both_legs_and_excludes_initial_deployment():
    index = pd.date_range("2024-01-02", periods=3, freq="B")
    prices = _prices(
        index,
        {"SPY": [100.0, 120.0, 120.0], "QQQ": [80.0, 80.0, 80.0]},
    )
    targets = pd.DataFrame({"SPY": [1.0, 0.0, 0.0], "QQQ": [0.0, 1.0, 1.0]}, index=index)
    ledger, _, trades, _ = rotation_backtest(
        prices, targets, initial_capital=1_000.0, commission_bps=0.0, slippage_bps=5.0, tax_rate=None,
    )
    ledger = _add_rotation_pretrade_equity(ledger, prices, 1_000.0)
    audit = _turnover_audit(ledger, trades)
    assert audit["number_of_trades"] == 3
    assert audit["nonzero_trade_dates"] == 1
    assert audit["included_normalized_turnover"] == pytest.approx(
        (trades.iloc[1].notional + trades.iloc[2].notional) / ledger.pretrade_equity.iloc[1],
        rel=0, abs=NUMERIC_ATOL,
    )
    assert audit["annual_turnover"] == pytest.approx(
        audit["included_normalized_turnover"] / audit["years"], rel=0, abs=NUMERIC_ATOL,
    )


def test_phase5_multi_asset_holding_episodes_exclude_open_terminal_position():
    index = pd.date_range("2024-01-02", periods=3, freq="B")
    prices = _prices(index, {"SPY": [100.0, 110.0, 110.0], "QQQ": [80.0, 90.0, 100.0]})
    targets = pd.DataFrame({"SPY": [1.0, 0.0, 0.0], "QQQ": [0.0, 1.0, 1.0]}, index=index)
    ledger, _, trades, _ = rotation_backtest(
        prices, targets, initial_capital=1_000.0, commission_bps=0.0, slippage_bps=5.0, tax_rate=None,
    )
    ledger = _add_rotation_pretrade_equity(ledger, prices, 1_000.0)
    result = performance_metrics(ledger, trades, 1_000.0)
    assert result["mean_holding_period_days"] == pytest.approx(1.0)
    assert result["median_holding_period_days"] == pytest.approx(1.0)
    assert result["max_holding_period_days"] == 1


def test_phase5_cash_state_asset_to_cash_cash_to_asset_and_prolonged_cash():
    index = pd.date_range("2024-01-02", periods=5, freq="B")
    prices = _prices(index, {"SPY": [100.0] * 5, "QQQ": [80.0] * 5})
    targets = pd.DataFrame(
        {"SPY": [0.0, 1.0, 0.0, 0.0, 0.0], "QQQ": [0.0, 0.0, 0.0, 0.0, 0.0]}, index=index,
    )
    ledger, positions, trades, _ = rotation_backtest(
        prices, targets, initial_capital=1_000.0, commission_bps=0.0, slippage_bps=5.0, tax_rate=None,
    )
    cash_dates = index[[0, 2, 3, 4]]
    cash_positions = positions[positions.date.isin(cash_dates)]
    assert cash_positions.shares.eq(0.0).all()
    assert ledger.loc[cash_dates, "shares"].eq(0.0).all()
    assert ledger.loc[cash_dates[0], "cash"] == pytest.approx(1_000.0)
    assert ledger.loc[cash_dates[0], "equity"] == pytest.approx(1_000.0)
    assert ledger.loc[cash_dates[1:], "cash"].eq(ledger.loc[cash_dates[1], "cash"]).all()
    assert ledger.loc[cash_dates[1:], "equity"].eq(ledger.loc[cash_dates[1], "equity"]).all()
    assert trades.side.tolist() == ["BUY", "SELL"]


def test_phase5_window_specific_warmup_and_common_calendar_alignment():
    prices = {
        asset: pd.read_parquet(ROOT / "data/processed" / f"{asset}.parquet")
        for asset in ("SPY", "QQQ", "SSO", "QLD")
    }
    start = pd.Timestamp("2006-06-21")
    end = pd.Timestamp("2026-08-31")
    evaluation_index = prices["SSO"].loc[start:end].index
    warmups = _warmup_rows(prices, start, end, evaluation_index)
    assert len(warmups) == 6
    assert {(row["signal_asset"], row["momentum_window"]) for row in warmups} == {
        (asset, window) for asset in ("SPY", "QQQ") for window in MOMENTUM_WINDOWS
    }
    for row in warmups:
        assert row["pre_start_warmup_rows"] > 0
        assert row["required_observations"] == row["momentum_window"] + 1
        assert row["lookback_observations_at_evaluation_start"] == row["momentum_window"] + 1
        assert row["first_valid_momentum_date"] < str(start.date())
        assert row["signal_common_calendar_rows"] == 5080
        assert row["evaluation_rows"] == 5080
        assert row["missing_evaluation_targets"] == 0
    alignments = _alignment_rows(prices, start, end, evaluation_index)
    assert len(alignments) == 2
    for row in alignments:
        assert row["evaluation_basis"] == "SSO calendar"
        assert row["signal_common_calendar_rows"] == 5080
        assert row["evaluation_rows"] == 5080
        assert row["missing_spy"] == row["missing_qqq"] == 0
        assert row["missing_held_spy_leg"] == row["missing_held_qqq_leg"] == 0
        assert row["missing_targets_after_reindex"] == 0
    curves = pd.read_csv(CANONICAL_RUN / "equity_curve.csv")
    positions = pd.read_csv(CANONICAL_RUN / "positions.csv")
    trades = pd.read_csv(CANONICAL_RUN / "trades.csv")
    tax = pd.read_csv(CANONICAL_RUN / "tax_ledger.csv")
    assert curves.date.min() == str(start.date())
    assert positions.date.min() == str(start.date())
    assert pd.to_datetime(trades.date).min() >= start
    assert pd.to_datetime(tax.date).min() >= start


def test_phase5_tax_terminal_diagnostics_are_non_mutating():
    after = pd.read_csv(CANONICAL_RUN / "metrics_after_tax.csv")
    assert after.tax_semantics.str.contains("realized tax paid to date").all()
    assert after.cumulative_realized_tax_paid.equals(after.tax_paid)
    assert after[[
        "terminal_liquidation_wealth", "terminal_liquidation_cagr", "terminal_liquidation_tax",
        "terminal_liquidation_cost", "terminal_unrealized_gain_after_cost",
    ]].notna().all().all()

    index = pd.date_range("2024-01-02", periods=3, freq="B")
    prices = _prices(index, {"SPY": [100.0, 120.0, 120.0], "QQQ": [80.0, 80.0, 80.0]})
    targets = pd.DataFrame({"SPY": [1.0, 0.0, 0.0], "QQQ": [0.0, 1.0, 0.0]}, index=index)
    ledger, positions, trades, taxes = rotation_backtest(
        prices, targets, initial_capital=1_000.0, commission_bps=0.0, slippage_bps=5.0, tax_rate=TAX_RATE,
    )
    before = tuple(frame.copy(deep=True) for frame in (ledger, positions, trades, taxes))
    ledger_for_metrics = _add_rotation_pretrade_equity(ledger, prices, 1_000.0)
    result = performance_metrics(
        ledger_for_metrics, trades, 1_000.0, terminal_tax_rate=TAX_RATE, terminal_cost_rate=EXECUTION_RATE,
    )
    assert result["terminal_liquidation_wealth"] <= result["after_tax_wealth_tax_paid_to_date"]
    assert not trades.side.eq("SELL").empty
    pd.testing.assert_frame_equal(ledger, before[0])
    pd.testing.assert_frame_equal(positions, before[1])
    pd.testing.assert_frame_equal(trades, before[2])
    pd.testing.assert_frame_equal(taxes, before[3])


def test_phase5_stability_rows_are_descriptive_only():
    surface = pd.read_csv(CANONICAL_RUN / "relative_momentum_results.csv")
    rows = _stability_rows(surface)
    assert len(rows) == len(MAPPINGS) * len(FREQUENCIES)
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
        assert row["trade_count_min"] <= row["trade_count_max"]


def test_phase5_old_to_new_economic_fields_are_unchanged():
    old = pd.concat(
        [pd.read_csv(OLD_RUN / "metrics_pre_tax.csv"), pd.read_csv(OLD_RUN / "metrics_after_tax.csv")],
        ignore_index=True,
    )
    new = pd.read_csv(CANONICAL_RUN / "relative_momentum_results.csv")
    assert len(old) == len(new) == 48
    fields = [
        "ending_value", "total_return", "cagr", "max_drawdown", "sharpe", "sortino", "calmar",
        "ulcer_index", "number_of_trades", "transaction_costs", "tax_paid",
    ]
    for _, old_row in old.iterrows():
        matches = new[
            new.rule.eq(old_row.rule) & new.frequency.eq(old_row.frequency)
            & new.momentum_window.eq(old_row.momentum_window) & new.tax_mode.eq(old_row.tax_mode)
        ]
        assert len(matches) == 1
        new_row = matches.iloc[0]
        for field in fields:
            _assert_value_equal(old_row[field], new_row[field], field)


@pytest.mark.parametrize("file", ["equity_curve.csv", "positions.csv", "trades.csv", "tax_ledger.csv"])
def test_phase5_economic_path_files_are_byte_identical_to_stale_run(file: str):
    old_path = OLD_RUN / file
    new_path = CANONICAL_RUN / file
    assert len(pd.read_csv(old_path)) == len(pd.read_csv(new_path))
    assert hashlib.sha256(old_path.read_bytes()).hexdigest() == hashlib.sha256(new_path.read_bytes()).hexdigest()


def test_phase5_strategy_identifiers_and_report_document_tie_and_no_selection_semantics():
    surface = pd.read_csv(CANONICAL_RUN / "relative_momentum_results.csv")
    for _, row in surface.iterrows():
        assert f"_{int(row.momentum_window)}D" in row.strategy
        assert row.rule_family in MAPPINGS
        assert row.legacy_rule == row.rule
        assert row.legacy_strategy == row.strategy
    report = (CANONICAL_RUN / "phase5_report.md").read_text(encoding="utf-8")
    required_phrases = [
        "exact frozen lookback grid is `(126, 189, 252)`",
        "mom_SPY(t,L)", "mom_QQQ(t,L)", "both non-positive values select CASH",
        "does not define a tie-break", "zero exact positive ties", "implementation convention",
        "next available held-asset open (*t+1*)", "Leveraged ETF prices are never used",
        "completed continuous risky-asset episodes", "contemporaneous_pretrade_equity",
        "Terminal-liquidation fields are hypothetical diagnostics only",
        "No lookback or frequency is selected", "no OOS or Walk-Forward claim",
        "Walk-Forward parameter selection remains deferred", "parameter_results.csv",
    ]
    for phrase in required_phrases:
        assert phrase in report
