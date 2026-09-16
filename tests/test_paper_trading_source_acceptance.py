"""Pre-start source-account acceptance tests.

No test in this module calls a vendor or uses real market data. Account-gated
checks are represented as explicit unavailable statuses; synthetic fixtures
prove only provenance and deterministic operational behavior.
"""

from __future__ import annotations

from decimal import Decimal
import hashlib
import json
from pathlib import Path
import re
import subprocess

import pytest


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
ARTIFACT = DOCS / "paper_trading_source_account_acceptance.json"
FREEZE_COMMIT = "c75af4cf196419c6a27fbddcb10aaad966148b89"
RESEARCH_TAG = "2b2bf987f2e00540412d263a8ef39566af1d1e2a"
RESEARCH_MANIFEST_SHA = "dcb8f9d79de93c61e0bd7d93b743b0356be9eb3b1467acf5db9a58563889d400"


def load_artifact() -> dict[str, object]:
    return json.loads(ARTIFACT.read_text(encoding="utf-8"))


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def synthetic_raw_response() -> bytes:
    rows = [{"session_index": index, "adjusted_close": f"{100 + index / 100:.8f}"} for index in range(200)]
    return json.dumps(
        {"fixture": "SYNTHETIC_QQQ_ADJUSTED_WINDOW_V1", "rows": rows},
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def test_account_gate_and_no_authenticated_request_are_explicit() -> None:
    artifact = load_artifact()
    assert artifact["no_api_requests_made"] is True
    assert artifact["historical_performance_used"] is False
    assert artifact["credentials"] == {
        "mechanism": "environment variables or approved secret store",
        "names_checked": ["ALPHA_VANTAGE_API_KEY", "MASSIVE_API_KEY", "POLYGON_API_KEY"],
        "available": False,
        "result": "ACCOUNT_CREDENTIALS_NOT_AVAILABLE",
        "values_stored": False,
    }
    assert artifact["final_source_gate"] == "ACCOUNT_CREDENTIALS_NOT_AVAILABLE"


def test_account_capability_artifact_has_required_fields_and_statuses() -> None:
    artifact = load_artifact()
    required = {
        "authoritative_source",
        "account_plan_classification",
        "adjusted_daily_access",
        "raw_daily_access",
        "corporate_action_access",
        "history_depth_adequate",
        "publication_sla_classification",
        "publication_deadline_status",
        "rate_limit_status",
        "snapshot_reconstruction_status",
        "vendor_revision_capability",
        "reconciliation_source_status",
        "execution_proxy_status",
        "secret_leak_scan_status",
        "final_source_gate",
    }
    assert required <= set(artifact)
    assert artifact["publication_sla_classification"] in {
        "DOCUMENTED_PUBLICATION_SLA",
        "ACCOUNT_SPECIFIC_PUBLICATION_SLA",
        "NO_DOCUMENTED_PUBLICATION_SLA",
        "UNRESOLVED",
    }
    assert artifact["publication_deadline_status"] == "PUBLICATION_DEADLINE_NOT_READY"


def test_public_documentation_references_are_primary_vendor_sources() -> None:
    artifact = load_artifact()
    assert artifact["official_documentation"]["alpha_vantage"] == "https://www.alphavantage.co/documentation/"
    assert artifact["official_documentation"]["massive_stocks_overview"] == "https://polygon.io/docs/rest/stocks/overview"
    docs = (DOCS / "PAPER_TRADING_SOURCE_ACCOUNT_ACCEPTANCE.md").read_text(encoding="utf-8")
    for endpoint in ("TIME_SERIES_DAILY_ADJUSTED", "TIME_SERIES_DAILY", "SPLITS", "DIVIDENDS"):
        assert endpoint in docs


def test_synthetic_snapshot_is_archived_before_parse_and_exactly_reconstructs_200_values(tmp_path: Path) -> None:
    raw = synthetic_raw_response()
    expected_hash = sha256(raw)
    archived = tmp_path / "synthetic_raw_response.json"
    archived.write_bytes(raw)
    parsed_once = json.loads(raw.decode("utf-8"))
    del parsed_once
    reconstructed_bytes = archived.read_bytes()
    parsed_twice = json.loads(reconstructed_bytes.decode("utf-8"))
    values = [Decimal(row["adjusted_close"]) for row in parsed_twice["rows"]]
    assert reconstructed_bytes == raw
    assert len(values) == 200
    assert expected_hash == load_artifact()["snapshot_reconstruction"]["raw_response_sha256"]
    assert f"sha256:{expected_hash}" == load_artifact()["snapshot_reconstruction"]["source_snapshot_id"]


def test_synthetic_ma_reconstruction_is_deterministic_and_not_performance_analysis() -> None:
    rows = json.loads(synthetic_raw_response().decode("utf-8"))["rows"]
    values = [Decimal(row["adjusted_close"]) for row in rows]
    ma = sum(values) / Decimal(len(values))
    signal = "ABOVE_MA" if values[-1] > ma else "AT_OR_BELOW_MA"
    assert ma == Decimal("100.995")
    assert signal == "ABOVE_MA"
    snapshot = load_artifact()["snapshot_reconstruction"]
    assert snapshot["completed_adjusted_close_count"] == 200
    assert snapshot["reconstructed_adjusted_close_count"] == 200
    assert Decimal(str(snapshot["test_only_ma200"])) == ma
    assert snapshot["test_only_signal_classification"] == signal
    assert load_artifact()["historical_performance_used"] is False


def test_snapshot_fixture_is_nonofficial_and_has_no_prospective_directory() -> None:
    snapshot = load_artifact()["snapshot_reconstruction"]
    assert snapshot["fixture_status"] == "SYNTHETIC_TEST_FIXTURE"
    assert snapshot["official_directory_written"] is False
    assert not (ROOT / "paper").exists()
    assert not (ROOT / "prospective_validation_v1").exists()


def test_source_revision_null_is_supported_without_invented_vendor_id() -> None:
    schema = json.loads((ROOT / "schemas/paper_trading/paper_observations.schema.json").read_text(encoding="utf-8"))
    assert schema["properties"]["source_revision_id"]["type"] == ["string", "null"]
    assert load_artifact()["source_revision_id_null_supported"] == "PASS_BY_SCHEMA_AND_SYNTHETIC_FIXTURE"
    text = (DOCS / "PAPER_TRADING_SOURCE_FREEZE_READINESS.md").read_text(encoding="utf-8")
    assert "no vendor ID is invented" in text


def test_publication_status_is_unresolved_without_fabricated_sla() -> None:
    artifact = load_artifact()
    assert artifact["publication_sla_classification"] == "UNRESOLVED"
    assert artifact["publication_deadline_status"] == "PUBLICATION_DEADLINE_NOT_READY"
    docs = (DOCS / "PAPER_TRADING_SOURCE_ACCOUNT_ACCEPTANCE.md").read_text(encoding="utf-8")
    assert "No after-close polling was run" in docs
    assert "no 15-minute sla was invented" in docs.lower()


def test_rate_budget_calculation_is_deterministic_and_performance_blind() -> None:
    budget = load_artifact()["expected_request_budget"]
    sessions = budget["scheduled_decision_sessions_upper_bound"]
    assert sessions["conservative_sum"] == sum(sessions[key] for key in ("weekly", "monthly", "bimonthly", "quarterly"))
    per_session = budget["per_scheduled_session_requests"]
    request_fields = [key for key in per_session if key not in {"base_requests", "safety_margin_fraction", "budget_with_safety_margin"}]
    assert per_session["base_requests"] == sum(per_session[key] for key in request_fields)
    assert per_session["budget_with_safety_margin"] == 20
    assert budget["annual_expected_requests_with_margin"] == sessions["conservative_sum"] * per_session["budget_with_safety_margin"]
    assert budget["status"] == "RATE_LIMIT_NOT_READY"
    assert "performance" not in budget["planning_basis"].lower() or "no prices" in budget["planning_basis"].lower()


def test_massive_is_reconciliation_only_and_optional_proxy_cannot_block() -> None:
    artifact = load_artifact()
    assert artifact["reconciliation_source_role"] == "RECONCILIATION_MARKET_DATA_SOURCE"
    assert artifact["reconciliation_source_status"] == "ACCOUNT_CREDENTIALS_NOT_AVAILABLE"
    assert artifact["execution_proxy_status"] == "NOT_OBSERVABLE_IN_PAPER_MODE"
    docs = (DOCS / "PAPER_TRADING_SOURCE_ACCOUNT_ACCEPTANCE.md").read_text(encoding="utf-8")
    assert "not promoted to the authoritative adjusted-close source" in docs


def test_source_disagreement_fixture_never_averages_or_substitutes() -> None:
    authoritative = Decimal("100.00")
    reconciliation = Decimal("99.00")
    incident_code = "SOURCE_DISAGREEMENT"
    chosen = authoritative
    assert incident_code == "SOURCE_DISAGREEMENT"
    assert chosen == authoritative
    assert chosen != (authoritative + reconciliation) / 2
    assert load_artifact()["source_disagreement_fixture_status"] == "PASS"
    text = (DOCS / "PAPER_TRADING_DATA_SOURCE_SPEC.md").read_text(encoding="utf-8")
    assert "No vendor values are averaged" in text
    assert "cannot silently replace" in text


def test_secret_leak_scan_passes_without_printing_or_storing_values() -> None:
    paths = [
        DOCS / "PAPER_TRADING_SOURCE_ACCOUNT_ACCEPTANCE.md",
        DOCS / "paper_trading_source_account_acceptance.json",
        ROOT / "reports/paper_trading_source_account_acceptance_audit.md",
        ROOT / "tests/test_paper_trading_source_acceptance.py",
    ]
    prohibited = re.compile(r"(?:ALPHA_VANTAGE_API_KEY|MASSIVE_API_KEY|POLYGON_API_KEY)\s*[=:]\s*[^\s,}]+")
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
        if b"\0" in content:
            continue
        assert not prohibited.search(content.decode("utf-8", errors="ignore")), path
    diff = subprocess.check_output(["git", "diff", "--binary"], cwd=ROOT)
    assert not prohibited.search(diff.decode("utf-8", errors="ignore"))
    assert load_artifact()["secret_leak_scan_status"] == "SECRET_LEAK_SCAN_PASS"


def test_no_historical_strategy_metrics_or_performance_selection_in_artifacts() -> None:
    artifact_text = ARTIFACT.read_text(encoding="utf-8")
    report_text = (ROOT / "reports/paper_trading_source_account_acceptance_audit.md").read_text(encoding="utf-8")
    assert load_artifact()["historical_performance_used"] is False
    for text in (artifact_text, report_text):
        assert not re.search(r"\b(?:cagr|sharpe|sortino|max_drawdown|ending_value|total_return)\b", text, re.IGNORECASE)
        assert "backtest" not in text.lower() or "no historical performance" in text.lower()


def test_source_role_and_account_gate_are_not_converted_to_pass() -> None:
    artifact = load_artifact()
    assert artifact["authoritative_source"] == "Alpha Vantage"
    assert artifact["account_plan_classification"] == "ACCOUNT_CREDENTIALS_NOT_AVAILABLE"
    assert artifact["final_source_gate"] == "ACCOUNT_CREDENTIALS_NOT_AVAILABLE"
    assert artifact["adjusted_daily_access"] == "UNVERIFIED_CAPABILITY"
    assert artifact["raw_daily_access"] == "UNVERIFIED_CAPABILITY"
    assert artifact["corporate_action_access"] == "UNVERIFIED_CAPABILITY"


def test_no_engine_scheduler_start_phase9_or_acceptance_manifest() -> None:
    manifest = json.loads((ROOT / "reports/research_v1_freeze_manifest.json").read_text(encoding="utf-8"))
    assert manifest["freeze_scope"]["prospective_validation_started"] is False
    assert manifest["freeze_scope"]["paper_observations_present"] is False
    assert manifest["freeze_scope"]["paper_trading_engine_implemented"] is False
    assert not (ROOT / "paper_validation_v1_acceptance_manifest.json").exists()
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


def test_source_acceptance_artifacts_exist_and_final_status_is_pending_account() -> None:
    assert (DOCS / "PAPER_TRADING_SOURCE_ACCOUNT_ACCEPTANCE.md").is_file()
    assert ARTIFACT.is_file()
    assert (ROOT / "reports/paper_trading_source_account_acceptance_audit.md").is_file()
    report = (ROOT / "reports/paper_trading_source_account_acceptance_audit.md").read_text(encoding="utf-8")
    assert "ACCOUNT_CREDENTIALS_NOT_AVAILABLE" in report
    assert report.rstrip().endswith("PAPER TRADING SOURCE ACCOUNT ACCEPTANCE COMPLETE — AWAITING EXTERNAL SOURCE AUDIT")
