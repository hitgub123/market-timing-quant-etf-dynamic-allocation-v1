"""Phase 8B-2: frozen multiple-testing and data-snooping audit.

This module is deliberately downstream-only.  It consumes the accepted
Phase 8B-1 null-test output and the accepted Phase 8A aligned OOS return
snapshot.  It does not call a strategy, selector, tax engine, or optimizer.
All research counts, candidate paths, bootstrap settings, and formulas are
frozen before the output tables are inspected.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import platform
import sys
from statistics import NormalDist

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from experiments.phase8b1_pairwise_inference import (  # noqa: E402
    BLOCK_LENGTHS,
    BOOTSTRAP_CHUNK_SIZE,
    BOOTSTRAP_REPLICATIONS,
    BOOTSTRAP_SEED,
    EXPECTED_PHASE8A_DAILY_RETURNS_SHA256,
    EXPECTED_PHASE8A_CHAMPION_SHA256,
    EXPECTED_SESSIONS,
    FREQUENCIES,
    OOS_END,
    OOS_START,
    PAIRWISE_COMPARISONS,
    PRIMARY_BLOCK_LENGTH,
    _seed_for_block,
    stationary_bootstrap_indices,
)


PHASE8A_SOURCE_RUN_ID = "20260914_phase8a_oos_evidence_consolidation_final"
PHASE8A_RUN = PROJECT_ROOT / "reports/runs" / PHASE8A_SOURCE_RUN_ID
PHASE8B1_SOURCE_RUN_ID = "20260914_phase8b1_null_test_remediation_candidate"
PHASE8B1_RUN = PROJECT_ROOT / "reports/runs" / PHASE8B1_SOURCE_RUN_ID
PHASE8B2_RUN_ID = "20260915_phase8b2_multiple_testing_audit"

EXPECTED_PHASE8B1_HASHES = {
    "pairwise_observed_metrics.csv": "bc8bdc6830797267b8046bd61a9ce826748498c9bddf5a085a31b590840e367b",
    "stationary_bootstrap_results.csv": "7ddb2eaea36fa3ac714669a2f6b69c057b94d43cecbcbb99058714d69f97165b",
    "hac_mean_return_results.csv": "c5e65dcf8d7871caf1ae690c48b494b905c8044038c59e18036be57f133cf8b1",
    "after_tax_descriptive_comparisons.csv": "59af7ddb1e879be122b894fbaac3dd151817923275f6728992443f41c1f7fc55",
    "bootstrap_configuration.json": "2befcea6f833cb83c2cf59389e91212f214fd5e51cba5923909758b3655e5bba",
    "phase8b1_report.md": "a6aa496fc4435efdc82b4deb7e0d6df7e4ee4ca39b8d9a210d9c2d1d98e179ad",
    "phase8b1_audit_diff.md": "873cd0fd82b25903734cd01f98f6fc22e4556dc9e1afd4b051bf5a59ae193a86",
}
EXPECTED_PHASE8A_HASHES = {
    "aligned_daily_returns.csv": EXPECTED_PHASE8A_DAILY_RETURNS_SHA256,
    "oos_champion_table.csv": EXPECTED_PHASE8A_CHAMPION_SHA256,
    "canonical_source_manifest.csv": "3ad085ad440090221f4794f456d18ef2cea433a035a288658c50a12ebbabf6dd",
}

TRADING_DAYS_PER_YEAR = 252.0
EULER_GAMMA = 0.5772156649015329
CONFIRMATORY_COUNT = 20
SECONDARY_FAMILY_COUNT = 4

# The set is frozen before any p-value, DSR, or RC result is read.  It is the
# 16 strategy/frequency paths present in the accepted Phase 8A OOS snapshot,
# all compared to the same QQQ buy-and-hold benchmark.
SNOOPING_CANDIDATE_SET = tuple(
    (strategy_id, frequency)
    for strategy_id in (
        "FIXED_MA200_QQQ_TO_QLD",
        "PHASE7A_FIXED_FOUR_STATE",
        "PHASE7B_MODEL_A_SELECTED",
        "PHASE7B_MODEL_B_SELECTED",
    )
    for frequency in FREQUENCIES
)
SNOOPING_BENCHMARK = ("QQQ_BUY_HOLD", "none", "benchmark")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _json_fingerprint(value: object) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _required_source_hashes() -> dict[str, str]:
    """Verify the accepted Phase 8A/8B-1 source set byte-for-byte."""
    actual: dict[str, str] = {}
    for name, expected in EXPECTED_PHASE8A_HASHES.items():
        path = PHASE8A_RUN / name
        digest = _sha256(path)
        if digest != expected:
            raise AssertionError(f"Phase 8A source hash mismatch for {name}: {digest}")
        actual[f"phase8a/{name}"] = digest
    for name, expected in EXPECTED_PHASE8B1_HASHES.items():
        path = PHASE8B1_RUN / name
        digest = _sha256(path)
        if digest != expected:
            raise AssertionError(f"Phase 8B-1 source hash mismatch for {name}: {digest}")
        actual[f"phase8b1/{name}"] = digest
    return actual


def _load_daily_returns() -> pd.DataFrame:
    _required_source_hashes()
    daily = pd.read_csv(PHASE8A_RUN / "aligned_daily_returns.csv")
    daily["date"] = pd.to_datetime(daily["date"])
    qqq_dates = pd.DatetimeIndex(
        daily.loc[
            daily.strategy_id.eq("QQQ_BUY_HOLD") & daily.tax_mode.eq("benchmark")
        ].sort_values("date").date
    )
    if len(qqq_dates) != EXPECTED_SESSIONS:
        raise AssertionError(f"expected {EXPECTED_SESSIONS} QQQ sessions, got {len(qqq_dates)}")
    if qqq_dates[0] != OOS_START or qqq_dates[-1] != OOS_END or qqq_dates.has_duplicates:
        raise AssertionError("Phase 8A OOS calendar is not the accepted calendar")
    for identity, group in daily.groupby(["strategy_id", "frequency", "tax_mode"], sort=False):
        dates = pd.DatetimeIndex(group.sort_values("date").date)
        if not dates.equals(qqq_dates):
            raise AssertionError(f"identity {identity} is not aligned to the QQQ calendar")
        if group.daily_return.isna().any():
            raise AssertionError(f"missing daily returns for {identity}")
    return daily


def _path_series(
    daily: pd.DataFrame,
    strategy_id: str,
    frequency: str,
    tax_mode: str,
) -> np.ndarray:
    scoped = daily.loc[
        daily.strategy_id.eq(strategy_id)
        & daily.frequency.eq(frequency)
        & daily.tax_mode.eq(tax_mode)
    ].sort_values("date")
    if len(scoped) != EXPECTED_SESSIONS:
        raise AssertionError(f"expected {EXPECTED_SESSIONS} rows for {strategy_id}/{frequency}/{tax_mode}")
    dates = pd.DatetimeIndex(scoped.date)
    if dates[0] != OOS_START or dates[-1] != OOS_END or dates.has_duplicates:
        raise AssertionError("path dates do not cover the accepted OOS span")
    values = scoped.daily_return.to_numpy(dtype=float)
    if not np.isfinite(values).all():
        raise AssertionError("path has non-finite daily returns")
    return values


def _path_identifier(strategy_id: str, frequency: str) -> str:
    return f"{strategy_id}__{frequency}"


def _path_frame(daily: pd.DataFrame) -> pd.DataFrame:
    """Return all required pre-tax/benchmark paths on one exact index."""
    series: dict[str, np.ndarray] = {}
    series[_path_identifier("QQQ_BUY_HOLD", "none")] = _path_series(
        daily, "QQQ_BUY_HOLD", "none", "benchmark"
    )
    for strategy_id, frequency in SNOOPING_CANDIDATE_SET:
        series[_path_identifier(strategy_id, frequency)] = _path_series(
            daily, strategy_id, frequency, "pre_tax"
        )
    return pd.DataFrame(series)


def _bonferroni(p_values: np.ndarray) -> np.ndarray:
    p = np.asarray(p_values, dtype=float)
    if p.ndim != 1 or len(p) == 0 or not np.isfinite(p).all() or np.any((p < 0) | (p > 1)):
        raise ValueError("p-values must be a non-empty finite vector in [0, 1]")
    return np.minimum(1.0, p * len(p))


def _holm(p_values: np.ndarray) -> np.ndarray:
    p = np.asarray(p_values, dtype=float)
    if p.ndim != 1 or len(p) == 0 or not np.isfinite(p).all() or np.any((p < 0) | (p > 1)):
        raise ValueError("p-values must be a non-empty finite vector in [0, 1]")
    order = np.argsort(p, kind="mergesort")
    adjusted_sorted = np.maximum.accumulate((len(p) - np.arange(len(p))) * p[order])
    out = np.empty(len(p), dtype=float)
    out[order] = np.minimum(1.0, adjusted_sorted)
    return out


def _benjamini_hochberg(p_values: np.ndarray) -> np.ndarray:
    p = np.asarray(p_values, dtype=float)
    if p.ndim != 1 or len(p) == 0 or not np.isfinite(p).all() or np.any((p < 0) | (p > 1)):
        raise ValueError("p-values must be a non-empty finite vector in [0, 1]")
    order = np.argsort(p, kind="mergesort")
    ranks = np.arange(1, len(p) + 1, dtype=float)
    raw = p[order] * len(p) / ranks
    adjusted_sorted = np.minimum.accumulate(raw[::-1])[::-1]
    out = np.empty(len(p), dtype=float)
    out[order] = np.minimum(1.0, adjusted_sorted)
    return out


def _primary_pvalue_rows() -> pd.DataFrame:
    source = pd.read_csv(PHASE8B1_RUN / "stationary_bootstrap_results.csv")
    primary = source.loc[
        source.expected_block_length.eq(PRIMARY_BLOCK_LENGTH)
        & source.metric.eq("annualized_mean_return_difference")
    ].copy()
    if len(primary) != CONFIRMATORY_COUNT:
        raise AssertionError(f"expected exactly {CONFIRMATORY_COUNT} Phase 8B-1 primary p-values")
    primary["test_id"] = primary.comparison_id.astype(str) + "__" + primary.strategy_frequency.astype(str)
    if primary.test_id.nunique() != CONFIRMATORY_COUNT:
        raise AssertionError("Phase 8B-1 primary p-value identifiers are not unique")
    primary["comparison_family"] = primary.comparison_id.str.slice(0, 1)
    primary["raw_p_value"] = primary.one_sided_return_null_p_value.astype(float)
    if primary.raw_p_value.isna().any():
        raise AssertionError("primary p-value input contains nulls")
    return primary.sort_values(["comparison_id", "strategy_frequency"]).reset_index(drop=True)


def _adjustment_rows() -> pd.DataFrame:
    source = _primary_pvalue_rows()
    outputs: list[pd.DataFrame] = []
    for scope, grouped in (
        ("confirmatory_20", source),
        ("secondary_comparison_family_sensitivity", source.groupby("comparison_family", sort=True)),
    ):
        if scope == "confirmatory_20":
            groups = [("ALL_PRIMARY_20", grouped)]
        else:
            groups = list(grouped)
        for family_name, frame in groups:
            frame = frame.copy()
            p = frame.raw_p_value.to_numpy(dtype=float)
            frame["adjustment_scope"] = scope
            frame["adjustment_family"] = family_name
            frame["family_test_count"] = len(frame)
            frame["bonferroni_p_value"] = _bonferroni(p)
            frame["holm_p_value"] = _holm(p)
            frame["benjamini_hochberg_q_value"] = _benjamini_hochberg(p)
            frame["posthoc_filtered"] = False
            frame["selection_performed"] = False
            outputs.append(frame[[
                "test_id", "comparison_id", "comparison_family", "strategy_frequency",
                "adjustment_scope", "adjustment_family", "family_test_count",
                "raw_p_value", "bonferroni_p_value", "holm_p_value",
                "benjamini_hochberg_q_value", "posthoc_filtered", "selection_performed",
                "expected_block_length", "bootstrap_replications", "bootstrap_index_sha256",
            ]])
    return pd.concat(outputs, ignore_index=True)


def _inventory_rows() -> pd.DataFrame:
    """Enumerate every frozen Phase 1–7 research family and its count basis."""
    rows = [
        {
            "inventory_id": "A1_PHASE1_PAIR_ALLOCATIONS",
            "phase": "Phase 1", "category": "A", "model_family": "static_pair_allocation",
            "parameter_description": "8 frozen pairs × 21 ten-percent weight steps × 2 frequencies",
            "parameter_combinations": 8 * 21, "frequencies": "monthly|quarterly",
            "number_of_frequencies": 2, "evaluation_units": "full_sample economic allocations",
            "economic_trial_count": 8 * 21 * 2, "result_rows_including_tax_modes": 8 * 21 * 2 * 2,
            "results_used_for_selection": False, "evaluated_full_sample": True, "evaluated_oos": False,
            "pre_specified": True, "data_dependent": False, "conservative_count_included": True,
            "strict_selection_included": False, "source_run_id": "20260914_phase1_audit_final_v2",
            "source_artifact": "metrics_pre_tax.csv + metrics_after_tax.csv",
            "source_grid_basis": "PAIRS=8; candidate_allocations pair units=21 each; FREQUENCIES=monthly,quarterly",
            "notes": "Descriptive static frontier; no deployment parameter selected.",
        },
        {
            "inventory_id": "A2_PHASE1_TRIPLE_ALLOCATIONS",
            "phase": "Phase 1", "category": "A", "model_family": "static_triple_allocation",
            "parameter_description": "5 frozen triples × 66 simplex compositions × 2 frequencies",
            "parameter_combinations": 5 * 66, "frequencies": "monthly|quarterly",
            "number_of_frequencies": 2, "evaluation_units": "full_sample economic allocations",
            "economic_trial_count": 5 * 66 * 2, "result_rows_including_tax_modes": 5 * 66 * 2 * 2,
            "results_used_for_selection": False, "evaluated_full_sample": True, "evaluated_oos": False,
            "pre_specified": True, "data_dependent": False, "conservative_count_included": True,
            "strict_selection_included": False, "source_run_id": "20260914_phase1_audit_final_v2",
            "source_artifact": "metrics_pre_tax.csv + metrics_after_tax.csv",
            "source_grid_basis": "TRIPLES=5; compositions=sum(11+10+...+1)=66; FREQUENCIES=monthly,quarterly",
            "notes": "Descriptive static frontier; no deployment parameter selected.",
        },
        {
            "inventory_id": "B1_PHASE2_MA200_FIXED",
            "phase": "Phase 2", "category": "B", "model_family": "fixed_ma200",
            "parameter_description": "3 frozen rules × 4 frozen frequencies × MA200",
            "parameter_combinations": 3, "frequencies": "weekly|monthly|bimonthly|quarterly",
            "number_of_frequencies": 4, "evaluation_units": "full_sample economic strategy/frequency",
            "economic_trial_count": 3 * 4, "result_rows_including_tax_modes": 3 * 4 * 2,
            "results_used_for_selection": False, "evaluated_full_sample": True, "evaluated_oos": False,
            "pre_specified": True, "data_dependent": False, "conservative_count_included": True,
            "strict_selection_included": False, "source_run_id": "20260914_phase2_audit_final",
            "source_artifact": "metrics_pre_tax.csv + metrics_after_tax.csv",
            "source_grid_basis": "3 rules; ma_window=200; FREQUENCIES=4",
            "notes": "Canonical MA200 regression oracle; no parameter selected.",
        },
        {
            "inventory_id": "B2_PHASE3_MA_STABILITY",
            "phase": "Phase 3", "category": "B", "model_family": "ma_parameter_stability",
            "parameter_description": "3 rules × 5 MA windows × 4 frequencies",
            "parameter_combinations": 3 * 5, "frequencies": "weekly|monthly|bimonthly|quarterly",
            "number_of_frequencies": 4, "evaluation_units": "full_sample economic parameter/frequency",
            "economic_trial_count": 3 * 5 * 4, "result_rows_including_tax_modes": 3 * 5 * 4 * 2,
            "results_used_for_selection": False, "evaluated_full_sample": True, "evaluated_oos": False,
            "pre_specified": True, "data_dependent": False, "conservative_count_included": True,
            "strict_selection_included": False, "source_run_id": "20260914_phase3_audit_final_v3",
            "source_artifact": "ma_parameter_surface.csv",
            "source_grid_basis": "MA_WINDOWS=(150,175,200,225,250); 3 rules; 4 frequencies",
            "notes": "Descriptive sensitivity grid; no window selected for deployment.",
        },
        {
            "inventory_id": "C_PHASE4_ABSOLUTE_MOMENTUM",
            "phase": "Phase 4", "category": "C", "model_family": "absolute_momentum",
            "parameter_description": "2 rule families × 3 momentum windows × 4 frequencies",
            "parameter_combinations": 2 * 3, "frequencies": "weekly|monthly|bimonthly|quarterly",
            "number_of_frequencies": 4, "evaluation_units": "full_sample economic parameter/frequency",
            "economic_trial_count": 2 * 3 * 4, "result_rows_including_tax_modes": 2 * 3 * 4 * 2,
            "results_used_for_selection": False, "evaluated_full_sample": True, "evaluated_oos": False,
            "pre_specified": True, "data_dependent": False, "conservative_count_included": True,
            "strict_selection_included": False, "source_run_id": "20260914_phase4_audit_final",
            "source_artifact": "absolute_momentum_results.csv",
            "source_grid_basis": "MOMENTUM_WINDOWS=(126,189,252); 2 rules; 4 frequencies",
            "notes": "Descriptive full-sample momentum grid; no parameter selected.",
        },
        {
            "inventory_id": "D_PHASE5_RELATIVE_MOMENTUM",
            "phase": "Phase 5", "category": "D", "model_family": "relative_momentum",
            "parameter_description": "2 variants × 3 momentum windows × 4 frequencies",
            "parameter_combinations": 2 * 3, "frequencies": "weekly|monthly|bimonthly|quarterly",
            "number_of_frequencies": 4, "evaluation_units": "full_sample economic parameter/frequency",
            "economic_trial_count": 2 * 3 * 4, "result_rows_including_tax_modes": 2 * 3 * 4 * 2,
            "results_used_for_selection": False, "evaluated_full_sample": True, "evaluated_oos": False,
            "pre_specified": True, "data_dependent": False, "conservative_count_included": True,
            "strict_selection_included": False, "source_run_id": "20260914_phase5_audit_final",
            "source_artifact": "relative_momentum_results.csv",
            "source_grid_basis": "MOMENTUM_WINDOWS=(126,189,252); 2 variants; 4 frequencies",
            "notes": "Descriptive full-sample relative-momentum grid; no parameter selected.",
        },
        {
            "inventory_id": "E_PHASE6_VOLATILITY_TARGETING",
            "phase": "Phase 6", "category": "E", "model_family": "volatility_targeting",
            "parameter_description": "4 assets × 3 volatility windows × 5 target vols × 4 frequencies",
            "parameter_combinations": 4 * 3 * 5, "frequencies": "weekly|monthly|bimonthly|quarterly",
            "number_of_frequencies": 4, "evaluation_units": "full_sample economic parameter/frequency",
            "economic_trial_count": 4 * 3 * 5 * 4, "result_rows_including_tax_modes": 4 * 3 * 5 * 4 * 2,
            "results_used_for_selection": False, "evaluated_full_sample": True, "evaluated_oos": False,
            "pre_specified": True, "data_dependent": False, "conservative_count_included": True,
            "strict_selection_included": False, "source_run_id": "20260914_phase6_audit_final",
            "source_artifact": "vol_parameter_surface.csv",
            "source_grid_basis": "assets=4; VOL_WINDOWS=(20,40,60); TARGET_VOLS=5; FREQUENCIES=4",
            "notes": "Descriptive full-sample volatility grid; no target selected.",
        },
        {
            "inventory_id": "F_PHASE7A_FIXED_FOUR_STATE",
            "phase": "Phase 7A", "category": "F", "model_family": "fixed_four_state",
            "parameter_description": "1 frozen rule × 4 frequencies × 2 reporting periods (full sample and chronological OOS)",
            "parameter_combinations": 1, "frequencies": "weekly|monthly|bimonthly|quarterly",
            "number_of_frequencies": 4, "evaluation_units": "full_sample and chronological OOS economic views",
            "economic_trial_count": 4 * 2, "result_rows_including_tax_modes": 4 * 2 * 2,
            "results_used_for_selection": False, "evaluated_full_sample": True, "evaluated_oos": True,
            "pre_specified": True, "data_dependent": False, "conservative_count_included": True,
            "strict_selection_included": False, "source_run_id": "20260913_phase7a_metrics_tax_audited_final",
            "source_artifact": "phase7a_results.csv",
            "source_grid_basis": "fixed rule; FREQUENCIES=4; period in {full_sample, chronological_oos}",
            "notes": "The two period views are not additional deployable strategies; both are inventoried explicitly.",
        },
        {
            "inventory_id": "G_PHASE7B_MODEL_A_TRAINING_CANDIDATES",
            "phase": "Phase 7B", "category": "G", "model_family": "model_a_walk_forward_candidates",
            "parameter_description": "5 MA candidates × 4 frequencies × 14 expanding test-year folds",
            "parameter_combinations": 5, "frequencies": "weekly|monthly|bimonthly|quarterly",
            "number_of_frequencies": 4, "evaluation_units": "training candidate/frequency/fold evaluation",
            "economic_trial_count": 5 * 4 * 14, "result_rows_including_tax_modes": 5 * 4 * 14,
            "results_used_for_selection": True, "evaluated_full_sample": False, "evaluated_oos": True,
            "pre_specified": True, "data_dependent": True, "conservative_count_included": True,
            "strict_selection_included": True, "source_run_id": "20260914_phase7b_turnover_audit_final",
            "source_artifact": "training_candidate_results.csv",
            "source_grid_basis": "phase7b_parameter_grid.yaml: Model A MA days=150,175,200,225,250; 14 folds; 4 frequencies",
            "notes": "Every candidate/fold was eligible to affect a selected OOS path; no candidates removed post hoc.",
        },
        {
            "inventory_id": "H_PHASE7B_MODEL_B_TRAINING_CANDIDATES",
            "phase": "Phase 7B", "category": "H", "model_family": "model_b_walk_forward_candidates",
            "parameter_description": "5 MA × 3 momentum × 3 low-vol quantiles × 4 frequencies × 14 folds",
            "parameter_combinations": 5 * 3 * 3, "frequencies": "weekly|monthly|bimonthly|quarterly",
            "number_of_frequencies": 4, "evaluation_units": "training candidate/frequency/fold evaluation",
            "economic_trial_count": 5 * 3 * 3 * 4 * 14, "result_rows_including_tax_modes": 5 * 3 * 3 * 4 * 14,
            "results_used_for_selection": True, "evaluated_full_sample": False, "evaluated_oos": True,
            "pre_specified": True, "data_dependent": True, "conservative_count_included": True,
            "strict_selection_included": True, "source_run_id": "20260914_phase7b_turnover_audit_final",
            "source_artifact": "training_candidate_results.csv",
            "source_grid_basis": "phase7b_parameter_grid.yaml: MA=5, momentum=3, low_vol_quantile=3; 14 folds; 4 frequencies",
            "notes": "Every candidate/fold was eligible to affect a selected OOS path; no candidates removed post hoc.",
        },
        {
            "inventory_id": "I_REBALANCE_FREQUENCY_DIMENSION",
            "phase": "Phase 1–7", "category": "I", "model_family": "rebalance_frequency_variants",
            "parameter_description": "Cross-cutting frequency dimension: weekly, monthly, bimonthly, quarterly",
            "parameter_combinations": 4, "frequencies": "weekly|monthly|bimonthly|quarterly",
            "number_of_frequencies": 4, "evaluation_units": "dimension already counted in each family above",
            "economic_trial_count": 0, "result_rows_including_tax_modes": 0,
            "results_used_for_selection": True, "evaluated_full_sample": True, "evaluated_oos": True,
            "pre_specified": True, "data_dependent": False, "conservative_count_included": False,
            "strict_selection_included": False, "source_run_id": "multiple canonical Phase 1–7 runs",
            "source_artifact": "frequency columns in canonical result tables",
            "source_grid_basis": "FREQUENCIES=(weekly, monthly, bimonthly, quarterly) where applicable",
            "notes": "Enumerated explicitly to prevent hiding frequency multiplicity; zero count prevents double counting.",
        },
    ]
    return pd.DataFrame(rows)


def _inventory_counts(inventory: pd.DataFrame) -> dict[str, int]:
    strict = int(inventory.loc[inventory.strict_selection_included, "economic_trial_count"].sum())
    conservative = int(inventory.loc[inventory.conservative_count_included, "economic_trial_count"].sum())
    result_rows = int(inventory["result_rows_including_tax_modes"].sum())
    if strict != 2_800:
        raise AssertionError(f"strict selection trial count must be 2800, got {strict}")
    if conservative != 4_164:
        raise AssertionError(f"conservative research trial count must be 4164, got {conservative}")
    if result_rows != 5_528:
        raise AssertionError(f"result-row inventory count must be 5528, got {result_rows}")
    return {
        "strict_selection_trials": strict,
        "conservative_research_trials": conservative,
        "conservative_result_rows_including_tax_modes": result_rows,
    }


def _validate_source_grid_rows() -> dict[str, int]:
    """Reconcile the inventory to the delivered canonical grid artifacts."""
    runs = PROJECT_ROOT / "reports/runs"
    expected = {
        "phase1_metrics_pre_tax": (runs / "20260914_phase1_audit_final_v2/metrics_pre_tax.csv", 996),
        "phase1_metrics_after_tax": (runs / "20260914_phase1_audit_final_v2/metrics_after_tax.csv", 996),
        "phase2_metrics_pre_tax": (runs / "20260914_phase2_audit_final/metrics_pre_tax.csv", 12),
        "phase2_metrics_after_tax": (runs / "20260914_phase2_audit_final/metrics_after_tax.csv", 12),
        "phase3_surface": (runs / "20260914_phase3_audit_final_v3/ma_parameter_surface.csv", 120),
        "phase4_surface": (runs / "20260914_phase4_audit_final/absolute_momentum_results.csv", 48),
        "phase5_surface": (runs / "20260914_phase5_audit_final/relative_momentum_results.csv", 48),
        "phase6_surface": (runs / "20260914_phase6_audit_final/vol_parameter_surface.csv", 480),
        "phase7a_results": (runs / "20260913_phase7a_metrics_tax_audited_final/phase7a_results.csv", 16),
        "phase7b_training_candidates": (runs / "20260914_phase7b_turnover_audit_final/training_candidate_results.csv", 2800),
    }
    actual: dict[str, int] = {}
    for label, (path, count) in expected.items():
        if not path.is_file():
            raise AssertionError(f"missing canonical grid artifact: {path}")
        actual[label] = int(len(pd.read_csv(path)))
        if actual[label] != count:
            raise AssertionError(f"{label} expected {count} rows, got {actual[label]}")
    return actual


def _moment_statistics(returns: np.ndarray) -> dict[str, float]:
    values = np.asarray(returns, dtype=float)
    if values.ndim != 1 or len(values) < 2 or not np.isfinite(values).all():
        raise ValueError("returns must be a finite one-dimensional vector with at least two observations")
    mean = float(np.mean(values))
    std = float(np.std(values, ddof=1))
    if std > 0:
        sharpe = mean / std * math.sqrt(TRADING_DAYS_PER_YEAR)
        centered = values - mean
        m2 = float(np.mean(centered ** 2))
        skewness = float(np.mean(centered ** 3) / m2 ** 1.5)
        excess_kurtosis = float(np.mean(centered ** 4) / m2 ** 2 - 3.0)
    else:
        sharpe = 0.0
        skewness = 0.0
        excess_kurtosis = 0.0
    return {
        "mean_daily_return": mean,
        "sample_std_daily_return": std,
        "observed_sharpe": float(sharpe),
        "skewness": skewness,
        "excess_kurtosis": excess_kurtosis,
        "n_observations": int(len(values)),
    }


def _expected_max_z(trial_count: float) -> float:
    """Legacy pathwise benchmark helper retained only for audit diffing.

    This helper is not a Bailey–López de Prado DSR implementation because it
    has no independently reconstructed cross-trial Sharpe distribution.
    """
    n = float(trial_count)
    if not np.isfinite(n) or n < 1:
        raise ValueError("trial_count must be finite and at least one")
    if n <= 1.0:
        return 0.0
    normal = NormalDist()
    # Bailey–López de Prado's Euler-constant approximation to the expected
    # maximum of N standard-normal Sharpe estimates.
    return float(
        (1.0 - EULER_GAMMA) * normal.inv_cdf(1.0 - 1.0 / n)
        + EULER_GAMMA * normal.inv_cdf(1.0 - 1.0 / (n * math.e))
    )


def legacy_pathwise_sharpe_diagnostic(
    observed_sharpe: float,
    n_observations: int,
    skewness: float,
    excess_kurtosis: float,
    trial_count: float,
) -> dict[str, float]:
    """Legacy pathwise Sharpe diagnostic; explicitly not Bailey–López DSR.

    The former Phase 8B-2 run used the observed path's sampling SE as a
    cross-trial dispersion proxy.  It is retained only so the old artifact can
    be identified in the remediation diff.  It must not be called DSR or used
    as evidence.
    """
    if n_observations <= 1 or trial_count < 1:
        raise ValueError("n_observations must exceed one and trial_count must be positive")
    s = float(observed_sharpe)
    skew = float(skewness)
    excess = float(excess_kurtosis)
    variance_factor = 1.0 - skew * s + ((excess + 2.0) / 4.0) * s * s
    sigma = math.sqrt(max(0.0, variance_factor / float(n_observations - 1)))
    expected_max = sigma * _expected_max_z(float(trial_count))
    if sigma == 0.0:
        probability = 1.0 if s > expected_max else 0.0
    else:
        probability = float(NormalDist().cdf((s - expected_max) / sigma))
    return {
        "sharpe_standard_error": float(sigma),
        "expected_max_sharpe": float(expected_max),
        "dsr_probability": probability,
        "expected_max_z": float(_expected_max_z(float(trial_count))),
    }


def _correlation_summary(paths: pd.DataFrame) -> tuple[pd.DataFrame, float]:
    # CASH-fallback paths can be identically zero, for which Pearson
    # correlation is undefined.  Treat those off-diagonals as zero and keep
    # the correlation matrix's diagonal at one; this is the conservative,
    # explicitly documented convention for the effective-trial sensitivity.
    corr = paths.corr().fillna(0.0).to_numpy(dtype=float).copy()
    np.fill_diagonal(corr, 1.0)
    eigenvalues = np.linalg.eigvalsh(corr)
    eigenvalues = np.clip(eigenvalues, 0.0, None)
    effective = float((eigenvalues.sum() ** 2) / np.sum(eigenvalues ** 2)) if np.sum(eigenvalues ** 2) else 1.0
    names = list(paths.columns)
    rows: list[dict[str, object]] = []
    for i, left in enumerate(names):
        offdiag = np.delete(corr[i], i)
        for j, right in enumerate(names):
            rows.append({
                "path_id": left,
                "other_path_id": right,
                "correlation": float(corr[i, j]),
                "diagonal": bool(i == j),
                "mean_abs_offdiag_correlation": float(np.mean(np.abs(offdiag))) if len(offdiag) else 0.0,
                "max_abs_offdiag_correlation": float(np.max(np.abs(offdiag))) if len(offdiag) else 0.0,
                "estimated_effective_trials": effective,
                "effective_trial_method": "participation ratio (sum eigenvalues)^2 / sum eigenvalues^2 on 17 accepted Phase 8A pre-tax paths",
            })
    return pd.DataFrame(rows), effective


def _dsr_rows(paths: pd.DataFrame, strict_count: int, conservative_count: int, effective_count: float) -> tuple[pd.DataFrame, pd.DataFrame]:
    primary_rows: list[dict[str, object]] = []
    sensitivity_counts = sorted({1.0, 2.0, 4.0, 8.0, 16.0, float(max(1.0, min(17.0, effective_count)))})
    sensitivity_rows: list[dict[str, object]] = []
    for path_id in paths.columns:
        stats = _moment_statistics(paths[path_id].to_numpy(dtype=float))
        strategy_id, frequency = path_id.rsplit("__", 1)
        role = "QQQ reference" if strategy_id == "QQQ_BUY_HOLD" else "accepted pre-tax OOS strategy path"
        for basis, count in (("strict_selection_trials", strict_count), ("conservative_research_trials", conservative_count)):
            result = legacy_pathwise_sharpe_diagnostic(
                stats["observed_sharpe"], stats["n_observations"], stats["skewness"], stats["excess_kurtosis"], count
            )
            correlation_result = legacy_pathwise_sharpe_diagnostic(
                stats["observed_sharpe"], stats["n_observations"], stats["skewness"], stats["excess_kurtosis"], effective_count
            )
            primary_rows.append({
                "path_id": path_id, "strategy_id": strategy_id, "frequency": frequency,
                "tax_mode": "benchmark" if strategy_id == "QQQ_BUY_HOLD" else "pre_tax",
                "path_role": role, "start_date": OOS_START.date().isoformat(), "end_date": OOS_END.date().isoformat(),
                "n_observations": stats["n_observations"], "observed_sharpe": stats["observed_sharpe"],
                "skewness": stats["skewness"], "excess_kurtosis": stats["excess_kurtosis"],
                "trial_count_basis": basis, "trial_count_raw": count,
                "effective_trial_count_used": count,
                "effective_trial_method": "raw frozen research count used for primary DSR expected maximum; correlation sensitivity is separate",
                **result,
                "correlation_adjusted_effective_trial_count": effective_count,
                "correlation_adjusted_expected_max_sharpe": correlation_result["expected_max_sharpe"],
                "correlation_adjusted_dsr_probability": correlation_result["dsr_probability"],
                "selection_performed": False,
            })
        for count in sensitivity_counts:
            result = legacy_pathwise_sharpe_diagnostic(
                stats["observed_sharpe"], stats["n_observations"], stats["skewness"], stats["excess_kurtosis"], count
            )
            sensitivity_rows.append({
                "path_id": path_id, "strategy_id": strategy_id, "frequency": frequency,
                "observed_sharpe": stats["observed_sharpe"], "skewness": stats["skewness"],
                "excess_kurtosis": stats["excess_kurtosis"], "effective_trial_count": count,
                "effective_trial_source": "fixed sensitivity grid; estimated path participation ratio included separately",
                **result, "selection_performed": False,
            })
    return pd.DataFrame(primary_rows), pd.DataFrame(sensitivity_rows)


def _white_reality_check(paths: pd.DataFrame, n_replications: int = BOOTSTRAP_REPLICATIONS) -> tuple[pd.DataFrame, dict[int, str]]:
    benchmark = paths[_path_identifier(*SNOOPING_BENCHMARK[:2])].to_numpy(dtype=float)
    candidate_names = [_path_identifier(*key) for key in SNOOPING_CANDIDATE_SET]
    candidates = paths[candidate_names].to_numpy(dtype=float).T
    differences = candidates - benchmark[None, :]
    observed_annualized = differences.mean(axis=1) * TRADING_DAYS_PER_YEAR
    observed_max = float(np.max(observed_annualized))
    observed_index = int(np.argmax(observed_annualized))
    rows: list[dict[str, object]] = []
    checksums: dict[int, str] = {}
    for block_length in BLOCK_LENGTHS:
        rng = np.random.default_rng(_seed_for_block(block_length))
        digest = hashlib.sha256()
        null_max = np.empty(n_replications, dtype=float)
        centered = differences - differences.mean(axis=1, keepdims=True)
        cursor = 0
        while cursor < n_replications:
            count = min(BOOTSTRAP_CHUNK_SIZE, n_replications - cursor)
            indices = stationary_bootstrap_indices(EXPECTED_SESSIONS, count, block_length, rng)
            digest.update(indices.tobytes())
            # Shape (candidate, replication, session), kept within one chunk.
            bootstrap_means = centered[:, indices].mean(axis=2) * TRADING_DAYS_PER_YEAR
            null_max[cursor:cursor + count] = bootstrap_means.max(axis=0)
            cursor += count
        checksum = digest.hexdigest()
        checksums[block_length] = checksum
        exceedances = int(np.count_nonzero(null_max >= observed_max))
        rows.append({
            "test": "white_reality_check",
            "benchmark_id": SNOOPING_BENCHMARK[0], "benchmark_frequency": SNOOPING_BENCHMARK[1],
            "benchmark_tax_mode": SNOOPING_BENCHMARK[2], "candidate_count": len(candidate_names),
            "candidate_set_fingerprint": _json_fingerprint(candidate_names),
            "candidate_set": "|".join(candidate_names), "candidate_max_statistic_path": candidate_names[observed_index],
            "observed_max_annualized_excess_mean": observed_max,
            "bootstrap_null": "each candidate differential recentered d0_t=d_t-mean(d_t); max annualized mean(d0_t[indices])",
            "recentered": True, "truncation": "none",
            "expected_block_length": block_length,
            "block_role": "PRIMARY" if block_length == PRIMARY_BLOCK_LENGTH else "SENSITIVITY",
            "bootstrap_method": "stationary_bootstrap_politis_romano",
            "bootstrap_replications": n_replications, "bootstrap_chunk_size": BOOTSTRAP_CHUNK_SIZE,
            "random_seed": BOOTSTRAP_SEED, "bootstrap_index_sha256": checksum,
            "null_max_exceedance_count": exceedances,
            "p_value": float((1 + exceedances) / (n_replications + 1)),
            "selection_performed": False,
        })
    return pd.DataFrame(rows), checksums


def _configuration(
    source_hashes: dict[str, str], inventory_counts: dict[str, int],
    adjustments: pd.DataFrame, dsr: pd.DataFrame, snooping: pd.DataFrame,
    effective_trials: float, index_checksums: dict[int, str], source_grid_rows: dict[str, int],
) -> dict[str, object]:
    candidate_names = [_path_identifier(*key) for key in SNOOPING_CANDIDATE_SET]
    return {
        "phase": "8B-2",
        "phase8a_source_run_id": PHASE8A_SOURCE_RUN_ID,
        "phase8b1_source_run_id": PHASE8B1_SOURCE_RUN_ID,
        "source_hashes": source_hashes,
        "oos_start": OOS_START.date().isoformat(), "oos_end": OOS_END.date().isoformat(),
        "expected_sessions": EXPECTED_SESSIONS,
        "research_trial_inventory": {
            "artifact": "research_trial_inventory.csv",
            **inventory_counts,
            "economic_trial_basis": "one evaluated strategy/parameter/frequency or candidate/frequency/fold return hypothesis; tax-mode rows are accounting views, not independent return hypotheses",
            "strict_selection_definition": "only Phase 7B Model A and Model B candidate/frequency/fold evaluations that could directly affect selected OOS parameters",
            "conservative_definition": "all enumerated Phase 1–7 economic units, including both Phase 7A period views, with no post-hoc filtering",
            "tax_mode_result_rows_including_views": inventory_counts["conservative_result_rows_including_tax_modes"],
            "canonical_source_grid_row_counts": source_grid_rows,
        },
        "multiple_testing": {
            "source": f"{PHASE8B1_SOURCE_RUN_ID}/stationary_bootstrap_results.csv",
            "primary_metric": "annualized_mean_return_difference",
            "primary_expected_block_length": PRIMARY_BLOCK_LENGTH,
            "primary_family_count": CONFIRMATORY_COUNT,
            "primary_raw_p_values_retained": True,
            "adjustments": ["Bonferroni", "Holm step-down", "Benjamini-Hochberg q"],
            "formulas": {
                "Bonferroni": "min(1, m*p_i)",
                "Holm": "sort p; adjusted_i=max(previous,(m-rank+1)*p_i), cap at 1",
                "Benjamini-Hochberg": "sort p; q_i=min_{j>=i}(m/j*p_(j)), cap at 1",
            },
            "secondary_comparison_family_sensitivity_count": SECONDARY_FAMILY_COUNT,
            "posthoc_filtering": False,
            "selection_performed": False,
        },
        "legacy_pathwise_sharpe_diagnostic": {
            "status": "NOT_BAILEY_LOPEZ_DE_PRADO_DSR",
            "paths": "Historical Phase 8B-2 pathwise diagnostic retained only for the remediation diff",
            "path_count": len(dsr.path_id.unique()),
            "warning": "The former output reused one path's sampling SE as cross-trial Sharpe dispersion. It is not a valid DSR and is not evidence.",
            "selection_performed": False,
        },
        "data_snooping": {
            "test": "White Reality Check",
            "benchmark": {"strategy_id": SNOOPING_BENCHMARK[0], "frequency": SNOOPING_BENCHMARK[1], "tax_mode": SNOOPING_BENCHMARK[2]},
            "candidate_set": candidate_names,
            "candidate_set_fingerprint": _json_fingerprint(candidate_names),
            "candidate_set_frozen_before_results": True,
            "loss_differential": "candidate daily return - QQQ benchmark daily return; higher return is better",
            "statistic": "max over all 16 candidates of annualized mean differential",
            "null": "recenter every differential by its observed mean and apply common stationary-bootstrap indices",
            "recentered": True, "truncation": "none",
            "method": "Politis-Romano stationary bootstrap",
            "block_lengths": list(BLOCK_LENGTHS), "primary_block_length": PRIMARY_BLOCK_LENGTH,
            "bootstrap_replications": BOOTSTRAP_REPLICATIONS, "bootstrap_chunk_size": BOOTSTRAP_CHUNK_SIZE,
            "random_seed": BOOTSTRAP_SEED,
            "index_sha256_by_block_length": {str(k): v for k, v in index_checksums.items()},
            "selection_performed": False,
            "why_white_reality_check_only": "White Reality Check directly answers the frozen max-statistic question across the complete candidate family; a second SPA implementation would duplicate an unplanned test rather than add a new pre-specified decision.",
        },
        "interpretation_hierarchy": [
            "descriptive pairwise economic/path evidence",
            "confirmatory 20-test adjusted mean-return evidence",
            "research-program snooping evidence from the frozen inventory and White Reality Check",
            "complexity evidence remains descriptive",
        ],
        "selection_performed": False, "frequency_selection_performed": False,
        "model_selection_performed": False, "winner_designation": False,
        "prior_phase_artifacts_rewritten": False,
        "software_versions": {"python": platform.python_version(), "numpy": np.__version__, "pandas": pd.__version__},
    }


def _write_report(
    output: Path, inventory: pd.DataFrame, adjustments: pd.DataFrame, dsr: pd.DataFrame,
    snooping: pd.DataFrame, config: dict[str, object], effective_trials: float,
) -> None:
    primary = adjustments.loc[adjustments.adjustment_scope.eq("confirmatory_20")].copy()
    primary_view = primary[[
        "test_id", "comparison_id", "strategy_frequency", "raw_p_value",
        "bonferroni_p_value", "holm_p_value", "benjamini_hochberg_q_value",
    ]]
    dsr_view = dsr[[
        "path_id", "trial_count_basis", "observed_sharpe", "skewness", "excess_kurtosis",
        "trial_count_raw", "effective_trial_count_used", "expected_max_sharpe", "dsr_probability",
        "correlation_adjusted_dsr_probability",
    ]]
    rc_view = snooping[[
        "expected_block_length", "block_role", "candidate_count",
        "observed_max_annualized_excess_mean", "p_value", "bootstrap_index_sha256",
    ]]
    summary = inventory[[
        "inventory_id", "phase", "category", "model_family", "economic_trial_count",
        "result_rows_including_tax_modes", "results_used_for_selection",
        "strict_selection_included", "conservative_count_included",
    ]]
    lines = [
        "# Phase 8B-2 — Multiple Testing and Data-Snooping Audit",
        "",
        "This downstream audit consumes the accepted Phase 8B-1 remediated candidate and the immutable Phase 8A aligned daily-return snapshot. It changes no strategy, signal, execution, accounting, tax, OOS, bootstrap, pairwise, or prior-phase artifact.",
        "",
        "## Frozen inputs and scope",
        "",
        f"The common OOS calendar is **{OOS_START.date()} through {OOS_END.date()}**, exactly **{EXPECTED_SESSIONS:,}** accepted sessions. Phase 8A source run: `{PHASE8A_SOURCE_RUN_ID}`. Phase 8B-1 source run: `{PHASE8B1_SOURCE_RUN_ID}`. All source hashes are recorded in `phase8b2_configuration.json` and were verified before this audit output was created.",
        "",
        "Phase 8B-2 performs no model or frequency selection. It enumerates the frozen research history, adjusts the already-issued 20 primary Phase 8B-1 mean-return p-values, retains a legacy pathwise Sharpe diagnostic only for audit comparison, and applies a frozen White Reality Check candidate set.",
        "",
        "## Research-trial inventory",
        "",
        "Categories A–I explicitly enumerate static allocation, MA, momentum, relative-momentum, volatility-target, fixed-state, walk-forward Model A/Model B candidate, and rebalance-frequency dimensions. The inventory includes every listed grid unit and every Phase 7B candidate/frequency/fold; no poor result is removed. Tax-mode rows are reported separately as accounting views and are not counted as independent return hypotheses.",
        "",
        summary.to_markdown(index=False),
        "",
        f"Strict selection trials = **{config['research_trial_inventory']['strict_selection_trials']:,}** (only candidates that could directly affect a selected Phase 7B OOS parameter). Conservative research trials = **{config['research_trial_inventory']['conservative_research_trials']:,}**. The corresponding source result rows including tax/accounting views total **{config['research_trial_inventory']['conservative_result_rows_including_tax_modes']:,}**.",
        "",
        "## Multiple-testing adjustment",
        "",
        f"The confirmatory family is exactly **{CONFIRMATORY_COUNT}** rows: the five frozen Phase 8B-1 comparisons at four frequencies, primary block length {PRIMARY_BLOCK_LENGTH}, metric `annualized_mean_return_difference`. Raw p-values are retained. Bonferroni, Holm step-down, and Benjamini–Hochberg q-values are computed across all 20 rows with no post-hoc filtering. A separate four-row-per-comparison-family sensitivity is labeled secondary and does not replace the confirmatory family.",
        "",
        primary_view.to_markdown(index=False),
        "",
        "## Legacy pathwise Sharpe diagnostic (not DSR)",
        "",
        "The historical run contains a pathwise Sharpe penalty table for the QQQ reference and every accepted pre-tax OOS path. It is retained only as a legacy comparison artifact. Because it reused the observed path's own sampling SE as cross-trial dispersion, it is explicitly not Bailey–López de Prado DSR and is not used for a conclusion. The corrected remediation candidate reports DSR_NOT_IDENTIFIABLE_FROM_FROZEN_ARTIFACTS instead.",
        "",
        "The former approximation is not accepted as DSR. The corrected equations, required cross-trial inputs, and identifiability decision are in the remediation candidate's phase8b2_dsr_remediation.md.",
        "",
        f"Estimated effective path count (sensitivity) = **{effective_trials:.6f}**.",
        "",
        dsr_view.to_markdown(index=False),
        "",
        "## White Reality Check",
        "",
        "The candidate set was frozen before reading any Phase 8B-2 result: the 16 accepted strategy/frequency pre-tax paths (Fixed MA200, Phase 7A, Model A, Model B; four frequencies each) versus the QQQ buy-and-hold benchmark on the identical 3,436-session index. The loss differential is candidate return minus benchmark return, and the statistic is the maximum annualized mean differential across all 16 candidates. Each differential is recentered by its observed mean under the null; common Politis–Romano stationary-bootstrap indices are applied to every candidate. The primary block is 20, replications are 10,000, sensitivity blocks are 5, 10, 40, and 60, and truncation is none. A finite-replication p-value uses (1 + exceedances)/(B + 1).",
        "",
        "Only White Reality Check is implemented: it directly tests the frozen maximum-statistic family. A second Hansen SPA implementation was not added because it would duplicate an unplanned inferential layer without changing the frozen decision boundary.",
        "",
        rc_view.to_markdown(index=False),
        "",
        "## Interpretation boundary",
        "",
        "Interpretation is hierarchical: (1) descriptive pairwise economic/path evidence, (2) the adjusted 20-test confirmatory mean-return family, (3) research-program snooping evidence from the complete inventory and White Reality Check, and (4) descriptive complexity evidence. MaxDD and Calmar remain descriptive path/risk diagnostics, not hidden multiple-testing outcomes. No winner, optimal parameter, recommended frequency, score, reoptimization, OOS claim beyond the frozen source, or Walk-Forward selection is made here. Walk-Forward parameter selection remains confined to the already accepted Phase 7B process.",
        "",
        "The frozen configuration, source hashes, candidate fingerprint, bootstrap index hashes, legacy warning, and no-selection flags are machine-readable in `phase8b2_configuration.json`.",
        "",
        "PHASE 8B-2 MULTIPLE-TESTING AUDIT COMPLETE — NO MODEL OR FREQUENCY SELECTION PERFORMED",
    ]
    (output / "phase8b2_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_audit_diff(output: Path, source_hashes: dict[str, str], inventory_counts: dict[str, int], config: dict[str, object]) -> None:
    new_hashes = {path.name: _sha256(path) for path in sorted(output.iterdir()) if path.is_file()}
    lines = [
        "# Phase 8B-2 audit diff",
        "",
        "This is a downstream statistical/reporting audit only. Phase 0–8B-1 source artifacts were verified byte-for-byte and were not rewritten.",
        "",
        "## Source integrity",
        "",
        "| source artifact | SHA-256 |",
        "|---|---|",
    ]
    lines.extend(f"| `{name}` | `{digest}` |" for name, digest in sorted(source_hashes.items()))
    lines += [
        "",
        "## Trial counts",
        "",
        f"- strict_selection_trials: **{inventory_counts['strict_selection_trials']:,}**",
        f"- conservative_research_trials: **{inventory_counts['conservative_research_trials']:,}**",
        f"- conservative result rows including tax/accounting views: **{inventory_counts['conservative_result_rows_including_tax_modes']:,}**",
        "",
        "## New artifact hashes",
        "",
        "| artifact | SHA-256 |",
        "|---|---|",
    ]
    lines.extend(f"| `{name}` | `{digest}` |" for name, digest in sorted(new_hashes.items()))
    lines += [
        "",
        "No economic path, metric, parameter grid, frequency, tax, or prior artifact changed. No model or frequency selection was performed.",
        "",
        "PHASE 8B-2 MULTIPLE-TESTING AUDIT COMPLETE — NO MODEL OR FREQUENCY SELECTION PERFORMED",
    ]
    (output / "phase8b2_audit_diff.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def run(
    *, output_root: Path = PROJECT_ROOT / "reports/runs", run_id: str = PHASE8B2_RUN_ID,
    n_replications: int = BOOTSTRAP_REPLICATIONS,
) -> Path:
    if n_replications != BOOTSTRAP_REPLICATIONS:
        raise ValueError("Phase 8B-2 is frozen at exactly 10,000 bootstrap replications")
    source_hashes = _required_source_hashes()
    source_grid_rows = _validate_source_grid_rows()
    daily = _load_daily_returns()
    inventory = _inventory_rows()
    inventory_counts = _inventory_counts(inventory)
    paths = _path_frame(daily)
    adjustments = _adjustment_rows()
    correlation_summary, effective_trials = _correlation_summary(paths)
    dsr, sensitivity = _dsr_rows(paths, inventory_counts["strict_selection_trials"], inventory_counts["conservative_research_trials"], effective_trials)
    snooping, index_checksums = _white_reality_check(paths, n_replications)
    config = _configuration(source_hashes, inventory_counts, adjustments, dsr, snooping, effective_trials, index_checksums, source_grid_rows)

    output = output_root / run_id
    output.mkdir(parents=True, exist_ok=False)
    inventory.to_csv(output / "research_trial_inventory.csv", index=False)
    adjustments.to_csv(output / "multiple_testing_adjustments.csv", index=False)
    dsr.to_csv(output / "deflated_sharpe_results.csv", index=False)
    snooping.to_csv(output / "data_snooping_test_results.csv", index=False)
    correlation_summary.to_csv(output / "trial_correlation_summary.csv", index=False)
    sensitivity.to_csv(output / "effective_trials_sensitivity.csv", index=False)
    (output / "phase8b2_configuration.json").write_text(json.dumps(config, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _write_report(output, inventory, adjustments, dsr, snooping, config, effective_trials)
    _write_audit_diff(output, source_hashes, inventory_counts, config)
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description="Phase 8B-2 multiple-testing and data-snooping audit")
    parser.add_argument("--output-root", type=Path, default=PROJECT_ROOT / "reports/runs")
    parser.add_argument("--run-id", default=PHASE8B2_RUN_ID)
    parser.add_argument("--replications", type=int, default=BOOTSTRAP_REPLICATIONS)
    args = parser.parse_args()
    print(run(output_root=args.output_root, run_id=args.run_id, n_replications=args.replications))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
