"""Governance tests for paper-trading operational freeze preparation.

The tests are pre-start only.  They inspect documents, schemas, and synthetic
calendar fixtures; they do not import or start a paper engine and they never
create official prospective rows.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess

import pandas as pd
import pandas_market_calendars as mcal


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
SCHEMAS = ROOT / "schemas/paper_trading"
FREEZE_COMMIT = "c75af4cf196419c6a27fbddcb10aaad966148b89"
FREEZE_MANIFEST_SHA = "dcb8f9d79de93c61e0bd7d93b743b0356be9eb3b1467acf5db9a58563889d400"
REQUIRED_DOCS = {
    "PAPER_TRADING_DATA_SOURCE_SPEC.md",
    "paper_trading_data_source_decision.csv",
    "PAPER_TRADING_CALENDAR_SPEC.md",
    "PAPER_TRADING_LEDGER_SCHEMA.md",
    "PAPER_TRADING_ENVIRONMENT_SPEC.md",
    "PAPER_TRADING_OPERATIONAL_RUNBOOK.md",
    "paper_trading_incident_taxonomy.csv",
    "PAPER_TRADING_DRY_RUN_ACCEPTANCE.md",
    "PAPER_TRADING_IMPLEMENTATION_ACCEPTANCE_SPEC.md",
    "PAPER_TRADING_GOLDEN_FIXTURE_SPEC.md",
    "paper_trading_operational_decision_registry.csv",
    "PAPER_TRADING_ACCEPTANCE_MANIFEST_SPEC.md",
}
SCHEMA_FILES = {
    "paper_observations.schema.json",
    "paper_decisions.schema.json",
    "paper_orders.schema.json",
    "paper_fills.schema.json",
    "paper_nav.schema.json",
    "paper_tax.schema.json",
    "paper_incidents.schema.json",
    "paper_data_revisions.schema.json",
}


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _calendar(start: str, end: str) -> pd.DataFrame:
    return mcal.get_calendar("NASDAQ").schedule(start, end)


def _scheduled(index: pd.DatetimeIndex, frequency: str) -> pd.Series:
    periods = pd.Series(index.to_period("W-SUN" if frequency == "weekly" else frequency_to_period(frequency)), index=index)
    first = periods.ne(periods.shift(1))
    if frequency == "bimonthly":
        return first & index.month.isin((1, 3, 5, 7, 9, 11))
    return first


def frequency_to_period(frequency: str) -> str:
    return {"monthly": "M", "bimonthly": "M", "quarterly": "Q"}[frequency]


def test_required_operational_artifacts_exist() -> None:
    assert all((DOCS / name).is_file() for name in REQUIRED_DOCS)
    assert (ROOT / "reports/paper_trading_protocol_v1_operational_freeze_preparation_audit.md").is_file()


def test_all_machine_schemas_exist_and_are_valid_json() -> None:
    assert {p.name for p in SCHEMAS.glob("*.schema.json")} == SCHEMA_FILES
    for path in SCHEMAS.glob("*.schema.json"):
        schema = json.loads(path.read_text(encoding="utf-8"))
        assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
        assert schema["x-append-only"] is True
        assert schema["x-primary-key"] in schema["required"]
        assert schema["x-primary-key"] in schema["properties"]


def test_data_source_csv_schema_and_statuses() -> None:
    frame = pd.read_csv(DOCS / "paper_trading_data_source_decision.csv")
    assert list(frame.columns) == [
        "data_role", "vendor", "product_or_endpoint", "required_fields",
        "timestamp_semantics", "adjustment_semantics", "corporate_actions",
        "revision_policy", "raw_snapshot_available", "operational_dependency",
        "verified_status", "evidence_reference", "freeze_status",
    ]
    assert {"AUTHORITATIVE_MARKET_DATA_SOURCE", "RECONCILIATION_MARKET_DATA_SOURCE", "EXECUTION_PROXY_SOURCE", "CANONICAL_SESSION_CALENDAR"} <= set(frame.data_role)
    assert frame.freeze_status.eq("PROPOSED_NOT_FROZEN").all()


def test_data_source_roles_and_unverified_capabilities_are_explicit() -> None:
    text = _text(DOCS / "PAPER_TRADING_DATA_SOURCE_SPEC.md")
    for phrase in ("AUTHORITATIVE_MARKET_DATA_SOURCE", "RECONCILIATION_MARKET_DATA_SOURCE", "EXECUTION_PROXY_SOURCE", "UNVERIFIED_CAPABILITY", "NOT_OBSERVABLE_IN_PAPER_MODE"):
        assert phrase in text
    assert "historical strategy result" in text
    assert "not used" in text


def test_authoritative_source_documents_adjusted_and_raw_fields() -> None:
    text = _text(DOCS / "PAPER_TRADING_DATA_SOURCE_SPEC.md")
    for phrase in ("TIME_SERIES_DAILY_ADJUSTED", "TIME_SERIES_DAILY", "adjusted close", "raw OHLC", "SPLITS", "DIVIDENDS"):
        assert phrase in text
    assert "dividend-adjusted close not claimed" in text or "dividend adjustment is not currently provided" in text


def test_reconciliation_source_has_utc_and_raw_hash_policy() -> None:
    text = _text(DOCS / "PAPER_TRADING_DATA_SOURCE_SPEC.md")
    assert "Massive" in text and "UTC" in text and "raw-object SHA-256" in text
    assert "No vendor values are averaged" in text
    assert "cannot silently replace" in text


def test_calendar_is_explicit_new_york_and_not_vendor_derived() -> None:
    text = _text(DOCS / "PAPER_TRADING_CALENDAR_SPEC.md")
    for phrase in ("pandas_market_calendars.get_calendar(\"NASDAQ\")", "America/New_York", "09:30:00", "16:00:00", "early-close", "next_eligible_session"):
        assert phrase in text
    assert "never inferred from observed price rows" in text


def test_calendar_monday_holiday_fixture() -> None:
    sessions = _calendar("2024-01-15", "2024-01-19").index
    assert sessions[0].date().isoformat() == "2024-01-16"
    flags = _scheduled(pd.DatetimeIndex(sessions), "weekly")
    assert flags.sum() == 1 and flags.iloc[0]


def test_calendar_month_quarter_and_year_fixtures() -> None:
    sessions = _calendar("2023-12-29", "2024-04-03").index
    monthly = _scheduled(pd.DatetimeIndex(sessions), "monthly")
    quarterly = _scheduled(pd.DatetimeIndex(sessions), "quarterly")
    assert list(pd.DatetimeIndex(sessions[monthly]).date) == [pd.Timestamp("2023-12-29").date(), pd.Timestamp("2024-01-02").date(), pd.Timestamp("2024-02-01").date(), pd.Timestamp("2024-03-01").date(), pd.Timestamp("2024-04-01").date()]
    assert list(pd.DatetimeIndex(sessions[quarterly]).date) == [pd.Timestamp("2023-12-29").date(), pd.Timestamp("2024-01-02").date(), pd.Timestamp("2024-04-01").date()]


def test_calendar_bimonthly_odd_month_fixture() -> None:
    sessions = _calendar("2024-01-02", "2024-05-03").index
    selected = pd.DatetimeIndex(sessions[_scheduled(pd.DatetimeIndex(sessions), "bimonthly")])
    assert [d.month for d in selected] == [1, 3, 5]


def test_calendar_early_close_and_dst_fixtures() -> None:
    early = _calendar("2024-11-29", "2024-11-29").iloc[0]
    assert early.market_close.tz_convert("America/New_York").hour == 13
    spring = _calendar("2024-03-08", "2024-03-11").iloc[1]
    autumn = _calendar("2024-11-01", "2024-11-04").iloc[1]
    assert spring.market_open.tz_convert("America/New_York").hour == 9
    assert autumn.market_open.tz_convert("America/New_York").hour == 9
    assert spring.market_open.tz_convert("America/New_York").utcoffset() != autumn.market_open.tz_convert("America/New_York").utcoffset()


def test_schedule_semantics_and_required_fixture_names_are_documented() -> None:
    text = _text(DOCS / "PAPER_TRADING_CALENDAR_SPEC.md")
    for phrase in ("first eligible date in its Monday–Sunday", "first eligible date in its calendar month", "odd-numbered calendar month", "first eligible date in its calendar quarter", "SYNTHETIC_TEST_FIXTURE"):
        assert phrase in text
    for fixture in ("Monday holidays", "month-end", "January/April/July/October", "DST transitions", "early-close"):
        assert fixture in text


def test_timestamp_ontology_and_timezone_awareness_are_required() -> None:
    text = "\n".join(_text(p) for p in (DOCS / "PAPER_TRADING_DATA_SOURCE_SPEC.md", DOCS / "PAPER_TRADING_LEDGER_SCHEMA.md", DOCS / "PAPER_TRADING_ENVIRONMENT_SPEC.md"))
    for field in ("session_date", "exchange_open_at", "exchange_close_at", "signal_close_at", "data_available_at", "data_acquired_at", "decision_ready_at", "order_created_at", "order_recorded_at", "intended_execution_at", "proxy_price_timestamp", "fill_recorded_at", "valuation_timestamp", "ledger_written_at"):
        assert field in text
    assert "naive datetimes are rejected" in text
    assert "Japan" in text


def test_adjustment_and_revision_policy_is_append_only() -> None:
    text = "\n".join(_text(p) for p in (DOCS / "PAPER_TRADING_DATA_SOURCE_SPEC.md", DOCS / "PAPER_TRADING_LEDGER_SCHEMA.md"))
    for phrase in ("DATA_REVISION_INCIDENT", "original value", "revised value", "original raw hash", "revised raw hash", "never overwritten", "PROTOCOL_INVALID"):
        assert phrase in text


def test_fail_closed_actions_cover_required_conditions() -> None:
    frame = pd.read_csv(DOCS / "paper_trading_incident_taxonomy.csv")
    actions = set(frame.automatic_action)
    assert {"WAIT_THEN_SKIP", "INCIDENT_AND_CONTINUE", "INCIDENT_AND_RECONSTRUCT", "PROTOCOL_INVALID", "SKIP_WITH_INCIDENT"} <= actions
    text = _text(DOCS / "PAPER_TRADING_DATA_SOURCE_SPEC.md")
    for phrase in ("missing", "stale", "non-positive", "duplicate", "partial", "early close", "unscheduled", "outage", "ambiguity", "revision", "unavailable"):
        assert phrase in text
    assert "No operator may choose a price" in text


def test_source_disagreement_never_averages() -> None:
    text = _text(DOCS / "PAPER_TRADING_DATA_SOURCE_SPEC.md")
    assert "No vendor values are averaged" in text
    assert "unresolved disagreement creates an incident" in text
    assert "cannot silently replace" in text


def test_all_ledger_schemas_are_append_only_and_provenance_bearing() -> None:
    required_common = {"schema_version", "protocol_version", "fixture_status", "created_at", "previous_record_hash", "record_hash"}
    for path in SCHEMAS.glob("*.schema.json"):
        schema = json.loads(path.read_text(encoding="utf-8"))
        assert required_common <= set(schema["required"])
        assert schema["additionalProperties"] is False
        assert schema["properties"]["fixture_status"]["enum"] == ["SYNTHETIC_TEST_FIXTURE", "OFFICIAL_PROSPECTIVE"]


def test_each_named_ledger_schema_exists() -> None:
    text = _text(DOCS / "PAPER_TRADING_LEDGER_SCHEMA.md")
    for name in ("paper_observations", "paper_decisions", "paper_orders", "paper_fills", "paper_nav", "paper_tax", "paper_incidents", "paper_data_revisions"):
        assert name in text
        assert (SCHEMAS / f"{name}.schema.json").is_file()


def test_hash_chain_and_canonicalization_rules_are_exactly_documented() -> None:
    text = _text(DOCS / "PAPER_TRADING_LEDGER_SCHEMA.md")
    for phrase in ("UTF-8", "LF line endings", "SHA-256", "sorted keys", "compact separators", "NaN", "infinity", "previous_record_hash", "record_hash"):
        assert phrase in text
    assert "raw vendor-object hash" in text


def test_future_archive_layout_and_secret_exclusion_are_documented() -> None:
    text = _text(DOCS / "PAPER_TRADING_LEDGER_SCHEMA.md")
    for directory in ("paper/", "raw/", "observations/", "decisions/", "orders/", "fills/", "nav/", "tax/", "incidents/", "revisions/", "manifests/"):
        assert directory in text
    assert "API keys" in text and "never" in text


def test_gitignore_covers_credentials_and_official_future_data() -> None:
    text = _text(ROOT / ".gitignore")
    for pattern in (".env", "*.pem", "*.key", "secrets/", "paper/raw/", "paper/observations/", "paper/manifests/"):
        assert pattern in text


def test_environment_spec_preserves_dependency_contract_and_no_upgrade() -> None:
    text = _text(DOCS / "PAPER_TRADING_ENVIRONMENT_SPEC.md")
    for phrase in ("requirements.txt", "Python 3.14.4", "pandas-market-calendars", "IANA timezone", "No Research v1 dependency was upgraded"):
        assert phrase in text
    assert "no tokens or secrets" in text


def test_runbook_is_manual_and_covers_lifecycle() -> None:
    text = _text(DOCS / "PAPER_TRADING_OPERATIONAL_RUNBOOK.md")
    for heading in ("Before the scheduled close", "At the scheduled close", "After the decision", "At the next eligible open", "End of session", "Incident handling", "Manual intervention policy"):
        assert heading in text
    assert "no scheduler" in text
    assert "never backdate" in text


def test_manual_intervention_policy_is_explicit() -> None:
    text = _text(DOCS / "PAPER_TRADING_OPERATIONAL_RUNBOOK.md")
    for phrase in ("restart a crashed process", "restore connectivity", "refresh credentials", "append an incident", "choose favorable prices", "alter MA200", "delete a loss", "reset the start date", "modify thresholds"):
        assert phrase in text


def test_incident_taxonomy_is_machine_readable_and_deterministic() -> None:
    frame = pd.read_csv(DOCS / "paper_trading_incident_taxonomy.csv")
    expected = ["incident_code", "category", "trigger", "severity", "automatic_action", "operator_action_allowed", "evidence_required", "protocol_validity_effect", "restart_required", "freeze_status"]
    assert list(frame.columns) == expected
    assert frame.incident_code.is_unique
    assert frame.freeze_status.eq("PROPOSED_NOT_FROZEN").all()
    assert set(frame.severity) <= {"INFO", "WARNING", "RECOVERABLE", "MATERIAL", "PROTOCOL_INVALIDATING"}
    assert {"UNRESOLVED_SOURCE_DISAGREEMENT", "HASH_CHAIN_BREAK", "TIMESTAMP_AMBIGUITY"} <= set(frame.incident_code)


def test_dry_run_is_uncounted_and_return_blind() -> None:
    text = _text(DOCS / "PAPER_TRADING_DRY_RUN_ACCEPTANCE.md")
    assert "UNCOUNTED_OPERATIONAL_DRY_RUN" in text
    for phrase in ("zero to the 36-month horizon", "500 paired sessions", "not a dry-run acceptance criterion", "SYNTHETIC_TEST_FIXTURE", "official observation #1"):
        assert phrase in text


def test_dry_run_semantic_defect_requires_restart() -> None:
    text = _text(DOCS / "PAPER_TRADING_DRY_RUN_ACCEPTANCE.md")
    assert "economic-semantic defect" in text
    assert "complete restart of the uncounted dry run" in text
    assert "documentation/logging defect" in text


def test_implementation_acceptance_contract_exists() -> None:
    text = _text(DOCS / "PAPER_TRADING_IMPLEMENTATION_ACCEPTANCE_SPEC.md")
    for phrase in ("MA200", "calendar schedule", "close-`t`", "next-eligible-open", "5-bps", "position quantity", "NAV", "tax", "turnover", "drawdown", "paired daily excess", "terminal decision"):
        assert phrase in text
    assert "does not implement the production paper engine" in text


def test_golden_fixture_spec_covers_all_required_edge_cases() -> None:
    text = _text(DOCS / "PAPER_TRADING_GOLDEN_FIXTURE_SPEC.md")
    for fixture in ("MA_199", "MA_200", "MA_201", "MA_EQUAL", "MA_ABOVE", "MA_BELOW", "MONDAY_HOLIDAY", "MONTH_BOUNDARY", "BIMONTHLY_BOUNDARY", "QUARTER_BOUNDARY", "YEAR_BOUNDARY", "EARLY_CLOSE", "DST_SPRING", "DST_AUTUMN", "SPLIT", "DIVIDEND", "MISSING_CLOSE", "MISSING_OPEN", "STALE_CLOSE", "VENDOR_DISAGREEMENT", "QLD_TO_CASH", "CASH_TO_QLD", "TAX_GAIN", "TAX_LOSS", "INITIAL_DEPLOYMENT", "TERMINAL_DIAGNOSTIC", "HASH_BREAK"):
        assert fixture in text
    assert "written before execution" in text
    assert "historical strategy outputs" in text


def test_acceptance_manifest_is_spec_only_and_not_created() -> None:
    text = _text(DOCS / "PAPER_TRADING_ACCEPTANCE_MANIFEST_SPEC.md")
    assert "final `paper_validation_v1_acceptance_manifest.json` is deliberately not created" in text
    assert not (ROOT / "paper_validation_v1_acceptance_manifest.json").exists()
    for path in ("PAPER_TRADING_DATA_SOURCE_SPEC.md", "PAPER_TRADING_CALENDAR_SPEC.md", "PAPER_TRADING_LEDGER_SCHEMA.md", "PAPER_TRADING_OPERATIONAL_RUNBOOK.md", "PAPER_TRADING_DRY_RUN_ACCEPTANCE.md", "PAPER_TRADING_IMPLEMENTATION_ACCEPTANCE_SPEC.md"):
        assert path in text


def test_operational_registry_schema_and_statuses() -> None:
    frame = pd.read_csv(DOCS / "paper_trading_operational_decision_registry.csv")
    expected = ["decision_id", "domain", "decision", "rationale", "dependency", "evidence_source", "failure_behavior", "human_discretion", "implementation_required", "freeze_status"]
    assert list(frame.columns) == expected
    assert frame.decision_id.is_unique
    assert frame.freeze_status.eq("PROPOSED_NOT_FROZEN").all()
    assert {"DATA_AUTHORITY", "CALENDAR", "LEDGERS", "DRY_RUN", "ACCEPTANCE_MANIFEST", "PROSPECTIVE_BOUNDARY", "CLOCK_SOURCE", "STORAGE", "SECRET_MANAGEMENT", "SCHEDULER"} <= set(frame.decision_id)


def test_main_draft_references_operational_specs_without_freezing() -> None:
    text = _text(DOCS / "PAPER_TRADING_VALIDATION_PROTOCOL_V1_DRAFT.md")
    for name in ("PAPER_TRADING_DATA_SOURCE_SPEC.md", "PAPER_TRADING_CALENDAR_SPEC.md", "PAPER_TRADING_LEDGER_SCHEMA.md", "PAPER_TRADING_OPERATIONAL_RUNBOOK.md", "PAPER_TRADING_ACCEPTANCE_MANIFEST_SPEC.md"):
        assert name in text
    assert "PROPOSED_NOT_FROZEN" in text
    assert "does not create the final acceptance manifest" in text


def test_closed_statistical_and_economic_artifacts_are_byte_identical_to_design_close() -> None:
    closed = [
        "docs/PAPER_TRADING_PROTOCOL_V1_STATISTICAL_DESIGN.md",
        "docs/PAPER_TRADING_PROTOCOL_V1_DESIGN_RATIONALE.md",
        "docs/PAPER_TRADING_OUTCOME_DECISION_SPEC.md",
        "docs/paper_trading_outcome_decision_table.csv",
        "docs/paper_trading_threshold_registry.csv",
        "docs/paper_trading_protocol_decision_table.csv",
    ]
    for relative in closed:
        expected = subprocess.check_output(["git", "show", f"{FREEZE_COMMIT}:{relative}"], cwd=ROOT)
        assert (ROOT / relative).read_bytes() == expected


def test_research_tag_manifest_and_raw_hash_integrity_are_unchanged() -> None:
    tagged = subprocess.check_output(["git", "rev-parse", "research-v1.0-final^{commit}"], cwd=ROOT, text=True).strip()
    assert tagged == "2b2bf987f2e00540412d263a8ef39566af1d1e2a"
    manifest = ROOT / "reports/research_v1_freeze_manifest.json"
    assert _sha(manifest) == FREEZE_MANIFEST_SHA
    assert _sha(manifest) == manifest.with_suffix(".sha256").read_text(encoding="utf-8").split()[0]
    data = json.loads(manifest.read_text(encoding="utf-8"))
    assert data["freeze_scope"]["historical_research_frozen"] is True


def test_no_start_observation_engine_scheduler_or_phase9_exists() -> None:
    manifest = json.loads((ROOT / "reports/research_v1_freeze_manifest.json").read_text(encoding="utf-8"))
    assert manifest["freeze_scope"]["prospective_validation_started"] is False
    assert manifest["freeze_scope"]["paper_observations_present"] is False
    assert manifest["freeze_scope"]["paper_trading_engine_implemented"] is False
    assert not (ROOT / "paper").exists()
    assert not (ROOT / "prospective_validation_v1").exists()
    assert not any("phase9" in p.name.lower() for p in (ROOT / "experiments").glob("*.py"))
    assert not (ROOT / "paper_validation_v1_acceptance_manifest.json").exists()


def test_new_operational_decisions_have_no_frozen_status() -> None:
    for path in (DOCS / "paper_trading_data_source_decision.csv", DOCS / "paper_trading_incident_taxonomy.csv", DOCS / "paper_trading_operational_decision_registry.csv"):
        frame = pd.read_csv(path)
        status = frame["freeze_status"]
        assert status.eq("PROPOSED_NOT_FROZEN").all()
        assert not status.eq("FROZEN").any()
