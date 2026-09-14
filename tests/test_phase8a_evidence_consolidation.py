"""Dedicated Phase 8A OOS evidence-consolidation regressions."""

from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np
import pandas as pd

from experiments.phase8a_evidence_consolidation import (
    FREQUENCIES,
    OOS_END,
    OOS_START,
    SOURCE_RUNS,
)


ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / "reports/runs/20260914_phase8a_oos_evidence_consolidation_final"
PHASE7A = ROOT / "reports/runs/20260913_phase7a_metrics_tax_audited_final"
PHASE7B = ROOT / "reports/runs/20260914_phase7b_turnover_audit_final"
FIXED = ROOT / "reports/runs/20260914_oos_fixed_ma200_audit_final"

COMMON_DATES = pd.DatetimeIndex(
    pd.to_datetime(pd.read_csv(FIXED / "equity_curve.csv").date).unique()
).sort_values()
REQUIRED_ARTIFACTS = (
    "oos_champion_table.csv",
    "benchmark_relative_metrics.csv",
    "complexity_comparison.csv",
    "canonical_source_manifest.csv",
    "phase8a_report.md",
    "aligned_daily_equity.csv",
    "aligned_daily_returns.csv",
)
METRIC_COLUMNS = (
    "start_date",
    "end_date",
    "ending_value",
    "cagr",
    "max_drawdown",
    "calmar",
    "sharpe",
    "sortino",
    "ulcer_index",
    "recovery_trading_days",
    "annual_turnover",
    "number_of_trades",
    "mean_holding_period_days",
    "median_holding_period_days",
    "max_holding_period_days",
    "transaction_costs",
    "realized_tax_paid",
    "after_tax_CAGR_tax_paid_to_date",
    "after_tax_ending_value_terminal_liquidation",
    "after_tax_CAGR_terminal_liquidation",
    "invested_session_pct",
    "cash_session_pct",
)
SOURCE_HASHES = {
    ("phase7a", "state_decisions.csv"): "228529085687af082df26d8a3a5e42826facacbd3fec4395d1339cfbf56be6d0",
    ("phase7a", "execution_targets.csv"): "d48dc37826f711db427ad7c4e5338b9048037d506f4289cc729d6afb3609005e",
    ("phase7a", "equity_curve.csv"): "836b8e14960752338cc8051adb342616402a23188747e8fe308022f8dc08359d",
    ("phase7a", "positions.csv"): "e3ffcd95c648decb9b8e1bac48bbdfefeafe5c8594d477d1952c075862d533c8",
    ("phase7a", "trades.csv"): "0e1da9c04712c8e0c7d115ce24235a603ae98ef03e6990b12db4c30f1adf08d8",
    ("phase7a", "tax_ledger.csv"): "7ba3546765876629bc3217a4a1efa09d1a7cb189df0582398b1153ee65205301",
    ("phase7b", "equity_curve.csv"): "c50093611649cfa379ba71498dcc58568a8ca4a6be780987a5287ad30f93cca0",
    ("phase7b", "positions.csv"): "f56dfa8f629fbac46b27725c799da8fdc733715bb92d9310e5c7f3e3225e8013",
    ("phase7b", "trades.csv"): "9a8e25ea5e79e291f06c7cf66b198bed1018d2bb231ddf7b83c2331a42d13b57",
    ("phase7b", "tax_ledger.csv"): "c6faf011c00d82608a1a0572edfc2c6eb3255d924e8052b7c7466e465a3f7b5a",
    ("fixed_ma200", "equity_curve.csv"): "8eb1176e05b1a5bd3da75fefebc4b6f99255d7468f442c781832857cef8fc404",
    ("fixed_ma200", "positions.csv"): "14fe3cc83160d13be49a3fe3542e5ab310d8b3dd0c8d1efddd66a601f67adbf0",
    ("fixed_ma200", "trades.csv"): "36fa8cf1d9837bcaf1f0b01c91bf2378866806ecaa3586439c65478ccf9905f1",
    ("fixed_ma200", "tax_ledger.csv"): "6ba2d9b423022ef59a11c5c445f8323b4bd3af6adfd484551086b3f4df80ff6c",
}


def _read(name: str) -> pd.DataFrame:
    return pd.read_csv(RUN / name)


def _assert_numeric_equal(left: pd.Series, right: pd.Series) -> None:
    np.testing.assert_allclose(
        pd.to_numeric(left),
        pd.to_numeric(right),
        rtol=0.0,
        # CSV float serialization can differ by a few ulps for large wealth
        # values while preserving the canonical economic result.
        atol=1e-8,
        equal_nan=True,
    )


def _source_rows(source: pd.DataFrame, strategy_id: str, frequency: str, tax_mode: str) -> pd.DataFrame:
    if strategy_id == "FIXED_MA200_QQQ_TO_QLD":
        return source.loc[
            source.held_asset.eq("QLD")
            & source.frequency.eq(frequency)
            & source.tax_mode.eq(tax_mode)
        ]
    if strategy_id == "PHASE7A_FIXED_FOUR_STATE":
        return source.loc[
            source.strategy.eq(f"PHASE7A_{frequency}")
            & source.frequency.eq(frequency)
            & source.tax_mode.eq(tax_mode)
            & source.start.eq(OOS_START.strftime("%Y-%m-%d"))
        ]
    if strategy_id == "PHASE7B_MODEL_A_SELECTED":
        return source.loc[
            source.model.eq("MODEL_A_QLD_TREND")
            & source.frequency.eq(frequency)
            & source.tax_mode.eq(tax_mode)
        ]
    if strategy_id == "PHASE7B_MODEL_B_SELECTED":
        return source.loc[
            source.model.eq("MODEL_B_FOUR_STATE")
            & source.frequency.eq(frequency)
            & source.tax_mode.eq(tax_mode)
        ]
    raise AssertionError(strategy_id)


def test_phase8a_artifact_completeness_and_expected_shape():
    for name in REQUIRED_ARTIFACTS:
        assert (RUN / name).is_file(), name
    champion = _read("oos_champion_table.csv")
    assert len(champion) == 34
    assert champion.strategy_id.nunique() == 6
    assert len(champion.loc[champion.frequency.isin(FREQUENCIES)]) == 32
    assert set(METRIC_COLUMNS).issubset(champion.columns)
    assert champion.loc[champion.frequency.isin(FREQUENCIES)].groupby(
        ["strategy_id", "frequency", "tax_mode"]
    ).size().eq(1).all()


def test_all_rows_use_accepted_canonical_source_run_ids_and_common_dates():
    champion = _read("oos_champion_table.csv")
    assert set(champion.source_run_id) == set(SOURCE_RUNS.values())
    assert champion.start_date.eq(OOS_START.strftime("%Y-%m-%d")).all()
    assert champion.end_date.eq(OOS_END.strftime("%Y-%m-%d")).all()
    manifest = _read("canonical_source_manifest.csv")
    assert set(manifest.source_run_id) == set(SOURCE_RUNS.values())
    assert manifest.sha256.str.len().eq(64).all()


def test_fixed_ma200_metrics_reproduce_accepted_oos_rows():
    champion = _read("oos_champion_table.csv")
    source = pd.read_csv(FIXED / "oos_results.csv")
    for frequency in FREQUENCIES:
        for mode in ("pre_tax", "after_tax"):
            out = champion.loc[
                champion.strategy_id.eq("FIXED_MA200_QQQ_TO_QLD")
                & champion.frequency.eq(frequency)
                & champion.tax_mode.eq(mode)
            ].iloc[0]
            ref = _source_rows(source, out.strategy_id, frequency, mode).iloc[0]
            for column, source_column in {
                "ending_value": "ending_value",
                "cagr": "cagr",
                "max_drawdown": "max_drawdown",
                "calmar": "calmar",
                "sharpe": "sharpe",
                "sortino": "sortino",
                "ulcer_index": "ulcer_index",
                "recovery_trading_days": "recovery_trading_days",
                "annual_turnover": "annual_turnover",
                "number_of_trades": "number_of_trades",
                "mean_holding_period_days": "mean_holding_period_days",
                "median_holding_period_days": "median_holding_period_days",
                "max_holding_period_days": "max_holding_period_days",
                "transaction_costs": "transaction_costs",
                "realized_tax_paid": "tax_paid",
            }.items():
                _assert_numeric_equal(pd.Series([out[column]]), pd.Series([ref[source_column]]))


def test_phase7a_and_phase7b_metrics_reproduce_accepted_source_rows():
    champion = _read("oos_champion_table.csv")
    phase7a = pd.concat(
        [pd.read_csv(PHASE7A / "metrics_pre_tax.csv"), pd.read_csv(PHASE7A / "metrics_after_tax.csv")],
        ignore_index=True,
    )
    phase7b = pd.read_csv(PHASE7B / "phase7b_stitched_oos_results.csv")
    for strategy_id, source in (
        ("PHASE7A_FIXED_FOUR_STATE", phase7a),
        ("PHASE7B_MODEL_A_SELECTED", phase7b),
        ("PHASE7B_MODEL_B_SELECTED", phase7b),
    ):
        for frequency in FREQUENCIES:
            for mode in ("pre_tax", "after_tax"):
                out = champion.loc[
                    champion.strategy_id.eq(strategy_id)
                    & champion.frequency.eq(frequency)
                    & champion.tax_mode.eq(mode)
                ].iloc[0]
                ref = _source_rows(source, strategy_id, frequency, mode).iloc[0]
                for column in (
                    "ending_value", "cagr", "max_drawdown", "calmar", "sharpe", "sortino",
                    "ulcer_index", "recovery_trading_days", "annual_turnover",
                    "number_of_trades", "mean_holding_period_days", "median_holding_period_days",
                    "max_holding_period_days", "transaction_costs",
                ):
                    _assert_numeric_equal(pd.Series([out[column]]), pd.Series([ref[column]]))
                _assert_numeric_equal(pd.Series([out.realized_tax_paid]), pd.Series([ref.tax_paid]))


def test_qqq_and_qld_benchmarks_are_identical_and_relative_arithmetic_is_exact():
    champion = _read("oos_champion_table.csv")
    relative = _read("benchmark_relative_metrics.csv")
    qqq = champion.loc[champion.strategy_id.eq("QQQ_BUY_HOLD")].iloc[0]
    assert len(champion.loc[champion.strategy_id.eq("QQQ_BUY_HOLD")]) == 1
    assert len(champion.loc[champion.strategy_id.eq("QLD_BUY_HOLD")]) == 1
    assert relative.qqq_benchmark_source_run_id.eq(SOURCE_RUNS["phase7b"]).all()
    for _, row in champion.iterrows():
        rel = relative.loc[
            relative.strategy_id.eq(row.strategy_id)
            & relative.frequency.eq(row.frequency)
            & relative.tax_mode.eq(row.tax_mode)
        ].iloc[0]
        for column, expected in {
            "cagr_minus_qqq": row.cagr - qqq.cagr,
            "max_drawdown_minus_qqq": row.max_drawdown - qqq.max_drawdown,
            "calmar_minus_qqq": row.calmar - qqq.calmar,
            "sharpe_minus_qqq": row.sharpe - qqq.sharpe,
            "sortino_minus_qqq": row.sortino - qqq.sortino,
            "terminal_after_tax_cagr_minus_qqq": row.after_tax_CAGR_terminal_liquidation - qqq.after_tax_CAGR_terminal_liquidation,
            "turnover_minus_qqq": row.annual_turnover - qqq.annual_turnover,
        }.items():
            _assert_numeric_equal(pd.Series([rel[column]]), pd.Series([expected]))
        dominance = bool(row.cagr > qqq.cagr and row.max_drawdown >= qqq.max_drawdown and pd.notna(row.calmar) and row.calmar > qqq.calmar)
        assert bool(rel.qqq_dominance) is dominance


def test_turnover_is_canonical_and_initial_deployment_is_excluded():
    champion = _read("oos_champion_table.csv")
    fixed = champion.loc[champion.strategy_id.eq("FIXED_MA200_QQQ_TO_QLD")]
    expected = {"weekly": 1.610241, "monthly": 1.171084, "bimonthly": 0.731928, "quarterly": 0.878313}
    for frequency, value in expected.items():
        values = fixed.loc[fixed.frequency.eq(frequency), "annual_turnover"]
        assert np.allclose(values, value, rtol=0.0, atol=1e-6)
    assert champion.loc[champion.frequency.eq("none"), "annual_turnover"].eq(0.0).all()


def test_terminal_liquidation_diagnostics_are_report_only_and_non_mutating():
    champion = _read("oos_champion_table.csv")
    for phase, files in (("phase7a", ("equity_curve.csv", "positions.csv", "trades.csv", "tax_ledger.csv")),
                         ("phase7b", ("equity_curve.csv", "positions.csv", "trades.csv", "tax_ledger.csv")),
                         ("fixed_ma200", ("equity_curve.csv", "positions.csv", "trades.csv", "tax_ledger.csv"))):
        root = {"phase7a": PHASE7A, "phase7b": PHASE7B, "fixed_ma200": FIXED}[phase]
        for name in files:
            assert hashlib.sha256((root / name).read_bytes()).hexdigest() == SOURCE_HASHES[(phase, name)]
    after = champion.loc[champion.tax_mode.eq("after_tax") & champion.frequency.isin(FREQUENCIES)]
    assert (after.after_tax_ending_value_terminal_liquidation > 0).all()
    assert (after.number_of_trades >= 0).all()
    assert (after.annual_turnover >= 0).all()
    phase7a = pd.concat([pd.read_csv(PHASE7A / "metrics_pre_tax.csv"), pd.read_csv(PHASE7A / "metrics_after_tax.csv")], ignore_index=True)
    phase7b = pd.read_csv(PHASE7B / "phase7b_stitched_oos_results.csv")
    fixed = pd.read_csv(FIXED / "oos_results.csv")
    for _, row in after.iterrows():
        if row.strategy_id == "FIXED_MA200_QQQ_TO_QLD":
            ref = _source_rows(fixed, row.strategy_id, row.frequency, row.tax_mode).iloc[0]
        elif row.strategy_id == "PHASE7A_FIXED_FOUR_STATE":
            ref = _source_rows(phase7a, row.strategy_id, row.frequency, row.tax_mode).iloc[0]
        else:
            ref = _source_rows(phase7b, row.strategy_id, row.frequency, row.tax_mode).iloc[0]
        for output_column, source_column in (
            ("source_terminal_liquidation_wealth", "terminal_liquidation_wealth"),
            ("source_terminal_liquidation_tax", "terminal_liquidation_tax"),
            ("source_terminal_liquidation_cost", "terminal_liquidation_cost"),
            ("source_terminal_unrealized_gain_after_cost", "terminal_unrealized_gain_after_cost"),
            ("after_tax_CAGR_tax_paid_to_date", "after_tax_cagr_tax_paid_to_date"),
            ("after_tax_ending_value_terminal_liquidation", "after_tax_terminal_liquidation"),
            ("after_tax_CAGR_terminal_liquidation", "after_tax_cagr_terminal_liquidation"),
        ):
            _assert_numeric_equal(pd.Series([row[output_column]]), pd.Series([ref[source_column]]))


def test_no_parameter_selection_or_winner_is_performed_in_phase8a():
    report = (RUN / "phase8a_report.md").read_text(encoding="utf-8")
    assert "No new strategy, parameter optimization, parameter selection" in report
    assert "No strategy winner" in report
    assert "Phase 8B is not started" in report
    assert not (RUN / "selected_parameters.csv").exists()
    assert _read("complexity_comparison.csv").descriptive_only.eq(True).all()


def test_aligned_daily_series_have_exact_common_sessions_without_duplicates():
    equity = _read("aligned_daily_equity.csv")
    returns = _read("aligned_daily_returns.csv")
    assert len(equity) == len(returns)
    equity.date = pd.to_datetime(equity.date)
    returns.date = pd.to_datetime(returns.date)
    assert equity.date.nunique() == len(COMMON_DATES)
    assert equity.groupby(["strategy_id", "frequency", "tax_mode"]).size().eq(len(COMMON_DATES)).all()
    assert not equity.duplicated(["strategy_id", "frequency", "tax_mode", "date"]).any()
    assert not returns.duplicated(["strategy_id", "frequency", "tax_mode", "date"]).any()
    for _, group in equity.groupby(["strategy_id", "frequency", "tax_mode"], sort=False):
        assert pd.DatetimeIndex(group.sort_values("date").date).equals(COMMON_DATES)
    assert returns.daily_return.notna().all()


def test_source_artifact_hashes_remain_unchanged_and_manifest_matches():
    manifest = _read("canonical_source_manifest.csv")
    for (phase, name), expected in SOURCE_HASHES.items():
        path = {"phase7a": PHASE7A, "phase7b": PHASE7B, "fixed_ma200": FIXED}[phase] / name
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        assert actual == expected
        row = manifest.loc[manifest.source_phase.eq(phase) & manifest.artifact.eq(name)].iloc[0]
        assert row.sha256 == expected


def test_report_ends_with_required_phase8a_status():
    report = (RUN / "phase8a_report.md").read_text(encoding="utf-8").rstrip()
    assert report.endswith("PHASE 8A EVIDENCE CONSOLIDATION COMPLETE — NO NEW STRATEGY OR PARAMETER SELECTION PERFORMED")


def test_immutable_raw_snapshot_hashes_match_manifest():
    import yaml

    manifest = yaml.safe_load((ROOT / "data/raw/manifest.yaml").read_text(encoding="utf-8"))
    for asset, info in manifest["sources"].items():
        digest = hashlib.sha256((ROOT / "data/raw" / f"{asset}.parquet").read_bytes()).hexdigest()
        assert digest == info["sha256"]
