"""Dedicated Phase 8B-1 frozen pairwise-inference regressions."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re

import numpy as np
import pandas as pd

from experiments.phase8b1_pairwise_inference import (
    BLOCK_LENGTHS,
    BOOTSTRAP_REPLICATIONS,
    BOOTSTRAP_SEED,
    EXPECTED_PHASE8A_DAILY_RETURNS_SHA256,
    EXPECTED_SESSIONS,
    FREQUENCIES,
    METRICS,
    OOS_END,
    OOS_START,
    PAIRWISE_COMPARISONS,
    PRIMARY_BLOCK_LENGTH,
    SENSITIVITY_BLOCK_LENGTHS,
    _batch_pair_statistics,
    _bootstrap_pair,
    centered_null_bootstrap_means,
    centered_null_bootstrap_p_value,
    _load_inputs,
    _observed_rows,
    _seed_for_block,
    _hac_mean_return_rows,
    stationary_bootstrap_indices,
)


ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / "reports/runs/20260914_phase8b1_null_test_remediation_candidate"
PRIOR_RUN = ROOT / "reports/runs/20260914_phase8b1_pairwise_inference_final"
PHASE8A = ROOT / "reports/runs/20260914_phase8a_oos_evidence_consolidation_final"


def _read(name: str) -> pd.DataFrame:
    return pd.read_csv(RUN / name)


def _source_daily() -> pd.DataFrame:
    daily = pd.read_csv(PHASE8A / "aligned_daily_returns.csv")
    daily.date = pd.to_datetime(daily.date)
    return daily


def test_phase8b1_artifact_completeness_and_source_metadata():
    required = (
        "pairwise_observed_metrics.csv",
        "stationary_bootstrap_results.csv",
        "hac_mean_return_results.csv",
        "after_tax_descriptive_comparisons.csv",
        "bootstrap_configuration.json",
        "phase8b1_report.md",
        "phase8b1_audit_diff.md",
    )
    for name in required:
        assert (RUN / name).is_file(), name
    config = json.loads((RUN / "bootstrap_configuration.json").read_text(encoding="utf-8"))
    assert config["phase8a_source_run_id"] == "20260914_phase8a_oos_evidence_consolidation_final"
    assert config["phase8a_aligned_daily_returns_sha256"] == EXPECTED_PHASE8A_DAILY_RETURNS_SHA256
    assert config["phase8a_champion_table_sha256"] == "718ca799db65ea03ae625e400634f5246195e58a8b8fc9ec6416852d7a8a53af"
    assert config["phase"] == "8B-1"
    null_test = config["stationary_bootstrap"]["null_test"]
    assert null_test["boundary_null_series"] == "d0_t = d_t - observed_mean_daily"
    assert null_test["bootstrap_statistic"] == "null_bootstrap_mean_daily = mean(d0_t[indices])"
    assert null_test["tail"] == "null_bootstrap_mean_daily >= observed_mean_daily"
    assert config["stationary_bootstrap"]["null_p_value_correction"] == "(1 + count(null_bootstrap_stat >= observed_stat)) / (B + 1)"
    assert config["stationary_bootstrap"]["confidence_intervals"]["centering_applied"] is False


def test_exact_phase8a_source_hash_is_consumed_and_prior_artifact_is_unchanged():
    path = PHASE8A / "aligned_daily_returns.csv"
    assert hashlib.sha256(path.read_bytes()).hexdigest() == EXPECTED_PHASE8A_DAILY_RETURNS_SHA256
    # The complete Phase 8A source set remains byte-identical.
    expected = {
        "oos_champion_table.csv": "718ca799db65ea03ae625e400634f5246195e58a8b8fc9ec6416852d7a8a53af",
        "aligned_daily_equity.csv": "4271efc5106fb60229fdb7a43c47158b3f229b7dc1ad7ce012a6f01878b200d0",
        "aligned_daily_returns.csv": EXPECTED_PHASE8A_DAILY_RETURNS_SHA256,
        "canonical_source_manifest.csv": "3ad085ad440090221f4794f456d18ef2cea433a035a288658c50a12ebbabf6dd",
    }
    for name, digest in expected.items():
        assert hashlib.sha256((PHASE8A / name).read_bytes()).hexdigest() == digest


def test_exact_3436_paired_dates_without_missing_or_duplicates():
    daily = _source_daily()
    qqq_dates = pd.DatetimeIndex(daily.loc[daily.strategy_id.eq("QQQ_BUY_HOLD") & daily.tax_mode.eq("benchmark")].sort_values("date").date)
    assert len(qqq_dates) == EXPECTED_SESSIONS == 3_436
    assert qqq_dates[0] == OOS_START and qqq_dates[-1] == OOS_END
    assert not qqq_dates.has_duplicates
    for _, group in daily.groupby(["strategy_id", "frequency", "tax_mode"]):
        dates = pd.DatetimeIndex(group.sort_values("date").date)
        assert dates.equals(qqq_dates)
        assert not group.duplicated(["date"]).any()


def test_all_frozen_pairwise_comparisons_and_frequencies_are_present():
    observed = _read("pairwise_observed_metrics.csv")
    bootstrap = _read("stationary_bootstrap_results.csv")
    hac = _read("hac_mean_return_results.csv")
    after = _read("after_tax_descriptive_comparisons.csv")
    expected_ids = {item["comparison_id"] for item in PAIRWISE_COMPARISONS}
    assert set(observed.comparison_id) == expected_ids
    assert len(observed) == len(PAIRWISE_COMPARISONS) * len(FREQUENCIES) == 20
    assert set(observed.strategy_frequency) == set(FREQUENCIES)
    assert len(hac) == len(after) == 20
    assert len(bootstrap) == 20 * len(BLOCK_LENGTHS) * len(METRICS) == 600
    assert set(bootstrap.comparison_id) == expected_ids
    assert set(bootstrap.expected_block_length) == set(BLOCK_LENGTHS)


def test_same_stationary_indices_are_applied_to_both_pair_members():
    strategy = np.linspace(0.01, 0.06, 12)
    benchmark = np.linspace(-0.01, 0.02, 12)
    indices = stationary_bootstrap_indices(12, 5, 3, np.random.default_rng(123))
    result = _batch_pair_statistics(strategy, benchmark, indices)
    expected = (strategy[indices] - benchmark[indices]).mean(axis=1) * 252.0
    np.testing.assert_allclose(result["annualized_mean_return_difference"], expected, rtol=0.0, atol=1e-14)


def test_stationary_bootstrap_is_deterministic_under_frozen_seed():
    strategy = np.linspace(-0.01, 0.02, 40)
    benchmark = np.linspace(0.0, 0.01, 40)
    first_indices = stationary_bootstrap_indices(40, 20, 5, np.random.default_rng(BOOTSTRAP_SEED))
    second_indices = stationary_bootstrap_indices(40, 20, 5, np.random.default_rng(BOOTSTRAP_SEED))
    np.testing.assert_array_equal(first_indices, second_indices)
    first, first_hash, first_mean = _bootstrap_pair(strategy, benchmark, expected_block_length=5, n_replications=20, seed=BOOTSTRAP_SEED, chunk_size=7)
    second, second_hash, second_mean = _bootstrap_pair(strategy, benchmark, expected_block_length=5, n_replications=20, seed=BOOTSTRAP_SEED, chunk_size=7)
    assert first_hash == second_hash and first_mean == second_mean
    for metric in METRICS:
        np.testing.assert_array_equal(first[metric], second[metric])


def test_centered_null_matches_independent_autocorrelated_recomputation():
    """The production p-value must use the explicitly centered d0 series."""
    shocks = np.array([0.002, -0.001, 0.003, -0.002, 0.001, 0.004, -0.003, 0.002, -0.001, 0.003], dtype=float)
    difference = np.empty_like(shocks)
    difference[0] = 0.004
    for i in range(1, len(shocks)):
        difference[i] = 0.65 * difference[i - 1] + shocks[i]
    indices = stationary_bootstrap_indices(
        len(difference), 257, 4, np.random.default_rng(_seed_for_block(4))
    )
    observed_mean_daily = float(np.mean(difference))
    d0 = difference - observed_mean_daily
    expected_null_statistics = np.mean(d0[indices], axis=1)
    expected_p = (1 + int(np.count_nonzero(expected_null_statistics >= observed_mean_daily))) / (len(indices) + 1)
    np.testing.assert_allclose(
        centered_null_bootstrap_means(difference, indices),
        expected_null_statistics,
        rtol=0.0,
        atol=1e-15,
    )
    assert centered_null_bootstrap_p_value(difference, indices) == expected_p


def test_centered_null_positive_mean_is_small_and_zero_mean_is_not_mechanically_significant():
    indices = stationary_bootstrap_indices(64, 10_000, 5, np.random.default_rng(_seed_for_block(5)))
    positive = np.full(64, 0.002, dtype=float)
    positive += np.sin(np.arange(64, dtype=float)) * 0.00005
    positive_p = centered_null_bootstrap_p_value(positive, indices)
    assert positive.mean() > 0.0 and positive_p < 0.01

    zero_mean = np.tile(np.array([0.001, 0.001, -0.001, -0.001], dtype=float), 16)
    zero_p = centered_null_bootstrap_p_value(zero_mean, indices)
    assert abs(zero_mean.mean()) < 1e-15
    assert zero_p > 0.01


def test_centered_null_monte_carlo_correction_has_no_zero_p_values():
    difference = np.linspace(-0.01, 0.02, 37, dtype=float)
    replications = 101
    indices = stationary_bootstrap_indices(37, replications, 7, np.random.default_rng(9182))
    p_value = centered_null_bootstrap_p_value(difference, indices)
    assert 1.0 / (replications + 1) <= p_value <= 1.0
    assert p_value != 0.0


def test_centered_null_is_invariant_to_chunking_with_the_same_index_stream():
    difference = np.array([0.003, -0.001, 0.002, 0.004, -0.002, 0.001, 0.0, 0.002], dtype=float)
    indices = stationary_bootstrap_indices(8, 103, 3, np.random.default_rng(1122))
    observed_mean_daily = float(np.mean(difference))
    full_p = centered_null_bootstrap_p_value(difference, indices)
    exceedances = 0
    for start in range(0, len(indices), 11):
        null_statistics = centered_null_bootstrap_means(
            difference,
            indices[start:start + 11],
            observed_mean_daily=observed_mean_daily,
        )
        exceedances += int(np.count_nonzero(null_statistics >= observed_mean_daily))
    chunked_p = (1 + exceedances) / (len(indices) + 1)
    assert chunked_p == full_p


def test_primary_and_sensitivity_block_lengths_are_frozen():
    config = json.loads((RUN / "bootstrap_configuration.json").read_text(encoding="utf-8"))
    assert PRIMARY_BLOCK_LENGTH == 20
    assert tuple(config["stationary_bootstrap"]["all_expected_block_lengths"]) == (5, 10, 20, 40, 60)
    assert tuple(config["stationary_bootstrap"]["sensitivity_expected_block_lengths"]) == SENSITIVITY_BLOCK_LENGTHS
    results = _read("stationary_bootstrap_results.csv")
    assert results.loc[results.block_role.eq("PRIMARY"), "expected_block_length"].unique().tolist() == [20]
    assert set(results.loc[results.block_role.eq("SENSITIVITY"), "expected_block_length"]) == set(SENSITIVITY_BLOCK_LENGTHS)


def test_bootstrap_replications_meet_minimum_and_index_checksums_are_recorded():
    config = json.loads((RUN / "bootstrap_configuration.json").read_text(encoding="utf-8"))
    results = _read("stationary_bootstrap_results.csv")
    assert config["bootstrap_replications"] >= BOOTSTRAP_REPLICATIONS == 10_000
    assert results.bootstrap_replications.eq(config["bootstrap_replications"]).all()
    assert results.bootstrap_index_sha256.str.len().eq(64).all()
    assert set(config["stationary_bootstrap"]["index_sha256_by_block_length"]) == {str(x) for x in BLOCK_LENGTHS}


def test_observed_metrics_reproduce_paired_daily_return_arithmetic_exactly():
    daily, _, source_hash = _load_inputs()
    observed = _observed_rows(daily)
    assert source_hash == EXPECTED_PHASE8A_DAILY_RETURNS_SHA256
    for _, row in observed.iterrows():
        strategy = daily.loc[daily.strategy_id.eq(row.strategy_id) & daily.frequency.eq(row.strategy_frequency) & daily.tax_mode.eq("pre_tax")].sort_values("date").daily_return.to_numpy()
        benchmark_mode = "benchmark" if row.benchmark_id.endswith("BUY_HOLD") else "pre_tax"
        benchmark = daily.loc[daily.strategy_id.eq(row.benchmark_id) & daily.frequency.eq(row.benchmark_frequency) & daily.tax_mode.eq(benchmark_mode)].sort_values("date").daily_return.to_numpy()
        assert len(strategy) == len(benchmark) == EXPECTED_SESSIONS
        np.testing.assert_allclose(row.annualized_mean_return_difference, (strategy - benchmark).mean() * 252.0, rtol=0.0, atol=1e-14)
        np.testing.assert_allclose(row.sharpe_difference, row.strategy_sharpe - row.benchmark_sharpe, rtol=0.0, atol=1e-14)


def test_bootstrap_probability_and_interval_fields_are_present():
    results = _read("stationary_bootstrap_results.csv")
    required = {
        "ci_lower_95", "ci_upper_95", "probability_difference_gt_zero",
        "probability_strategy_maxdd_ge_benchmark", "one_sided_return_null_p_value",
    }
    assert required.issubset(results.columns)
    for metric in ("annualized_mean_return_difference", "sharpe_difference", "cagr_difference", "calmar_difference"):
        # A zero-volatility/zero-drawdown CASH path has undefined Sharpe or
        # Calmar, so its probability is deliberately unavailable rather than
        # coerced to a misleading zero.
        assert results.loc[results.metric.eq(metric), "probability_difference_gt_zero"].notna().any()
    maxdd = results.loc[results.metric.eq("max_drawdown_difference")]
    assert maxdd.probability_strategy_maxdd_ge_benchmark.notna().all()
    mean_rows = results.loc[results.metric.eq("annualized_mean_return_difference")]
    assert mean_rows.one_sided_return_null_p_value.notna().all()
    assert mean_rows.null_observed_mean_daily.notna().all()
    assert mean_rows.null_bootstrap_exceedance_count.notna().all()
    assert mean_rows.null_p_value_correction.eq("(1 + count(null_bootstrap_stat >= observed_mean_daily)) / (B + 1)").all()
    assert (mean_rows.one_sided_return_null_p_value >= 1.0 / (mean_rows.bootstrap_replications + 1)).all()
    assert (mean_rows.one_sided_return_null_p_value <= 1.0).all()
    assert (mean_rows.one_sided_return_null_p_value > 0.0).all()
    assert (mean_rows.null_bootstrap_exceedance_count >= 0).all()
    assert (mean_rows.null_bootstrap_exceedance_count <= mean_rows.bootstrap_replications).all()


def test_remediation_preserves_observed_metrics_and_ordinary_percentile_cis():
    old_observed = pd.read_csv(PRIOR_RUN / "pairwise_observed_metrics.csv")
    new_observed = _read("pairwise_observed_metrics.csv")
    keys = ["comparison_id", "strategy_frequency"]
    old_observed = old_observed.sort_values(keys).reset_index(drop=True)
    new_observed = new_observed.sort_values(keys).reset_index(drop=True)
    pd.testing.assert_frame_equal(old_observed, new_observed, check_exact=False, rtol=0.0, atol=1e-14)

    old_bootstrap = pd.read_csv(PRIOR_RUN / "stationary_bootstrap_results.csv")
    new_bootstrap = _read("stationary_bootstrap_results.csv")
    ci_keys = ["comparison_id", "strategy_frequency", "expected_block_length", "metric"]
    old_ci = old_bootstrap.set_index(ci_keys)[["ci_lower_95", "ci_upper_95"]].sort_index()
    new_ci = new_bootstrap.set_index(ci_keys)[["ci_lower_95", "ci_upper_95"]].sort_index()
    pd.testing.assert_frame_equal(old_ci, new_ci, check_exact=False, rtol=0.0, atol=1e-14)


def test_remediation_keeps_frozen_index_hashes_and_hac_rows_unchanged():
    old_config = json.loads((PRIOR_RUN / "bootstrap_configuration.json").read_text(encoding="utf-8"))
    new_config = json.loads((RUN / "bootstrap_configuration.json").read_text(encoding="utf-8"))
    assert old_config["stationary_bootstrap"]["index_sha256_by_block_length"] == new_config["stationary_bootstrap"]["index_sha256_by_block_length"]
    old_hac = pd.read_csv(PRIOR_RUN / "hac_mean_return_results.csv").sort_values(["comparison_id", "strategy_frequency"]).reset_index(drop=True)
    new_hac = _read("hac_mean_return_results.csv").sort_values(["comparison_id", "strategy_frequency"]).reset_index(drop=True)
    pd.testing.assert_frame_equal(old_hac, new_hac, check_exact=False, rtol=0.0, atol=1e-14)


def test_remediation_audit_diff_covers_primary_and_sensitivity_p_values():
    diff = (RUN / "phase8b1_audit_diff.md").read_text(encoding="utf-8")
    assert "Explicit null-test correction" in diff
    assert "ordinary uncentered paired strategy/benchmark bootstrap" in diff
    for block_length in BLOCK_LENGTHS:
        assert re.search(rf"\|\s+{block_length}\s+\|", diff)
    assert "changed: **False**" in diff


def test_hac_lag_rule_is_deterministic_and_all_rows_use_lag_eight():
    hac = _read("hac_mean_return_results.csv")
    expected_lag = int(np.floor(4.0 * (EXPECTED_SESSIONS / 100.0) ** (2.0 / 9.0)))
    assert expected_lag == 8
    assert hac.hac_lag.eq(expected_lag).all()
    assert hac.hac_lag_rule.eq("floor(4 * (T / 100)^(2/9))").all()
    daily = _source_daily()
    pd.testing.assert_frame_equal(hac, _hac_mean_return_rows(daily), check_exact=False, rtol=0.0, atol=1e-14)


def test_cash_fallback_zero_return_sessions_are_retained():
    daily = _source_daily()
    for frequency in ("monthly", "bimonthly", "quarterly"):
        cash = daily.loc[
            daily.strategy_id.eq("PHASE7B_MODEL_A_SELECTED")
            & daily.frequency.eq(frequency)
            & daily.tax_mode.eq("pre_tax"),
            "daily_return",
        ]
        assert len(cash) == EXPECTED_SESSIONS and cash.eq(0.0).all()
    # The retained zero-return path is represented in the pairwise outputs.
    assert _read("pairwise_observed_metrics.csv").loc[
        _read("pairwise_observed_metrics.csv").strategy_id.eq("PHASE7B_MODEL_A_SELECTED")
    ].strategy_frequency.nunique() == 4


def test_after_tax_terminal_liquidation_is_descriptive_not_daily_inference():
    bootstrap = _read("stationary_bootstrap_results.csv")
    after = _read("after_tax_descriptive_comparisons.csv")
    daily = _source_daily()
    assert set(bootstrap.tax_mode) == {"pre_tax"}
    assert set(after.tax_mode) == {"after_tax_diagnostic"}
    assert after.terminal_liquidation_is_daily_return.eq(False).all()
    assert after.descriptive_only.eq(True).all() and after.inference_performed.eq(False).all()
    assert daily.loc[daily.tax_mode.eq("after_tax")].daily_return.notna().all()


def test_no_parameter_or_frequency_selection_occurs():
    config = json.loads((RUN / "bootstrap_configuration.json").read_text(encoding="utf-8"))
    report = (RUN / "phase8b1_report.md").read_text(encoding="utf-8")
    assert config["selection_performed"] is False
    assert config["frequency_selection_performed"] is False
    assert config["winner_designation"] is False
    assert config["phase8b2_started"] is False
    assert "No model or frequency is selected" in report
    assert "No frequency selection" in report
    assert not any("selected_parameters" in path.name for path in RUN.iterdir())


def test_report_ends_with_required_phase8b1_status():
    report = (RUN / "phase8b1_report.md").read_text(encoding="utf-8").rstrip()
    assert report.endswith("PHASE 8B-1 NULL-TEST REMEDIATION COMPLETE — AWAITING STATISTICAL AUDIT")


def test_frozen_seed_for_each_block_length_is_deterministic_and_distinct():
    seeds = [_seed_for_block(length) for length in BLOCK_LENGTHS]
    assert len(set(seeds)) == len(BLOCK_LENGTHS)
    assert seeds == [BOOTSTRAP_SEED + length * 1_000_003 for length in BLOCK_LENGTHS]
