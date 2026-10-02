"""Authenticated, performance-blind Massive Basic Free feasibility controls."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "docs/paper_trading_massive_basic_free_feasibility.json"
MATRIX = ROOT / "docs/paper_trading_source_remediation_matrix.csv"
REPORT = ROOT / "reports/paper_trading_source_remediation_options_audit.md"
ACCOUNT_ARTIFACT = ROOT / "docs/paper_trading_source_account_acceptance.json"
BASELINE_COMMIT = "639157058cbacb2bfad8dca86d9c937b2a3850a3"
RESEARCH_TAG = "2b2bf987f2e00540412d263a8ef39566af1d1e2a"
RESEARCH_MANIFEST_SHA = "dcb8f9d79de93c61e0bd7d93b743b0356be9eb3b1467acf5db9a58563889d400"


def evidence() -> dict:
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def basic_matrix_row() -> dict[str, str]:
    with MATRIX.open(newline="", encoding="utf-8") as handle:
        return next(row for row in csv.DictReader(handle) if row["option_id"] == "MASSIVE_BASIC")


def test_authenticated_evidence_is_sanitized_and_scoped() -> None:
    data = evidence()
    assert data["evidence_classes"]["authenticated_vendor_evidence"] is True
    assert data["credential_controls"] == {
        "credential_present": True,
        "credential_value_stored": False,
        "credential_value_logged": False,
        "sanitized_request_urls_only": True,
        "collector": "isolated process",
        "api_request_count": 8,
    }
    assert data["scope_controls"] == {
        "historical_performance_calculated": False,
        "backtest_run": False,
        "signal_calculated": False,
        "strategy_or_protocol_changed": False,
        "source_promoted": False,
        "reconciliation_role_preserved": True,
    }


def test_qqq_and_qld_raw_and_split_adjusted_history_is_complete() -> None:
    aggregates = evidence()["daily_aggregates"]
    assert set(aggregates) == {"QQQ_raw", "QQQ_split_adjusted", "QLD_raw", "QLD_split_adjusted"}
    for name, series in aggregates.items():
        assert series["http_status"] == 200
        assert series["response_status"] == "OK"
        assert series["row_count"] == series["unique_session_count"] == 501
        assert series["first_session"] == "2024-09-26"
        assert series["last_session"] == series["expected_last_completed_session"] == "2026-09-25"
        assert series["latest_completed_session_present"] is True
        assert series["missing_completed_sessions_count"] == 0
        assert series["duplicate_session_count"] == 0
        assert series["fields"] == ["c", "h", "l", "n", "o", "t", "v", "vw"]
        assert series["adjusted"] is name.endswith("split_adjusted")
    assert evidence()["history_depth"] == {
        "required_completed_sessions": 200,
        "observed_completed_sessions": 501,
        "gate": "PASS_501_GE_200",
    }


def test_corporate_action_access_and_field_semantics() -> None:
    actions = evidence()["corporate_actions"]
    assert actions["QQQ_splits"]["row_count"] == 0
    assert actions["QLD_splits"]["row_count"] == 6
    assert actions["QQQ_dividends"]["row_count"] == 65
    assert actions["QLD_dividends"]["row_count"] == 34
    assert actions["QLD_splits"]["fields"] == ["execution_date", "id", "split_from", "split_to", "ticker"]
    dividend_fields = [
        "cash_amount", "currency", "declaration_date", "dividend_type",
        "ex_dividend_date", "frequency", "id", "pay_date", "record_date", "ticker",
    ]
    assert actions["QQQ_dividends"]["fields"] == dividend_fields
    assert actions["QLD_dividends"]["fields"] == dividend_fields


def test_all_authenticated_raw_responses_were_reconstructed_before_deletion() -> None:
    data = evidence()
    records = list(data["daily_aggregates"].values()) + list(data["corporate_actions"].values())
    assert len(records) == 8
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
    }


def test_rate_limit_and_publication_evidence_remain_honest() -> None:
    data = evidence()
    account = data["account_observations"]
    assert account["documented_rate_limit"] == "5 requests per minute"
    assert account["observed_rate_limit_headers"] == []
    assert account["rate_limit_headroom_accepted"] is False
    publication = data["publication_timing"]
    assert publication["deterministic_after_close_sla_established"] is False
    assert publication["classification"] == "UNRESOLVED_PRE_START_OPERATIONAL_LATENCY_EVIDENCE_REQUIRED"


def test_dividend_adjusted_semantic_equivalence_fails_closed() -> None:
    data = evidence()
    semantics = data["adjustment_semantics"]
    assert semantics["native_split_adjusted_aggregates"] is True
    assert semantics["native_dividend_adjusted_close"] is False
    assert semantics["documented_adjusted_parameter_semantics"] == "split adjustment only"
    assert semantics["frozen_dividend_adjusted_ma200_semantic_equivalence"] == "NOT_PROVEN"
    assert data["final_classification"] == "SOURCE_OPTION_NOT_VIABLE"
    basic = basic_matrix_row()
    assert basic["classification"] == "SOURCE_OPTION_NOT_VIABLE"
    assert "reconciliation-only" in basic["unresolved_blockers"]


def test_prior_alpha_gate_is_preserved_and_frozen_research_is_identical() -> None:
    account = json.loads(ACCOUNT_ARTIFACT.read_text(encoding="utf-8"))
    assert account["final_source_gate"] == "SOURCE_ACCEPTANCE_FAIL"
    assert account["prior_alpha_vantage_acceptance"]["historical_gate"] == "SOURCE_ACCEPTANCE_FAIL"
    assert subprocess.check_output(
        ["git", "show", f"{BASELINE_COMMIT}:docs/paper_trading_massive_basic_free_feasibility.json"], cwd=ROOT
    ) == EVIDENCE.read_bytes()
    tagged = subprocess.check_output(
        ["git", "rev-parse", "research-v1.0-final^{commit}"], cwd=ROOT, text=True
    ).strip()
    assert tagged == RESEARCH_TAG
    manifest = ROOT / "reports/research_v1_freeze_manifest.json"
    assert hashlib.sha256(manifest.read_bytes()).hexdigest() == RESEARCH_MANIFEST_SHA


def test_report_preserves_source_roles_and_no_operational_start() -> None:
    text = REPORT.read_text(encoding="utf-8")
    assert "Massive remains a reconciliation source only" in text
    assert "SOURCE_OPTION_NOT_VIABLE" in text
    assert "SOURCE_ACCEPTANCE_FAIL" in text
    assert "no deterministic after-close" in text.lower()
    assert not (ROOT / "paper_validation_v1_acceptance_manifest.json").exists()
    assert not (ROOT / "paper").exists()
    assert not (ROOT / "prospective_validation_v1").exists()
    assert not any("phase9" in path.name.lower() for path in (ROOT / "experiments").glob("*.py"))


def test_artifacts_contain_no_secret_or_authorization_material() -> None:
    contents = EVIDENCE.read_text(encoding="utf-8") + MATRIX.read_text(encoding="utf-8") + REPORT.read_text(encoding="utf-8")
    assert ("ALPHA_VANTAGE_API_KEY" + "=") not in contents
    assert ("MASSIVE_API_KEY" + "=") not in contents
    assert "apikey=" not in contents.lower()
    assert "api_key=" not in contents.lower()
    assert "authorization:" not in contents.lower()
    assert "historical_performance_calculated\": false" in contents
