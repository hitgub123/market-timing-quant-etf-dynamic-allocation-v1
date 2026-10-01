"""Pre-start authenticated EODHD Free source-account acceptance tests."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
import re
import subprocess


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
ARTIFACT = DOCS / "paper_trading_source_account_acceptance.json"
LATENCY_EVIDENCE = ROOT / "reports/eodhd_prestart_latency_evidence.json"
RESUME_COMMIT = "e94326ae3f4b765bcf895de4684328ee756e6bd1"
FREEZE_COMMIT = "c75af4cf196419c6a27fbddcb10aaad966148b89"
RESEARCH_TAG = "2b2bf987f2e00540412d263a8ef39566af1d1e2a"
RESEARCH_MANIFEST_SHA = "dcb8f9d79de93c61e0bd7d93b743b0356be9eb3b1467acf5db9a58563889d400"
FAIL_GATE = "SOURCE_ACCEPTANCE_FAIL"


def load_artifact() -> dict:
    return json.loads(ARTIFACT.read_text(encoding="utf-8"))


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def test_account_gate_fails_on_operational_latency() -> None:
    artifact = load_artifact()
    assert artifact["no_api_requests_made"] is False
    assert artifact["historical_performance_used"] is False
    assert artifact["official_prospective_rows_created"] is False
    assert artifact["final_source_gate"] == FAIL_GATE
    assert artifact["publication_latency_observation_status"] == "FAIL_NOT_AVAILABLE_BY_DOCUMENTED_DEADLINE"


def test_credential_presence_is_recorded_without_value() -> None:
    credentials = load_artifact()["credentials"]
    assert credentials["available"] is True
    assert credentials["result"] == "ACCOUNT_CREDENTIALS_PRESENT"
    assert credentials["names_checked"] == ["EODHD_API_KEY"]
    assert credentials["values_printed"] is False
    assert credentials["values_stored"] is False
    assert load_artifact()["rerun_from_commit"] == RESUME_COMMIT


def test_prior_alpha_failure_is_preserved_as_historical_evidence() -> None:
    prior = load_artifact()["prior_alpha_vantage_acceptance"]
    assert prior["historical_gate"] == "SOURCE_ACCEPTANCE_FAIL"
    assert prior["preserved_as_historical_evidence"] is True
    assert prior["current_authoritative_role"] is False
    assert prior["historical_artifact_commit"] == "639157058cbacb2bfad8dca86d9c937b2a3850a3"


def test_authenticated_account_is_free_with_exact_limits() -> None:
    artifact = load_artifact()
    account = artifact["authenticated_endpoint_evidence"]["account"]
    assert artifact["account_plan_classification"] == "AUTHENTICATED_FREE_PLAN"
    assert account["access"] == "PASS"
    assert account["subscription_mode"] == account["subscription_type"] == "free"
    assert account["daily_rate_limit"] == 20
    assert account["minute_rate_limit_header"] == 1200
    assert "limited by one year" in account["free_history_warning"]


def test_qqq_and_qld_eod_fields_and_history_depth_pass() -> None:
    artifact = load_artifact()
    assert artifact["history_depth_adequate"] == "PASS_251_ROWS_GE_200"
    expected_fields = ["date", "open", "high", "low", "close", "adjusted_close", "volume"]
    for name in ("EOD_QQQ_US", "EOD_QLD_US"):
        endpoint = artifact["authenticated_endpoint_evidence"][name]
        assert endpoint["access"] == "PASS"
        assert endpoint["row_count"] == endpoint["unique_session_count"] == 251
        assert endpoint["duplicate_session_count"] == 0
        assert endpoint["first_date"] == "2025-09-26"
        assert endpoint["last_date"] == "2026-09-25"
        assert endpoint["field_semantics"] == expected_fields
        assert endpoint["required_field_null_count"] == 0


def test_corporate_action_access_and_fields_pass() -> None:
    endpoints = load_artifact()["authenticated_endpoint_evidence"]
    assert endpoints["DIVIDENDS_QQQ_US"]["row_count"] == 5
    assert endpoints["DIVIDENDS_QLD_US"]["row_count"] == 5
    assert endpoints["SPLITS_QQQ_US"]["row_count"] == 0
    assert endpoints["SPLITS_QLD_US"]["row_count"] == 1
    assert endpoints["SPLITS_QLD_US"]["field_semantics"] == ["date", "split"]
    assert "unadjustedValue" in endpoints["DIVIDENDS_QQQ_US"]["field_semantics"]


def test_all_authenticated_endpoint_bytes_reconstructed() -> None:
    endpoints = load_artifact()["authenticated_endpoint_evidence"]
    assert len(endpoints) == 7
    for endpoint in endpoints.values():
        assert endpoint["http_status"] == 200
        assert endpoint["raw_archive_reconstruction"] == "PASS"
        assert endpoint["raw_byte_length"] > 0
        assert re.fullmatch(r"[a-f0-9]{64}", endpoint["raw_sha256"])


def test_authenticated_200_value_window_reconstruction_passes() -> None:
    artifact = load_artifact()
    snapshot = artifact["snapshot_reconstruction"]
    assert artifact["snapshot_reconstruction_status"] == "AUTHENTICATED_200_VALUE_RECONSTRUCTION_PASS"
    assert snapshot["available_adjusted_close_count"] == 251
    assert snapshot["completed_adjusted_close_count"] == 200
    assert snapshot["reconstructed_adjusted_close_count"] == 200
    assert snapshot["window_first_date"] == "2025-12-09"
    assert snapshot["window_last_date"] == "2026-09-25"
    assert snapshot["byte_reconstruction"] == "PASS"
    assert snapshot["window_reconstruction"] == "PASS"
    assert re.fullmatch(r"[a-f0-9]{64}", snapshot["window_values_sha256"])
    assert snapshot["source_snapshot_id"] == f"sha256:{snapshot['raw_response_sha256']}"


def test_adjustment_semantics_are_frozen_without_cross_vendor_identity_claim() -> None:
    semantics = load_artifact()["adjustment_semantics"]
    assert semantics["raw_ohlc"] == "as traded"
    assert semantics["adjusted_close"] == "split and dividend adjusted"
    assert semantics["historical_recomputation_after_dividends"] is True
    assert semantics["point_in_time_snapshot_required"] is True
    assert semantics["cross_vendor_numeric_identity_claimed"] is False
    assert semantics["cross_vendor_splicing_or_averaging_allowed"] is False


def test_publication_gate_records_failed_observed_latency_without_invention() -> None:
    artifact = load_artifact()
    assert artifact["publication_sla_classification"] == "DOCUMENTED_MAJOR_US_EXCHANGES_WITHIN_15_MINUTES"
    assert artifact["publication_deadline_status"] == "FAIL_EXPECTED_SESSION_NOT_AVAILABLE_BY_DOCUMENTED_DEADLINE"
    assert artifact["final_source_gate"] == FAIL_GATE
    docs = (DOCS / "PAPER_TRADING_SOURCE_ACCOUNT_ACCEPTANCE.md").read_text(encoding="utf-8")
    assert "was not available by the documented deadline" in docs
    assert "must not calculate MA200 or a signal" in (DOCS / "PAPER_TRADING_SOURCE_FREEZE_READINESS.md").read_text(encoding="utf-8")


def test_prestart_latency_observer_records_exact_failed_run() -> None:
    observer = load_artifact()["prestart_latency_observer"]
    assert observer["status"] == "COMPLETED_FAIL_NOT_AVAILABLE_BY_DOCUMENTED_DEADLINE"
    assert observer["live_latency_requests_made"] is True
    assert observer["validate_only_status"] == "PASS"
    assert observer["expected_session"] == "2026-10-01"
    assert observer["exchange_close_at"] == "2026-10-01T20:00:00Z"
    assert observer["japan_close_at"] == "2026-10-02T05:00:00+09:00"
    assert observer["poll_offsets_seconds"] == [0, 300, 600, 900]
    assert observer["max_poll_count"] == observer["actual_poll_count"] == 4
    assert observer["http_status_counts"] == {"200": 4}
    assert observer["expected_session_row_counts"] == [0, 0, 0, 0]
    assert observer["raw_archive_reconstruction"] == "PASS_ALL_4"
    assert observer["first_available_at"] is observer["latency_seconds"] is None
    assert observer["final_status"] == "FAIL_NOT_AVAILABLE_BY_DOCUMENTED_DEADLINE"
    assert observer["raw_files_committed"] is False
    assert observer["sanitized_evidence_sha256"] == sha256(LATENCY_EVIDENCE.read_bytes())
    for relative in (observer["script"], observer["schema"], observer["runbook"], observer["sanitized_evidence"]):
        assert (ROOT / relative).is_file()


def test_committed_latency_evidence_matches_mechanical_failure_contract() -> None:
    evidence = json.loads(LATENCY_EVIDENCE.read_text(encoding="utf-8"))
    assert evidence["fixture_status"] == "PRE_START_NONOFFICIAL_SOURCE_EVIDENCE"
    assert evidence["expected_session"] == "2026-10-01"
    assert evidence["poll_offsets_seconds"] == [0, 300, 600, 900]
    assert evidence["max_poll_count"] == len(evidence["polls"]) == 4
    assert evidence["first_available_at"] is evidence["latency_seconds"] is None
    assert evidence["final_status"] == "FAIL_NOT_AVAILABLE_BY_DOCUMENTED_DEADLINE"
    assert evidence["credential_present"] is True
    assert evidence["credential_value_stored"] is False
    for ordinal, poll in enumerate(evidence["polls"], start=1):
        assert poll["ordinal"] == ordinal
        assert poll["http_status"] == 200
        assert poll["returned_row_count"] == 0
        assert poll["returned_last_date"] is None
        assert poll["raw_archive_reconstruction"] == "PASS"
        assert poll["raw_byte_length"] == 2
        assert re.fullmatch(r"[a-f0-9]{64}", poll["raw_sha256"])
    assert all(value is False for value in evidence["scope_controls"].values())


def test_rate_budget_arithmetic_and_daily_headroom() -> None:
    budget = load_artifact()["expected_request_budget"]
    sessions = budget["scheduled_decision_sessions_upper_bound"]
    assert sessions["conservative_sum"] == 74 == sum(sessions[k] for k in ("weekly", "monthly", "bimonthly", "quarterly"))
    per_date = budget["per_source_acquisition_date_requests"]
    components = [k for k in per_date if k not in {"base_requests", "safety_margin_fraction", "budget_with_safety_margin"}]
    assert per_date["base_requests"] == sum(per_date[k] for k in components) == 14
    assert per_date["budget_with_safety_margin"] == 18
    assert budget["annual_expected_requests_with_margin"] == 74 * 18
    assert budget["daily_account_limit"] == 20
    assert budget["daily_headroom_requests"] == 2
    assert budget["status"] == "RATE_LIMIT_ACCEPTANCE_PASS"


def test_massive_remains_reconciliation_only() -> None:
    artifact = load_artifact()
    assert artifact["reconciliation_source"] == "Massive Basic Free"
    assert artifact["reconciliation_source_role"] == "RECONCILIATION_MARKET_DATA_SOURCE"
    assert artifact["reconciliation_source_status"] == "AUTHENTICATED_ACCESS_PASS_501_ROWS"
    assert artifact["execution_proxy_status"] == "NOT_OBSERVABLE_IN_PAPER_MODE"


def test_active_source_contract_names_eodhd_authority() -> None:
    artifact = load_artifact()
    assert artifact["authoritative_source"] == "EODHD Free"
    assert artifact["source_role_update_status"] == "EODHD_AUTHORITY_REJECTED_BY_OPERATIONAL_LATENCY_GATE"
    with (DOCS / "paper_trading_data_source_decision.csv").open(newline="", encoding="utf-8") as handle:
        authority = next(row for row in csv.DictReader(handle) if row["data_role"] == "AUTHORITATIVE_MARKET_DATA_SOURCE")
    assert authority["vendor"] == "EODHD Free"
    assert authority["freeze_status"] == "PROPOSED_NOT_FROZEN"
    assert authority["verified_status"] == "AUTHENTICATED_CAPABILITY_PASS_OPERATIONAL_LATENCY_FAIL"
    registry = (DOCS / "paper_trading_operational_decision_registry.csv").read_text(encoding="utf-8")
    assert "Use EODHD Free" in registry


def test_source_disagreement_never_averages_or_substitutes() -> None:
    assert load_artifact()["source_disagreement_fixture_status"] == "PASS"
    text = (DOCS / "PAPER_TRADING_DATA_SOURCE_SPEC.md").read_text(encoding="utf-8")
    assert "No vendor values are averaged" in text
    assert "cannot silently replace" in text


def test_source_revision_null_is_supported_without_invented_vendor_id() -> None:
    schema = json.loads((ROOT / "schemas/paper_trading/paper_observations.schema.json").read_text(encoding="utf-8"))
    assert schema["properties"]["source_revision_id"]["type"] == ["string", "null"]
    assert load_artifact()["source_revision_id_null_supported"] == "PASS_BY_SCHEMA_AND_AUTHENTICATED_RESPONSES"
    readiness = (DOCS / "PAPER_TRADING_SOURCE_FREEZE_READINESS.md").read_text(encoding="utf-8")
    assert "no vendor ID invented" in readiness


def test_official_documentation_references_are_primary_vendor_sources() -> None:
    docs = load_artifact()["official_documentation"]
    assert docs["eod_endpoint"] == "https://eodhd.com/financial-apis/api-for-historical-data-and-volumes"
    assert docs["rate_limits"] == "https://eodhd.com/financial-apis/api-limits"
    assert docs["terms"] == "https://eodhd.com/financial-apis/terms-conditions"
    assert docs["data_sources"] == "https://eodhd.com/financial-apis/our-data-sources-and-data-partners"


def test_secret_leak_scan_passes_without_printing_or_storing_values() -> None:
    paths = [
        DOCS / "PAPER_TRADING_SOURCE_ACCOUNT_ACCEPTANCE.md",
        DOCS / "paper_trading_source_account_acceptance.json",
        ROOT / "reports/paper_trading_source_account_acceptance_audit.md",
        LATENCY_EVIDENCE,
        ROOT / "tests/test_paper_trading_source_acceptance.py",
    ]
    names = "(?:ALPHA_VANTAGE_API_KEY|MASSIVE_API_KEY|POLYGON_API_KEY|EODHD_API_KEY)"
    prohibited = re.compile(names + r"\s*[=:]\s*[^\s,}\]]+")
    for path in paths:
        assert not prohibited.search(path.read_text(encoding="utf-8")), path
    tracked = subprocess.check_output(["git", "ls-files", "-z"], cwd=ROOT).split(b"\0")
    for raw_path in tracked:
        if not raw_path:
            continue
        path = ROOT / raw_path.decode("utf-8")
        if not path.is_file():
            continue
        content = path.read_bytes()
        if b"\0" not in content:
            assert not prohibited.search(content.decode("utf-8", errors="ignore")), path
    diff = subprocess.check_output(["git", "diff", "--binary"], cwd=ROOT)
    assert not prohibited.search(diff.decode("utf-8", errors="ignore"))
    assert load_artifact()["secret_leak_scan_status"] == "SECRET_LEAK_SCAN_PASS"


def test_no_historical_strategy_metrics_or_performance_selection() -> None:
    artifact_text = ARTIFACT.read_text(encoding="utf-8")
    report_text = (ROOT / "reports/paper_trading_source_account_acceptance_audit.md").read_text(encoding="utf-8")
    assert load_artifact()["historical_performance_used"] is False
    for text in (artifact_text, report_text):
        assert not re.search(r"\b(?:cagr|sharpe|sortino|max_drawdown|ending_value|total_return)\b", text, re.IGNORECASE)


def test_no_engine_scheduler_start_phase9_or_acceptance_manifest() -> None:
    manifest = json.loads((ROOT / "reports/research_v1_freeze_manifest.json").read_text(encoding="utf-8"))
    assert manifest["freeze_scope"]["prospective_validation_started"] is False
    assert manifest["freeze_scope"]["paper_observations_present"] is False
    assert manifest["freeze_scope"]["paper_trading_engine_implemented"] is False
    assert not (ROOT / "paper_validation_v1_acceptance_manifest.json").exists()
    assert not (ROOT / "paper").exists()
    assert not (ROOT / "prospective_validation_v1").exists()
    assert not any("phase9" in path.name.lower() for path in (ROOT / "experiments").glob("*.py"))


def test_research_v1_freeze_and_closed_design_integrity_unchanged() -> None:
    tagged = subprocess.check_output(["git", "rev-parse", "research-v1.0-final^{commit}"], cwd=ROOT, text=True).strip()
    assert tagged == RESEARCH_TAG
    manifest = ROOT / "reports/research_v1_freeze_manifest.json"
    assert sha256(manifest.read_bytes()) == RESEARCH_MANIFEST_SHA
    closed = [
        "docs/PAPER_TRADING_PROTOCOL_V1_STATISTICAL_DESIGN.md",
        "docs/PAPER_TRADING_PROTOCOL_V1_DESIGN_RATIONALE.md",
        "docs/PAPER_TRADING_OUTCOME_DECISION_SPEC.md",
        "docs/paper_trading_outcome_decision_table.csv",
        "docs/paper_trading_threshold_registry.csv",
        "docs/paper_trading_protocol_decision_table.csv",
    ]
    for relative in closed:
        assert (ROOT / relative).read_bytes() == subprocess.check_output(["git", "show", f"{FREEZE_COMMIT}:{relative}"], cwd=ROOT)


def test_acceptance_artifacts_end_with_failed_gate_and_external_audit_line() -> None:
    assert (DOCS / "PAPER_TRADING_SOURCE_ACCOUNT_ACCEPTANCE.md").is_file()
    assert ARTIFACT.is_file()
    report = (ROOT / "reports/paper_trading_source_account_acceptance_audit.md").read_text(encoding="utf-8")
    assert FAIL_GATE in report
    assert report.rstrip().endswith("PAPER TRADING SOURCE ACCOUNT ACCEPTANCE COMPLETE — AWAITING EXTERNAL SOURCE AUDIT")
