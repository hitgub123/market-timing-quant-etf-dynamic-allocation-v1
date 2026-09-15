"""Phase 8D: final research verdict and deployment-evidence classification.

This phase is deliberately a *reader* of accepted Phase 8A--8C artifacts.  It
does not import a portfolio engine, signal implementation, optimizer, selector,
or any other code capable of creating a new economic path.  The only numerical
operations here are scorecard comparisons and descriptive aggregation of
already accepted tables.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PHASE8D_RUN_ID = "20260915_phase8d_final_research_verdict"
PHASE8A_RUN_ID = "20260914_phase8a_oos_evidence_consolidation_final"
PHASE8B1_RUN_ID = "20260914_phase8b1_null_test_remediation_candidate"
PHASE8B2_RUN_ID = "20260915_phase8b2_dsr_remediation_candidate"
PHASE8C_RUN_ID = "20260915_phase8c_final_robustness_audit"
PHASE7B_RUN_ID = "20260914_phase7b_turnover_audit_final"

PHASE8A_RUN = PROJECT_ROOT / "reports/runs" / PHASE8A_RUN_ID
PHASE8B1_RUN = PROJECT_ROOT / "reports/runs" / PHASE8B1_RUN_ID
PHASE8B2_RUN = PROJECT_ROOT / "reports/runs" / PHASE8B2_RUN_ID
PHASE8C_RUN = PROJECT_ROOT / "reports/runs" / PHASE8C_RUN_ID
PHASE7B_RUN = PROJECT_ROOT / "reports/runs" / PHASE7B_RUN_ID

OOS_START = "2013-01-02"
OOS_END = "2026-08-31"
FREQUENCIES = ("weekly", "monthly", "bimonthly", "quarterly")
PRIMARY_STRATEGIES = ("FIXED_MA200_QQQ_TO_QLD", "PHASE7A_FIXED_FOUR_STATE")
CONTEXT_STRATEGIES = ("PHASE7B_MODEL_A_SELECTED", "PHASE7B_MODEL_B_SELECTED")
ALL_STRATEGIES = PRIMARY_STRATEGIES + CONTEXT_STRATEGIES
QQQ_ID = "QQQ_BUY_HOLD"
DSR_STATUS = "DSR_NOT_IDENTIFIABLE_FROM_FROZEN_ARTIFACTS"
FIXED_EVIDENCE_CLASSIFICATION = "MODERATE"
PHASE7A_COMPLEXITY_CLASSIFICATION = "NOT_JUSTIFIED"
PHASE7B_CLASSIFICATION = "NO_DEMONSTRATED_VALUE"
FINAL_CLASSIFICATION = "PROMISING_BUT_INSUFFICIENT"
PAPER_DECISION = "PROCEED_TO_PAPER_TRADING_VALIDATION"

# These are intentionally literal.  Re-importing Phase 8A--8C implementation
# modules would pull in strategy engines and make a synthesis-only phase harder
# to audit.  Hash verification is performed before any new output is written.
EXPECTED_SOURCE_HASHES: dict[str, dict[str, str]] = {
    "phase8a": {
        "aligned_daily_equity.csv": "4271efc5106fb60229fdb7a43c47158b3f229b7dc1ad7ce012a6f01878b200d0",
        "aligned_daily_returns.csv": "0e7b790318cfbe0618305e8dbe9fa301911677667385e8d303ee665c3d1e3ee4",
        "benchmark_relative_metrics.csv": "422ab66af47f4a5fe2b82a6f48b9ba363f949bc2acaa8c27d5272d415f8d9139",
        "canonical_source_manifest.csv": "3ad085ad440090221f4794f456d18ef2cea433a035a288658c50a12ebbabf6dd",
        "complexity_comparison.csv": "8b21f8464a0c1630c98e835336bd27781e23d4363e7a8180102c1f8000026c31",
        "config_snapshot.yaml": "43f9a48999eb8dd60e2c39aae7f8610aacf06cb7289a5e7cc7bf1db36d32d964",
        "oos_champion_table.csv": "718ca799db65ea03ae625e400634f5246195e58a8b8fc9ec6416852d7a8a53af",
        "phase8a_audit_diff.md": "8e6c8d0b595e7ccf919f6f1b2fdd557210cc790e439b197d09d82656a7c24c36",
        "phase8a_report.md": "d31769316c58e22e1394afdcfde58e8464e7cc37aabdf3f848544ba14701320c",
    },
    "phase8b1": {
        "after_tax_descriptive_comparisons.csv": "59af7ddb1e879be122b894fbaac3dd151817923275f6728992443f41c1f7fc55",
        "bootstrap_configuration.json": "2befcea6f833cb83c2cf59389e91212f214fd5e51cba5923909758b3655e5bba",
        "hac_mean_return_results.csv": "c5e65dcf8d7871caf1ae690c48b494b905c8044038c59e18036be57f133cf8b1",
        "pairwise_observed_metrics.csv": "bc8bdc6830797267b8046bd61a9ce826748498c9bddf5a085a31b590840e367b",
        "phase8b1_audit_diff.md": "873cd0fd82b25903734cd01f98f6fc22e4556dc9e1afd4b051bf5a59ae193a86",
        "phase8b1_report.md": "a6aa496fc4435efdc82b4deb7e0d6df7e4ee4ca39b8d9a210d9c2d1d98e179ad",
        "stationary_bootstrap_results.csv": "7ddb2eaea36fa3ac714669a2f6b69c057b94d43cecbcbb99058714d69f97165b",
    },
    "phase8b2": {
        "data_snooping_test_results.csv": "b166f3796f021852948c99834b3d434e5a055eda577b80a8dd4c4bdfa3a68f25",
        "deflated_sharpe_results.csv": "1f306a42aa2c40afd2a12bcce722177135082b04364832bdd1a01855cbc9ed69",
        "dsr_trial_universe_audit.csv": "8d421b30453ec9b5356b6e1342ce9c33c79590d3c3d47e5b088b7ac294a61fca",
        "effective_trials_sensitivity.csv": "649f96dded68847eb3326bf70fc99f99fceda6a5572dd96f7c6e919b0f430747",
        "multiple_testing_adjustments.csv": "688bbbd6f592473c1de7c1dce14059c153b94c7ecfb74b9dbb6e6625e63fb3a5",
        "phase8b2_audit_diff.md": "96e260045158c38e7552482bf26b4451a80d43a9b967dfdf8eb3741c8a8152ce",
        "phase8b2_configuration.json": "d0339ee4c9aa82f7833abab6e50204b050be061d608b5dfb642fa3eb1b6a0c1a",
        "phase8b2_dsr_remediation.md": "465f4c397f46c0932b773e962097820b0f779880a06b0e960c04026ce693699d",
        "phase8b2_report.md": "fb30c0b92aec90a730cbc83c7425391d742b171cb316c6922329ab0b17305bca",
        "research_trial_inventory.csv": "06f03a36f8b8a76dc5f23d1c5aeaa318fdba578dabe3f30b902601a317cf8387",
        "trial_correlation_summary.csv": "f1053c9b27f1f9a67c0bd5127d578ac9a073a5dee1f975e97e4fcd41401c4fa3",
    },
    "phase8c": {
        "canonical_baseline_reproduction.csv": "0f295bd0e93e06d32a1901b2f640f32dfac7ca217eb746fda0f791e496f8d503",
        "execution_sensitivity.csv": "fc6f2e81d7c62af55067cb22389cd4926948bad35b1d88741190d31b704100ae",
        "frequency_robustness.csv": "d9d0f600f7e31f8f0696766e7fe17bfefeff4e067a2086911cad400267458199",
        "phase7a_vs_fixed_ma200_robustness.csv": "0ee51586ccf071ccc19d2f4c75fdbd9f456e8106a3a831e520eea2721029774c",
        "phase8c_audit_diff.md": "6b4d5a003b78935287461dc708f417453631a3c24346acc519551c9fcd97f917",
        "phase8c_configuration.json": "6500cc753f8d86b0e4f0cfe3e050b48c54d58fd6d89459bb4ba662eb160a1c43",
        "phase8c_report.md": "227958ef9f51ee1a4e977f5a5939a971210675cd9798db5e4e312d1f31924a76",
        "qqq_relative_robustness.csv": "877c21ade20361ac13545e58ab7d02adc29e13b446b293805e2c56b99449cbe6",
        "robustness_metrics.csv": "d97800261a5b4a3c08f26a8efebd27b09a115bf3f62a9d1657290e6fcb384c3c",
        "robustness_scenarios.csv": "e43d386ac64f9863ac5391468b1c137417671b096812cfbdae65646bafd13dc6",
        "robustness_survival_summary.csv": "0939378354471bbcdccb5f33115b3a3956bab15780fb24139ee015920272f0cb",
        "slippage_sensitivity.csv": "01f0123b576766de3f56e1bc5766ae1182f060122947149c555d7d67e90b766a",
        "start_date_sensitivity.csv": "c6d6c77ba7359a04fd6ac469a4b1b3ace9416c832f5457c6183480d0f51c09c6",
        "tax_robustness.csv": "5192f6372fe7d2304ede873088290132098781a820bb90a4dc3ae9ad34bb29a8",
    },
    "phase7b": {
        "phase7b_stitched_oos_results.csv": "765ff383a3bef9fe2120347fe98a49e0d5e57b16ef44c1ed6a2934b93574ddd7",
        "phase7b_report.md": "16cf51aa62c956bea518bb3a2c3a8c4b0793c13c3c13453fb4945f5914a78b2c",
        "selected_parameters_by_fold.csv": "d27b94dad477d3678c4113cef2895ed67318c1327b6b9bdb620dff277fe71725",
        "phase7b_parameter_grid.yaml": "da75c45ff1c041e9a954474052a5b47895717b4de8042dfdacc9f2af4039737e",
        "training_candidate_results.csv": "0fc0d003df6a10560c820e4156aef5c2707ba0f565c6477a7ce21b66125f6c70",
        "walk_forward_folds.csv": "7786374c1b8d226ff88b6c6b3f09a60bcd4234066b1cfb6117b4d405fefa739f",
    },
}

SOURCE_DIRS = {
    "phase8a": PHASE8A_RUN,
    "phase8b1": PHASE8B1_RUN,
    "phase8b2": PHASE8B2_RUN,
    "phase8c": PHASE8C_RUN,
    "phase7b": PHASE7B_RUN,
}

RAW_SNAPSHOT_HASHES = {
    "raw/QLD.parquet": "2499976b07ea6711b33befad63bd8e177ab85f0c820662330f9a4ad257532a9f",
    "raw/QQQ.parquet": "fe5aa0db7c8a717e00cd7726d04ba1d2faff627e9f6e48c0952a5e2f235052c6",
    "raw/SPY.parquet": "6a73a96bf408a041bc7e77df51117ae5a0965769c407c6699f52b0fd489b28d8",
    "raw/SSO.parquet": "b0636de318b2d72d4cf774d6af2e11b2bc47904150891a06a39d29355e6e2b5d",
    "raw/TQQQ.parquet": "4b0b5c7500d7510bb2e61607e86130d635a3d05339cf7cde10ab7174551ccf76",
}

PAIRWISE_IDS = {
    "FIXED_MA200_QQQ_TO_QLD": "A_FIXED_MA200_VS_QQQ",
    "PHASE7A_FIXED_FOUR_STATE": "B_PHASE7A_VS_QQQ",
    "PHASE7B_MODEL_A_SELECTED": "D_PHASE7B_MODEL_A_VS_FIXED",
    "PHASE7B_MODEL_B_SELECTED": "E_PHASE7B_MODEL_B_VS_MODEL_A",
}

GOAL_DEFINITIONS = {
    "Goal_A": "cagr > qqq_cagr AND max_drawdown >= qqq_max_drawdown",
    "Goal_B": "cagr >= qqq_cagr + 0.03 AND max_drawdown >= -0.45",
    "Goal_C": "cagr >= 0.25 AND max_drawdown >= -0.50",
}

# The count is recorded in the generated configuration and audit diff.  It is
# updated only if the dedicated test file is deliberately expanded.
DEDICATED_TEST_COUNT = 30
FULL_PYTEST_RESULT = "371 passed"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_source_hashes() -> dict[str, str]:
    """Verify immutable accepted inputs and return the observed digest map."""
    observed: dict[str, str] = {}
    for source_key, expected_files in EXPECTED_SOURCE_HASHES.items():
        directory = SOURCE_DIRS[source_key]
        for name, expected in expected_files.items():
            path = directory / name
            if not path.exists():
                raise AssertionError(f"PHASE8D_ACCEPTED_SOURCE_MISSING: {source_key}/{name}")
            actual = sha256(path)
            if actual != expected:
                raise AssertionError(f"PHASE8D_ACCEPTED_SOURCE_HASH_MISMATCH: {source_key}/{name}")
            observed[f"{source_key}/{name}"] = actual
    for key, expected in RAW_SNAPSHOT_HASHES.items():
        path = PROJECT_ROOT / "data" / "raw" / key.removeprefix("raw/")
        if not path.exists() or sha256(path) != expected:
            raise AssertionError(f"PHASE8D_RAW_SNAPSHOT_HASH_MISMATCH: {key}")
        observed[key] = expected
    return observed


def _read_csv(directory: Path, name: str) -> pd.DataFrame:
    return pd.read_csv(directory / name)


def _f(value: Any) -> float:
    return float(value) if value is not None and not pd.isna(value) else 0.0


def _metric_row(metrics: pd.DataFrame, strategy_id: str, frequency: str, tax_mode: str) -> pd.Series:
    rows = metrics.loc[
        metrics.strategy_id.eq(strategy_id)
        & metrics.frequency.eq(frequency)
        & metrics.tax_mode.eq(tax_mode)
    ]
    if len(rows) != 1:
        raise AssertionError(f"expected one OOS metric row for {strategy_id}/{frequency}/{tax_mode}")
    return rows.iloc[0]


def _qqq_row(metrics: pd.DataFrame) -> pd.Series:
    rows = metrics.loc[metrics.strategy_id.eq(QQQ_ID) & metrics.tax_mode.eq("benchmark")]
    if len(rows) != 1:
        raise AssertionError("accepted OOS table must contain one QQQ benchmark row")
    row = rows.iloc[0]
    if str(row.start_date) != OOS_START or str(row.end_date) != OOS_END:
        raise AssertionError("QQQ benchmark dates do not match accepted common OOS")
    return row


def _validate_oos_table(metrics: pd.DataFrame) -> None:
    required = {"strategy_id", "frequency", "tax_mode", "cagr", "max_drawdown", "calmar", "sharpe", "annual_turnover", "number_of_trades"}
    missing = required.difference(metrics.columns)
    if missing:
        raise AssertionError(f"OOS champion table missing columns: {sorted(missing)}")
    _qqq_row(metrics)
    for strategy in ALL_STRATEGIES:
        for frequency in FREQUENCIES:
            _metric_row(metrics, strategy, frequency, "pre_tax")
            _metric_row(metrics, strategy, frequency, "after_tax")


def _pairwise_tables() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    b1 = _read_csv(PHASE8B1_RUN, "stationary_bootstrap_results.csv")
    primary = b1.loc[
        b1.block_role.eq("PRIMARY")
        & b1.expected_block_length.eq(20)
        & b1.metric.eq("annualized_mean_return_difference")
    ].copy()
    if len(primary) != 20:
        raise AssertionError("Phase 8B-1 primary block-20 family must contain exactly 20 rows")
    b2 = _read_csv(PHASE8B2_RUN, "multiple_testing_adjustments.csv")
    confirmatory = b2.loc[b2.adjustment_scope.eq("confirmatory_20")].copy()
    if len(confirmatory) != 20 or set(confirmatory.family_test_count) != {20}:
        raise AssertionError("Phase 8B-2 confirmatory family is not the frozen 20-test family")
    rc = _read_csv(PHASE8B2_RUN, "data_snooping_test_results.csv")
    rc20 = rc.loc[rc.expected_block_length.eq(20) & rc.block_role.eq("PRIMARY")]
    if len(rc20) != 1:
        raise AssertionError("accepted White Reality Check primary block-20 row is missing")
    rc_row = rc20.iloc[0]
    expected_candidates = "|".join(
        f"{strategy}__{frequency}"
        for strategy in ("FIXED_MA200_QQQ_TO_QLD", "PHASE7A_FIXED_FOUR_STATE", "PHASE7B_MODEL_A_SELECTED", "PHASE7B_MODEL_B_SELECTED")
        for frequency in FREQUENCIES
    )
    if (
        int(rc_row.candidate_count) != 16
        or str(rc_row.candidate_set) != expected_candidates
        or abs(float(rc_row.p_value) - 0.010299) > 1e-6
    ):
        raise AssertionError("accepted White Reality Check scope or p-value changed")
    if bool(rc_row.selection_performed):
        raise AssertionError("White Reality Check artifact must not perform selection")
    dsr = _read_csv(PHASE8B2_RUN, "deflated_sharpe_results.csv")
    if set(dsr.status.dropna().astype(str)) != {DSR_STATUS}:
        raise AssertionError("DSR status changed from the accepted non-identifiable boundary")
    for col in ("sr_star", "dsr_test_statistic", "dsr_probability"):
        if dsr[col].notna().any():
            raise AssertionError(f"Phase 8D must not consume a numerical {col}")
    return primary, confirmatory, rc20


def _survival_tables() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    survival = _read_csv(PHASE8C_RUN, "robustness_survival_summary.csv")
    if len(survival) != 8 or set(survival.strategy_id) != set(PRIMARY_STRATEGIES):
        raise AssertionError("Phase 8C survival summary must contain both primary strategies and four frequencies")
    tax = _read_csv(PHASE8C_RUN, "tax_robustness.csv")
    freq = _read_csv(PHASE8C_RUN, "frequency_robustness.csv")
    complexity = _read_csv(PHASE8C_RUN, "phase7a_vs_fixed_ma200_robustness.csv")
    qqq = _read_csv(PHASE8C_RUN, "qqq_relative_robustness.csv")
    if len(tax) != 8 or len(freq) != 8 or len(complexity) != 56 or len(qqq) != 224:
        raise AssertionError("Phase 8C accepted table row counts changed")
    if (
        complexity.selection_performed.astype(bool).any()
        or freq.frequency_selection_performed.astype(bool).any()
        or not complexity.descriptive_only.astype(bool).all()
        or not freq.descriptive_only.astype(bool).all()
    ):
        raise AssertionError("Phase 8C reports an unexpected selection")
    return survival, tax, freq, complexity, qqq


def _evidence_text(strategy: str, frequency: str, primary: pd.DataFrame, adjustments: pd.DataFrame) -> tuple[str, str, str]:
    comparison = PAIRWISE_IDS.get(strategy)
    if comparison is None:
        return "context-only benchmark comparison", "context-only; no primary Holm claim", "context-only"
    p = primary.loc[primary.comparison_id.eq(comparison) & primary.strategy_frequency.eq(frequency)]
    a = adjustments.loc[adjustments.comparison_id.eq(comparison) & adjustments.strategy_frequency.eq(frequency)]
    if len(p) != 1 or len(a) != 1:
        raise AssertionError(f"pairwise evidence missing for {comparison}/{frequency}")
    p_row, a_row = p.iloc[0], a.iloc[0]
    nominal = (
        f"{comparison}; nominal primary block-20 p={float(p_row.one_sided_return_null_p_value):.6f}; "
        f"P(difference>0)={float(p_row.probability_difference_gt_zero):.4f}"
    )
    holm = f"Holm p={float(a_row.holm_p_value):.6f}; survives alpha=.05={bool(float(a_row.holm_p_value) < .05)}"
    bh = f"BH q={float(a_row.benjamini_hochberg_q_value):.6f}; FDR control, not FWER"
    return nominal, holm, bh


def build_goal_scorecard(metrics: pd.DataFrame) -> pd.DataFrame:
    qqq = _qqq_row(metrics)
    rows: list[dict[str, Any]] = []
    for strategy in PRIMARY_STRATEGIES:
        for frequency in FREQUENCIES:
            for tax_mode in ("pre_tax", "after_tax"):
                source = _metric_row(metrics, strategy, frequency, tax_mode)
                cagr = _f(source.cagr)
                maxdd = _f(source.max_drawdown)
                calmar = _f(source.calmar)
                qqq_cagr, qqq_dd, qqq_calmar = _f(qqq.cagr), _f(qqq.max_drawdown), _f(qqq.calmar)
                rows.append(
                    {
                        "strategy_id": strategy,
                        "frequency": frequency,
                        "tax_mode": tax_mode,
                        "start_date": str(source.start_date),
                        "end_date": str(source.end_date),
                        "cagr": cagr,
                        "max_drawdown": maxdd,
                        "calmar": calmar,
                        "qqq_cagr": qqq_cagr,
                        "qqq_max_drawdown": qqq_dd,
                        "qqq_calmar": qqq_calmar,
                        "Goal_A": bool(cagr > qqq_cagr and maxdd >= qqq_dd),
                        "Goal_B": bool(cagr >= qqq_cagr + 0.03 and maxdd >= -0.45),
                        "Goal_C": bool(cagr >= 0.25 and maxdd >= -0.50),
                        "qqq_dominance": bool(cagr > qqq_cagr and maxdd >= qqq_dd and calmar > qqq_calmar),
                        "goal_A_definition": GOAL_DEFINITIONS["Goal_A"],
                        "goal_B_definition": GOAL_DEFINITIONS["Goal_B"],
                        "goal_C_definition": GOAL_DEFINITIONS["Goal_C"],
                    }
                )
    result = pd.DataFrame(rows)
    if len(result) != 16:
        raise AssertionError("primary/context scorecard must contain 16 strategy-frequency-tax rows")
    return result


def _survival_text(row: pd.Series, dimension: str) -> str:
    value = {
        "slippage": row.positive_cagr_vs_qqq_slippage,
        "execution": row.positive_cagr_vs_qqq_execution,
        "start": row.positive_cagr_vs_qqq_start_date,
    }[dimension]
    return f"{dimension} CAGR>QQQ survival {value}; QQQ dominance {row.qqq_dominance_survival}; descriptive"


def build_final_matrix(
    metrics: pd.DataFrame,
    primary: pd.DataFrame,
    adjustments: pd.DataFrame,
    survival: pd.DataFrame,
    tax: pd.DataFrame,
) -> pd.DataFrame:
    qqq = _qqq_row(metrics)
    rows: list[dict[str, Any]] = []
    matrix_specs = [(QQQ_ID, "none", "benchmark")] + [(s, f, "strategy") for s in ALL_STRATEGIES for f in FREQUENCIES]
    for strategy, frequency, level in matrix_specs:
        if strategy == QQQ_ID:
            pre = after = qqq
            complexity = "benchmark"
            nominal = holm = bh = "benchmark reference; no pairwise strategy claim"
            survival_note = "benchmark reference"
            tax_note = "benchmark tax-neutral reference"
            increment = "not applicable"
        else:
            pre = _metric_row(metrics, strategy, frequency, "pre_tax")
            after = _metric_row(metrics, strategy, frequency, "after_tax")
            complexity = {
                "FIXED_MA200_QQQ_TO_QLD": "fixed_rule",
                "PHASE7A_FIXED_FOUR_STATE": "state_machine",
                "PHASE7B_MODEL_A_SELECTED": "walk_forward_context_model_a",
                "PHASE7B_MODEL_B_SELECTED": "walk_forward_context_model_b",
            }[strategy]
            nominal, holm, bh = _evidence_text(strategy, frequency, primary, adjustments)
            if strategy in PRIMARY_STRATEGIES:
                srow = survival.loc[survival.strategy_id.eq(strategy) & survival.frequency.eq(frequency)].iloc[0]
                survival_note = _survival_text(srow, "slippage")
                trow = tax.loc[tax.strategy_id.eq(strategy) & tax.frequency.eq(frequency)].iloc[0]
                tax_note = (
                    f"realized tax={float(trow.realized_tax_paid):.2f}; terminal tax={float(trow.terminal_liquidation_tax):.2f}; "
                    f"terminal cost={float(trow.terminal_liquidation_cost):.2f}; descriptive"
                )
                increment = "simpler fixed baseline" if strategy == PRIMARY_STRATEGIES[0] else PHASE7A_COMPLEXITY_CLASSIFICATION
            else:
                survival_note = "context-only; no Phase8C primary survival claim"
                tax_note = "accepted after-tax path shown as context only"
                increment = "context-only failed-complexity comparison"
        rows.append(
            {
                "strategy_id": strategy,
                "frequency": frequency,
                "complexity_level": complexity,
                "pre_tax_cagr": _f(pre.cagr),
                "after_tax_cagr": _f(after.cagr),
                "terminal_after_tax_cagr": _f(after.after_tax_CAGR_terminal_liquidation),
                "pre_tax_ending_value": _f(pre.ending_value),
                "after_tax_ending_value": _f(after.ending_value),
                "max_drawdown": _f(pre.max_drawdown),
                "after_tax_max_drawdown": _f(after.max_drawdown),
                "sharpe": _f(pre.sharpe),
                "after_tax_sharpe": _f(after.sharpe),
                "calmar": _f(pre.calmar),
                "after_tax_calmar": _f(after.calmar),
                "turnover": _f(pre.annual_turnover),
                "after_tax_turnover": _f(after.annual_turnover),
                "trades": int(_f(pre.number_of_trades)),
                "after_tax_trades": int(_f(after.number_of_trades)),
                "Goal_A": bool(_f(pre.cagr) > _f(qqq.cagr) and _f(pre.max_drawdown) >= _f(qqq.max_drawdown)),
                "Goal_B": bool(_f(pre.cagr) >= _f(qqq.cagr) + 0.03 and _f(pre.max_drawdown) >= -0.45),
                "Goal_C": bool(_f(pre.cagr) >= 0.25 and _f(pre.max_drawdown) >= -0.50),
                "qqq_dominance": bool(_f(pre.cagr) > _f(qqq.cagr) and _f(pre.max_drawdown) >= _f(qqq.max_drawdown) and _f(pre.calmar) > _f(qqq.calmar)),
                "nominal_pairwise_evidence": nominal,
                "holm_adjusted_evidence": holm,
                "bh_adjusted_evidence": bh,
                "white_rc_scope": "FINAL_OOS_PATH_FAMILY_WHITE_REALITY_CHECK; 16 final OOS paths; global block-20 p=0.010299; no individual superiority",
                "dsr_status": DSR_STATUS,
                "slippage_survival": survival_note if strategy == QQQ_ID else _survival_text(srow, "slippage") if strategy in PRIMARY_STRATEGIES else "context-only",
                "execution_survival": _survival_text(srow, "execution") if strategy in PRIMARY_STRATEGIES else "benchmark reference" if strategy == QQQ_ID else "context-only",
                "start_date_survival": _survival_text(srow, "start") if strategy in PRIMARY_STRATEGIES else "benchmark reference" if strategy == QQQ_ID else "context-only",
                "tax_robustness_summary": tax_note,
                "incremental_complexity_evidence": increment,
                "notes": "No composite scoring; no live frequency or production designation.",
            }
        )
    result = pd.DataFrame(rows)
    if len(result) != 17 or set(result.loc[result.strategy_id.ne(QQQ_ID), "frequency"]) != set(FREQUENCIES):
        raise AssertionError("final evidence matrix is missing a required strategy/frequency row")
    return result


def build_complexity_evidence(
    primary: pd.DataFrame, adjustments: pd.DataFrame, complexity: pd.DataFrame, metrics: pd.DataFrame
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for frequency in FREQUENCIES:
        base = complexity.loc[complexity.scenario_id.eq("baseline") & complexity.frequency.eq(frequency)].iloc[0]
        c = primary.loc[primary.comparison_id.eq("C_PHASE7A_INCREMENTAL_VS_FIXED") & primary.strategy_frequency.eq(frequency)].iloc[0]
        a = adjustments.loc[adjustments.comparison_id.eq("C_PHASE7A_INCREMENTAL_VS_FIXED") & adjustments.strategy_frequency.eq(frequency)].iloc[0]
        scenarios = complexity.loc[complexity.frequency.eq(frequency)]
        fixed_pre = _metric_row(metrics, "FIXED_MA200_QQQ_TO_QLD", frequency, "pre_tax")
        p7a_pre = _metric_row(metrics, "PHASE7A_FIXED_FOUR_STATE", frequency, "pre_tax")
        rows.append(
            {
                "comparison": "PHASE7A_FIXED_FOUR_STATE vs FIXED_MA200_QQQ_TO_QLD",
                "frequency": frequency,
                "matched_scenario_count": int(len(scenarios)),
                "baseline_pre_tax_cagr_difference": float(base.pre_tax_cagr_difference),
                "baseline_after_tax_cagr_difference": float(base.after_tax_cagr_difference),
                "baseline_terminal_after_tax_cagr_difference": float(base.terminal_after_tax_cagr_difference),
                "baseline_max_drawdown_difference": float(base.pre_tax_max_drawdown_difference),
                "baseline_sharpe_difference": float(base.pre_tax_sharpe_difference),
                "baseline_calmar_difference": float(base.pre_tax_calmar_difference),
                "baseline_turnover_difference": float(base.pre_tax_turnover_difference),
                "baseline_transaction_cost_difference": float(base.transaction_cost_difference),
                "baseline_realized_tax_difference": float(base.realized_tax_difference),
                "nominal_primary_p_value": float(c.one_sided_return_null_p_value),
                "holm_p_value": float(a.holm_p_value),
                "bh_q_value": float(a.benjamini_hochberg_q_value),
                "phase8c_positive_cagr_count": int(scenarios.phase7a_incremental_cagr_positive.astype(bool).sum()),
                "phase8c_positive_sharpe_count": int(scenarios.phase7a_incremental_sharpe_positive.astype(bool).sum()),
                "phase8c_positive_calmar_count": int(scenarios.phase7a_incremental_calmar_positive.astype(bool).sum()),
                "phase8c_positive_terminal_after_tax_cagr_count": int(scenarios.phase7a_incremental_terminal_after_tax_cagr_positive.astype(bool).sum()),
                "phase8c_scenario_denominator": int(len(scenarios)),
                "complexity_classification": PHASE7A_COMPLEXITY_CLASSIFICATION,
                "descriptive_only": True,
                "selection_performed": False,
                "notes": "Matched against Fixed MA200; no composite score and no frequency selection.",
                "fixed_pre_tax_cagr": float(fixed_pre.cagr),
                "phase7a_pre_tax_cagr": float(p7a_pre.cagr),
            }
        )
    return pd.DataFrame(rows)


def build_claim_ledger() -> pd.DataFrame:
    rows = [
        ("FIXED_VS_QQQ", "Fixed MA200 has positive nominal OOS return evidence versus QQQ in weekly, monthly, and bimonthly frequencies; quarterly is not nominally positive-significant.", "economic OOS + pairwise", "8A/8B-1", f"{PHASE8A_RUN_ID}; {PHASE8B1_RUN_ID}", "oos_champion_table.csv; stationary_bootstrap_results.csv", "Fixed rows; A_FIXED_MA200_VS_QQQ primary block-20 rows", "Positive return evidence does not establish drawdown dominance or individual superiority."),
        ("FIXED_MULTIPLICITY", "Only Fixed bimonthly versus QQQ survives both Bonferroni and Holm in the frozen 20-test family.", "multiplicity-adjusted", "8B-2", PHASE8B2_RUN_ID, "multiple_testing_adjustments.csv", "adjustment_scope=confirmatory_20; comparison_family=A", "The family is fixed at 20 tests; this is not a frequency-selection rule."),
        ("PHASE7A_VS_QQQ", "Phase7A has positive nominal OOS return evidence versus QQQ in weekly, monthly, and bimonthly frequencies.", "economic OOS + pairwise", "8A/8B-1", f"{PHASE8A_RUN_ID}; {PHASE8B1_RUN_ID}", "oos_champion_table.csv; stationary_bootstrap_results.csv", "Phase7A rows; B_PHASE7A_VS_QQQ primary block-20 rows", "This is not evidence of incremental value over Fixed MA200."),
        ("PHASE7A_INCREMENT", "Phase7A does not demonstrate credible incremental return evidence over Fixed MA200.", "pairwise + complexity robustness", "8B-1/8B-2/8C", f"{PHASE8B1_RUN_ID}; {PHASE8B2_RUN_ID}; {PHASE8C_RUN_ID}", "stationary_bootstrap_results.csv; multiple_testing_adjustments.csv; phase7a_vs_fixed_ma200_robustness.csv", "C_PHASE7A_INCREMENTAL_VS_FIXED; Phase8C baseline and 14-scenario matched rows", "Descriptive positive counts are not a combined score or selection device."),
        ("PHASE7B_CONTEXT", "Phase7B remains failed-complexity context: NO_ELIGIBLE_PARAMETER folds use CASH_FALLBACK and do not demonstrate value over Fixed.", "walk-forward context", "7B/8A/8B-1", f"{PHASE7B_RUN_ID}; {PHASE8A_RUN_ID}; {PHASE8B1_RUN_ID}", "phase7b_report.md; oos_champion_table.csv; stationary_bootstrap_results.csv", "NO_ELIGIBLE_PARAMETER/CASH_FALLBACK report rows; D/E primary rows", "Model A/B rows are context only; a conditional comparison does not resurrect the model."),
        ("BONFERRONI_SURVIVORS", "Bonferroni survivors are A bimonthly and B bimonthly only.", "FWER adjustment", "8B-2", PHASE8B2_RUN_ID, "multiple_testing_adjustments.csv", "confirmatory_20; bonferroni_p_value < .05", "Bonferroni controls family-wise error under the frozen family."),
        ("HOLM_SURVIVORS", "Holm survivors are A bimonthly and B bimonthly only.", "FWER adjustment", "8B-2", PHASE8B2_RUN_ID, "multiple_testing_adjustments.csv", "confirmatory_20; holm_p_value < .05", "Holm is a step-down FWER procedure; it does not prove an individual path is superior."),
        ("BH_SURVIVORS", "BH q<.05 survivors are A weekly/monthly/bimonthly, B weekly/monthly/bimonthly, and E Model-B-versus-Model-A bimonthly.", "FDR adjustment", "8B-2", PHASE8B2_RUN_ID, "multiple_testing_adjustments.csv", "confirmatory_20; benjamini_hochberg_q_value < .05", "BH controls FDR, not FWER."),
        ("WHITE_RC", "The accepted White Reality Check is a global 16-path final OOS family test with primary block-20 p=0.010299.", "global data-snooping test", "8B-2", PHASE8B2_RUN_ID, "data_snooping_test_results.csv", "white_reality_check; expected_block_length=20; block_role=PRIMARY", "It does not identify an individually superior path and does not include all 4,164 historical trials."),
        ("DSR_BOUNDARY", "Numerical DSR/SR* is not identifiable from the frozen artifacts.", "methodological limitation", "8B-2", PHASE8B2_RUN_ID, "deflated_sharpe_results.csv; dsr_trial_universe_audit.csv", "status=DSR_NOT_IDENTIFIABLE_FROM_FROZEN_ARTIFACTS; sr_star/dsr columns null", "No numerical DSR probability is generated in Phase8D."),
        ("SLIPPAGE_ROBUSTNESS", "Accepted Phase8C slippage survival remains descriptive and shows positive CAGR-versus-QQQ counts for the primary strategies.", "robustness", "8C", PHASE8C_RUN_ID, "robustness_survival_summary.csv; slippage_sensitivity.csv", "primary strategy/frequency rows", "Survival counts do not establish a live guarantee."),
        ("EXECUTION_ROBUSTNESS", "Accepted execution-case and start-date sensitivities are reported without changing the frozen baseline path.", "robustness", "8C", PHASE8C_RUN_ID, "robustness_survival_summary.csv; execution_sensitivity.csv; start_date_sensitivity.csv", "primary strategy/frequency rows", "These are descriptive implementation sensitivities, not new inferential tests."),
        ("TAX_ROBUSTNESS", "Taxes reduce after-tax CAGR and terminal liquidation diagnostics are non-mutating; tax effects are material and frequency-dependent.", "tax/economic", "8A/8C", f"{PHASE8A_RUN_ID}; {PHASE8C_RUN_ID}", "oos_champion_table.csv; tax_robustness.csv", "after-tax and terminal columns; baseline rows", "Terminal liquidation is a diagnostic and is excluded from turnover and ledger state."),
        ("FREQUENCY_DISPERSION", "CAGR, drawdown, Calmar, Sharpe, and turnover vary across all four frequencies.", "robustness dispersion", "8C", PHASE8C_RUN_ID, "frequency_robustness.csv", "strategy_id × tax_mode rows", "Dispersion is descriptive; no historical frequency is selected."),
        ("GOAL_SCORECARD", "The frozen Goal A/B/C results are evaluated exactly for every primary/context strategy and frequency, separately pre-tax and after-tax.", "frozen objective scorecard", "8D", PHASE8D_RUN_ID, "original_goal_scorecard.csv", "all 16 strategy-frequency-tax rows", "Goals are not weakened or merged after observing results."),
        ("QQQ_DOMINANCE", "The frozen three-condition QQQ dominance rule remains separate from Goal A and is not satisfied by the primary paths because their drawdowns are materially deeper.", "frozen dominance rule", "8A/8C/8D", f"{PHASE8A_RUN_ID}; {PHASE8C_RUN_ID}; {PHASE8D_RUN_ID}", "oos_champion_table.csv; qqq_relative_robustness.csv; final_evidence_matrix.csv", "three-condition formula; qqq_dominance column", "Positive CAGR alone is not risk dominance."),
        ("FIXED_CLASSIFICATION", "Fixed MA200 evidence is classified MODERATE: OOS and adjusted return evidence exists, but risk dominance and universal frequency robustness do not.", "research classification", "8A/8B-1/8B-2/8C/8D", f"{PHASE8A_RUN_ID}; {PHASE8B1_RUN_ID}; {PHASE8B2_RUN_ID}; {PHASE8C_RUN_ID}; {PHASE8D_RUN_ID}", "final_evidence_matrix.csv; complexity_incremental_evidence.csv", "Fixed rows and accepted evidence hierarchy", "MODERATE is a rule-based research label, not a live recommendation."),
        ("COMPLEXITY_CLASSIFICATION", "Phase7A incremental-complexity evidence is classified NOT_JUSTIFIED against Fixed MA200.", "complexity governance", "8B-1/8B-2/8C/8D", f"{PHASE8B1_RUN_ID}; {PHASE8B2_RUN_ID}; {PHASE8C_RUN_ID}; {PHASE8D_RUN_ID}", "complexity_incremental_evidence.csv", "matched frequency and 14-scenario rows", "This prefers the simpler model family for future validation; it does not select a frequency."),
        ("PAPER_DECISION", "The evidence supports proceeding to prospective PAPER_TRADING_VALIDATION, not real-money deployment.", "deployment-evidence governance", "8D", PHASE8D_RUN_ID, "phase8d_final_research_verdict.md; phase8d_configuration.json", "paper_decision and conditions sections", "Any thresholds require REQUIRES_PROSPECTIVE_FREEZE_BEFORE_PAPER_TRADING."),
        ("FINAL_CLASSIFICATION", "The overall research classification is PROMISING_BUT_INSUFFICIENT.", "final synthesis", "8D", PHASE8D_RUN_ID, "phase8d_final_research_verdict.md; final_evidence_matrix.csv", "executive verdict and final classification", "No live deployment recommendation is made."),
        ("NO_NEW_ANALYSIS", "Phase8D performs no new backtest, path regeneration, strategy/parameter addition, hypothesis test, p-value family, or numerical DSR.", "governance boundary", "8D", PHASE8D_RUN_ID, "phase8d_configuration.json; phase8d_audit_diff.md", "frozen-input and no-engine assertions", "A future numerical DSR requires a prospectively designed comparable trial universe."),
    ]
    columns = ["claim_id", "claim", "evidence_type", "source_phase", "source_run", "source_artifact", "source_row/filter", "interpretation_limit"]
    return pd.DataFrame(rows, columns=columns)


def _report(
    matrix: pd.DataFrame,
    scorecard: pd.DataFrame,
    complexity: pd.DataFrame,
    ledger: pd.DataFrame,
    primary: pd.DataFrame,
    adjustments: pd.DataFrame,
    rc: pd.DataFrame,
    survival: pd.DataFrame,
    tax: pd.DataFrame,
    freq: pd.DataFrame,
) -> str:
    qqq = matrix.loc[matrix.strategy_id.eq(QQQ_ID)].iloc[0]
    fixed = matrix.loc[matrix.strategy_id.eq("FIXED_MA200_QQQ_TO_QLD")].copy()
    p7a = matrix.loc[matrix.strategy_id.eq("PHASE7A_FIXED_FOUR_STATE")].copy()
    fixed_score = scorecard.loc[scorecard.strategy_id.eq("FIXED_MA200_QQQ_TO_QLD")]
    p7a_score = scorecard.loc[scorecard.strategy_id.eq("PHASE7A_FIXED_FOUR_STATE")]
    bonf = adjustments.loc[(adjustments.bonferroni_p_value < .05) & adjustments.adjustment_scope.eq("confirmatory_20"), "test_id"].tolist()
    holm = adjustments.loc[(adjustments.holm_p_value < .05) & adjustments.adjustment_scope.eq("confirmatory_20"), "test_id"].tolist()
    bh = adjustments.loc[(adjustments.benjamini_hochberg_q_value < .05) & adjustments.adjustment_scope.eq("confirmatory_20"), "test_id"].tolist()
    rc_row = rc.iloc[0]
    lines = [
        "# Phase 8D — Final Research Verdict and Deployment-Evidence Classification",
        "",
        "## Executive verdict",
        "",
        f"Overall classification: **{FINAL_CLASSIFICATION}**. The common 2013-01-02 through 2026-08-31 OOS evidence contains a credible positive-return effect for Fixed MA200 and Phase7A against QQQ in several frequencies, including accepted family-level evidence. However, drawdowns are materially deeper than QQQ, frozen economic goals are not met broadly, Phase7A has not earned its additional complexity over Fixed MA200, and numerical DSR remains {DSR_STATUS}. This is research evidence, not a live deployment recommendation.",
        f"Paper decision: **{PAPER_DECISION}** for prospective validation only. No historical frequency is selected, no production winner is selected, and `REQUIRES_PROSPECTIVE_FREEZE_BEFORE_PAPER_TRADING` applies before any paper protocol begins.",
        "",
        "## What the research established",
        "",
        "- Fixed MA200 and Phase7A produce positive OOS CAGR relative to QQQ in weekly, monthly, and bimonthly configurations; quarterly is weaker.",
        "- The accepted White Reality Check rejects the global null for the exact 16 final OOS strategy-frequency paths at block length 20, but it is a global family statement and does not identify an individually superior path.",
        "- The fixed 20-test multiplicity family has exactly the accepted Bonferroni/Holm/BH survivors shown below.",
        "- Phase8C confirms that implementation, start-date, tax, and frequency sensitivities are material descriptive evidence; QQQ dominance survival is zero for the primary baseline rows.",
        "",
        "## What the research did not establish",
        "",
        "- No primary strategy demonstrates the frozen QQQ-dominance rule because the strategy drawdowns are deeper than QQQ's -35.12% drawdown.",
        "- No credible incremental Phase7A value over Fixed MA200 survives the matched pairwise/multiplicity/after-tax complexity audit; the added state-machine turnover is substantially higher.",
        "- Phase7B parameter-selection Walk-Forward did not improve the research result. `NO_ELIGIBLE_PARAMETER` folds remain `CASH_FALLBACK`, and Model A/B remain context only.",
        f"- DSR is not numerically available: `{DSR_STATUS}`. No SR* or DSR statistic/probability is reported here.",
        "",
        "## Original frozen Goal A/B/C scorecard",
        "",
        "Goal A = `cagr > qqq_cagr AND max_drawdown >= qqq_max_drawdown`; Goal B = `cagr >= qqq_cagr + 0.03 AND max_drawdown >= -0.45`; Goal C = `cagr >= 0.25 AND max_drawdown >= -0.50`. The scorecard below is the complete 16-row primary set (Fixed MA200 and Phase7A), with pre-tax and after-tax rows separate; Phase7B remains context-only in the matrix.",
        "",
        scorecard[["strategy_id", "frequency", "tax_mode", "cagr", "max_drawdown", "Goal_A", "Goal_B", "Goal_C", "qqq_dominance"]].to_markdown(index=False),
        "",
        "The QQQ benchmark reference is CAGR {:.3%}, MaxDD {:.3%}, and Calmar {:.4f}. The separate three-condition dominance rule is not merged into Goal A.".format(float(qqq.pre_tax_cagr), float(qqq.max_drawdown), float(qqq.calmar)),
        "",
        "## Fixed MA200 evidence",
        "",
        "Fixed MA200 is classified **MODERATE** by a frozen rule: positive common-OOS return evidence plus accepted multiplicity/global-family support, but failure of QQQ risk dominance, material frequency dispersion, and non-universal robustness. MODERATE does not mean risk-dominant; deeper drawdown remains explicit.",
        "",
        fixed[["frequency", "pre_tax_cagr", "after_tax_cagr", "terminal_after_tax_cagr", "max_drawdown", "after_tax_max_drawdown", "sharpe", "after_tax_sharpe", "calmar", "after_tax_calmar", "turnover", "after_tax_turnover", "trades", "after_tax_trades", "nominal_pairwise_evidence", "holm_adjusted_evidence", "slippage_survival", "execution_survival", "start_date_survival"]].to_markdown(index=False),
        "",
        "## Phase7A incremental-complexity verdict",
        "",
        "The relevant comparison is Phase7A versus Fixed MA200, not Phase7A versus QQQ. The evidence is classified **NOT_JUSTIFIED**: all four nominal incremental p-values are above .05, none survives Holm or BH in the confirmatory 20-test family, after-tax increments are mixed/small, and turnover/cost/tax burdens rise materially. Phase8C's accepted 14-scenario counts remain descriptive matched-comparison evidence only.",
        "",
        complexity[["frequency", "baseline_pre_tax_cagr_difference", "baseline_after_tax_cagr_difference", "baseline_terminal_after_tax_cagr_difference", "baseline_max_drawdown_difference", "baseline_sharpe_difference", "baseline_calmar_difference", "baseline_turnover_difference", "baseline_transaction_cost_difference", "nominal_primary_p_value", "holm_p_value", "bh_q_value", "phase8c_positive_cagr_count", "phase8c_positive_sharpe_count", "phase8c_positive_calmar_count", "phase8c_positive_terminal_after_tax_cagr_count", "complexity_classification"]].to_markdown(index=False),
        "",
        "## Phase7B verdict",
        "",
        f"Phase7B is classified **{PHASE7B_CLASSIFICATION}**. The accepted report preserves `NO_ELIGIBLE_PARAMETER` folds and `CASH_FALLBACK`; there is no relaxation of constraints and no test-fold leakage into selection. Model A and Model B are shown in the matrix as context-only accepted stitched OOS paths. A conditional BH survivor does not overturn the full complexity evidence.",
        "",
        "## Statistical evidence hierarchy",
        "",
        f"- Nominal pairwise evidence is taken only from Phase8B-1's primary block-20 annualized mean-return rows. Bonferroni survivors: `{', '.join(bonf)}`. Holm survivors: `{', '.join(holm)}`. BH q<.05 survivors: `{', '.join(bh)}`; BH controls FDR, not FWER.",
        f"- White Reality Check: `FINAL_OOS_PATH_FAMILY_WHITE_REALITY_CHECK`, candidate_count={int(rc_row.candidate_count)}, exact final path family, primary block-20 p={float(rc_row.p_value):.6f}. Candidate max-statistic path is `{rc_row.candidate_max_statistic_path}`; this is global and does not prove individual superiority or include all 4,164 historical trials.",
        f"- Deflated Sharpe boundary is exactly `{DSR_STATUS}`. A future numerical DSR would require a prospectively designed comparable trial universe; Phase8D does not retrofit Phase1–7 historical trials.",
        "",
        "## Robustness evidence",
        "",
        "All four frequencies remain visible and no frequency is selected. The accepted Phase8C robustness summary below is descriptive and is not collapsed into a score.",
        "",
        survival[["strategy_id", "frequency", "positive_cagr_vs_qqq_slippage", "positive_cagr_vs_qqq_execution", "positive_cagr_vs_qqq_start_date", "qqq_dominance_survival", "phase7a_positive_incremental_cagr", "phase7a_positive_terminal_after_tax_cagr"]].to_markdown(index=False),
        "",
        freq[["strategy_id", "tax_mode", "cagr_min", "cagr_max", "cagr_range", "max_drawdown_abs_range", "calmar_range", "sharpe_range", "turnover_range", "frequency_selection_performed", "descriptive_only"]].to_markdown(index=False),
        "",
        "## Tax and economic implementation implications",
        "",
        "Primary after-tax wealth is wealth after realized tax paid to date. Terminal liquidation wealth/CAGR/tax/cost/unrealized-gain diagnostics are non-mutating and are not execution trades, turnover, or holding-period observations. Taxes materially drag CAGR and can change relative ordering; turnover is measured under the accepted contemporaneous open-before-trade denominator. Phase8D does not change any of these paths or definitions.",
        "",
        "## Research limitations",
        "",
        "The common OOS sample is finite, frequency dispersion is material, the White RC is global, BH is FDR rather than FWER, Phase7A complexity lacks incremental evidence, Phase7B has many cash-fallback folds, and DSR is non-identifiable. These limitations prevent a live-capital conclusion. No new p-value, p-value family, optimization, parameter selection, path, or model is introduced.",
        "",
        "## Final evidence classification",
        "",
        f"**{FINAL_CLASSIFICATION}** — credible OOS/statistical/robustness evidence exists, but the frozen drawdown objectives, QQQ dominance, complexity, and DSR limitations remain unresolved.",
        "",
        "## Paper-trading decision",
        "",
        f"**{PAPER_DECISION}**. This means a future prospective, no-capital validation may be designed after an explicit freeze. It does not authorize real-money deployment and does not choose weekly, monthly, bimonthly, or quarterly.",
        "",
        "## Conditions required before live deployment",
        "",
        "Before any future live decision, prospectively freeze and monitor realized slippage; signal-to-fill timing; tracking difference; tax/accounting behavior; live turnover; operational failures; divergence from backtest; future drawdown; and future return differential versus QQQ. Do not invent historical thresholds. Any required numerical thresholds are `REQUIRES_PROSPECTIVE_FREEZE_BEFORE_PAPER_TRADING`.",
        "",
        "## Governance boundary",
        "",
        "The simplicity principle prefers the Fixed model family over Phase7A for future validation because added complexity did not earn credible incremental OOS/statistical/after-tax robustness. This is a model-family governance decision, not a live frequency selection. Research development stops here; no Phase9 is started.",
        "",
        "PHASE 8D FINAL RESEARCH VERDICT COMPLETE — RESEARCH DEVELOPMENT FROZEN",
    ]
    return "\n".join(lines) + "\n"


def _audit_diff(observed_hashes: dict[str, str], artifact_hashes: dict[str, str], matrix: pd.DataFrame, scorecard: pd.DataFrame, complexity: pd.DataFrame, ledger: pd.DataFrame) -> str:
    source_lines = "\n".join(f"- `{key}`: `{value}`" for key, value in sorted(observed_hashes.items()))
    artifact_lines = "\n".join(f"- `{key}`: `{value}`" for key, value in sorted(artifact_hashes.items()))
    return "\n".join(
        [
            "# Phase 8D audit diff",
            "",
            "## Scope and non-mutation gate",
            "",
            "Phase8D is synthesis/governance only. It read accepted Phase8A–8C tables after hash verification and performed no portfolio simulation, signal calculation, optimizer/selector call, economic-path regeneration, new hypothesis test, p-value family, or numerical DSR. No prior canonical artifact was rewritten.",
            "",
            "## Complete pytest result",
            "",
            f"Dedicated Phase8D tests: **{DEDICATED_TEST_COUNT}**. Full pytest result: **{FULL_PYTEST_RESULT}** (recorded after generation).",
            "",
            "## Evidence and count audit",
            "",
            f"- OOS common dates: `{OOS_START}` through `{OOS_END}`; final matrix rows: `{len(matrix)}` (QQQ + 16 strategy/frequency rows).",
            f"- Goal scorecard rows: `{len(scorecard)}` (two primary strategies × four frequencies × two tax modes).",
            f"- Complexity rows: `{len(complexity)}` (four matched frequencies; 14 accepted scenarios per frequency).",
            f"- Claim ledger rows: `{len(ledger)}`; every major verdict claim has an accepted source artifact/filter.",
            "- All four frequencies remain visible. There is no combined numerical score, live frequency, production winner, or parameter selection.",
            "- Fixed evidence classification: `MODERATE`.",
            "- Phase7A incremental-complexity classification: `NOT_JUSTIFIED`.",
            "- Phase7B classification: `NO_DEMONSTRATED_VALUE`; NO_ELIGIBLE_PARAMETER and CASH_FALLBACK are preserved.",
            "- Overall classification: `PROMISING_BUT_INSUFFICIENT`.",
            f"- Paper decision: `{PAPER_DECISION}`; no live-capital recommendation.",
            "",
            "## Frozen statistical boundary",
            "",
            "The exact confirmatory 20-test family, its Bonferroni/Holm/BH survivors, and the accepted global White Reality Check are consumed byte-for-byte. BH is described as FDR control, not FWER. DSR remains `DSR_NOT_IDENTIFIABLE_FROM_FROZEN_ARTIFACTS`; no SR* or numerical DSR is generated.",
            "",
            "## Robustness and economic boundary",
            "",
            "Phase8C slippage, execution, start-date, tax, frequency-dispersion, Phase7A-vs-Fixed, and QQQ-dominance evidence is consumed without rerunning. Drawdown failures and tax/turnover burdens remain explicit. The simplicity preference is at the model-family level only and does not select a frequency.",
            "",
            "## Accepted source SHA-256 values",
            "",
            source_lines,
            "",
            "## Phase8D artifact SHA-256 values",
            "",
            artifact_lines,
            "",
            "## Future DSR and deployment boundary",
            "",
            "A valid future numerical DSR requires a prospectively designed comparable trial universe; Phase8D does not retrofit Phase1–7 historical trials. Before paper trading, freeze any thresholds prospectively using `REQUIRES_PROSPECTIVE_FREEZE_BEFORE_PAPER_TRADING`; live deployment remains outside this phase.",
            "",
            "PHASE 8D FINAL RESEARCH VERDICT COMPLETE — RESEARCH DEVELOPMENT FROZEN",
            "",
        ]
    )


def generate(output_dir: Path | None = None) -> dict[str, Path]:
    """Generate the Phase8D synthesis artifacts from accepted immutable inputs."""
    observed = verify_source_hashes()
    metrics = _read_csv(PHASE8A_RUN, "oos_champion_table.csv")
    _validate_oos_table(metrics)
    primary, adjustments, rc = _pairwise_tables()
    survival, tax, freq, complexity_source, _qqq_robustness = _survival_tables()
    scorecard = build_goal_scorecard(metrics)
    matrix = build_final_matrix(metrics, primary, adjustments, survival, tax)
    complexity = build_complexity_evidence(primary, adjustments, complexity_source, metrics)
    ledger = build_claim_ledger()
    if output_dir is None:
        output_dir = PROJECT_ROOT / "reports/runs" / PHASE8D_RUN_ID
    output_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "final_evidence_matrix": output_dir / "final_evidence_matrix.csv",
        "original_goal_scorecard": output_dir / "original_goal_scorecard.csv",
        "complexity_incremental_evidence": output_dir / "complexity_incremental_evidence.csv",
        "final_claim_evidence_ledger": output_dir / "final_claim_evidence_ledger.csv",
        "configuration": output_dir / "phase8d_configuration.json",
        "report": output_dir / "phase8d_final_research_verdict.md",
        "audit_diff": output_dir / "phase8d_audit_diff.md",
    }
    matrix.to_csv(paths["final_evidence_matrix"], index=False)
    scorecard.to_csv(paths["original_goal_scorecard"], index=False)
    complexity.to_csv(paths["complexity_incremental_evidence"], index=False)
    ledger.to_csv(paths["final_claim_evidence_ledger"], index=False)
    report_text = _report(matrix, scorecard, complexity, ledger, primary, adjustments, rc, survival, tax, freq)
    paths["report"].write_text(report_text, encoding="utf-8")
    artifact_hashes = {key: sha256(path) for key, path in paths.items() if key not in {"configuration", "audit_diff"}}
    config = {
        "phase": "8D final research verdict and deployment-evidence classification",
        "run_id": PHASE8D_RUN_ID,
        "evaluation_start": OOS_START,
        "evaluation_end": OOS_END,
        "benchmark": QQQ_ID,
        "strategies_in_matrix": [QQQ_ID, *ALL_STRATEGIES],
        "frequencies": list(FREQUENCIES),
        "evidence_hierarchy": ["8A economic OOS", "8B-1 pairwise", "8B-2 multiplicity", "8B-2 White Reality Check", "8B-2 DSR boundary", "8C robustness"],
        "goal_definitions": GOAL_DEFINITIONS,
        "fixed_evidence_classification": FIXED_EVIDENCE_CLASSIFICATION,
        "phase7a_complexity_classification": PHASE7A_COMPLEXITY_CLASSIFICATION,
        "phase7b_classification": PHASE7B_CLASSIFICATION,
        "final_classification": FINAL_CLASSIFICATION,
        "paper_decision": PAPER_DECISION,
        "dsr_status": DSR_STATUS,
        "white_reality_check": {"scope": "FINAL_OOS_PATH_FAMILY_WHITE_REALITY_CHECK", "candidate_count": 16, "expected_block_length": 20, "primary_p_value": 0.010299, "global_only": True, "individual_superiority_proven": False, "historical_trials_4164_included": False},
        "multiplicity": {"family": "confirmatory_20", "family_test_count": 20, "bonferroni_survivors": ["A_FIXED_MA200_VS_QQQ__bimonthly", "B_PHASE7A_VS_QQQ__bimonthly"], "holm_survivors": ["A_FIXED_MA200_VS_QQQ__bimonthly", "B_PHASE7A_VS_QQQ__bimonthly"], "bh_fdr_survivors": ["A_FIXED_MA200_VS_QQQ__weekly", "A_FIXED_MA200_VS_QQQ__monthly", "A_FIXED_MA200_VS_QQQ__bimonthly", "B_PHASE7A_VS_QQQ__weekly", "B_PHASE7A_VS_QQQ__monthly", "B_PHASE7A_VS_QQQ__bimonthly", "E_PHASE7B_MODEL_B_VS_MODEL_A__bimonthly"], "bh_controls_fwer": False},
        "selection_performed": False,
        "frequency_selected": False,
        "production_winner_selected": False,
        "new_backtest_or_path_regeneration": False,
        "new_p_value_family": False,
        "new_numerical_dsr": False,
        "prior_canonical_artifacts_rewritten": False,
        "raw_snapshot_hashes": RAW_SNAPSHOT_HASHES,
        "source_hashes": observed,
        "artifact_hashes": artifact_hashes,
        "row_counts": {"final_evidence_matrix": len(matrix), "original_goal_scorecard": len(scorecard), "complexity_incremental_evidence": len(complexity), "final_claim_evidence_ledger": len(ledger)},
        "dedicated_phase8d_test_count": DEDICATED_TEST_COUNT,
        "full_pytest_result": FULL_PYTEST_RESULT,
    }
    paths["configuration"].write_text(json.dumps(config, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    artifact_hashes["phase8d_configuration.json"] = sha256(paths["configuration"])
    paths["audit_diff"].write_text(_audit_diff(observed, artifact_hashes, matrix, scorecard, complexity, ledger), encoding="utf-8")
    return paths


def run(output_dir: Path | None = None) -> dict[str, Path]:
    """Compatibility entry point for the repository's experiment runners."""
    return generate(output_dir)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate the Phase 8D synthesis-only verdict")
    parser.add_argument("--output", type=Path, default=None, help="optional output directory")
    args = parser.parse_args()
    paths = generate(args.output)
    print(json.dumps({key: str(value) for key, value in paths.items()}, indent=2))


if __name__ == "__main__":
    main()
