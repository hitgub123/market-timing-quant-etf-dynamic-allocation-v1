"""Dedicated Phase 8B-2 multiple-testing/data-snooping audit tests."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from statistics import NormalDist

import numpy as np
import pandas as pd

from experiments.phase8b1_pairwise_inference import (
    BLOCK_LENGTHS,
    PRIMARY_BLOCK_LENGTH,
    PAIRWISE_COMPARISONS,
    BOOTSTRAP_REPLICATIONS,
)
from experiments.phase8b2_multiple_testing import (
    EXPECTED_PHASE8A_HASHES,
    EXPECTED_PHASE8B1_HASHES,
    FREQUENCIES,
    SNOOPING_CANDIDATE_SET,
    SNOOPING_BENCHMARK,
    _benjamini_hochberg,
    _bonferroni,
    _holm,
    _inventory_counts,
    _inventory_rows,
    _moment_statistics,
    deflated_sharpe_ratio,
    _expected_max_z,
    _json_fingerprint,
)


ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / "reports/runs/20260915_phase8b2_multiple_testing_audit"
PHASE8A = ROOT / "reports/runs/20260914_phase8a_oos_evidence_consolidation_final"
PHASE8B1 = ROOT / "reports/runs/20260914_phase8b1_null_test_remediation_candidate"


def _read(name: str) -> pd.DataFrame:
    return pd.read_csv(RUN / name)


def _config() -> dict:
    return json.loads((RUN / "phase8b2_configuration.json").read_text(encoding="utf-8"))


def test_phase8b2_artifact_completeness():
    required = (
        "research_trial_inventory.csv",
        "multiple_testing_adjustments.csv",
        "deflated_sharpe_results.csv",
        "data_snooping_test_results.csv",
        "trial_correlation_summary.csv",
        "effective_trials_sensitivity.csv",
        "phase8b2_configuration.json",
        "phase8b2_report.md",
        "phase8b2_audit_diff.md",
    )
    for name in required:
        assert (RUN / name).is_file(), name


def test_phase8b2_source_hashes_are_accepted_and_byte_identical():
    config = _config()
    for name, expected in EXPECTED_PHASE8A_HASHES.items():
        assert hashlib.sha256((PHASE8A / name).read_bytes()).hexdigest() == expected
        assert config["source_hashes"][f"phase8a/{name}"] == expected
    for name, expected in EXPECTED_PHASE8B1_HASHES.items():
        assert hashlib.sha256((PHASE8B1 / name).read_bytes()).hexdigest() == expected
        assert config["source_hashes"][f"phase8b1/{name}"] == expected


def test_exact_phase8b1_primary_family_of_twenty_is_adjusted():
    adjustments = _read("multiple_testing_adjustments.csv")
    primary = adjustments.loc[adjustments.adjustment_scope.eq("confirmatory_20")]
    source = pd.read_csv(PHASE8B1 / "stationary_bootstrap_results.csv")
    source = source.loc[
        source.expected_block_length.eq(PRIMARY_BLOCK_LENGTH)
        & source.metric.eq("annualized_mean_return_difference")
    ].copy()
    assert len(primary) == 20
    assert primary.family_test_count.eq(20).all()
    assert primary.test_id.nunique() == 20
    expected_ids = set(source.comparison_id + "__" + source.strategy_frequency)
    assert set(primary.test_id) == expected_ids
    assert set(primary.raw_p_value) == set(source.one_sided_return_null_p_value)
    assert primary.posthoc_filtered.eq(False).all()


def test_bonferroni_formula_matches_hand_calculation():
    p = np.array([0.001, 0.02, 0.2, 0.9])
    np.testing.assert_allclose(_bonferroni(p), np.minimum(1.0, 4 * p), rtol=0, atol=0)
    output = _read("multiple_testing_adjustments.csv")
    primary = output.loc[output.adjustment_scope.eq("confirmatory_20")]
    np.testing.assert_allclose(
        primary.bonferroni_p_value.to_numpy(),
        np.minimum(1.0, 20 * primary.raw_p_value.to_numpy()),
        rtol=0, atol=1e-15,
    )


def test_holm_step_down_formula_and_monotonicity():
    p = np.array([0.4, 0.01, 0.03, 0.9])
    expected = np.array([0.8, 0.04, 0.09, 0.9])
    np.testing.assert_allclose(_holm(p), expected, rtol=0, atol=1e-15)
    out = _read("multiple_testing_adjustments.csv").loc[
        lambda frame: frame.adjustment_scope.eq("confirmatory_20")
    ].sort_values("raw_p_value")
    assert np.all(np.diff(out.holm_p_value.to_numpy()) >= -1e-15)


def test_benjamini_hochberg_q_formula_and_monotonicity():
    p = np.array([0.4, 0.01, 0.03, 0.9])
    expected = np.array([0.5333333333333333, 0.04, 0.06, 0.9])
    np.testing.assert_allclose(_benjamini_hochberg(p), expected, rtol=0, atol=1e-15)
    out = _read("multiple_testing_adjustments.csv").loc[
        lambda frame: frame.adjustment_scope.eq("confirmatory_20")
    ].sort_values("raw_p_value")
    assert np.all(np.diff(out.benjamini_hochberg_q_value.to_numpy()) >= -1e-15)


def test_secondary_comparison_family_is_sensitivity_only():
    adjustments = _read("multiple_testing_adjustments.csv")
    secondary = adjustments.loc[adjustments.adjustment_scope.eq("secondary_comparison_family_sensitivity")]
    assert len(secondary) == 20
    assert set(secondary.family_test_count) == {4}
    assert set(secondary.adjustment_family) == {item["comparison_id"][0] for item in PAIRWISE_COMPARISONS}
    assert not secondary.selection_performed.any()


def test_inventory_has_all_categories_a_through_i_and_reconciles_counts():
    inventory = _read("research_trial_inventory.csv")
    assert set(inventory.category) == set("ABCDEFGHI")
    assert len(inventory) == 11
    counts = _inventory_counts(inventory)
    config = _config()["research_trial_inventory"]
    assert counts["strict_selection_trials"] == config["strict_selection_trials"] == 2800
    assert counts["conservative_research_trials"] == config["conservative_research_trials"] == 4164
    assert counts["conservative_result_rows_including_tax_modes"] == 5528


def test_inventory_grid_arithmetic_matches_canonical_result_rows():
    inventory = _read("research_trial_inventory.csv").set_index("inventory_id")
    assert int(inventory.loc["A1_PHASE1_PAIR_ALLOCATIONS", "economic_trial_count"]) == 336
    assert int(inventory.loc["A2_PHASE1_TRIPLE_ALLOCATIONS", "economic_trial_count"]) == 660
    assert int(inventory.loc["B2_PHASE3_MA_STABILITY", "economic_trial_count"]) == 60
    assert int(inventory.loc["C_PHASE4_ABSOLUTE_MOMENTUM", "economic_trial_count"]) == 24
    assert int(inventory.loc["D_PHASE5_RELATIVE_MOMENTUM", "economic_trial_count"]) == 24
    assert int(inventory.loc["E_PHASE6_VOLATILITY_TARGETING", "economic_trial_count"]) == 240
    assert len(pd.read_csv(ROOT / "reports/runs/20260914_phase3_audit_final_v3/ma_parameter_surface.csv")) == 120
    assert len(pd.read_csv(ROOT / "reports/runs/20260914_phase6_audit_final/vol_parameter_surface.csv")) == 480
    training = pd.read_csv(ROOT / "reports/runs/20260914_phase7b_turnover_audit_final/training_candidate_results.csv")
    assert len(training) == 2800
    assert len(training.loc[training.model.eq("MODEL_A_QLD_TREND")]) == 280
    assert len(training.loc[training.model.eq("MODEL_B_FOUR_STATE")]) == 2520
    source_counts = _config()["research_trial_inventory"]["canonical_source_grid_row_counts"]
    assert source_counts == {
        "phase1_metrics_pre_tax": 996,
        "phase1_metrics_after_tax": 996,
        "phase2_metrics_pre_tax": 12,
        "phase2_metrics_after_tax": 12,
        "phase3_surface": 120,
        "phase4_surface": 48,
        "phase5_surface": 48,
        "phase6_surface": 480,
        "phase7a_results": 16,
        "phase7b_training_candidates": 2800,
    }


def test_strict_and_conservative_trial_flags_are_not_posthoc_filtered():
    inventory = _read("research_trial_inventory.csv")
    strict = inventory.loc[inventory.strict_selection_included]
    conservative = inventory.loc[inventory.conservative_count_included]
    assert set(strict.category) == {"G", "H"}
    assert strict.results_used_for_selection.all()
    assert conservative.economic_trial_count.sum() == 4164
    assert inventory.loc[inventory.category.eq("I"), "conservative_count_included"].eq(False).all()


def test_dsr_hand_formula_matches_published_expression():
    observed = 0.8
    n_obs = 100
    skew = 0.25
    excess = 1.5
    trials = 20
    variance_factor = 1 - skew * observed + ((excess + 2) / 4) * observed**2
    sigma = (variance_factor / (n_obs - 1)) ** 0.5
    expected_z = _expected_max_z(trials)
    expected_max = sigma * expected_z
    expected_probability = NormalDist().cdf((observed - expected_max) / sigma)
    result = deflated_sharpe_ratio(observed, n_obs, skew, excess, trials)
    np.testing.assert_allclose(result["sharpe_standard_error"], sigma, rtol=0, atol=1e-15)
    np.testing.assert_allclose(result["expected_max_sharpe"], expected_max, rtol=0, atol=1e-15)
    np.testing.assert_allclose(result["dsr_probability"], expected_probability, rtol=0, atol=1e-15)


def test_dsr_moments_are_sourced_from_exact_aligned_oos_path():
    daily = pd.read_csv(PHASE8A / "aligned_daily_returns.csv")
    daily.date = pd.to_datetime(daily.date)
    values = daily.loc[
        daily.strategy_id.eq("FIXED_MA200_QQQ_TO_QLD")
        & daily.frequency.eq("weekly")
        & daily.tax_mode.eq("pre_tax")
    ].sort_values("date").daily_return.to_numpy()
    expected = _moment_statistics(values)
    row = _read("deflated_sharpe_results.csv").loc[
        lambda frame: frame.path_id.eq("FIXED_MA200_QQQ_TO_QLD__weekly")
        & frame.trial_count_basis.eq("strict_selection_trials")
    ].iloc[0]
    for column in ("observed_sharpe", "skewness", "excess_kurtosis", "n_observations"):
        np.testing.assert_allclose(float(row[column]), expected[column], rtol=0, atol=1e-14)


def test_dsr_contains_both_trial_bases_for_all_required_paths():
    dsr = _read("deflated_sharpe_results.csv")
    expected_paths = {"QQQ_BUY_HOLD__none"} | {_id + "__" + freq for _id, freq in SNOOPING_CANDIDATE_SET}
    assert set(dsr.path_id) == expected_paths
    assert len(dsr) == len(expected_paths) * 2 == 34
    assert set(dsr.trial_count_basis) == {"strict_selection_trials", "conservative_research_trials"}
    assert dsr.n_observations.eq(3436).all()
    assert dsr.selection_performed.eq(False).all()
    assert dsr.dsr_probability.between(0, 1).all()


def test_correlation_effective_trial_summary_and_sensitivity_are_present():
    correlation = _read("trial_correlation_summary.csv")
    sensitivity = _read("effective_trials_sensitivity.csv")
    paths = {"QQQ_BUY_HOLD__none"} | {_id + "__" + freq for _id, freq in SNOOPING_CANDIDATE_SET}
    assert correlation.shape[0] == len(paths) ** 2
    assert set(correlation.path_id) == paths == set(correlation.other_path_id)
    assert correlation.estimated_effective_trials.nunique() == 1
    assert correlation.estimated_effective_trials.iloc[0] >= 1
    assert set(sensitivity.effective_trial_count.unique()) >= {1, 2, 4, 8, 16}
    assert sensitivity.selection_performed.eq(False).all()


def test_white_reality_check_candidate_set_is_frozen_and_complete():
    config = _config()["data_snooping"]
    results = _read("data_snooping_test_results.csv")
    expected_names = [f"{strategy}__{frequency}" for strategy, frequency in SNOOPING_CANDIDATE_SET]
    assert config["candidate_set"] == expected_names
    assert config["candidate_set_fingerprint"] == _json_fingerprint(expected_names)
    assert config["candidate_set_frozen_before_results"] is True
    assert set(results.candidate_count) == {16}
    assert set(results.candidate_set_fingerprint) == {config["candidate_set_fingerprint"]}
    assert results.candidate_set.eq("|".join(expected_names)).all()
    assert results.benchmark_id.eq(SNOOPING_BENCHMARK[0]).all()
    assert results.selection_performed.eq(False).all()


def test_white_reality_check_has_primary_and_sensitivity_blocks_with_finite_p_values():
    results = _read("data_snooping_test_results.csv")
    assert set(results.expected_block_length) == set(BLOCK_LENGTHS)
    assert results.loc[results.block_role.eq("PRIMARY"), "expected_block_length"].tolist() == [20]
    assert results.bootstrap_replications.eq(BOOTSTRAP_REPLICATIONS).all()
    assert results.p_value.between(1 / (BOOTSTRAP_REPLICATIONS + 1), 1).all()
    assert results.recentered.eq(True).all()
    assert results.truncation.eq("none").all()
    assert "why_white_reality_check_only" in _config()["data_snooping"]


def test_white_reality_check_reuses_accepted_phase8b1_index_stream():
    old = json.loads((PHASE8B1 / "bootstrap_configuration.json").read_text(encoding="utf-8"))
    new = _config()
    assert new["data_snooping"]["index_sha256_by_block_length"] == old["stationary_bootstrap"]["index_sha256_by_block_length"]
    results = _read("data_snooping_test_results.csv")
    for block in BLOCK_LENGTHS:
        actual = results.loc[results.expected_block_length.eq(block), "bootstrap_index_sha256"].iloc[0]
        assert actual == old["stationary_bootstrap"]["index_sha256_by_block_length"][str(block)]


def test_required_paths_are_paired_on_exact_common_calendar():
    daily = pd.read_csv(PHASE8A / "aligned_daily_returns.csv")
    daily.date = pd.to_datetime(daily.date)
    qqq = pd.DatetimeIndex(daily.loc[daily.strategy_id.eq("QQQ_BUY_HOLD") & daily.tax_mode.eq("benchmark")].sort_values("date").date)
    assert len(qqq) == 3436
    for strategy, frequency in SNOOPING_CANDIDATE_SET:
        mode = "pre_tax"
        rows = daily.loc[daily.strategy_id.eq(strategy) & daily.frequency.eq(frequency) & daily.tax_mode.eq(mode)].sort_values("date")
        assert pd.DatetimeIndex(rows.date).equals(qqq)
        assert rows.daily_return.notna().all()


def test_no_selection_flags_or_claims_are_introduced():
    config = _config()
    for key in ("selection_performed", "frequency_selection_performed", "model_selection_performed", "winner_designation"):
        assert config[key] is False
    for section in ("multiple_testing", "deflated_sharpe_ratio", "data_snooping"):
        assert config[section]["selection_performed"] is False
    report = (RUN / "phase8b2_report.md").read_text(encoding="utf-8")
    assert "No winner, optimal parameter, recommended frequency" in report
    assert "oos claim beyond the frozen source" in report.lower()
    assert "Walk-Forward parameter selection remains confined" in report


def test_report_and_audit_diff_have_required_terminal_status():
    expected = "PHASE 8B-2 MULTIPLE-TESTING AUDIT COMPLETE — NO MODEL OR FREQUENCY SELECTION PERFORMED"
    report = (RUN / "phase8b2_report.md").read_text(encoding="utf-8")
    diff = (RUN / "phase8b2_audit_diff.md").read_text(encoding="utf-8")
    assert report.rstrip().endswith(expected)
    assert diff.rstrip().endswith(expected)


def test_prior_phase8a_manifest_hashes_remain_unchanged():
    manifest = pd.read_csv(PHASE8A / "canonical_source_manifest.csv")
    for _, row in manifest.iterrows():
        path = ROOT / str(row.relative_path)
        assert path.is_file(), path
        assert hashlib.sha256(path.read_bytes()).hexdigest() == row.sha256


def test_inventory_constructor_is_reproducible_and_has_no_hidden_rows():
    regenerated = _inventory_rows()
    written = _read("research_trial_inventory.csv")
    assert regenerated.shape == written.shape
    assert list(regenerated.inventory_id) == list(written.inventory_id)
    assert regenerated.economic_trial_count.sum() == written.economic_trial_count.sum()
    assert regenerated.result_rows_including_tax_modes.sum() == written.result_rows_including_tax_modes.sum()
