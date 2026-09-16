"""Dedicated tests for the final prospective paper-outcome clarification.

These are design-contract tests only.  They deliberately implement a tiny
local classifier from the published pseudocode so that the contract's regions
and equality boundaries are executable without implementing or starting a
paper engine.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "docs/PAPER_TRADING_OUTCOME_DECISION_SPEC.md"
OUTCOME_TABLE = ROOT / "docs/paper_trading_outcome_decision_table.csv"
PROTOCOL = ROOT / "docs/PAPER_TRADING_VALIDATION_PROTOCOL_V1_DRAFT.md"
RATIONALE = ROOT / "docs/PAPER_TRADING_PROTOCOL_V1_DESIGN_RATIONALE.md"
STATISTICAL = ROOT / "docs/PAPER_TRADING_PROTOCOL_V1_STATISTICAL_DESIGN.md"
DECISIONS = ROOT / "docs/paper_trading_protocol_decision_table.csv"
THRESHOLDS = ROOT / "docs/paper_trading_threshold_registry.csv"
MANIFEST = ROOT / "reports/research_v1_freeze_manifest.json"
MANIFEST_SHA = "dcb8f9d79de93c61e0bd7d93b743b0356be9eb3b1467acf5db9a58563889d400"


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _base(**overrides: object) -> dict[str, object]:
    values: dict[str, object] = {
        "protocol_valid": True,
        "hard_gate_status": "PASS",
        "information_adequate": True,
        "n_state_changes": 1,
        "n_completed_episodes": 1,
        "n_valid": 756,
        "n_primary_scheduled": 156,
        "mean_excess_ann": 0.03,
        "hac_se": 0.005,
        "ci95_two_sided_lower": 0.02,
        "ci95_two_sided_upper": 0.04,
        "ci95_one_sided_lower": 0.022,
        "cumulative_excess": 0.04,
        "extension_available": False,
        "extension_used": False,
    }
    values.update(overrides)
    return values


def _region(x: dict[str, object]) -> str:
    upper = float(x["ci95_two_sided_upper"])
    lower2 = float(x["ci95_two_sided_lower"])
    lower1 = float(x["ci95_one_sided_lower"])
    mean = float(x["mean_excess_ann"])
    cumulative = float(x["cumulative_excess"])
    if upper < -0.02:
        return "HARMFUL_BELOW_FLOOR"
    if upper < 0:
        return "STATISTICALLY_NEGATIVE_ECONOMICALLY_SMALL"
    if lower1 > 0 and cumulative > 0:
        return "STRONG_POSITIVE"
    if mean > 0 and lower2 <= 0 <= upper:
        return "POSITIVE_ESTIMATE_CI_CROSSES_ZERO"
    if mean == 0:
        return "ESTIMATE_NEAR_ZERO"
    if mean < 0 and lower2 <= 0 <= upper:
        return "NEGATIVE_ESTIMATE_CI_INCLUDES_ZERO"
    return "OTHER_UNCERTAIN"


def _result(x: dict[str, object]) -> str:
    if x["protocol_valid"] is False:
        return "PROTOCOL_INVALID"
    if x.get("hard_gate_status") != "PASS":
        return "PROSPECTIVE_VALIDATION_FAIL"
    if x["information_adequate"] is False:
        return "PROSPECTIVE_VALIDATION_INCONCLUSIVE"
    if int(x["n_state_changes"]) == 0 or int(x["n_completed_episodes"]) == 0:
        return "PROSPECTIVE_VALIDATION_INCONCLUSIVE"
    region = _region(x)
    if region == "HARMFUL_BELOW_FLOOR":
        return "PROSPECTIVE_VALIDATION_FAIL"
    if region == "STRONG_POSITIVE" and float(x["ci95_one_sided_lower"]) > 0 and float(x["cumulative_excess"]) > 0:
        return "PROSPECTIVE_VALIDATION_PASS"
    return "PROSPECTIVE_VALIDATION_INCONCLUSIVE"


def test_outcome_table_schema_and_row_count() -> None:
    frame = pd.read_csv(OUTCOME_TABLE)
    assert list(frame.columns) == [
        "priority",
        "protocol_valid",
        "information_adequate",
        "mechanism_information_limited",
        "hard_gate_status",
        "return_evidence_region",
        "extension_available",
        "outcome",
        "rationale",
    ]
    assert len(frame) == 11
    assert frame.priority.tolist() == list(range(1, 12))


def test_outcome_table_is_exhaustive_and_outcomes_are_valid() -> None:
    frame = pd.read_csv(OUTCOME_TABLE)
    assert set(frame.return_evidence_region) == {
        "ANY",
        "HARMFUL_BELOW_FLOOR",
        "STRONG_POSITIVE",
        "STATISTICALLY_NEGATIVE_ECONOMICALLY_SMALL",
        "POSITIVE_ESTIMATE_CI_CROSSES_ZERO",
        "ESTIMATE_NEAR_ZERO",
        "NEGATIVE_ESTIMATE_CI_INCLUDES_ZERO",
        "OTHER_UNCERTAIN",
    }
    assert set(frame.outcome) <= {
        "PROTOCOL_INVALID",
        "PROSPECTIVE_VALIDATION_FAIL",
        "PROSPECTIVE_VALIDATION_INCONCLUSIVE",
        "PROSPECTIVE_VALIDATION_PASS",
    }
    assert frame.outcome.iloc[0] == "PROTOCOL_INVALID"
    assert frame.outcome.iloc[1] == "PROSPECTIVE_VALIDATION_FAIL"
    assert frame.outcome.iloc[5] == "PROSPECTIVE_VALIDATION_PASS"


def test_exact_return_variables_are_named_in_spec() -> None:
    text = _text(SPEC)
    for name in (
        "n_valid",
        "mean_excess_ann",
        "hac_se",
        "ci95_two_sided_lower",
        "ci95_two_sided_upper",
        "ci95_one_sided_lower",
        "cumulative_excess",
        "information_adequate",
        "protocol_valid",
        "hard_implementation_gate",
        "hard_risk_gate",
        "hard_accounting_gate",
        "hard_turnover_gate",
    ):
        assert name in text


def test_information_adequacy_is_deterministic() -> None:
    text = _text(SPEC)
    assert "n_valid >= 500" in text
    assert "n_primary_scheduled >= 1" in text
    assert "All numeric return inputs must be finite" in text
    assert "There is no discretionary" in text


def test_protocol_invalid_has_absolute_priority() -> None:
    assert _result(_base(protocol_valid=False, hard_gate_status="FAIL", information_adequate=False)) == "PROTOCOL_INVALID"
    assert "protocol_valid is FALSE" in _text(SPEC)


def test_hard_gate_failure_precedes_information_and_return() -> None:
    assert _result(_base(hard_gate_status="FAIL", information_adequate=False)) == "PROSPECTIVE_VALIDATION_FAIL"
    text = _text(SPEC)
    assert "any hard gate is `FAIL`" in text
    for gate in ("hard_implementation_gate", "hard_risk_gate", "hard_accounting_gate", "hard_turnover_gate"):
        assert gate in text
    assert "otherwise hard_gate_status = FAIL" in text


def test_inadequate_information_is_inconclusive() -> None:
    assert _result(_base(information_adequate=False, mean_excess_ann=0.20, cumulative_excess=0.20)) == "PROSPECTIVE_VALIDATION_INCONCLUSIVE"


def test_zero_mechanism_events_are_inconclusive() -> None:
    assert _result(_base(n_state_changes=0)) == "PROSPECTIVE_VALIDATION_INCONCLUSIVE"
    assert _result(_base(n_completed_episodes=0)) == "PROSPECTIVE_VALIDATION_INCONCLUSIVE"
    assert "n_state_changes == 0" in _text(SPEC)
    assert "n_completed_episodes == 0" in _text(SPEC)


def test_strong_positive_requires_both_strict_return_conditions() -> None:
    x = _base()
    assert _region(x) == "STRONG_POSITIVE"
    assert _result(x) == "PROSPECTIVE_VALIDATION_PASS"
    assert "ci95_one_sided_lower > 0" in _text(SPEC)
    assert "cumulative_excess > 0" in _text(SPEC)


def test_positive_estimate_with_zero_crossing_is_inconclusive() -> None:
    x = _base(mean_excess_ann=0.01, ci95_two_sided_lower=-0.01, ci95_two_sided_upper=0.03, ci95_one_sided_lower=-0.005)
    assert _region(x) == "POSITIVE_ESTIMATE_CI_CROSSES_ZERO"
    assert _result(x) == "PROSPECTIVE_VALIDATION_INCONCLUSIVE"


def test_exact_zero_estimate_is_inconclusive() -> None:
    x = _base(mean_excess_ann=0.0, ci95_two_sided_lower=-0.01, ci95_two_sided_upper=0.01, ci95_one_sided_lower=-0.008, cumulative_excess=0.0)
    assert _region(x) == "ESTIMATE_NEAR_ZERO"
    assert _result(x) == "PROSPECTIVE_VALIDATION_INCONCLUSIVE"


def test_negative_estimate_with_interval_including_zero_is_inconclusive() -> None:
    x = _base(mean_excess_ann=-0.005, ci95_two_sided_lower=-0.015, ci95_two_sided_upper=0.005, ci95_one_sided_lower=-0.012, cumulative_excess=-0.01)
    assert _region(x) == "NEGATIVE_ESTIMATE_CI_INCLUDES_ZERO"
    assert _result(x) == "PROSPECTIVE_VALIDATION_INCONCLUSIVE"


def test_statistically_negative_but_economically_small_is_inconclusive() -> None:
    x = _base(mean_excess_ann=-0.01, ci95_two_sided_lower=-0.02, ci95_two_sided_upper=-0.005, ci95_one_sided_lower=-0.018, cumulative_excess=-0.02)
    assert _region(x) == "STATISTICALLY_NEGATIVE_ECONOMICALLY_SMALL"
    assert _result(x) == "PROSPECTIVE_VALIDATION_INCONCLUSIVE"


def test_confidently_below_harm_floor_is_fail() -> None:
    x = _base(mean_excess_ann=-0.03, ci95_two_sided_lower=-0.04, ci95_two_sided_upper=-0.025, ci95_one_sided_lower=-0.037, cumulative_excess=-0.04)
    assert _region(x) == "HARMFUL_BELOW_FLOOR"
    assert _result(x) == "PROSPECTIVE_VALIDATION_FAIL"


def test_all_return_regions_are_mutually_exclusive() -> None:
    cases = [
        _base(),
        _base(mean_excess_ann=0.01, ci95_two_sided_lower=-0.01, ci95_two_sided_upper=0.03, ci95_one_sided_lower=-0.005),
        _base(mean_excess_ann=0, ci95_two_sided_lower=-0.01, ci95_two_sided_upper=0.01, ci95_one_sided_lower=-0.005, cumulative_excess=0),
        _base(mean_excess_ann=-0.005, ci95_two_sided_lower=-0.015, ci95_two_sided_upper=0.005, ci95_one_sided_lower=-0.012),
        _base(mean_excess_ann=-0.01, ci95_two_sided_lower=-0.02, ci95_two_sided_upper=-0.005, ci95_one_sided_lower=-0.018),
        _base(mean_excess_ann=-0.03, ci95_two_sided_lower=-0.04, ci95_two_sided_upper=-0.025, ci95_one_sided_lower=-0.037),
    ]
    assert len({_region(x) for x in cases}) == len(cases)
    assert "The `elif` order makes regions mutually exclusive" in _text(SPEC)


def test_primary_pass_is_not_a_point_estimate_rule() -> None:
    text = _text(SPEC)
    assert "positive point estimate alone cannot PASS" in text
    assert "PRIMARY_RETURN_PASS = (" in text
    assert "ci95_one_sided_lower > 0 and cumulative_excess > 0" in text


def test_equality_boundaries_are_explicit() -> None:
    assert _result(_base(ci95_one_sided_lower=0.0)) == "PROSPECTIVE_VALIDATION_INCONCLUSIVE"
    assert _result(_base(cumulative_excess=0.0)) == "PROSPECTIVE_VALIDATION_INCONCLUSIVE"
    assert _region(_base(mean_excess_ann=-0.02, ci95_two_sided_lower=-0.03, ci95_two_sided_upper=-0.02, ci95_one_sided_lower=-0.028)) == "STATISTICALLY_NEGATIVE_ECONOMICALLY_SMALL"
    text = _text(SPEC)
    assert "upper bound equals −2% is not below" in text
    assert "one-sided lower bound equal to zero is not" in text


def test_extension_is_not_a_fifth_outcome() -> None:
    text = _text(SPEC)
    assert "There is no fifth outcome" in text
    assert "extension_available == TRUE" in text
    assert "extension_available` at 48 months" in text or "extension_available == FALSE" in text
    assert "PROSPECTIVE_VALIDATION_PASS" in set(pd.read_csv(OUTCOME_TABLE).outcome)


def test_paper_slippage_proxy_formula_and_order_level_semantics() -> None:
    text = _text(PROTOCOL)
    for phrase in ("P_ref_o", "P_proxy_o", "side_o = +1", "side_o = -1", "slippage_proxy_bps_o = 10000", "one value per eligible order"): 
        assert phrase in text
    assert "MODEL_SLIPPAGE_BPS = 5" in text
    assert "OBSERVED_SLIPPAGE_PROXY_BPS" in text


def test_proxy_percentile_requires_twenty_and_is_nearest_rank() -> None:
    text = _text(PROTOCOL)
    assert "nearest-rank empirical percentile" in text
    assert "ceil(0.95 * m)" in text
    assert "at least **20** valid proxy" in text
    assert "NOT_OBSERVABLE_IN_PAPER_MODE" in text


def test_paper_mode_makes_no_realized_execution_claim() -> None:
    text = _text(PROTOCOL)
    assert "does not execute a broker transaction" in text
    assert "may not claim realized slippage" in text
    assert "SMALL_CAPITAL_LIVE_VALIDATION" in text


def test_tracking_difference_and_nav_reconciliation_are_distinct() -> None:
    text = _text(PROTOCOL)
    assert "tracking_difference_bps_o = 10000" in text
    assert "CANONICAL_FILL_TRACKING_DIFFERENCE_BPS" in text
    assert "NAV_RECONCILIATION_ERROR_USD = paper_nav - independently_reconstructed_nav" in text
    assert "never combined" in text


def test_latency_fields_are_exact_paper_diagnostics() -> None:
    text = _text(PROTOCOL)
    for expression in (
        "signal_to_order_latency_seconds = order_created_at - signal_close_at",
        "order_generation_latency_seconds = order_recorded_at - decision_ready_at",
        "market_data_acquisition_latency_seconds = data_acquired_at - exchange_event_at",
        "simulated_fill_recording_latency_seconds = fill_recorded_at - intended_execution_at",
    ):
        assert expression in text
    assert "PAPER_SYSTEM_OPERATIONAL_DIAGNOSTIC" in text
    assert "not proof of achievable live execution" in text


def test_paper_result_and_original_goals_are_separate() -> None:
    text = "\n".join(_text(path) for path in (SPEC, PROTOCOL, RATIONALE, STATISTICAL))
    assert "PAPER_PROTOCOL_RESULT" in text
    assert "ORIGINAL_RESEARCH_GOAL_STATUS" in text
    assert "PAPER_PROTOCOL_PASS_DOES_NOT_IMPLY_ORIGINAL_GOAL_PASS" in text


def test_severe_drawdown_limits_are_governance_not_original_objectives() -> None:
    text = _text(PROTOCOL)
    assert "PAPER_SEVERE_RISK_GOVERNANCE_LIMIT" in text
    assert "not `ORIGINAL_RESEARCH_OBJECTIVE`" in text
    assert "Goal A: `strategy MaxDD >= QQQ MaxDD`" in text
    assert "Goal B: `MaxDD >= -45%`" in text
    assert "Goal C: `MaxDD >= -50%`" in text


def test_mechanism_diagnostics_do_not_create_a_crossing_quota() -> None:
    text = "\n".join(_text(path) for path in (SPEC, PROTOCOL, STATISTICAL))
    assert "n_adverse_observations" in text
    assert "diagnostic only" in text
    assert "arbitrary crossing quota" in text
    assert "No arbitrary count of crossings" in text


def test_power_illustration_is_not_a_decision_input() -> None:
    text = "\n".join(_text(path) for path in (SPEC, PROTOCOL, STATISTICAL))
    assert "1.5%" in text and "phi = 0.25" in text
    assert "not used in PASS/FAIL" in text
    assert "not estimates of future volatility" in text
    assert "do not justify the 36-month horizon" in text


def test_primary_and_shadow_schedule_architecture_is_unchanged() -> None:
    text = _text(PROTOCOL)
    assert "PRIMARY_PROSPECTIVE_SCHEDULE = WEEKLY" in text
    assert "MONTHLY" in text and "BIMONTHLY" in text and "QUARTERLY" in text
    assert "ROBUSTNESS_SHADOW_EVIDENCE" in _text(STATISTICAL)
    assert "36 calendar months" in text
    assert "one fixed **12-calendar-month extension**" in text


def test_registry_distinguishes_assumptions_diagnostics_risk_goals_and_statistics() -> None:
    frame = pd.read_csv(THRESHOLDS)
    assert frame.prospective_status.eq("PROPOSED_NOT_FROZEN").all()
    registry_text = "\n".join(frame.rule.astype(str)) + "\n" + "\n".join(frame.derivation_rationale.astype(str))
    assert "MODEL_SLIPPAGE_BPS" in registry_text
    assert "PAPER_SYSTEM_OPERATIONAL_DIAGNOSTIC" in registry_text
    assert "NOT_OBSERVABLE_IN_PAPER_MODE" in registry_text
    assert {"BASELINE_SLIPPAGE_BPS", "OBSERVED_SLIPPAGE_PROXY_STATUS", "GOAL_A_DEFINITION", "PRIMARY_RETURN_PASS_LOWER_BOUND"} <= set(frame.threshold_id)
    assert set(frame.derivation_class) <= {"ORIGINAL_FROZEN_OBJECTIVE", "IMPLEMENTATION_TOLERANCE", "STATISTICAL_DESIGN", "ACCOUNTING_IDENTITY", "GOVERNANCE_LIMIT"}


def test_legacy_decision_table_has_new_terminal_contract_rows() -> None:
    frame = pd.read_csv(DECISIONS).set_index("decision_id")
    for key in ("TERMINAL_DECISION_FUNCTION", "RETURN_PASS_GATE", "RETURN_HARM_FLOOR", "MECHANISM_INFORMATION", "PAPER_SLIPPAGE_PROXY", "TRACKING_DIFFERENCE", "GOAL_OUTPUT_SEPARATION"):
        assert key in frame.index
        assert frame.loc[key, "status"] == "PROPOSED_NOT_FROZEN"


def test_frozen_manifest_and_research_tag_are_untouched() -> None:
    observed = hashlib.sha256(MANIFEST.read_bytes()).hexdigest()
    assert observed == MANIFEST_SHA
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert manifest["freeze_scope"]["historical_research_frozen"] is True
    assert manifest["freeze_scope"]["prospective_validation_started"] is False


def test_no_engine_observations_start_or_historical_backtest_were_added() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert manifest["freeze_scope"]["paper_trading_engine_implemented"] is False
    assert manifest["freeze_scope"]["paper_observations_present"] is False
    assert "does not collect official observations" in _text(PROTOCOL)
    assert "does not ... start Phase 9" not in _text(PROTOCOL)
    assert "This task creates no daemon" in _text(PROTOCOL)
