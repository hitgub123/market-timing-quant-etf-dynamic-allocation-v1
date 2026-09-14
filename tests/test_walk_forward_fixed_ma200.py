from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import yaml

from experiments.phase2_ma200 import _add_pretrade_equity as phase2_add_pretrade_equity
from experiments.phase2_ma200 import _turnover_audit as phase2_turnover_audit
from experiments.walk_forward_fixed_ma200 import (
    FREQUENCIES,
    MA_WINDOW,
    STRATEGIES,
    _add_pretrade_equity,
    _alignment_rows,
    _episodes_attributed_to_fold,
    _fold_turnover_audit,
    _holding_stats,
    _segment_metrics,
    _turnover_audit,
    _warmup_rows,
)
from market_timing_quant.metrics import completed_holding_periods, performance_metrics
from market_timing_quant.portfolio import single_asset_timed_backtest
from market_timing_quant.signals import ma_trend_decision, trend_target_next_open


ROOT = Path(__file__).resolve().parents[1]
CANONICAL_RUN = ROOT / "reports/runs/20260914_oos_fixed_ma200_audit_final"
OLD_RUN = ROOT / "reports/runs/20260913_oos_fixed_ma200_final"
NUMERIC_ATOL = 1e-8
EXECUTION_RATE = 5 / 10_000
TAX_RATE = 0.20315


def _prices(index: pd.DatetimeIndex, opens: list[float], closes: list[float] | None = None) -> pd.DataFrame:
    adjusted_close = opens if closes is None else closes
    return pd.DataFrame({"open": opens, "adjusted_close": adjusted_close}, index=index)


def _assert_value_equal(left: object, right: object, field: str) -> None:
    if pd.isna(left) and pd.isna(right):
        return
    if field in {"start", "end", "date", "tax_mode", "strategy", "rule", "frequency"}:
        assert str(left) == str(right), field
    else:
        assert float(left) == pytest.approx(float(right), rel=0, abs=NUMERIC_ATOL), field


def _read_metrics(path: Path) -> pd.DataFrame:
    return pd.concat(
        [pd.read_csv(path / "metrics_pre_tax.csv"), pd.read_csv(path / "metrics_after_tax.csv")],
        ignore_index=True,
    )


def test_fixed_strategy_universe_and_frequency_grid_are_exact():
    assert MA_WINDOW == 200
    assert STRATEGIES == {
        "QQQ_MA200_QQQ": ("QQQ", "QQQ"),
        "QQQ_MA200_QLD": ("QQQ", "QLD"),
        "SPY_MA200_SSO": ("SPY", "SSO"),
    }
    assert FREQUENCIES == ("weekly", "monthly", "bimonthly", "quarterly")
    metrics = _read_metrics(CANONICAL_RUN)
    assert len(metrics) == 24
    assert set(metrics.ma_window) == {200}
    assert metrics.groupby(["rule", "frequency", "tax_mode"], dropna=False).size().eq(1).all()
    assert len(metrics.groupby(["rule", "frequency", "tax_mode"])) == 24


def test_parameter_report_is_fixed_enumeration_without_selection():
    parameters = pd.read_csv(CANONICAL_RUN / "parameter_results.csv")
    assert len(parameters) == 1
    assert parameters.ma_window.eq(200).all()
    for field in ("selected", "searched_for_selection", "selection_performed"):
        assert field in parameters
        assert parameters[field].eq(False).all()
    report = (CANONICAL_RUN / "oos_report.md").read_text(encoding="utf-8").lower()
    assert "fixed-rule chronological oos — ma200" in report
    assert "no optimization" in report
    assert "best" not in report
    assert "optimal" not in report
    assert "selected parameter" not in report


def test_oos_period_is_2013_through_latest_2026_ytd_and_continuous():
    folds = pd.read_csv(CANONICAL_RUN / "walk_forward_folds.csv")
    assert len(folds) == 14
    assert folds.test_year.tolist() == list(range(2013, 2027))
    assert folds.test_start.iloc[0] == "2013-01-02"
    assert folds.test_end.iloc[-1] == "2026-08-31"
    curves = pd.read_csv(CANONICAL_RUN / "equity_curve.csv")
    dates = pd.to_datetime(curves.date)
    assert dates.min() == pd.Timestamp("2013-01-02")
    assert dates.max() == pd.Timestamp("2026-08-31")
    for (strategy, mode), group in curves.groupby(["strategy", "tax_mode"]):
        assert group.date.is_monotonic_increasing
        assert group.date.duplicated().sum() == 0
        assert len(group) == 3436


def test_close_t_signal_uses_next_eligible_open_and_gap_price():
    index = pd.bdate_range(end="2023-01-09", periods=MA_WINDOW + 1)
    prices = _prices(index, [100.0] * (MA_WINDOW - 1) + [77.0, 150.0], [100.0] * (MA_WINDOW - 1) + [101.0, 101.0])
    target = trend_target_next_open(prices.adjusted_close, "weekly", MA_WINDOW)
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
    assert ledger.loc[friday, "shares"] == 0.0


def test_future_data_mutation_cannot_change_prior_targets_or_trades():
    index = pd.bdate_range("2020-01-02", periods=MA_WINDOW + 80)
    close = pd.Series(np.linspace(100.0, 130.0, len(index)), index=index)
    cutoff = index[MA_WINDOW + 35]
    changed = close.copy()
    changed.loc[index > cutoff] *= 9.0
    original = trend_target_next_open(close, "weekly", MA_WINDOW)
    mutated = trend_target_next_open(changed, "weekly", MA_WINDOW)
    pd.testing.assert_series_equal(original.loc[:cutoff], mutated.loc[:cutoff])
    prices = _prices(index, close.tolist())
    altered_prices = prices.copy()
    altered_prices.loc[index > cutoff, ["open", "adjusted_close"]] *= 9.0
    _, _, trades_a, _ = single_asset_timed_backtest(
        prices, original, initial_capital=1_000.0, commission_bps=0.0, slippage_bps=5.0, tax_rate=None,
    )
    _, _, trades_b, _ = single_asset_timed_backtest(
        altered_prices, mutated, initial_capital=1_000.0, commission_bps=0.0, slippage_bps=5.0, tax_rate=None,
    )
    assert trades_a.loc[pd.to_datetime(trades_a.date) <= cutoff].reset_index(drop=True).equals(
        trades_b.loc[pd.to_datetime(trades_b.date) <= cutoff].reset_index(drop=True)
    )


def test_cross_year_position_and_tax_basis_are_continuous_without_boundary_trade():
    index = pd.DatetimeIndex(["2024-12-30", "2024-12-31", "2025-01-02", "2025-01-03"])
    prices = _prices(index, [100.0, 110.0, 120.0, 130.0])
    target = pd.Series([1.0, 1.0, 1.0, 0.0], index=index)
    ledger, positions, trades, taxes = single_asset_timed_backtest(
        prices, target, initial_capital=1_000.0, commission_bps=0.0,
        slippage_bps=5.0, tax_rate=TAX_RATE,
    )
    assert len(trades) == 2
    assert trades.side.tolist() == ["BUY", "SELL"]
    assert pd.Timestamp(trades.date.iloc[1]) == index[-1]
    assert ledger.loc[index[1], "shares"] > 0
    assert ledger.loc[index[2], "shares"] > 0
    assert len(taxes) == 1 and pd.Timestamp(taxes.date.iloc[0]) == index[-1]
    assert taxes.cumulative_tax_paid.iloc[0] > 0
    assert positions.date.min() == index[0]
    assert not trades.date.astype(str).eq("2025-01-02").any()


def test_fold_turnover_uses_open_pretrade_denominator_and_excludes_only_true_initial_buy():
    index = pd.DatetimeIndex(["2024-12-30", "2024-12-31", "2025-01-02", "2025-01-03"])
    prices = _prices(index, [100.0, 120.0, 80.0, 110.0])
    target = pd.Series([1.0, 1.0, 0.0, 1.0], index=index)
    ledger, _, trades, _ = single_asset_timed_backtest(
        prices, target, initial_capital=1_000.0, commission_bps=0.0,
        slippage_bps=5.0, tax_rate=None,
    )
    reporting = _add_pretrade_equity(ledger, prices, 1_000.0)
    phase2 = phase2_turnover_audit(reporting, trades)
    local = _turnover_audit(reporting, trades)
    assert local["annual_turnover"] == pytest.approx(phase2["annual_turnover"], rel=0, abs=NUMERIC_ATOL)
    initial_date = pd.Timestamp(trades.date.min())
    dec = _fold_turnover_audit(reporting, trades, index[0], index[1], initial_date)
    jan = _fold_turnover_audit(reporting, trades, index[2], index[3], initial_date)
    assert dec["annual_turnover"] == 0.0
    expected_jan = float(trades.loc[trades.date.astype(str).isin([str(index[2].date()), str(index[3].date())]), "notional"].abs().sum())
    # The first trade in January is a SELL and the second is a genuine BUY.
    expected_jan_normalized = float(
        sum(
            float(row.notional) / float(reporting.loc[pd.Timestamp(row.date), "pretrade_equity"])
            for row in trades.itertuples(index=False)
            if pd.Timestamp(row.date) >= index[2]
        )
    )
    assert expected_jan > 0
    assert jan["included_normalized_turnover"] == pytest.approx(expected_jan_normalized, rel=0, abs=NUMERIC_ATOL)
    assert jan["number_of_trades"] == 2


def test_completed_holding_episode_crosses_fold_boundary_and_is_attributed_by_exit():
    index = pd.DatetimeIndex(["2024-12-30", "2024-12-31", "2025-01-02", "2025-01-03", "2025-01-06"])
    ledger = pd.DataFrame({
        "equity": [1000., 1100., 1200., 1300., 1000.],
        "cash": [1000., 0., 0., 0., 1000.],
        "shares": [0., 10., 10., 10., 0.],
        "tax_paid": 0.,
        "daily_return": 0.,
        "pretrade_equity": 1000.,
    }, index=index)
    episodes = completed_holding_periods(ledger)
    assert len(episodes) == 1
    assert episodes.trading_days.iloc[0] == 3
    assert _episodes_attributed_to_fold(ledger, pd.Timestamp("2024-12-30"), pd.Timestamp("2024-12-31")).empty
    attributed = _episodes_attributed_to_fold(ledger, pd.Timestamp("2025-01-01"), pd.Timestamp("2025-01-06"))
    assert len(attributed) == 1
    assert _holding_stats(attributed)["mean_holding_period_days"] == 3


def test_fold_metrics_do_not_use_fold_duration_as_holding_period():
    index = pd.DatetimeIndex(["2024-12-30", "2024-12-31", "2025-01-02", "2025-01-03", "2025-01-06"])
    ledger = pd.DataFrame({
        "equity": [1000., 1100., 1200., 1300., 1000.],
        "cash": [1000., 0., 0., 0., 1000.],
        "shares": [0., 10., 10., 10., 0.],
        "tax_paid": 0.,
        "daily_return": [0., .1, 1200/1100-1, 1300/1200-1, 1000/1300-1],
        "pretrade_equity": 1000.,
    }, index=index)
    trades = pd.DataFrame({
        "date": [index[1], index[-1]], "asset": "RISK", "side": ["BUY", "SELL"],
        "shares": [10., 10.], "price": [100., 100.], "notional": [1000., 1000.],
        "transaction_cost": 0., "realized_gain": [0., 0.],
    })
    fold_open = _segment_metrics(ledger, trades, index[0], index[2], 1_000., "S", "pre_tax", 2024, index[1])
    fold_exit = _segment_metrics(ledger, trades, index[2], index[-1], 1_200., "S", "pre_tax", 2025, index[1])
    assert pd.isna(fold_open["mean_holding_period_days"])
    assert fold_exit["mean_holding_period_days"] == 3
    assert fold_exit["max_holding_period_days"] == 3


def test_fold_boundaries_have_no_terminal_liquidation_fields():
    fold = pd.read_csv(CANONICAL_RUN / "oos_fold_metrics.csv")
    assert len(fold) == 336
    for field in ("terminal_liquidation_wealth", "terminal_liquidation_cagr", "terminal_liquidation_tax", "terminal_liquidation_cost"):
        assert field in fold
        assert fold[field].isna().all()


def test_terminal_liquidation_diagnostics_are_non_mutating():
    index = pd.date_range("2024-01-02", periods=2, freq="B")
    prices = _prices(index, [100.0, 200.0])
    target = pd.Series([1.0, 1.0], index=index)
    ledger, _, trades, taxes = single_asset_timed_backtest(
        prices, target, initial_capital=1_000.0, commission_bps=0.0,
        slippage_bps=5.0, tax_rate=TAX_RATE,
    )
    before = (ledger.copy(deep=True), trades.copy(deep=True), taxes.copy(deep=True))
    result = performance_metrics(
        _add_pretrade_equity(ledger, prices, 1_000.0), trades, 1_000.0,
        terminal_tax_rate=TAX_RATE, terminal_cost_rate=EXECUTION_RATE,
    )
    assert result["terminal_liquidation_wealth"] < result["after_tax_wealth_tax_paid_to_date"]
    assert not trades.side.eq("SELL").any()
    pd.testing.assert_frame_equal(ledger, before[0])
    pd.testing.assert_frame_equal(trades, before[1])
    pd.testing.assert_frame_equal(taxes, before[2])


def test_tax_semantics_and_terminal_fields_are_present_in_after_tax_rows():
    after = pd.read_csv(CANONICAL_RUN / "metrics_after_tax.csv")
    assert after.tax_mode.eq("after_tax").all()
    assert after.tax_semantics.str.contains("realized tax paid to date").all()
    assert after.cumulative_realized_tax_paid.equals(after.tax_paid)
    fields = [
        "after_tax_wealth_tax_paid_to_date", "after_tax_cagr_tax_paid_to_date",
        "terminal_liquidation_wealth", "terminal_liquidation_cagr", "terminal_liquidation_tax",
        "terminal_liquidation_cost", "terminal_unrealized_gain_after_cost",
    ]
    assert after[fields].notna().all().all()


def test_fold_tax_diagnostics_distinguish_fold_tax_from_cumulative_tax():
    fold = pd.read_csv(CANONICAL_RUN / "oos_fold_metrics.csv")
    stitched = pd.read_csv(CANONICAL_RUN / "oos_results.csv")
    tax_ledger = pd.read_csv(CANONICAL_RUN / "tax_ledger.csv")
    tax_ledger["date"] = pd.to_datetime(tax_ledger["date"])
    assert {"fold_realized_tax_paid", "cumulative_realized_tax_paid"} <= set(fold.columns)

    for strategy in stitched.strategy.unique():
        for mode in ("pre_tax", "after_tax"):
            rows = fold[(fold.strategy == strategy) & (fold.tax_mode == mode)].sort_values("test_year")
            assert len(rows) == 14
            if mode == "pre_tax":
                assert rows.fold_realized_tax_paid.eq(0.0).all()
                assert rows.cumulative_realized_tax_paid.eq(0.0).all()
                continue
            actual = tax_ledger[
                (tax_ledger.strategy == strategy) & (tax_ledger.tax_mode == mode)
            ]
            per_year = actual.groupby(actual.date.dt.year).tax_paid.sum()
            expected_fold = rows.test_year.map(per_year).fillna(0.0).to_numpy(dtype=float)
            np.testing.assert_allclose(
                rows.fold_realized_tax_paid.to_numpy(dtype=float), expected_fold,
                rtol=0, atol=NUMERIC_ATOL,
            )
            cumulative = rows.fold_realized_tax_paid.cumsum().to_numpy(dtype=float)
            np.testing.assert_allclose(
                rows.cumulative_realized_tax_paid.to_numpy(dtype=float), cumulative,
                rtol=0, atol=NUMERIC_ATOL,
            )
            assert rows.cumulative_realized_tax_paid.is_monotonic_increasing
            stitched_row = stitched[
                (stitched.strategy == strategy) & (stitched.tax_mode == mode)
            ].iloc[0]
            assert rows.fold_realized_tax_paid.sum() == pytest.approx(
                stitched_row.tax_paid, rel=0, abs=NUMERIC_ATOL,
            )
            assert rows.cumulative_realized_tax_paid.iloc[-1] == pytest.approx(
                stitched_row.cumulative_realized_tax_paid, rel=0, abs=NUMERIC_ATOL,
            )
            assert rows.cumulative_realized_tax_paid.iloc[-1] == pytest.approx(
                stitched_row.tax_paid, rel=0, abs=NUMERIC_ATOL,
            )


def test_warmup_and_calendar_alignment_are_explicit():
    prices = {asset: pd.read_parquet(ROOT / "data/processed" / f"{asset}.parquet") for asset in ("SPY", "QQQ", "SSO", "QLD")}
    folds = pd.read_csv(CANONICAL_RUN / "walk_forward_folds.csv")
    start, end = pd.Timestamp(folds.test_start.iloc[0]), pd.Timestamp(folds.test_end.iloc[-1])
    warmups = _warmup_rows(prices, start, end)
    assert {row["signal_asset"] for row in warmups} == {"QQQ", "SPY"}
    for row in warmups:
        assert row["ma_window"] == MA_WINDOW
        assert row["pre_start_warmup_rows"] > 0
        assert row["lookback_observations_at_start"] == MA_WINDOW
        assert pd.Timestamp(row["first_valid_ma_date"]) < start
        decision = ma_trend_decision(prices[row["signal_asset"]].adjusted_close, MA_WINDOW)
        assert decision.iloc[: MA_WINDOW - 1].eq(0.0).all()
    alignments = _alignment_rows(prices, start, end)
    assert len(alignments) == 3
    assert {row["missing_aligned_targets"] for row in alignments} == {0}
    assert {row["common_evaluation_rows"] for row in alignments} == {3436}


def test_artifact_completeness_counts_and_required_columns():
    required = {
        "config_snapshot.yaml", "metrics_pre_tax.csv", "metrics_after_tax.csv", "oos_results.csv",
        "oos_fold_metrics.csv", "parameter_results.csv", "walk_forward_folds.csv", "equity_curve.csv",
        "drawdown.csv", "positions.csv", "trades.csv", "tax_ledger.csv", "oos_report.md",
        "fixed_ma200_oos_audit_diff.md", "equity_curve.png", "drawdown.png", "rolling_returns.png",
        "rolling_maxdd.png", "cagr_maxdd_scatter.png",
    }
    missing = sorted(name for name in required if not (CANONICAL_RUN / name).exists())
    assert not missing, missing
    pre = pd.read_csv(CANONICAL_RUN / "metrics_pre_tax.csv")
    after = pd.read_csv(CANONICAL_RUN / "metrics_after_tax.csv")
    combined = pd.read_csv(CANONICAL_RUN / "oos_results.csv")
    fold = pd.read_csv(CANONICAL_RUN / "oos_fold_metrics.csv")
    assert len(pre) == len(after) == 12
    assert len(combined) == 24
    assert len(fold) == 336
    required_metric_fields = {
        "strategy", "rule", "signal_asset", "held_asset", "frequency", "ma_window", "tax_mode",
        "ending_value", "total_return", "cagr", "annualized_volatility", "max_drawdown", "sharpe",
        "sortino", "calmar", "ulcer_index", "number_of_trades", "annual_turnover",
        "transaction_costs", "tax_paid", "mean_holding_period_days", "median_holding_period_days",
        "max_holding_period_days", "terminal_liquidation_wealth", "terminal_liquidation_cagr",
        "terminal_liquidation_tax", "terminal_liquidation_cost", "terminal_unrealized_gain_after_cost",
        "cumulative_realized_tax_paid", "tax_semantics",
    }
    assert required_metric_fields <= set(combined.columns)
    assert {"fold_realized_tax_paid", "cumulative_realized_tax_paid"} <= set(fold.columns)


def test_source_metric_tables_match_stitched_rows_and_all_columns_survive():
    pre = pd.read_csv(CANONICAL_RUN / "metrics_pre_tax.csv")
    after = pd.read_csv(CANONICAL_RUN / "metrics_after_tax.csv")
    combined = pd.read_csv(CANONICAL_RUN / "oos_results.csv")
    assert set(pre.columns) <= set(combined.columns)
    assert set(after.columns) <= set(combined.columns)
    fields = [
        "ending_value", "total_return", "cagr", "annualized_volatility", "max_drawdown", "sharpe",
        "sortino", "calmar", "ulcer_index", "number_of_trades", "annual_turnover", "transaction_costs",
        "tax_paid", "mean_holding_period_days", "median_holding_period_days", "max_holding_period_days",
    ]
    for source in (pre, after):
        for _, row in source.iterrows():
            match = combined[combined.strategy.eq(row.strategy) & combined.tax_mode.eq(row.tax_mode)]
            assert len(match) == 1
            for field in fields:
                _assert_value_equal(row[field], match.iloc[0][field], field)
            if row.tax_mode == "after_tax":
                for field in ("terminal_liquidation_wealth", "terminal_liquidation_cagr", "terminal_liquidation_tax", "terminal_liquidation_cost"):
                    _assert_value_equal(row[field], match.iloc[0][field], field)


def test_old_to_new_economic_metrics_are_unchanged_and_reporting_fields_are_corrected():
    old = _read_metrics(OLD_RUN)
    new = pd.read_csv(CANONICAL_RUN / "oos_results.csv")
    fields = [
        "ending_value", "total_return", "cagr", "annualized_volatility", "max_drawdown", "sharpe",
        "sortino", "calmar", "ulcer_index", "number_of_trades", "transaction_costs", "tax_paid",
    ]
    assert len(old) == len(new) == 24
    for _, old_row in old.iterrows():
        match = new[new.strategy.eq(old_row.strategy) & new.tax_mode.eq(old_row.tax_mode)]
        assert len(match) == 1
        for field in fields:
            _assert_value_equal(old_row[field], match.iloc[0][field], field)
    assert new.mean_holding_period_days.notna().any()
    assert not new.mean_holding_period_days.eq(4989).any()


@pytest.mark.parametrize("filename", ["equity_curve.csv", "positions.csv", "trades.csv", "tax_ledger.csv"])
def test_economic_path_tables_are_byte_identical_to_old_run(filename: str):
    old_hash = hashlib.sha256((OLD_RUN / filename).read_bytes()).hexdigest()
    new_hash = hashlib.sha256((CANONICAL_RUN / filename).read_bytes()).hexdigest()
    assert old_hash == new_hash, filename


def test_raw_snapshot_hashes_match_immutable_manifest():
    manifest = yaml.safe_load((ROOT / "data/raw/manifest.yaml").read_text(encoding="utf-8"))
    sibling = ROOT.parent / "market-timing-quant"
    for asset in ("SPY", "QQQ", "SSO", "QLD"):
        source = manifest["sources"][asset]
        relative = Path(source["original_snapshot"])
        path = sibling / Path(*relative.parts[1:])
        assert path.exists(), path
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        assert digest == source["sha256"], asset


def test_audit_diff_declares_pass_and_path_integrity():
    diff = (CANONICAL_RUN / "fixed_ma200_oos_audit_diff.md").read_text(encoding="utf-8")
    assert "economic path" in diff.lower()
    assert "byte-identical" in diff.lower()
    assert diff.rstrip().endswith("FIXED MA200 CHRONOLOGICAL OOS AUDIT PASS")
