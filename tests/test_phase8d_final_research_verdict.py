"""Dedicated Phase 8D synthesis-only audit tests."""

from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path

import pandas as pd
import pytest

from experiments import phase8d_final_research_verdict as phase8d


@pytest.fixture(scope="module")
def run_dir(tmp_path_factory: pytest.TempPathFactory) -> Path:
    path = tmp_path_factory.mktemp("phase8d") / phase8d.PHASE8D_RUN_ID
    phase8d.generate(path)
    return path


@pytest.fixture(scope="module")
def artifacts(run_dir: Path) -> dict[str, pd.DataFrame | dict]:
    return {
        "matrix": pd.read_csv(run_dir / "final_evidence_matrix.csv"),
        "scorecard": pd.read_csv(run_dir / "original_goal_scorecard.csv"),
        "complexity": pd.read_csv(run_dir / "complexity_incremental_evidence.csv"),
        "ledger": pd.read_csv(run_dir / "final_claim_evidence_ledger.csv"),
        "config": json.loads((run_dir / "phase8d_configuration.json").read_text()),
    }


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_phase8a_source_hashes_unchanged() -> None:
    observed = phase8d.verify_source_hashes()
    for name, digest in phase8d.EXPECTED_SOURCE_HASHES["phase8a"].items():
        assert observed[f"phase8a/{name}"] == digest


def test_phase8b1_source_hashes_unchanged() -> None:
    observed = phase8d.verify_source_hashes()
    for name, digest in phase8d.EXPECTED_SOURCE_HASHES["phase8b1"].items():
        assert observed[f"phase8b1/{name}"] == digest


def test_phase8b2_source_hashes_unchanged() -> None:
    observed = phase8d.verify_source_hashes()
    for name, digest in phase8d.EXPECTED_SOURCE_HASHES["phase8b2"].items():
        assert observed[f"phase8b2/{name}"] == digest


def test_phase8c_source_hashes_unchanged() -> None:
    observed = phase8d.verify_source_hashes()
    for name, digest in phase8d.EXPECTED_SOURCE_HASHES["phase8c"].items():
        assert observed[f"phase8c/{name}"] == digest


def test_raw_snapshot_hashes_unchanged() -> None:
    observed = phase8d.verify_source_hashes()
    for name, digest in phase8d.RAW_SNAPSHOT_HASHES.items():
        assert observed[name] == digest


def test_module_has_no_strategy_engine_imports() -> None:
    tree = ast.parse(Path(phase8d.__file__).read_text(encoding="utf-8"))
    imported: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.append(node.module)
    forbidden = ("market_timing_quant", "portfolio", "signals", "backtest", "optimizer", "selector")
    assert not any(any(term in name.lower() for term in forbidden) for name in imported)


def test_no_backtest_engine_is_invoked() -> None:
    tree = ast.parse(Path(phase8d.__file__).read_text(encoding="utf-8"))
    calls = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            fn = node.func.attr if isinstance(node.func, ast.Attribute) else node.func.id if isinstance(node.func, ast.Name) else ""
            calls.append(fn.lower())
    assert not any("backtest" in fn for fn in calls)


def test_no_signal_engine_is_invoked() -> None:
    tree = ast.parse(Path(phase8d.__file__).read_text(encoding="utf-8"))
    call_names = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            call_names.append(node.func.attr.lower() if isinstance(node.func, ast.Attribute) else node.func.id.lower() if isinstance(node.func, ast.Name) else "")
    assert not any("signal" in fn or "decision" in fn for fn in call_names)


def test_no_optimizer_or_selector_is_invoked() -> None:
    tree = ast.parse(Path(phase8d.__file__).read_text(encoding="utf-8"))
    call_names = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            call_names.append(node.func.attr.lower() if isinstance(node.func, ast.Attribute) else node.func.id.lower() if isinstance(node.func, ast.Name) else "")
    assert not any("optim" in fn or "select" in fn for fn in call_names)


def test_no_new_p_values_are_calculated(artifacts: dict[str, pd.DataFrame | dict]) -> None:
    config = artifacts["config"]
    assert config["new_p_value_family"] is False
    assert config["new_backtest_or_path_regeneration"] is False
    assert set(phase8d._pairwise_tables()[1].adjustment_scope) == {"confirmatory_20"}


def test_no_numerical_dsr_is_generated(artifacts: dict[str, pd.DataFrame | dict]) -> None:
    matrix = artifacts["matrix"]
    config = artifacts["config"]
    assert set(matrix.dsr_status) == {phase8d.DSR_STATUS}
    assert config["new_numerical_dsr"] is False
    dsr = pd.read_csv(phase8d.PHASE8B2_RUN / "deflated_sharpe_results.csv")
    assert dsr[["sr_star", "dsr_test_statistic", "dsr_probability"]].isna().all().all()


def test_dsr_status_remains_not_identifiable(artifacts: dict[str, pd.DataFrame | dict]) -> None:
    assert artifacts["config"]["dsr_status"] == "DSR_NOT_IDENTIFIABLE_FROM_FROZEN_ARTIFACTS"


def test_goal_a_formula_is_exact(artifacts: dict[str, pd.DataFrame | dict]) -> None:
    frame = artifacts["scorecard"]
    expected = (frame.cagr > frame.qqq_cagr) & (frame.max_drawdown >= frame.qqq_max_drawdown)
    assert frame.Goal_A.tolist() == expected.tolist()


def test_goal_b_formula_is_exact(artifacts: dict[str, pd.DataFrame | dict]) -> None:
    frame = artifacts["scorecard"]
    expected = (frame.cagr >= frame.qqq_cagr + 0.03) & (frame.max_drawdown >= -0.45)
    assert frame.Goal_B.tolist() == expected.tolist()


def test_goal_c_formula_is_exact(artifacts: dict[str, pd.DataFrame | dict]) -> None:
    frame = artifacts["scorecard"]
    expected = (frame.cagr >= 0.25) & (frame.max_drawdown >= -0.50)
    assert frame.Goal_C.tolist() == expected.tolist()


def test_qqq_dominance_formula_is_exact_and_separate(artifacts: dict[str, pd.DataFrame | dict]) -> None:
    frame = artifacts["scorecard"]
    expected = (frame.cagr > frame.qqq_cagr) & (frame.max_drawdown >= frame.qqq_max_drawdown) & (frame.calmar > frame.qqq_calmar)
    assert frame.qqq_dominance.tolist() == expected.tolist()
    assert "qqq_dominance" in frame and "Goal_A" in frame
    assert frame.qqq_dominance.name != frame.Goal_A.name


def test_all_four_frequencies_remain_visible(artifacts: dict[str, pd.DataFrame | dict]) -> None:
    matrix = artifacts["matrix"]
    assert set(matrix.loc[matrix.strategy_id.ne(phase8d.QQQ_ID), "frequency"]) == set(phase8d.FREQUENCIES)
    assert set(artifacts["complexity"].frequency) == set(phase8d.FREQUENCIES)


def test_phase7a_incremental_evidence_is_matched_to_fixed(artifacts: dict[str, pd.DataFrame | dict]) -> None:
    frame = artifacts["complexity"]
    assert frame.comparison.eq("PHASE7A_FIXED_FOUR_STATE vs FIXED_MA200_QQQ_TO_QLD").all()
    assert frame.matched_scenario_count.eq(14).all()
    assert frame.selection_performed.eq(False).all()


def test_phase7b_remains_context_evidence(artifacts: dict[str, pd.DataFrame | dict]) -> None:
    matrix = artifacts["matrix"]
    context = matrix[matrix.strategy_id.str.startswith("PHASE7B")]
    assert len(context) == 8
    assert context.incremental_complexity_evidence.str.contains("context-only").all()
    assert context.notes.str.contains("no live frequency").all()
    assert "NO_DEMONSTRATED_VALUE" == phase8d.PHASE7B_CLASSIFICATION


def test_no_combined_numerical_score_exists(artifacts: dict[str, pd.DataFrame | dict]) -> None:
    for frame in (artifacts["matrix"], artifacts["complexity"], artifacts["scorecard"]):
        assert not any("score" in column.lower() for column in frame.columns)
    assert all("composite scoring" in value.lower() for value in artifacts["matrix"].notes)


def test_no_live_frequency_is_selected(artifacts: dict[str, pd.DataFrame | dict]) -> None:
    config = artifacts["config"]
    assert config["frequency_selected"] is False
    assert config["selection_performed"] is False
    assert config["frequencies"] == list(phase8d.FREQUENCIES)


def test_no_production_winner_is_selected(artifacts: dict[str, pd.DataFrame | dict]) -> None:
    assert artifacts["config"]["production_winner_selected"] is False
    assert "designation" in " ".join(artifacts["matrix"].notes).lower()


def test_claim_ledger_has_major_claim_coverage(artifacts: dict[str, pd.DataFrame | dict]) -> None:
    ids = set(artifacts["ledger"].claim_id)
    required = {"FIXED_VS_QQQ", "PHASE7A_VS_QQQ", "PHASE7A_INCREMENT", "PHASE7B_CONTEXT", "BONFERRONI_SURVIVORS", "HOLM_SURVIVORS", "BH_SURVIVORS", "WHITE_RC", "DSR_BOUNDARY", "GOAL_SCORECARD", "FINAL_CLASSIFICATION"}
    assert required <= ids
    assert artifacts["ledger"].source_artifact.notna().all()


def test_no_prior_canonical_artifact_is_rewritten(run_dir: Path) -> None:
    before = phase8d.verify_source_hashes()
    phase8d.generate(run_dir)
    after = phase8d.verify_source_hashes()
    assert before == after
    assert phase8d.PHASE8D_RUN_ID not in {phase8d.PHASE8A_RUN_ID, phase8d.PHASE8B1_RUN_ID, phase8d.PHASE8B2_RUN_ID, phase8d.PHASE8C_RUN_ID}


def test_artifact_completeness(run_dir: Path) -> None:
    required = {
        "final_evidence_matrix.csv",
        "original_goal_scorecard.csv",
        "complexity_incremental_evidence.csv",
        "final_claim_evidence_ledger.csv",
        "phase8d_configuration.json",
        "phase8d_final_research_verdict.md",
        "phase8d_audit_diff.md",
    }
    assert required <= {path.name for path in run_dir.iterdir()}


def test_expected_row_counts_and_required_columns(artifacts: dict[str, pd.DataFrame | dict]) -> None:
    matrix = artifacts["matrix"]
    scorecard = artifacts["scorecard"]
    complexity = artifacts["complexity"]
    ledger = artifacts["ledger"]
    assert len(matrix) == 17
    assert len(scorecard) == 16
    assert len(complexity) == 4
    assert len(ledger) >= 20
    required_matrix = {"strategy_id", "frequency", "complexity_level", "pre_tax_cagr", "after_tax_cagr", "terminal_after_tax_cagr", "max_drawdown", "sharpe", "calmar", "turnover", "trades", "Goal_A", "Goal_B", "Goal_C", "qqq_dominance", "nominal_pairwise_evidence", "holm_adjusted_evidence", "white_rc_scope", "dsr_status", "notes"}
    assert required_matrix <= set(matrix.columns)
    assert {"claim_id", "claim", "evidence_type", "source_phase", "source_run", "source_artifact", "source_row/filter", "interpretation_limit"} <= set(ledger.columns)


def test_white_rc_scope_is_exact_and_global(artifacts: dict[str, pd.DataFrame | dict]) -> None:
    rc = artifacts["config"]["white_reality_check"]
    assert rc["scope"] == "FINAL_OOS_PATH_FAMILY_WHITE_REALITY_CHECK"
    assert rc["candidate_count"] == 16
    assert rc["expected_block_length"] == 20
    assert rc["global_only"] is True
    assert rc["individual_superiority_proven"] is False
    assert rc["historical_trials_4164_included"] is False


def test_multiplicity_family_and_survivors_are_exact(artifacts: dict[str, pd.DataFrame | dict]) -> None:
    m = artifacts["config"]["multiplicity"]
    assert m["family"] == "confirmatory_20" and m["family_test_count"] == 20
    assert m["bonferroni_survivors"] == ["A_FIXED_MA200_VS_QQQ__bimonthly", "B_PHASE7A_VS_QQQ__bimonthly"]
    assert m["holm_survivors"] == m["bonferroni_survivors"]
    assert len(m["bh_fdr_survivors"]) == 7 and m["bh_controls_fwer"] is False


def test_report_and_audit_end_with_required_marker(run_dir: Path) -> None:
    marker = "PHASE 8D FINAL RESEARCH VERDICT COMPLETE — RESEARCH DEVELOPMENT FROZEN"
    assert (run_dir / "phase8d_final_research_verdict.md").read_text().rstrip().endswith(marker)
    assert (run_dir / "phase8d_audit_diff.md").read_text().rstrip().endswith(marker)


def test_output_hashes_are_recorded(run_dir: Path, artifacts: dict[str, pd.DataFrame | dict]) -> None:
    config = artifacts["config"]
    for key in ("final_evidence_matrix", "original_goal_scorecard", "complexity_incremental_evidence", "final_claim_evidence_ledger", "report"):
        name = {"final_evidence_matrix": "final_evidence_matrix.csv", "original_goal_scorecard": "original_goal_scorecard.csv", "complexity_incremental_evidence": "complexity_incremental_evidence.csv", "final_claim_evidence_ledger": "final_claim_evidence_ledger.csv", "report": "phase8d_final_research_verdict.md"}[key]
        assert config["artifact_hashes"][key] == _digest(run_dir / name)
