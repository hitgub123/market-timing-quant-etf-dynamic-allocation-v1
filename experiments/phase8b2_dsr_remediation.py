"""Phase 8B-2 DSR methodology remediation candidate.

The accepted Phase 8B-2 multiple-testing and White Reality Check artifacts are
copied byte-for-byte.  This module audits whether the historical trial Sharpe
distribution needed by a defensible Bailey–López de Prado DSR can be
reconstructed.  It deliberately reports a non-identifiable status when the
frozen artifacts do not provide one common, exchangeable calendar.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import platform
import shutil
import sys
from statistics import NormalDist

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from experiments.phase8b1_pairwise_inference import (  # noqa: E402
    EXPECTED_PHASE8A_CHAMPION_SHA256,
    EXPECTED_PHASE8A_DAILY_RETURNS_SHA256,
    EXPECTED_SESSIONS,
    OOS_END,
    OOS_START,
)
from experiments.phase8b2_multiple_testing import (  # noqa: E402
    EXPECTED_PHASE8A_HASHES,
    EXPECTED_PHASE8B1_HASHES,
    PHASE8A_RUN,
    SNOOPING_CANDIDATE_SET,
    _correlation_summary,
    _inventory_counts,
    _inventory_rows,
    _load_daily_returns,
    _moment_statistics,
    _path_frame,
)


PHASE8B2_ACCEPTED_RUN_ID = "20260915_phase8b2_multiple_testing_audit"
PHASE8B2_ACCEPTED_RUN = PROJECT_ROOT / "reports/runs" / PHASE8B2_ACCEPTED_RUN_ID
PHASE8B2_REMEDIATION_RUN_ID = "20260915_phase8b2_dsr_remediation_candidate"
DSR_STATUS = "DSR_NOT_IDENTIFIABLE_FROM_FROZEN_ARTIFACTS"

EXPECTED_ACCEPTED_B2_HASHES = {
    "research_trial_inventory.csv": "06f03a36f8b8a76dc5f23d1c5aeaa318fdba578dabe3f30b902601a317cf8387",
    "multiple_testing_adjustments.csv": "688bbbd6f592473c1de7c1dce14059c153b94c7ecfb74b9dbb6e6625e63fb3a5",
    "data_snooping_test_results.csv": "b166f3796f021852948c99834b3d434e5a055eda577b80a8dd4c4bdfa3a68f25",
    "trial_correlation_summary.csv": "f1053c9b27f1f9a67c0bd5127d578ac9a073a5dee1f975e97e4fcd41401c4fa3",
    "effective_trials_sensitivity.csv": "649f96dded68847eb3326bf70fc99f99fceda6a5572dd96f7c6e919b0f430747",
    "deflated_sharpe_results.csv": "889a8b5f3355003c478f58a9b11f01fc3ffe481f75d18822445fb6a26ab85f81",
    "phase8b2_configuration.json": "85b2fa17d3c8b3d90401c0f4b52c735ef5a444dddafc2765ac90db8fd9402493",
    "phase8b2_report.md": "5ca88803d20b80ae2833b206107d6f79f5906f7e99552f5e639595dd10498e28",
    "phase8b2_audit_diff.md": "e8b14d885edff760479f385e97071fd001b31300df888ba444b4457ce0f4d6b6",
}

TRADING_DAYS_PER_YEAR = 252.0
EULER_GAMMA = 0.5772156649015329


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _expected_max_z(effective_trial_count: float) -> float:
    """Euler-constant expected maximum of N standard-normal draws."""
    n = float(effective_trial_count)
    if not np.isfinite(n) or n < 1:
        raise ValueError("effective_trial_count must be finite and at least one")
    if n == 1:
        return 0.0
    normal = NormalDist()
    return float(
        (1.0 - EULER_GAMMA) * normal.inv_cdf(1.0 - 1.0 / n)
        + EULER_GAMMA * normal.inv_cdf(1.0 - 1.0 / (n * math.e))
    )


def cross_trial_sharpe_statistics(trial_sharpes: np.ndarray) -> dict[str, float]:
    """Return independent cross-trial mean/variance inputs for DSR."""
    values = np.asarray(trial_sharpes, dtype=float)
    if values.ndim != 1 or len(values) < 2 or not np.isfinite(values).all():
        raise ValueError("at least two finite comparable trial Sharpes are required")
    return {
        "comparable_trial_count": int(len(values)),
        "mean_trial_sharpe": float(np.mean(values)),
        "trial_sharpe_variance": float(np.var(values, ddof=1)),
        "trial_sharpe_std": float(np.std(values, ddof=1)),
    }


def sr_star_from_trial_distribution(
    trial_sharpes: np.ndarray, effective_trial_count: float
) -> dict[str, float]:
    """Construct SR* from an independently supplied trial Sharpe vector."""
    stats = cross_trial_sharpe_statistics(trial_sharpes)
    z_max = _expected_max_z(effective_trial_count)
    return {
        **stats,
        "effective_trial_count": float(effective_trial_count),
        "expected_max_z": z_max,
        "sr_star": float(stats["mean_trial_sharpe"] + stats["trial_sharpe_std"] * z_max),
    }


def observed_path_sampling_se(
    observed_sharpe: float, sample_length: int, skewness: float, excess_kurtosis: float
) -> float:
    """Bailey–López de Prado sampling SE for one observed Sharpe only."""
    if sample_length <= 1:
        raise ValueError("sample_length must exceed one")
    variance_factor = 1.0 - float(skewness) * float(observed_sharpe) + (
        (float(excess_kurtosis) + 2.0) / 4.0
    ) * float(observed_sharpe) ** 2
    return float(math.sqrt(max(0.0, variance_factor / (sample_length - 1))))


def corrected_dsr_from_trial_distribution(
    observed_sharpe: float,
    sample_length: int,
    skewness: float,
    excess_kurtosis: float,
    trial_sharpes: np.ndarray,
    effective_trial_count: float,
) -> dict[str, float]:
    """Independent reference calculation for an identifiable synthetic case."""
    trial = sr_star_from_trial_distribution(trial_sharpes, effective_trial_count)
    sampling_se = observed_path_sampling_se(observed_sharpe, sample_length, skewness, excess_kurtosis)
    statistic = float((float(observed_sharpe) - trial["sr_star"]) / sampling_se) if sampling_se else np.nan
    probability = float(NormalDist().cdf(statistic)) if np.isfinite(statistic) else np.nan
    return {
        **trial,
        "observed_sharpe": float(observed_sharpe),
        "sample_length": int(sample_length),
        "skewness": float(skewness),
        "excess_kurtosis": float(excess_kurtosis),
        "observed_path_sampling_se": sampling_se,
        "dsr_test_statistic": statistic,
        "dsr_probability": probability,
    }


def _verify_accepted_b2_artifacts() -> dict[str, str]:
    actual: dict[str, str] = {}
    for name, expected in EXPECTED_ACCEPTED_B2_HASHES.items():
        path = PHASE8B2_ACCEPTED_RUN / name
        digest = _sha256(path)
        if digest != expected:
            raise AssertionError(f"accepted Phase 8B-2 hash mismatch for {name}: {digest}")
        actual[name] = digest
    return actual


def _source_hashes() -> dict[str, str]:
    actual: dict[str, str] = {}
    for name, expected in EXPECTED_PHASE8A_HASHES.items():
        path = PHASE8A_RUN / name
        digest = _sha256(path)
        if digest != expected:
            raise AssertionError(f"Phase 8A hash mismatch for {name}: {digest}")
        actual[f"phase8a/{name}"] = digest
    for name, expected in EXPECTED_PHASE8B1_HASHES.items():
        path = PROJECT_ROOT / "reports/runs/20260914_phase8b1_null_test_remediation_candidate" / name
        digest = _sha256(path)
        if digest != expected:
            raise AssertionError(f"Phase 8B-1 hash mismatch for {name}: {digest}")
        actual[f"phase8b1/{name}"] = digest
    return actual


def _load_canonical_metrics() -> dict[str, pd.DataFrame]:
    runs = PROJECT_ROOT / "reports/runs"
    return {
        "A1": pd.read_csv(runs / "20260914_phase1_audit_final_v2/metrics_pre_tax.csv"),
        "A2": pd.read_csv(runs / "20260914_phase1_audit_final_v2/metrics_pre_tax.csv"),
        "B1": pd.read_csv(runs / "20260914_phase2_audit_final/metrics_pre_tax.csv"),
        "B2": pd.read_csv(runs / "20260914_phase3_audit_final_v3/ma_parameter_surface.csv"),
        "C": pd.read_csv(runs / "20260914_phase4_audit_final/absolute_momentum_results.csv"),
        "D": pd.read_csv(runs / "20260914_phase5_audit_final/relative_momentum_results.csv"),
        "E": pd.read_csv(runs / "20260914_phase6_audit_final/vol_parameter_surface.csv"),
        "F": pd.read_csv(runs / "20260913_phase7a_metrics_tax_audited_final/phase7a_results.csv"),
        "GH": pd.read_csv(runs / "20260914_phase7b_turnover_audit_final/training_candidate_results.csv"),
    }


def _trial_universe_audit() -> pd.DataFrame:
    """Audit Sharpe availability and calendar comparability for categories A–I."""
    inventory = _inventory_rows().set_index("inventory_id")
    source = _load_canonical_metrics()
    rows: list[dict[str, object]] = []

    def add(
        inventory_id: str,
        frame: pd.DataFrame,
        *,
        available: int,
        comparable: int,
        evaluation_period: str,
        full_sample_vs_oos: str,
        comparable_calendar: str,
        exclusion_reason: str,
    ) -> None:
        meta = inventory.loc[inventory_id]
        rows.append({
            "inventory_id": inventory_id,
            "phase": meta["phase"], "category": meta["category"], "model_family": meta["model_family"],
            "economic_trial_count": int(meta["economic_trial_count"]),
            "sharpe_observations_available": int(available),
            "comparable_sharpe_available": int(comparable),
            "source_artifact": f"{meta['source_run_id']}/{meta['source_artifact']}",
            "sharpe_definition": "canonical daily arithmetic mean / daily sample standard deviation × sqrt(252), zero risk-free rate",
            "evaluation_period": evaluation_period,
            "full_sample_vs_oos": full_sample_vs_oos,
            "comparable_calendar": comparable_calendar,
            "used_for_cross_trial_variance": False,
            "exclusion_reason": exclusion_reason,
        })

    p1 = source["A1"].loc[source["A1"].tax_mode.eq("pre_tax")]
    add("A1_PHASE1_PAIR_ALLOCATIONS", p1.loc[p1.kind.eq("pair")], available=int(p1.loc[p1.kind.eq("pair"), "sharpe"].notna().sum()), comparable=0,
        evaluation_period="2006-06-21 to 2026-08-31", full_sample_vs_oos="full_sample",
        comparable_calendar="2006-06-21..2026-08-31 full-sample calendar; not 2013..2026 OOS",
        exclusion_reason="Full-sample Sharpe is not exchangeable with the target 2013–2026 OOS path distribution.")
    add("A2_PHASE1_TRIPLE_ALLOCATIONS", p1.loc[p1.kind.eq("triple")], available=int(p1.loc[p1.kind.eq("triple"), "sharpe"].notna().sum()), comparable=0,
        evaluation_period="2006-06-21 to 2026-08-31", full_sample_vs_oos="full_sample",
        comparable_calendar="2006-06-21..2026-08-31 full-sample calendar; not 2013..2026 OOS",
        exclusion_reason="Full-sample Sharpe is not exchangeable with the target 2013–2026 OOS path distribution.")

    for inventory_id, frame, label in (
        ("B1_PHASE2_MA200_FIXED", source["B1"], "Phase 2 full-sample MA200"),
        ("B2_PHASE3_MA_STABILITY", source["B2"].loc[source["B2"].tax_mode.eq("pre_tax")], "Phase 3 full-sample MA stability"),
        ("C_PHASE4_ABSOLUTE_MOMENTUM", source["C"].loc[source["C"].tax_mode.eq("pre_tax")], "Phase 4 full-sample absolute momentum"),
        ("D_PHASE5_RELATIVE_MOMENTUM", source["D"].loc[source["D"].tax_mode.eq("pre_tax")], "Phase 5 full-sample relative momentum"),
        ("E_PHASE6_VOLATILITY_TARGETING", source["E"].loc[source["E"].tax_mode.eq("pre_tax")], "Phase 6 full-sample volatility targeting"),
    ):
        add(inventory_id, frame, available=int(frame.sharpe.notna().sum()), comparable=0,
            evaluation_period="2006-06-21 to 2026-08-31", full_sample_vs_oos="full_sample",
            comparable_calendar="2006-06-21..2026-08-31 full-sample calendar; not 2013..2026 OOS",
            exclusion_reason=f"{label} Sharpe values are full-sample and cannot be mixed with the target chronological OOS paths.")

    p7a = source["F"].loc[source["F"].tax_mode.eq("pre_tax")]
    add("F_PHASE7A_FIXED_FOUR_STATE", p7a, available=int(p7a.sharpe.notna().sum()), comparable=int(p7a.loc[p7a.period.eq("chronological_oos"), "sharpe"].notna().sum()),
        evaluation_period="4 full-sample rows plus 4 chronological OOS rows",
        full_sample_vs_oos="mixed_full_sample_and_chronological_oos",
        comparable_calendar="2013-01-02..2026-08-31 for 4 OOS rows only; final-path family, not full history",
        exclusion_reason="The four OOS rows are final paths already covered by the separate 16-path White RC; the 4,164 historical trials do not share this calendar.")

    for inventory_id, model in (("G_PHASE7B_MODEL_A_TRAINING_CANDIDATES", "MODEL_A_QLD_TREND"), ("H_PHASE7B_MODEL_B_TRAINING_CANDIDATES", "MODEL_B_FOUR_STATE")):
        frame = source["GH"].loc[source["GH"].model.eq(model)]
        add(inventory_id, frame, available=int(frame.sharpe.notna().sum()), comparable=0,
            evaluation_period="14 expanding training folds with fold-specific train_start/train_end",
            full_sample_vs_oos="OOS_training_folds",
            comparable_calendar="No single calendar; training windows change by test year",
            exclusion_reason="Fold-training Sharpe values are not exchangeable with the 2013–2026 OOS path and cannot form one cross-trial variance without unrecorded standardization.")

    add("I_REBALANCE_FREQUENCY_DIMENSION", pd.DataFrame(), available=0, comparable=0,
        evaluation_period="weekly/monthly/bimonthly/quarterly cross-cutting dimension",
        full_sample_vs_oos="mixed_by_family", comparable_calendar="Already represented in each source family; no separate Sharpe observations",
        exclusion_reason="Frequency is a dimension already counted in A–H, not an additional independent Sharpe table.")
    result = pd.DataFrame(rows)
    if set(result.inventory_id) != set(inventory.index):
        raise AssertionError("DSR trial-universe audit does not cover every inventory family")
    return result


def dsr_identifiability_status(audit: pd.DataFrame) -> str:
    """Return the frozen-artifact DSR status without manufacturing a number."""
    if audit is None or audit.empty:
        return DSR_STATUS
    required = {"comparable_sharpe_available", "used_for_cross_trial_variance"}
    if not required.issubset(audit.columns):
        return DSR_STATUS
    if not bool(audit.used_for_cross_trial_variance.any()):
        return DSR_STATUS
    comparable = pd.to_numeric(audit.comparable_sharpe_available, errors="coerce").fillna(0)
    return "DSR_IDENTIFIABLE_FROM_FROZEN_ARTIFACTS" if bool(comparable.sum() >= 2) else DSR_STATUS


def _status_rows(daily: pd.DataFrame, inventory_counts: dict[str, int]) -> tuple[pd.DataFrame, float]:
    paths = _path_frame(daily)
    _, effective_path_count = _correlation_summary(paths)
    exclusion = (
        "No single accepted historical Sharpe distribution is available on the target 2013-01-02..2026-08-31 calendar. "
        "Raw research counts cannot substitute for cross-trial Sharpe dispersion; SR_star and DSR are therefore not identifiable."
    )
    rows: list[dict[str, object]] = []
    for path_id in paths.columns:
        strategy_id, frequency = path_id.rsplit("__", 1)
        stats = _moment_statistics(paths[path_id].to_numpy(dtype=float))
        for basis, count in (("strict_selection_trials", inventory_counts["strict_selection_trials"]), ("conservative_research_trials", inventory_counts["conservative_research_trials"])):
            sampling_se = math.sqrt(max(0.0, (
                1.0 - stats["skewness"] * stats["observed_sharpe"]
                + ((stats["excess_kurtosis"] + 2.0) / 4.0) * stats["observed_sharpe"] ** 2
            ) / (stats["n_observations"] - 1)))
            rows.append({
                "path_id": path_id, "strategy_id": strategy_id,
                "frequency": frequency, "tax_mode": "benchmark" if strategy_id == "QQQ_BUY_HOLD" else "pre_tax",
                "path_role": "QQQ reference" if strategy_id == "QQQ_BUY_HOLD" else "accepted final pre-tax OOS path",
                "evaluation_start": OOS_START.date().isoformat(), "evaluation_end": OOS_END.date().isoformat(),
                "sample_length_T": stats["n_observations"], "observed_sharpe": stats["observed_sharpe"],
                "observed_path_skewness": stats["skewness"], "observed_path_excess_kurtosis": stats["excess_kurtosis"],
                "observed_path_kurtosis": stats["excess_kurtosis"] + 3.0,
                "trial_count_basis": basis, "raw_trial_count": count,
                "comparable_trial_count": 0, "cross_trial_mean_sharpe": np.nan,
                "cross_trial_sharpe_variance": np.nan, "cross_trial_sharpe_std": np.nan,
                "effective_path_count_sensitivity": effective_path_count,
                "effective_path_count_role": "descriptive_only; not a substitute for historical trial Sharpe dispersion",
                "sr_star": np.nan, "observed_path_sampling_se": sampling_se,
                "dsr_test_statistic": np.nan, "dsr_probability": np.nan,
                "cross_trial_variance_source": "not estimated",
                "status": DSR_STATUS, "exclusion_reason": exclusion,
                "selection_performed": False,
            })
    return pd.DataFrame(rows), effective_path_count


def _copy_preserved_artifacts(output: Path) -> None:
    for name in (
        "research_trial_inventory.csv", "multiple_testing_adjustments.csv", "data_snooping_test_results.csv",
        "trial_correlation_summary.csv", "effective_trials_sensitivity.csv",
    ):
        shutil.copyfile(PHASE8B2_ACCEPTED_RUN / name, output / name)


def _configuration(
    source_hashes: dict[str, str], accepted_hashes: dict[str, str], inventory_counts: dict[str, int],
    dsr: pd.DataFrame, effective_path_count: float, old_dsr_hash: str, new_dsr_hash: str,
) -> dict[str, object]:
    return {
        "phase": "8B-2 DSR remediation candidate",
        "status": DSR_STATUS,
        "phase8b2_accepted_run_id": PHASE8B2_ACCEPTED_RUN_ID,
        "phase8a_source_run_id": "20260914_phase8a_oos_evidence_consolidation_final",
        "phase8b1_source_run_id": "20260914_phase8b1_null_test_remediation_candidate",
        "source_hashes": source_hashes,
        "accepted_phase8b2_hashes": accepted_hashes,
        "invariant_artifact_comparison": {
            "multiple_testing_adjustments.csv": {"old_sha256": accepted_hashes["multiple_testing_adjustments.csv"], "new_sha256": accepted_hashes["multiple_testing_adjustments.csv"], "byte_identical": True},
            "data_snooping_test_results.csv": {"old_sha256": accepted_hashes["data_snooping_test_results.csv"], "new_sha256": accepted_hashes["data_snooping_test_results.csv"], "byte_identical": True},
            "research_trial_inventory.csv": {"old_sha256": accepted_hashes["research_trial_inventory.csv"], "new_sha256": accepted_hashes["research_trial_inventory.csv"], "byte_identical": True},
            "trial_correlation_summary.csv": {"old_sha256": accepted_hashes["trial_correlation_summary.csv"], "new_sha256": accepted_hashes["trial_correlation_summary.csv"], "byte_identical": True},
            "effective_trials_sensitivity.csv": {"old_sha256": accepted_hashes["effective_trials_sensitivity.csv"], "new_sha256": accepted_hashes["effective_trials_sensitivity.csv"], "byte_identical": True},
        },
        "dsr": {
            "status": DSR_STATUS,
            "methodology_artifact": "phase8b2_dsr_remediation.md",
            "trial_universe_audit_artifact": "dsr_trial_universe_audit.csv",
            "raw_trial_counts_preserved": {"strict_selection_trials": inventory_counts["strict_selection_trials"], "conservative_research_trials": inventory_counts["conservative_research_trials"]},
            "comparable_trial_count_used": 0,
            "cross_trial_dispersion_identifiable": False,
            "raw_trial_count_is_not_cross_trial_sharpe_distribution": True,
            "effective_path_count_sensitivity": effective_path_count,
            "effective_path_count_role": "descriptive only",
            "published_equations": {
                "cross_trial_mean": "mean(S_trial)",
                "cross_trial_variance": "sample variance(S_trial)",
                "sr_star": "mean(S_trial) + std(S_trial) * z_max(N_eff)",
                "observed_sampling_variance": "[1 - skew*SR + ((excess_kurtosis+2)/4)*SR^2] / (T-1)",
                "dsr": "Phi((SR_observed - SR_star) / sigma_observed)",
            },
            "selection_performed": False,
        },
        "multiple_testing_preserved": True,
        "white_reality_check_preserved": True,
        "white_reality_check_candidate_count": 16,
        "old_dsr_results_sha256": old_dsr_hash,
        "new_dsr_results_sha256": new_dsr_hash,
        "oos_start": OOS_START.date().isoformat(), "oos_end": OOS_END.date().isoformat(), "expected_sessions": EXPECTED_SESSIONS,
        "selection_performed": False, "frequency_selection_performed": False,
        "model_selection_performed": False, "winner_designation": False,
        "prior_phase_artifacts_rewritten": False,
        "software_versions": {"python": platform.python_version(), "numpy": np.__version__, "pandas": pd.__version__},
    }


def _write_report(output: Path, inventory_audit: pd.DataFrame, dsr: pd.DataFrame, config: dict[str, object]) -> None:
    adjustments = pd.read_csv(output / "multiple_testing_adjustments.csv")
    primary = adjustments.loc[adjustments.adjustment_scope.eq("confirmatory_20")]
    rc = pd.read_csv(output / "data_snooping_test_results.csv")
    rc_primary = rc.loc[rc.expected_block_length.eq(20)].iloc[0]
    survivors = {
        label: primary.loc[primary[label].lt(0.05), "test_id"].tolist()
        for label in ("bonferroni_p_value", "holm_p_value", "benjamini_hochberg_q_value")
    }
    lines = [
        "# Phase 8B-2 DSR remediation candidate",
        "",
        "This candidate addresses one methodology blocker only. It does not modify Phase 0–8B-1, any economic path, selection rule, Phase 8B-1 p-value, multiple-testing adjustment, or White Reality Check calculation. Phase 8B-2 is not statistically accepted by this document.",
        "",
        "## Methodology correction",
        "",
        "The prior DSR output reused a single observed path's Sharpe sampling standard error as the cross-trial Sharpe dispersion used to construct SR*. That conflation is withdrawn. `phase8b2_dsr_remediation.md` defines the separate cross-trial mean/variance, expected maximum SR*, observed-path sampling variance, test statistic, and probability.",
        "",
        "## Frozen trial-universe audit",
        "",
        inventory_audit.to_markdown(index=False),
        "",
        f"The governance counts remain strict **{int(config['dsr']['raw_trial_counts_preserved']['strict_selection_trials']):,}** and conservative **{int(config['dsr']['raw_trial_counts_preserved']['conservative_research_trials']):,}**. These counts are not treated as the number of comparable Sharpe observations.",
        "",
        "Phase 1–6 and Phase 7A full-sample metrics use the 2006–2026 full sample. Phase 7B candidate Sharpes use changing expanding training folds. Only a small final OOS path family has the 2013–2026 calendar, and those paths are already the separate White Reality Check family. Mixing these populations would not identify the cross-trial Sharpe variance.",
        "",
        "## Corrected DSR result",
        "",
        f"All required paths retain their observed Sharpe, skewness, excess kurtosis, and T={EXPECTED_SESSIONS:,}. The observed-path sampling SE is shown as a separate diagnostic. Because no complete comparable historical Sharpe vector exists, `SR_star`, the DSR test statistic, and DSR probability are intentionally unavailable. The status for every strict/conservative row is **{DSR_STATUS}**.",
        "",
        dsr[["path_id", "trial_count_basis", "observed_sharpe", "observed_path_skewness", "observed_path_excess_kurtosis", "sample_length_T", "raw_trial_count", "comparable_trial_count", "effective_path_count_sensitivity", "observed_path_sampling_se", "status"]].to_markdown(index=False),
        "",
        "The effective path count is retained only as a descriptive correlation sensitivity. It cannot repair the missing historical cross-trial Sharpe dispersion and is not presented as DSR evidence.",
        "",
        "## Accepted multiple-testing evidence preserved",
        "",
        "The exact 20-test confirmatory family and secondary four-per-comparison sensitivity are byte-identical to the accepted run. At alpha=0.05, the confirmatory survivors are recorded without changing their interpretation:",
        "",
        f"- Bonferroni: `{', '.join(survivors['bonferroni_p_value']) or 'none'}`",
        f"- Holm: `{', '.join(survivors['holm_p_value']) or 'none'}`",
        f"- BH/FDR: `{', '.join(survivors['benjamini_hochberg_q_value']) or 'none'}`",
        "",
        "## Accepted final-path-family White Reality Check preserved",
        "",
        f"The White Reality Check remains `FINAL_OOS_PATH_FAMILY_WHITE_REALITY_CHECK`: exactly **{int(rc_primary.candidate_count)}** final strategy/frequency OOS paths versus QQQ, with the accepted common stationary-bootstrap stream. Its primary block-20 p-value remains **{rc_primary.p_value:.6f}**. A global max-statistic result does not make the max-statistic path individually significant, and this RC does not include all 4,164 historical research trials.",
        "",
        "## Interpretation boundary",
        "",
        "Phase 7A does not show credible incremental mean-return evidence over Fixed MA200 after the frozen pairwise/multiplicity analysis. MaxDD and Calmar remain descriptive path diagnostics. No model, parameter, frequency, score, winner, or reoptimization is introduced. No new OOS claim is made; Walk-Forward selection remains confined to the accepted Phase 7B process.",
        "",
        "The complete old-vs-new hash comparison and unresolved DSR blocker are in `phase8b2_audit_diff.md`.",
        "",
        "PHASE 8B-2 DSR REMEDIATION COMPLETE — AWAITING STATISTICAL AUDIT",
    ]
    (output / "phase8b2_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_audit_diff(
    output: Path, source_hashes: dict[str, str], accepted_hashes: dict[str, str],
    old_dsr_hash: str, new_dsr_hash: str, inventory_counts: dict[str, int],
) -> None:
    lines = [
        "# Phase 8B-2 DSR remediation audit diff",
        "",
        "This is a Class A methodology/reporting correction. Phase 0–8B-1 and the accepted Phase 8B-2 multiple-testing and White Reality Check outputs remain unchanged.",
        "",
        "## Source hashes",
        "",
        "| source | SHA-256 |",
        "|---|---|",
    ]
    lines.extend(f"| `{name}` | `{digest}` |" for name, digest in sorted(source_hashes.items()))
    lines += [
        "",
        "## Accepted invariant outputs",
        "",
        "| artifact | old SHA-256 | new SHA-256 | byte-identical |",
        "|---|---|---|---|",
    ]
    for name in ("research_trial_inventory.csv", "multiple_testing_adjustments.csv", "data_snooping_test_results.csv", "trial_correlation_summary.csv", "effective_trials_sensitivity.csv"):
        lines.append(f"| `{name}` | `{accepted_hashes[name]}` | `{_sha256(output / name)}` | **{_sha256(output / name) == accepted_hashes[name]}** |")
    lines += [
        "",
        "## Intentionally changed reporting artifacts",
        "",
        "| artifact | old SHA-256 | new SHA-256 | reason |",
        "|---|---|---|---|",
        f"| `deflated_sharpe_results.csv` | `{old_dsr_hash}` | `{new_dsr_hash}` | Replaced unsupported numeric DSR with explicit non-identifiability status |",
        f"| `phase8b2_configuration.json` | `{EXPECTED_ACCEPTED_B2_HASHES['phase8b2_configuration.json']}` | `{_sha256(output / 'phase8b2_configuration.json')}` | Records remediation equations, status, and invariant comparisons |",
        f"| `phase8b2_report.md` | `{EXPECTED_ACCEPTED_B2_HASHES['phase8b2_report.md']}` | `{_sha256(output / 'phase8b2_report.md')}` | Documents the corrected DSR interpretation |",
        "",
        "## DSR correction",
        "",
        f"- Old defective DSR artifact SHA-256: `{old_dsr_hash}`",
        f"- New status artifact SHA-256: `{new_dsr_hash}`",
        f"- New status: **{DSR_STATUS}**",
        f"- Strict research count preserved: **{inventory_counts['strict_selection_trials']:,}**",
        f"- Conservative research count preserved: **{inventory_counts['conservative_research_trials']:,}**",
        "- Cross-trial Sharpe dispersion: unavailable from one common accepted OOS calendar; no SR* or DSR probability manufactured.",
        "- Economic paths, pairwise p-values, adjusted p-values, White Reality Check rows, and source files: unchanged.",
        "",
        "## Unresolved issue",
        "",
        "A future phase would need a pre-specified, comparable historical Sharpe trial distribution (or a justified resampling design) before a numerical Bailey–López de Prado DSR can be accepted. This remediation does not create one.",
        "",
        "PHASE 8B-2 DSR REMEDIATION COMPLETE — AWAITING STATISTICAL AUDIT",
    ]
    (output / "phase8b2_audit_diff.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def run(
    *, output_root: Path = PROJECT_ROOT / "reports/runs",
    run_id: str = PHASE8B2_REMEDIATION_RUN_ID,
) -> Path:
    accepted_hashes = _verify_accepted_b2_artifacts()
    source_hashes = _source_hashes()
    daily = _load_daily_returns()
    inventory = _inventory_rows()
    inventory_counts = _inventory_counts(inventory)
    inventory_audit = _trial_universe_audit()
    if dsr_identifiability_status(inventory_audit) != DSR_STATUS:
        raise AssertionError("unexpectedly identified a DSR distribution without a pre-specified comparable calendar")
    dsr, effective_path_count = _status_rows(daily, inventory_counts)
    output = output_root / run_id
    output.mkdir(parents=True, exist_ok=False)
    _copy_preserved_artifacts(output)
    inventory_audit.to_csv(output / "dsr_trial_universe_audit.csv", index=False)
    dsr.to_csv(output / "deflated_sharpe_results.csv", index=False)
    shutil.copyfile(PROJECT_ROOT / "phase8b2_dsr_remediation.md", output / "phase8b2_dsr_remediation.md")
    old_dsr_hash = accepted_hashes["deflated_sharpe_results.csv"]
    new_dsr_hash = _sha256(output / "deflated_sharpe_results.csv")
    config = _configuration(source_hashes, accepted_hashes, inventory_counts, dsr, effective_path_count, old_dsr_hash, new_dsr_hash)
    (output / "phase8b2_configuration.json").write_text(json.dumps(config, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _write_report(output, inventory_audit, dsr, config)
    _write_audit_diff(output, source_hashes, accepted_hashes, old_dsr_hash, new_dsr_hash, inventory_counts)
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description="Phase 8B-2 DSR remediation candidate")
    parser.add_argument("--output-root", type=Path, default=PROJECT_ROOT / "reports/runs")
    parser.add_argument("--run-id", default=PHASE8B2_REMEDIATION_RUN_ID)
    args = parser.parse_args()
    print(run(output_root=args.output_root, run_id=args.run_id))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
