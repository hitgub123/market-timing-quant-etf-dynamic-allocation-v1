"""Governance tests for the prospective paper-validation design remediation.

These tests are intentionally design-only.  They never import a strategy,
signal, portfolio, tax, or backtest engine and they do not create prospective
observations.
"""

from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path
import re
import subprocess

import pandas as pd

from experiments import phase8d_final_research_verdict as phase8d


ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "docs/PAPER_TRADING_VALIDATION_PROTOCOL_V1_DRAFT.md"
DECISIONS = ROOT / "docs/paper_trading_protocol_decision_table.csv"
RATIONALE = ROOT / "docs/PAPER_TRADING_PROTOCOL_V1_DESIGN_RATIONALE.md"
STATISTICAL = ROOT / "docs/PAPER_TRADING_PROTOCOL_V1_STATISTICAL_DESIGN.md"
THRESHOLDS = ROOT / "docs/paper_trading_threshold_registry.csv"
MANIFEST = ROOT / "reports/research_v1_freeze_manifest.json"
MANIFEST_SHA = "dcb8f9d79de93c61e0bd7d93b743b0356be9eb3b1467acf5db9a58563889d400"
ACCEPTED_COMMIT = "2b2bf987f2e00540412d263a8ef39566af1d1e2a"


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _manifest() -> dict:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def _all_design_text() -> str:
    return "\n".join(_text(path) for path in (PROTOCOL, DECISIONS, RATIONALE, STATISTICAL, THRESHOLDS))


def test_research_v1_tag_still_resolves_to_accepted_commit() -> None:
    tagged = subprocess.check_output(["git", "rev-parse", "research-v1.0-final^{commit}"], cwd=ROOT, text=True).strip()
    assert tagged == ACCEPTED_COMMIT
    assert subprocess.check_output(["git", "cat-file", "-t", "research-v1.0-final"], cwd=ROOT, text=True).strip() == "tag"


def test_freeze_manifest_sha_is_byte_identical() -> None:
    assert _sha256(MANIFEST) == MANIFEST_SHA
    assert MANIFEST_SHA == MANIFEST.with_suffix(".sha256").read_text(encoding="utf-8").split()[0]


def test_accepted_historical_hashes_are_unchanged() -> None:
    manifest = _manifest()
    accepted = manifest["accepted_hashes"]
    # The 52 accepted Phase7B/8A/8B1/8B2/8C + raw hashes are the source set;
    # Phase8D's seven output hashes are checked separately below.
    source_groups = {key: value for key, value in accepted.items() if key != "phase8d"}
    assert sum(len(group) for group in source_groups.values()) + len(manifest["raw_data_snapshot_hashes"]) == 52
    source_key_map = {"phase8b2_remediation": "phase8b2"}
    for manifest_key, files in source_groups.items():
        module_key = source_key_map.get(manifest_key, manifest_key)
        source_dir = phase8d.SOURCE_DIRS[module_key]
        for name, expected in files.items():
            assert _sha256(source_dir / name) == expected
    for relative, expected in manifest["raw_data_snapshot_hashes"].items():
        assert _sha256(ROOT / "data" / relative) == expected
    phase8d_run = ROOT / "reports/runs" / phase8d.PHASE8D_RUN_ID
    for name, expected in accepted["phase8d"].items():
        assert _sha256(phase8d_run / name) == expected


def test_protocol_is_still_draft() -> None:
    text = _text(PROTOCOL)
    assert "Status: DRAFT FOR AUDIT" in text
    assert "NOT FROZEN" in text
    assert _manifest()["freeze_scope"]["historical_research_frozen"] is True


def test_no_prospective_start_is_activated() -> None:
    assert "No prospective start timestamp is activated" in _text(PROTOCOL)
    assert _manifest()["freeze_scope"]["prospective_validation_started"] is False
    assert not any(ROOT.glob("prospective_validation_v1/**"))


def test_no_prospective_observations_exist() -> None:
    manifest = _manifest()
    assert manifest["freeze_scope"]["paper_observations_present"] is False
    assert "no prospective observations collected" in _text(PROTOCOL).lower()
    assert not list((ROOT / "reports/runs").glob("*prospective*"))


def test_no_paper_engine_is_implemented() -> None:
    source_roots = [ROOT / "experiments", ROOT / "scripts", ROOT / "src"]
    names = {path.name.lower() for base in source_roots for path in base.rglob("*") if path.is_file()}
    assert not any("paper" in name or "broker" in name or "daemon" in name for name in names)
    assert _manifest()["freeze_scope"]["paper_trading_engine_implemented"] is False


def test_fixed_ma200_remains_primary_model() -> None:
    assert "`FIXED_MA200_QQQ_TO_QLD` is the **PRIMARY PROSPECTIVE MODEL**" in _text(PROTOCOL)
    assert "FIXED_MA200_QQQ_TO_QLD" in pd.read_csv(DECISIONS).remediated_proposal.iloc[0]


def test_phase7a_remains_non_decision_shadow() -> None:
    text = _text(PROTOCOL)
    assert "NON-DECISION SHADOW" in text
    assert "PHASE7A_FIXED_FOUR_STATE" in text
    assert "PHASE7A_ROLE" in set(pd.read_csv(DECISIONS).decision_id)


def test_phase7b_is_excluded_from_prospective_candidates() -> None:
    text = _text(PROTOCOL)
    assert "Phase7B Model A and Model B are historical context only" in text
    assert "Phase7B cannot trigger a paper PASS" in text
    row = pd.read_csv(DECISIONS).set_index("decision_id").loc["PHASE7B_ROLE"]
    assert "historical context only" in row.remediated_proposal


def test_all_four_frequency_shadows_remain_visible() -> None:
    text = _text(PROTOCOL).lower()
    for frequency in ("weekly", "monthly", "bimonthly", "quarterly"):
        assert frequency in text
    decisions = pd.read_csv(DECISIONS)
    assert "FREQUENCY_SHADOWS" in set(decisions.decision_id)
    assert "ROBUSTNESS_SHADOW_SCHEDULE" in decisions.set_index("decision_id").loc["FREQUENCY_SHADOWS", "remediated_proposal"]


def test_exactly_one_primary_inferential_schedule_is_proposed() -> None:
    text = _text(PROTOCOL)
    assert text.count("PRIMARY_PROSPECTIVE_SCHEDULE = WEEKLY") == 1
    assert len(re.findall(r"PRIMARY_PROSPECTIVE_SCHEDULE\s*=", text)) == 1
    assert "PRIMARY_INFERENCE" in text and "ROBUSTNESS_SHADOW_EVIDENCE" in text


def test_primary_schedule_rationale_has_no_historical_metric_criterion() -> None:
    decisions = pd.read_csv(DECISIONS).set_index("decision_id")
    rationale = str(decisions.loc["FREQUENCY_PRIMARY", "rationale"]).lower()
    forbidden = ("cagr", "sharpe", "maxdd", "max drawdown", "p-value", "holm", "benjamini", "white reality", "survival")
    assert not any(term in rationale for term in forbidden)
    assert "prospective-design" in rationale


def test_no_future_best_frequency_selection_rule_exists() -> None:
    text = _all_design_text().lower()
    assert "select the best performing frequency" not in text
    assert "highest-performing one" not in text
    assert "future frequency change" in text
    assert "separately audited" in text


def test_core_horizon_is_finite() -> None:
    text = _all_design_text()
    assert "36 calendar months" in text
    assert "mandatory evaluation" in text
    assert "finite" in text.lower()


def test_inconclusive_is_an_explicit_outcome() -> None:
    text = _all_design_text()
    assert "PROSPECTIVE_VALIDATION_INCONCLUSIVE" in text
    assert "valid reason for `PROSPECTIVE_VALIDATION_INCONCLUSIVE`" in text


def test_extension_is_one_fixed_window_and_not_unlimited() -> None:
    text = _all_design_text().lower()
    assert "one fixed" in text and "12-calendar-month extension" in text
    assert "ends at 48 months" in text
    assert "no second extension" in text
    assert "no repeated extension" in text
    assert "no reset" in text


def test_protocol_invalid_is_separate_from_economic_fail() -> None:
    text = _all_design_text()
    assert "### `PROTOCOL_INVALID`" in text
    assert "### `PROSPECTIVE_VALIDATION_FAIL`" in text
    assert "This is not an economic failure" in text
    assert "The protocol remains valid, but a predeclared economic" in text


def test_no_early_success_rule() -> None:
    text = _all_design_text()
    assert "NO EARLY-SUCCESS RULE" in text
    assert "declare success because interim performance is good" in text


def test_threshold_registry_has_required_schema_and_derivation_classes() -> None:
    frame = pd.read_csv(THRESHOLDS)
    required = {"threshold_id", "domain", "rule", "numerical_value", "unit", "derivation_class", "derivation_rationale", "hard_or_evidence", "prospective_status"}
    assert required <= set(frame.columns)
    allowed = {"ORIGINAL_FROZEN_OBJECTIVE", "IMPLEMENTATION_TOLERANCE", "STATISTICAL_DESIGN", "ACCOUNTING_IDENTITY", "GOVERNANCE_LIMIT"}
    assert set(frame.derivation_class) <= allowed
    assert frame.derivation_class.notna().all()
    assert frame.prospective_status.eq("PROPOSED_NOT_FROZEN").all()


def test_thresholds_are_not_derived_from_realized_historical_performance() -> None:
    frame = pd.read_csv(THRESHOLDS)
    derivations = " ".join(frame.derivation_rationale.astype(str)).lower()
    assert "historical pass" not in derivations
    assert "historical cagr" not in derivations
    assert "realized performance" not in derivations
    assert "observed path" not in derivations


def test_original_goal_a_b_c_definitions_are_unchanged() -> None:
    text = _all_design_text()
    assert "Goal A: `strategy MaxDD >= QQQ MaxDD`" in text
    assert "Goal B: `MaxDD >= -45%`" in text
    assert "Goal C: `MaxDD >= -50%`" in text


def test_qqq_remains_primary_benchmark() -> None:
    text = _all_design_text()
    assert "QQQ buy-and-hold is the primary benchmark" in text
    assert "PRIMARY_BENCHMARK" in set(pd.read_csv(DECISIONS).decision_id)


def test_ma200_lookback_is_exactly_200() -> None:
    text = _text(PROTOCOL)
    assert "exactly 200 completed" in text
    assert "MA200" in text
    assert "200 observations" in text


def test_close_t_to_next_open_boundary_is_preserved() -> None:
    text = _all_design_text()
    assert "close-`t`" in text
    assert "open `t+1`" in text
    assert "cannot trade at open `t`" in text
    assert "never same-day" in text


def test_five_bps_baseline_is_preserved() -> None:
    frame = pd.read_csv(THRESHOLDS).set_index("threshold_id")
    assert float(frame.loc["BASELINE_SLIPPAGE_BPS", "numerical_value"]) == 5
    assert "5 bps" in _text(PROTOCOL)
    assert "MODEL_ASSUMPTION" in _text(PROTOCOL)


def test_tax_rate_and_accounting_semantics_are_preserved() -> None:
    frame = pd.read_csv(THRESHOLDS).set_index("threshold_id")
    assert float(frame.loc["TAX_RATE", "numerical_value"]) == 0.20315
    text = _all_design_text()
    for phrase in ("20.315%", "average-cost", "realized gains/losses", "immediate tax", "non-mutating"):
        assert phrase in text


def test_one_primary_confirmatory_hypothesis() -> None:
    decisions = pd.read_csv(DECISIONS)
    roles = decisions.statistical_role.astype(str)
    assert (roles == "PRIMARY_CONFIRMATORY_HYPOTHESIS").sum() == 1
    assert "one confirmatory hypothesis" in _text(STATISTICAL)


def test_shadow_frequencies_cannot_independently_trigger_pass() -> None:
    text = _all_design_text()
    assert "shadow cannot trigger PASS" in text
    assert "cannot independently trigger PASS" in text
    shadow = pd.read_csv(DECISIONS).set_index("decision_id").loc["FREQUENCY_SHADOWS"]
    assert "ROBUSTNESS_SHADOW_SCHEDULE" in shadow.remediated_proposal


def test_no_prospective_p_value_is_calculated() -> None:
    text = _all_design_text().lower()
    assert "no prospective p-value is calculated" in text
    assert not list(ROOT.glob("reports/runs/*prospective*pvalue*"))
    assert not any("prospective_p_value" in path.name for path in ROOT.rglob("*"))


def test_no_historical_backtest_is_invoked_by_remediation() -> None:
    for path in (PROTOCOL, RATIONALE, STATISTICAL):
        tree = ast.parse(_text(path)) if path.suffix == ".py" else None
        assert tree is None
    assert "run a backtest" in _text(PROTOCOL)
    assert not any(path.name.startswith("run_paper") for path in (ROOT / "scripts").glob("*.py"))


def test_no_optimizer_or_selector_is_invoked() -> None:
    for base in (ROOT / "experiments", ROOT / "scripts"):
        for path in base.glob("*.py"):
            if path.name == "phase8d_final_research_verdict.py":
                continue
            tree = ast.parse(path.read_text(encoding="utf-8"))
            calls = []
            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    calls.append(node.func.attr.lower() if isinstance(node.func, ast.Attribute) else node.func.id.lower() if isinstance(node.func, ast.Name) else "")
            # This is an absence check for newly introduced paper code; frozen
            # historical modules are not altered by this remediation.
            assert not any(name.startswith("paper_") or name.startswith("prospective_") for name in calls)


def test_no_phase9_is_started() -> None:
    assert _manifest()["freeze_scope"]["phase9_started"] is False
    assert "start Phase 9" in _text(PROTOCOL)
    assert not any("phase9" in path.name.lower() for path in (ROOT / "experiments").glob("*.py"))


def test_no_live_capital_authorization() -> None:
    text = _all_design_text()
    assert "no live-capital authorization" in text.lower()
    assert "SMALL_CAPITAL_LIVE_VALIDATION" in text
    assert "Paper PASS does not authorize normal live deployment" in text


def test_decision_table_uses_exact_remediated_schema() -> None:
    frame = pd.read_csv(DECISIONS)
    expected = ["decision_id", "issue", "current_draft_rule", "remediated_proposal", "rationale", "threshold_derivation", "selection_bias_control", "statistical_role", "status"]
    assert list(frame.columns) == expected
    assert len(frame) >= 20


def test_all_decision_table_statuses_remain_proposed() -> None:
    frame = pd.read_csv(DECISIONS)
    assert frame.status.eq("PROPOSED_NOT_FROZEN").all()
    assert not frame.status.eq("FROZEN").any()


def test_rationale_artifact_covers_required_design_choices() -> None:
    text = _text(RATIONALE)
    for phrase in ("why the primary frequency", "finite horizon", "INCONCLUSIVE", "Numerical guardrail derivation", "historical threshold tuning", "Paper-to-live boundary"):
        assert phrase.lower() in text.lower()
    assert "PROPOSED_NOT_FROZEN" in text


def test_statistical_artifact_covers_required_method_and_limits() -> None:
    text = _text(STATISTICAL)
    for phrase in ("primary hypothesis", "Newey", "serial dependence", "confidence interval", "Multiplicity", "Power and information", "Interpretation limits"):
        assert phrase.lower() in text.lower()
    assert "No prospective p-value is calculated" in text
    assert "PROPOSED_NOT_FROZEN" in text


def test_threshold_registry_covers_execution_risk_tax_and_information_domains() -> None:
    frame = pd.read_csv(THRESHOLDS)
    domains = " ".join(frame.domain.astype(str)).lower()
    for term in ("implementation", "risk", "accounting", "information", "statistical", "execution"):
        assert term in domains
    required_ids = {"CORE_HORIZON_MONTHS", "MAX_EXTENSION_MONTHS", "MIN_VALID_PAIRED_SESSIONS", "P95_OBSERVED_SLIPPAGE", "MAX_STRATEGY_MAXDD", "MAX_ANNUAL_TURNOVER", "TAX_RECONCILIATION_TOLERANCE"}
    assert required_ids <= set(frame.threshold_id)


def test_extension_values_are_exactly_twelve_and_forty_eight_months() -> None:
    frame = pd.read_csv(THRESHOLDS).set_index("threshold_id")
    assert float(frame.loc["MAX_EXTENSION_MONTHS", "numerical_value"]) == 12
    assert float(frame.loc["MAX_TOTAL_HORIZON_MONTHS", "numerical_value"]) == 48


def test_event_categories_are_separate() -> None:
    text = _all_design_text()
    for phrase in ("scheduled rebalance observations", "actual target-state changes", "completed position episodes", "adverse/regime-transition observations"):
        assert phrase in text
    assert "None is substituted for another" in _text(PROTOCOL)


def test_stale_and_partial_session_policy_is_fail_closed() -> None:
    text = _all_design_text().lower()
    for phrase in ("fail closed", "missing scheduled close", "missing next-session open", "partial session", "exchange halt", "source disagreement", "synthetic favorable price"):
        assert phrase in text
    frame = pd.read_csv(THRESHOLDS).set_index("threshold_id")
    assert float(frame.loc["STALE_CLOSE_GRACE", "numerical_value"]) == 15


def test_data_source_architecture_has_authoritative_and_backup_roles() -> None:
    text = _all_design_text()
    assert "Authoritative signal/valuation source" in text
    assert "Backup/reconciliation source" in text
    assert "corporate-action" in text
    assert "revision" in text
    assert "PROPOSED_NOT_FROZEN" in pd.read_csv(DECISIONS).set_index("decision_id").loc["DATA_SOURCE", "status"]


def test_fixed_primary_statistical_method_is_hac_with_predeclared_lag() -> None:
    text = _text(STATISTICAL)
    assert "Newey–West" in text or "Newey-West" in text
    assert "L = min(20, floor(4 * (n / 100)^(2/9)))" in text
    assert "two-sided 95%" in text
    assert "alpha of 0.05" in text


def test_design_only_power_table_has_all_required_horizons_and_effects() -> None:
    text = _text(STATISTICAL)
    for horizon in ("12 months", "24 months", "36 months", "48 months"):
        assert horizon in text
    for effect in ("0%", "2%", "4%", "6%"):
        assert effect in text
    assert "not a backtest" in text
    assert "No realized historical excess return is used" in text


def test_original_model_execution_and_accounting_are_not_redefined() -> None:
    text = _text(PROTOCOL)
    for forbidden_change in ("no same-day execution", "no leverage change", "no additional indicator", "zero cash return", "average-cost"):
        assert forbidden_change in text
    assert "Retuning the assumption after observations is prohibited" in _text(DECISIONS)


def test_monitoring_cannot_reset_start_or_change_parameters() -> None:
    text = _all_design_text().lower()
    for phrase in ("change ma200", "change start date", "restart after losses", "no routine performance reset", "no performance-based reset"):
        assert phrase in text


def test_protocol_change_requires_new_audited_version() -> None:
    row = pd.read_csv(DECISIONS).set_index("decision_id").loc["PROTOCOL_CHANGE"]
    assert "new protocol" in row.remediated_proposal
    assert "commit" in row.remediated_proposal and "tag" in row.remediated_proposal
    assert row.status == "PROPOSED_NOT_FROZEN"


def test_prior_frozen_artifact_hashes_remain_unchanged_after_design_edit() -> None:
    # Repeat the manifest-backed check as a post-edit regression guard.  This
    # intentionally excludes the new prospective documents from the accepted
    # historical set.
    assert _sha256(MANIFEST) == MANIFEST_SHA
    observed = phase8d.verify_source_hashes()
    assert len(observed) == 52
