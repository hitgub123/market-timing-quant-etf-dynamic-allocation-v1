"""Authenticated, performance-blind EODHD Free feasibility controls."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "docs/paper_trading_eodhd_free_feasibility.json"
MATRIX = ROOT / "docs/paper_trading_source_remediation_matrix.csv"
REPORT = ROOT / "reports/paper_trading_source_remediation_options_audit.md"
ACCOUNT_ARTIFACT = ROOT / "docs/paper_trading_source_account_acceptance.json"
BASELINE_COMMIT = "e94326ae3f4b765bcf895de4684328ee756e6bd1"
RESEARCH_TAG = "2b2bf987f2e00540412d263a8ef39566af1d1e2a"
RESEARCH_MANIFEST_SHA = "dcb8f9d79de93c61e0bd7d93b743b0356be9eb3b1467acf5db9a58563889d400"


def evidence() -> dict:
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def eodhd_matrix_row() -> dict[str, str]:
    with MATRIX.open(newline="", encoding="utf-8") as handle:
        return next(row for row in csv.DictReader(handle) if row["option_id"] == "EODHD_FREE")


def test_authenticated_free_account_and_limits_are_explicit() -> None:
    data = evidence()
    assert data["evidence_classes"]["authenticated_vendor_evidence"] is True
    assert data["account"]["http_status"] == 200
    assert data["account"]["subscription_mode"] == "free"
    assert data["account"]["subscription_type"] == "free"
    assert data["account"]["daily_rate_limit"] == 20
    assert data["account"]["minute_rate_limit_header"] == 1200
    assert "limited by one year" in data["account"]["free_history_warning"]


def test_qqq_and_qld_have_complete_required_fields_and_depth() -> None:
    data = evidence()
    assert data["history_depth"] == {
        "required_completed_sessions": 200,
        "observed_completed_sessions_per_symbol": 251,
        "gate": "PASS_251_GE_200",
    }
    required = ["date", "open", "high", "low", "close", "adjusted_close", "volume"]
    for symbol in ("QQQ.US", "QLD.US"):
        series = data["daily_eod"][symbol]
        assert series["http_status"] == 200
        assert series["row_count"] == series["unique_session_count"] == 251
        assert series["duplicate_session_count"] == 0
        assert series["first_session"] == "2025-09-26"
        assert series["last_session"] == "2026-09-25"
        assert series["latest_completed_session_present"] is True
        assert series["required_fields"] == required
        assert all(value == 0 for value in series["required_field_null_counts"].values())
        assert series["adjusted_close_differs_from_close_count"] > 200


def test_authenticated_corporate_action_endpoints_are_available() -> None:
    actions = evidence()["corporate_actions"]
    assert actions["QQQ.US_dividends"]["row_count"] == 5
    assert actions["QLD.US_dividends"]["row_count"] == 5
    assert actions["QQQ.US_splits"]["row_count"] == 0
    assert actions["QLD.US_splits"]["row_count"] == 1
    assert actions["QLD.US_splits"]["first_event_date"] == "2025-11-20"
    dividend_fields = [
        "currency", "date", "declarationDate", "paymentDate",
        "period", "recordDate", "unadjustedValue", "value",
    ]
    assert actions["QQQ.US_dividends"]["fields"] == dividend_fields
    assert actions["QLD.US_dividends"]["fields"] == dividend_fields


def test_raw_responses_are_byte_reconstructable_and_storage_is_permitted() -> None:
    data = evidence()
    records = [data["account"], *data["daily_eod"].values(), *data["corporate_actions"].values()]
    assert len(records) == 7
    for record in records:
        assert record["raw_archive_reconstruction"] == "PASS"
        assert record["raw_byte_length"] > 0
        assert len(record["raw_sha256"]) == 64
        int(record["raw_sha256"], 16)
    assert data["provenance"] == {
        "raw_response_archived_before_parse": True,
        "raw_response_reconstructed_byte_identically": True,
        "raw_archive_storage": "isolated temporary directory",
        "raw_archive_deleted_after_collector_exit": True,
        "personal_use_storage_documented_as_permitted": True,
        "redistribution_permitted": False,
    }


def test_adjustment_semantics_match_without_claiming_numeric_identity() -> None:
    semantics = evidence()["adjustment_semantics"]
    assert "splits and dividends" in semantics["vendor_documentation"]
    assert semantics["historical_adjusted_close_recomputed_after_new_dividends"] is True
    assert semantics["point_in_time_raw_snapshot_required"] is True
    assert semantics["compatible_with_frozen_adjusted_close_field_semantics"] is True
    assert semantics["exact_cross_vendor_numerical_identity_required"] is False
    comparison = evidence()["frozen_reference_comparison"]
    assert comparison["QQQ.US"]["adjusted_close_exact_count"] == 0
    assert comparison["QLD.US"]["adjusted_close_exact_count"] == 0
    assert comparison["classification"] == "DOCUMENTED_SEMANTIC_MATCH_WITH_EXPECTED_VENDOR_NUMERICAL_DIFFERENCES"


def test_publication_claim_requires_pre_start_observation() -> None:
    publication = evidence()["publication_timing"]
    assert "within 15 minutes" in publication["official_documentation"]
    assert publication["authenticated_latency_observation_completed"] is False
    assert publication["classification"] == "DOCUMENTED_SLA_REQUIRES_PRE_START_ACCOUNT_OBSERVATION"


def test_historical_feasibility_ready_is_preserved_but_current_option_failed() -> None:
    data = evidence()
    row = eodhd_matrix_row()
    assert data["final_classification"] == "SOURCE_OPTION_READY_FOR_ACCEPTANCE_TEST"
    assert row["classification"] == "SOURCE_OPTION_NOT_VIABLE"
    assert "2026-10-01" in row["publication_timing"]
    assert data["scope_controls"]["source_promoted"] is False
    assert data["scope_controls"]["official_observation_started"] is False
    report = REPORT.read_text(encoding="utf-8")
    assert "formal EODHD account acceptance" in report
    assert "SOURCE_REMEDIATION_REQUIRED" in report


def test_no_strategy_performance_or_prospective_operation_was_started() -> None:
    scope = evidence()["scope_controls"]
    assert scope == {
        "historical_performance_calculated": False,
        "backtest_run": False,
        "signal_calculated": False,
        "strategy_or_protocol_changed": False,
        "source_promoted": False,
        "official_observation_started": False,
    }
    assert not (ROOT / "paper_validation_v1_acceptance_manifest.json").exists()
    assert not (ROOT / "paper").exists()
    assert not (ROOT / "prospective_validation_v1").exists()
    assert not any("phase9" in path.name.lower() for path in (ROOT / "experiments").glob("*.py"))


def test_prior_failed_gate_is_preserved_and_frozen_research_remains_unchanged() -> None:
    account = json.loads(ACCOUNT_ARTIFACT.read_text(encoding="utf-8"))
    assert account["final_source_gate"] == "SOURCE_ACCEPTANCE_FAIL"
    assert account["prior_alpha_vantage_acceptance"]["historical_gate"] == "SOURCE_ACCEPTANCE_FAIL"
    assert subprocess.check_output(
        ["git", "show", f"{BASELINE_COMMIT}:docs/paper_trading_eodhd_free_feasibility.json"], cwd=ROOT
    ) == EVIDENCE.read_bytes()
    tagged = subprocess.check_output(
        ["git", "rev-parse", "research-v1.0-final^{commit}"], cwd=ROOT, text=True
    ).strip()
    assert tagged == RESEARCH_TAG
    manifest = ROOT / "reports/research_v1_freeze_manifest.json"
    assert hashlib.sha256(manifest.read_bytes()).hexdigest() == RESEARCH_MANIFEST_SHA


def test_artifacts_contain_no_secret_or_authorization_material() -> None:
    contents = EVIDENCE.read_text(encoding="utf-8") + MATRIX.read_text(encoding="utf-8") + REPORT.read_text(encoding="utf-8")
    assert ("EODHD_API_KEY" + "=") not in contents.upper()
    assert "api_token=" not in contents.lower()
    assert "authorization:" not in contents.lower()
    assert "credential_value_stored\": false" in contents
