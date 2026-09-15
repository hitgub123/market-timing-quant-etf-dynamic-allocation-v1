"""Dedicated Phase 8C final robustness/economic-decision audit tests."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from experiments.phase8c_robustness import (
    CONTEXT_STRATEGIES,
    DSR_STATUS,
    END_DATE,
    EXECUTION_GRID,
    EXPECTED_ACCEPTED_B2_HASHES,
    EXPECTED_B2_REMEDIATION_HASHES,
    EXPECTED_PHASE8A_HASHES,
    EXPECTED_PHASE8B1_HASHES,
    FREQUENCIES,
    PHASE8A_RUN,
    PHASE8B1_RUN,
    PHASE8B2_ACCEPTED_RUN,
    PRIMARY_STRATEGIES,
    SLIPPAGE_GRID,
    START_LABELS,
    _accepted_source_hashes,
    _raw_source_hashes,
)


ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / "reports/runs/20260915_phase8c_final_robustness_audit"
PHASE8B2_ACCEPTED = ROOT / "reports/runs/20260915_phase8b2_multiple_testing_audit"
PHASE8B2_REMEDIATION = ROOT / "reports/runs/20260915_phase8b2_dsr_remediation_candidate"


def _read(name: str) -> pd.DataFrame:
    return pd.read_csv(RUN / name)


def _config() -> dict:
    return json.loads((RUN / "phase8c_configuration.json").read_text(encoding="utf-8"))


def test_phase8c_artifact_completeness():
    required = {
        "robustness_scenarios.csv", "robustness_metrics.csv", "slippage_sensitivity.csv",
        "execution_sensitivity.csv", "start_date_sensitivity.csv", "tax_robustness.csv",
        "frequency_robustness.csv", "phase7a_vs_fixed_ma200_robustness.csv",
        "qqq_relative_robustness.csv", "robustness_survival_summary.csv",
        "canonical_baseline_reproduction.csv", "phase8c_configuration.json",
        "phase8c_report.md", "phase8c_audit_diff.md",
    }
    assert all((RUN / name).is_file() for name in required)


def test_phase8a_accepted_hashes_unchanged():
    config = _config()
    for name, expected in EXPECTED_PHASE8A_HASHES.items():
        assert hashlib.sha256((PHASE8A_RUN / name).read_bytes()).hexdigest() == expected
        assert config["source_hashes"][f"phase8a/{name}"] == expected


def test_phase8b1_accepted_hashes_unchanged():
    config = _config()
    for name, expected in EXPECTED_PHASE8B1_HASHES.items():
        assert hashlib.sha256((PHASE8B1_RUN / name).read_bytes()).hexdigest() == expected
        assert config["source_hashes"][f"phase8b1/{name}"] == expected


def test_phase8b2_accepted_and_remediated_hashes_unchanged():
    config = _config()
    for name, expected in EXPECTED_ACCEPTED_B2_HASHES.items():
        assert hashlib.sha256((PHASE8B2_ACCEPTED / name).read_bytes()).hexdigest() == expected
        assert config["source_hashes"][f"phase8b2_accepted/{name}"] == expected
    for name, expected in EXPECTED_B2_REMEDIATION_HASHES.items():
        assert hashlib.sha256((PHASE8B2_REMEDIATION / name).read_bytes()).hexdigest() == expected
        assert config["source_hashes"][f"phase8b2_remediation/{name}"] == expected


def test_canonical_baseline_reproduction_gate_passes_for_16_rows():
    baseline = _read("canonical_baseline_reproduction.csv")
    assert len(baseline) == 2 * 4 * 2
    assert baseline.baseline_reproduction_pass.eq(True).all()
    assert baseline.metric_match.eq(True).all()
    assert baseline.path_hash_match.eq(True).all()
    assert set(baseline.strategy_id) == set(PRIMARY_STRATEGIES)
    assert set(baseline.frequency) == set(FREQUENCIES)


def test_baseline_metrics_match_canonical_with_tight_tolerance():
    baseline = _read("canonical_baseline_reproduction.csv")
    for field in ("ending_value", "cagr", "max_drawdown", "calmar", "sharpe", "sortino", "annual_turnover", "transaction_costs"):
        assert np.allclose(baseline[f"canonical_{field}"], baseline[f"recomputed_{field}"], rtol=1e-12, atol=1e-7)
    assert baseline.canonical_number_of_trades.eq(baseline.recomputed_number_of_trades).all()
    assert baseline.canonical_realized_tax_paid.eq(baseline.recomputed_realized_tax_paid).all()


def test_slippage_grid_is_exact_and_all_primary_rows_present():
    data = _read("slippage_sensitivity.csv")
    assert tuple(sorted(data.slippage_bps.unique())) == tuple(SLIPPAGE_GRID)
    primary = data.loc[data.strategy_id.isin(PRIMARY_STRATEGIES)]
    assert len(primary) == 2 * 4 * 4 * 2
    assert set(primary.frequency) == set(FREQUENCIES)


def test_execution_grid_is_exact():
    data = _read("execution_sensitivity.csv")
    assert tuple(data.execution_case.unique()) == EXECUTION_GRID
    primary = data.loc[data.strategy_id.isin(PRIMARY_STRATEGIES)]
    assert len(primary) == 2 * 4 * 3 * 2
    assert "same_day_close" not in set(data.execution_case)


def test_execution_case_signal_timing_is_frozen_and_delayed():
    config = _config()
    assert config["baseline"]["signal"] == "adjusted close at t"
    assert config["execution_delay_sessions"] == {"next_close": 1, "next_open": 1, "t2_open": 2}
    report = (RUN / "phase8c_report.md").read_text(encoding="utf-8")
    assert "No same-day-close execution" in report
    assert "original frozen signal timestamp" in report


def test_start_grid_and_common_end_date_are_exact():
    data = _read("start_date_sensitivity.csv")
    assert tuple(sorted(data.start_label.astype(str).unique(), key=int)) == START_LABELS
    assert data.end_date.eq(END_DATE.date().isoformat()).all()
    config = _config()
    assert tuple(config["start_dates"]) == START_LABELS
    assert config["oos_end"] == END_DATE.date().isoformat()


def test_all_four_frequencies_remain_in_every_primary_scenario_family():
    metrics = _read("robustness_metrics.csv")
    for family in ("baseline", "slippage", "execution", "start_date"):
        scoped = metrics.loc[metrics.scenario_family.eq(family) & metrics.strategy_id.isin(PRIMARY_STRATEGIES)]
        assert set(scoped.loc[scoped.frequency.isin(FREQUENCIES), "frequency"]) == set(FREQUENCIES)
    assert set(metrics.loc[metrics.frequency.isin(FREQUENCIES), "frequency"]) == set(FREQUENCIES)


def test_no_strategy_parameter_or_frequency_selection():
    config = _config()
    for key in ("selection_performed", "model_selection_performed", "parameter_selection_performed", "frequency_selection_performed", "winner_designation", "prior_canonical_artifacts_rewritten"):
        assert config[key] is False
    scenarios = _read("robustness_scenarios.csv")
    assert scenarios.parameters_frozen.eq(True).all()
    assert scenarios.selection_performed.eq(False).all()
    freq = _read("frequency_robustness.csv")
    assert freq.frequency_selection_performed.eq(False).all()


def test_turnover_convention_and_exclusions_are_preserved():
    config = _config()
    assert config["baseline"]["turnover_denominator"] == "contemporaneous open-before-trade equity"
    assert config["baseline"]["initial_deployment_excluded"] is True
    assert config["baseline"]["terminal_liquidation_excluded"] is True
    metrics = _read("robustness_metrics.csv")
    primary = metrics.loc[metrics.strategy_id.isin(PRIMARY_STRATEGIES)]
    assert primary.initial_deployment_excluded_from_turnover.eq(True).all()
    assert primary.terminal_liquidation_excluded_from_turnover.eq(True).all()
    baseline = _read("canonical_baseline_reproduction.csv")
    assert np.allclose(baseline.canonical_annual_turnover, baseline.recomputed_annual_turnover, rtol=1e-12, atol=1e-12)


def test_terminal_liquidation_is_non_mutating_diagnostic():
    config = _config()
    assert config["baseline"]["terminal_liquidation_non_mutating"] is True
    metrics = _read("robustness_metrics.csv")
    primary = metrics.loc[metrics.strategy_id.isin(PRIMARY_STRATEGIES)]
    assert primary.terminal_liquidation_non_mutating.eq(True).all()
    assert primary.terminal_liquidation_excluded_from_turnover.eq(True).all()
    assert primary.holding_periods_completed_only.eq(True).all()


def test_tax_robustness_contains_both_modes_and_terminal_diagnostics():
    tax = _read("tax_robustness.csv")
    assert len(tax) == 8
    assert set(tax.strategy_id) == set(PRIMARY_STRATEGIES)
    for col in ("realized_tax_paid", "terminal_liquidation_wealth", "terminal_liquidation_cagr", "terminal_liquidation_tax", "terminal_liquidation_cost", "after_tax_cagr_tax_paid_to_date"):
        assert col in tax.columns


def test_phase7a_vs_fixed_uses_matched_frequency_and_scenario():
    comp = _read("phase7a_vs_fixed_ma200_robustness.csv")
    assert len(comp) == 14 * 4
    assert comp.duplicated(["scenario_id", "frequency"]).eq(False).all()
    assert comp.descriptive_only.eq(True).all()
    for col in ("phase7a_incremental_cagr_positive", "phase7a_incremental_sharpe_positive", "phase7a_incremental_calmar_positive", "phase7a_incremental_terminal_after_tax_cagr_positive"):
        assert set(comp[col].unique()) <= {True, False}


def test_qqq_relative_uses_identical_dates_and_frozen_dominance_formula():
    relative = _read("qqq_relative_robustness.csv")
    assert len(relative) == 14 * 2 * 4 * 2
    assert relative.identical_start_end_dates.eq(True).all()
    expected = (
        (relative.strategy_cagr > relative.qqq_cagr)
        & (relative.strategy_max_drawdown >= relative.qqq_max_drawdown)
        & (relative.strategy_calmar > relative.qqq_calmar)
    )
    assert relative.qqq_dominance.eq(expected).all()


def test_survival_summary_keeps_numerators_and_denominators():
    survival = _read("robustness_survival_summary.csv")
    assert len(survival) == 8
    assert set(survival.strategy_id) == set(PRIMARY_STRATEGIES)
    for col, denominator in (
        ("positive_cagr_vs_qqq_slippage_denominator", 4),
        ("positive_cagr_vs_qqq_execution_denominator", 3),
        ("positive_cagr_vs_qqq_start_date_denominator", 6),
        ("qqq_dominance_denominator", 14),
        ("phase7a_positive_incremental_cagr_denominator", 14),
        ("phase7a_positive_terminal_after_tax_cagr_denominator", 14),
    ):
        assert survival[col].eq(denominator).all()
    assert survival.survival_is_descriptive_only.eq(True).all()


def test_context_references_are_baseline_only_and_not_retuned():
    metrics = _read("robustness_metrics.csv")
    context = metrics.loc[metrics.strategy_id.isin(CONTEXT_STRATEGIES)]
    assert len(context) == len(CONTEXT_STRATEGIES) * 4 * 2
    assert context.scenario_family.eq("context_baseline").all()
    assert context.context_only.eq(True).all()
    assert set(context.frequency) == set(FREQUENCIES)


def test_dsr_boundary_and_no_new_inferential_family():
    config = _config()
    assert config["phase8b2_dsr_status"] == DSR_STATUS
    assert config["no_numerical_dsr"] is True
    assert config["new_inferential_p_value_family"] is False
    assert config["phase8b1_and_b2_formal_inference_rerun"] is False
    report = (RUN / "phase8c_report.md").read_text(encoding="utf-8")
    assert DSR_STATUS in report
    assert "No new inferential p-value family" in report


def test_prior_raw_manifest_and_source_hashes_are_unchanged():
    assert _accepted_source_hashes()
    raw = _raw_source_hashes()
    assert set(raw) == {"raw/SPY.parquet", "raw/QQQ.parquet", "raw/SSO.parquet", "raw/QLD.parquet", "raw/TQQQ.parquet"}


def test_no_prior_canonical_artifact_rewritten():
    config = _config()
    assert config["prior_canonical_artifacts_rewritten"] is False
    diff = (RUN / "phase8c_audit_diff.md").read_text(encoding="utf-8")
    assert "was rewritten" in diff
    assert "No accepted Phase 0–8B-2 artifact" in diff


def test_report_has_required_interpretation_boundaries_and_exact_final_line():
    report = (RUN / "phase8c_report.md").read_text(encoding="utf-8")
    for marker in (
        "Fixed MA200 versus QQQ", "Phase 7A's incremental benefit", "Tax-paid-to-date",
        "All four frequencies", "No production winner is declared", "not converted into post-hoc statistical inference",
    ):
        assert marker in report
    assert report.rstrip().endswith("PHASE 8C FINAL ROBUSTNESS AUDIT COMPLETE — NO MODEL, PARAMETER, OR FREQUENCY SELECTION PERFORMED")


def test_audit_diff_records_baseline_and_grid_evidence():
    diff = (RUN / "phase8c_audit_diff.md").read_text(encoding="utf-8")
    for marker in ("Baseline reproduction", "Frozen sensitivity grids", "Raw snapshot hash verification", "DSR_NOT_IDENTIFIABLE_FROM_FROZEN_ARTIFACTS"):
        assert marker in diff


def test_slippage_and_execution_degradation_are_relative_to_five_bps_baseline():
    baseline_selectors = {
        "slippage_sensitivity.csv": lambda data: data.slippage_bps.eq(5.0),
        "execution_sensitivity.csv": lambda data: data.execution_case.eq("next_open"),
        "start_date_sensitivity.csv": lambda data: data.start_label.astype(str).eq("2013"),
    }
    for name, selector in baseline_selectors.items():
        data = _read(name)
        assert data.baseline_slippage_bps.eq(5.0).all()
        assert data.degradation_is_reporting_only.eq(True).all()
        baseline_rows = data.loc[selector(data)]
        assert len(baseline_rows) > 0
