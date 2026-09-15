"""Dedicated tests for the Phase 8B-2 DSR methodology remediation."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from statistics import NormalDist

import numpy as np
import pandas as pd
import pytest

from experiments.phase8b2_dsr_remediation import (
    DSR_STATUS,
    EXPECTED_ACCEPTED_B2_HASHES,
    EXPECTED_PHASE8A_HASHES,
    EXPECTED_PHASE8B1_HASHES,
    cross_trial_sharpe_statistics,
    corrected_dsr_from_trial_distribution,
    dsr_identifiability_status,
    observed_path_sampling_se,
    sr_star_from_trial_distribution,
)


ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / "reports/runs/20260915_phase8b2_dsr_remediation_candidate"
ACCEPTED = ROOT / "reports/runs/20260915_phase8b2_multiple_testing_audit"
PHASE8A = ROOT / "reports/runs/20260914_phase8a_oos_evidence_consolidation_final"
PHASE8B1 = ROOT / "reports/runs/20260914_phase8b1_null_test_remediation_candidate"


def _read(name: str) -> pd.DataFrame:
    return pd.read_csv(RUN / name)


def _config() -> dict:
    return json.loads((RUN / "phase8b2_configuration.json").read_text(encoding="utf-8"))


def test_remediation_artifact_completeness():
    required = (
        "research_trial_inventory.csv",
        "dsr_trial_universe_audit.csv",
        "deflated_sharpe_results.csv",
        "multiple_testing_adjustments.csv",
        "data_snooping_test_results.csv",
        "trial_correlation_summary.csv",
        "effective_trials_sensitivity.csv",
        "phase8b2_dsr_remediation.md",
        "phase8b2_configuration.json",
        "phase8b2_report.md",
        "phase8b2_audit_diff.md",
    )
    for name in required:
        assert (RUN / name).is_file(), name


def test_phase8a_hashes_unchanged():
    config = _config()
    for name, expected in EXPECTED_PHASE8A_HASHES.items():
        assert hashlib.sha256((PHASE8A / name).read_bytes()).hexdigest() == expected
        assert config["source_hashes"][f"phase8a/{name}"] == expected


def test_phase8b1_hashes_unchanged():
    config = _config()
    for name, expected in EXPECTED_PHASE8B1_HASHES.items():
        assert hashlib.sha256((PHASE8B1 / name).read_bytes()).hexdigest() == expected
        assert config["source_hashes"][f"phase8b1/{name}"] == expected


def test_accepted_phase8b2_invariant_hashes_and_byte_equality():
    config = _config()
    for name, expected in EXPECTED_ACCEPTED_B2_HASHES.items():
        actual = hashlib.sha256((ACCEPTED / name).read_bytes()).hexdigest()
        assert actual == expected
    for name in (
        "research_trial_inventory.csv",
        "multiple_testing_adjustments.csv",
        "data_snooping_test_results.csv",
        "trial_correlation_summary.csv",
        "effective_trials_sensitivity.csv",
    ):
        assert (RUN / name).read_bytes() == (ACCEPTED / name).read_bytes()
        assert config["invariant_artifact_comparison"][name]["byte_identical"] is True


def test_exact_twenty_adjustments_and_secondary_sensitivity_preserved():
    adjustments = _read("multiple_testing_adjustments.csv")
    primary = adjustments.loc[adjustments.adjustment_scope.eq("confirmatory_20")]
    secondary = adjustments.loc[adjustments.adjustment_scope.eq("secondary_comparison_family_sensitivity")]
    assert len(primary) == 20
    assert primary.family_test_count.eq(20).all()
    assert len(secondary) == 20
    assert secondary.family_test_count.eq(4).all()
    assert primary.posthoc_filtered.eq(False).all()
    assert primary.selection_performed.eq(False).all()


def test_white_reality_check_remains_the_frozen_sixteen_path_family():
    rc = _read("data_snooping_test_results.csv")
    assert len(rc) == 5
    assert rc.candidate_count.eq(16).all()
    assert set(rc.expected_block_length) == {5, 10, 20, 40, 60}
    assert rc.equals(pd.read_csv(ACCEPTED / "data_snooping_test_results.csv"))
    assert rc.loc[rc.expected_block_length.eq(20), "p_value"].iloc[0] == pytest.approx(0.010299, abs=1e-6)


def test_research_inventory_counts_remain_2800_and_4164():
    inventory = _read("research_trial_inventory.csv")
    assert set(inventory.category) == set("ABCDEFGHI")
    assert inventory.loc[inventory.strict_selection_included, "economic_trial_count"].sum() == 2800
    assert inventory.loc[inventory.conservative_count_included, "economic_trial_count"].sum() == 4164
    assert inventory.loc[inventory.category.eq("I"), "conservative_count_included"].eq(False).all()


def test_trial_universe_audit_covers_every_family_and_records_availability():
    audit = _read("dsr_trial_universe_audit.csv")
    assert len(audit) == 11
    assert set(audit.category) == set("ABCDEFGHI")
    required = {
        "economic_trial_count", "comparable_sharpe_available", "source_artifact",
        "sharpe_definition", "evaluation_period", "full_sample_vs_oos",
        "comparable_calendar", "used_for_cross_trial_variance", "exclusion_reason",
    }
    assert required <= set(audit.columns)
    assert audit.loc[audit.inventory_id.eq("A1_PHASE1_PAIR_ALLOCATIONS"), "sharpe_observations_available"].iloc[0] == 330
    assert audit.loc[audit.inventory_id.eq("A2_PHASE1_TRIPLE_ALLOCATIONS"), "sharpe_observations_available"].iloc[0] == 656
    assert audit.loc[audit.inventory_id.eq("G_PHASE7B_MODEL_A_TRAINING_CANDIDATES"), "sharpe_observations_available"].iloc[0] == 280
    assert audit.loc[audit.inventory_id.eq("H_PHASE7B_MODEL_B_TRAINING_CANDIDATES"), "sharpe_observations_available"].iloc[0] == 2520


def test_no_unsupported_full_sample_oos_mixing_is_used():
    audit = _read("dsr_trial_universe_audit.csv")
    assert audit.used_for_cross_trial_variance.eq(False).all()
    assert audit.loc[audit.full_sample_vs_oos.eq("full_sample"), "comparable_sharpe_available"].eq(0).all()
    fold_rows = audit.loc[audit.inventory_id.str.startswith(("G_", "H_"))]
    assert fold_rows.comparable_sharpe_available.eq(0).all()
    phase7a = audit.loc[audit.inventory_id.eq("F_PHASE7A_FIXED_FOUR_STATE")].iloc[0]
    assert phase7a.comparable_sharpe_available == 4
    assert "final paths" in phase7a.exclusion_reason


def test_dsr_status_is_not_identifiable_for_every_required_path_and_trial_basis():
    dsr = _read("deflated_sharpe_results.csv")
    assert len(dsr) == 34
    assert set(dsr.status) == {DSR_STATUS}
    assert set(dsr.trial_count_basis) == {"strict_selection_trials", "conservative_research_trials"}
    assert set(dsr.raw_trial_count) == {2800, 4164}
    assert dsr.comparable_trial_count.eq(0).all()
    assert dsr.sr_star.isna().all()
    assert dsr.dsr_test_statistic.isna().all()
    assert dsr.dsr_probability.isna().all()


def test_dsr_required_paths_are_all_present_without_posthoc_filtering():
    dsr = _read("deflated_sharpe_results.csv")
    required_paths = {"QQQ_BUY_HOLD__none"}
    required_paths |= {f"{strategy}__{frequency}" for strategy in ("FIXED_MA200_QQQ_TO_QLD", "PHASE7A_FIXED_FOUR_STATE", "PHASE7B_MODEL_A_SELECTED", "PHASE7B_MODEL_B_SELECTED") for frequency in ("weekly", "monthly", "bimonthly", "quarterly")}
    assert set(dsr.path_id) == required_paths
    assert dsr.selection_performed.eq(False).all()
    assert dsr.sample_length_T.eq(3436).all()


def test_cross_trial_dispersion_is_not_observed_path_sampling_se():
    trial = np.array([0.1, 0.4, 0.7, 1.0], dtype=float)
    stats = cross_trial_sharpe_statistics(trial)
    observed_se = observed_path_sampling_se(0.8, 3436, -0.2, 2.0)
    assert stats["trial_sharpe_std"] == pytest.approx(np.std(trial, ddof=1))
    assert stats["trial_sharpe_std"] != pytest.approx(observed_se)
    row = _read("deflated_sharpe_results.csv").iloc[0]
    assert pd.isna(row.cross_trial_sharpe_std)
    assert row.observed_path_sampling_se > 0


def test_sr_star_changes_with_cross_trial_dispersion_independently():
    low_dispersion = np.array([0.40, 0.41, 0.39, 0.40])
    high_dispersion = np.array([0.0, 0.2, 0.8, 1.0])
    low = sr_star_from_trial_distribution(low_dispersion, 4)
    high = sr_star_from_trial_distribution(high_dispersion, 4)
    assert low["mean_trial_sharpe"] != high["mean_trial_sharpe"] or low["trial_sharpe_std"] != high["trial_sharpe_std"]
    assert high["trial_sharpe_std"] > low["trial_sharpe_std"]
    assert high["sr_star"] > low["sr_star"]


def test_observed_sampling_denominator_changes_with_skew_kurtosis_and_T_only():
    trial = np.array([0.20, 0.25, 0.30, 0.35])
    base = corrected_dsr_from_trial_distribution(0.8, 100, 0.0, 0.0, trial, 4)
    altered_moments = corrected_dsr_from_trial_distribution(0.8, 100, 0.5, 0.0, trial, 4)
    altered_T = corrected_dsr_from_trial_distribution(0.8, 200, 0.0, 0.0, trial, 4)
    se_a = observed_path_sampling_se(0.8, 100, 0.0, 0.0)
    se_b = observed_path_sampling_se(0.8, 100, 0.5, 0.0)
    se_c = observed_path_sampling_se(0.8, 200, 0.0, 0.0)
    assert se_a != pytest.approx(se_b)
    assert se_c < se_a
    assert base["sr_star"] == pytest.approx(altered_moments["sr_star"])
    assert base["sr_star"] == pytest.approx(altered_T["sr_star"])
    assert base["observed_path_sampling_se"] != pytest.approx(altered_moments["observed_path_sampling_se"])
    assert base["observed_path_sampling_se"] != pytest.approx(altered_T["observed_path_sampling_se"])
    assert base["dsr_test_statistic"] != pytest.approx(altered_moments["dsr_test_statistic"])


def test_independent_hand_worked_dsr_reference():
    trial = np.array([0.20, 0.40, 0.60, 0.80])
    observed = 0.75
    T = 120
    skew = 0.15
    excess = 1.2
    N_eff = 4
    result = corrected_dsr_from_trial_distribution(observed, T, skew, excess, trial, N_eff)
    variance = (1 - skew * observed + ((excess + 2) / 4) * observed**2) / (T - 1)
    se = variance**0.5
    expected_sr_star = np.mean(trial) + np.std(trial, ddof=1) * result["expected_max_z"]
    expected_stat = (observed - expected_sr_star) / se
    expected_prob = NormalDist().cdf(expected_stat)
    assert result["comparable_trial_count"] == 4
    assert result["trial_sharpe_variance"] == pytest.approx(np.var(trial, ddof=1))
    assert result["sr_star"] == pytest.approx(expected_sr_star)
    assert result["observed_path_sampling_se"] == pytest.approx(se)
    assert result["dsr_test_statistic"] == pytest.approx(expected_stat)
    assert result["dsr_probability"] == pytest.approx(expected_prob)


def test_missing_trial_distribution_returns_not_identifiable_status():
    audit = _read("dsr_trial_universe_audit.csv")
    assert dsr_identifiability_status(audit) == DSR_STATUS
    assert dsr_identifiability_status(pd.DataFrame()) == DSR_STATUS


def test_effective_path_count_is_descriptive_only_and_preserved():
    dsr = _read("deflated_sharpe_results.csv")
    config = _config()
    assert dsr.effective_path_count_role.str.contains("descriptive_only").all()
    assert dsr.effective_path_count_sensitivity.nunique() == 1
    assert dsr.effective_path_count_sensitivity.iloc[0] == pytest.approx(config["dsr"]["effective_path_count_sensitivity"])
    assert (RUN / "effective_trials_sensitivity.csv").read_bytes() == (ACCEPTED / "effective_trials_sensitivity.csv").read_bytes()


def test_no_selection_and_final_remediation_status():
    config = _config()
    for key in ("selection_performed", "frequency_selection_performed", "model_selection_performed", "winner_designation", "prior_phase_artifacts_rewritten"):
        assert config[key] is False
    assert config["dsr"]["selection_performed"] is False
    report = (RUN / "phase8b2_report.md").read_text(encoding="utf-8")
    assert DSR_STATUS in report
    assert "does not show credible incremental mean-return evidence over Fixed MA200" in report
    assert report.rstrip().endswith("PHASE 8B-2 DSR REMEDIATION COMPLETE — AWAITING STATISTICAL AUDIT")


def test_methodology_artifact_distinguishes_both_variance_concepts():
    text = (RUN / "phase8b2_dsr_remediation.md").read_text(encoding="utf-8")
    for marker in ("sigma_{trial}", "sigma_{observed}", "SR^*", "cross-trial", "sampling uncertainty", DSR_STATUS):
        assert marker in text


def test_prior_canonical_source_manifest_still_matches_every_file():
    manifest = pd.read_csv(PHASE8A / "canonical_source_manifest.csv")
    for _, row in manifest.iterrows():
        path = ROOT / str(row.relative_path)
        assert hashlib.sha256(path.read_bytes()).hexdigest() == row.sha256


def test_audit_diff_records_old_and_new_dsr_hashes_and_invariant_hashes():
    diff = (RUN / "phase8b2_audit_diff.md").read_text(encoding="utf-8")
    config = _config()
    assert config["old_dsr_results_sha256"] == EXPECTED_ACCEPTED_B2_HASHES["deflated_sharpe_results.csv"]
    assert config["new_dsr_results_sha256"] == hashlib.sha256((RUN / "deflated_sharpe_results.csv").read_bytes()).hexdigest()
    assert "Old defective DSR artifact SHA-256" in diff
    assert "byte-identical" in diff
    assert DSR_STATUS in diff


def test_audit_diff_identifies_changed_reporting_artifacts():
    diff = (RUN / "phase8b2_audit_diff.md").read_text(encoding="utf-8")
    assert "Intentionally changed reporting artifacts" in diff
    assert "phase8b2_configuration.json" in diff
    assert "phase8b2_report.md" in diff
    assert "deflated_sharpe_results.csv" in diff
