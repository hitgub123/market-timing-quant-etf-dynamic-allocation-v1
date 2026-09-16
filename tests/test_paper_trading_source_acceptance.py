"""Pre-start authenticated source-account acceptance tests.

The live vendor calls were performed once in an isolated process. These tests
validate only the sanitized, non-secret evidence artifact and retain synthetic
controls for provenance and deterministic reconstruction. They never call a
vendor and never contain credential values.
"""

from __future__ import annotations

from decimal import Decimal
import hashlib
import json
from pathlib import Path
import re
import subprocess


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
ARTIFACT = DOCS / "paper_trading_source_account_acceptance.json"
RUN_COMMIT = "1cec7f42a6942043a9a227349762d8e033890f2e"
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


def test_account_gate_records_authenticated_fail_closed_result() -> None:
    artifact = load_artifact()
    assert artifact["no_api_requests_made"] is False
    assert artifact["historical_performance_used"] is False
    assert artifact["credentials"]["available"] is True
    assert artifact["credentials"]["values_stored"] is False
    assert artifact["credentials"]["result"] == "ACCOUNT_CREDENTIALS_PRESENT"
    assert artifact["final_source_gate"] == "SOURCE_ACCEPTANCE_FAIL"


def test_account_enabled_rerun_records_presence_without_values() -> None:
    artifact = load_artifact()
    rerun = artifact["account_enabled_rerun"]
    assert artifact["rerun_from_commit"] == RUN_COMMIT
    presence = rerun["credential_presence_check"]
    assert presence["ALPHA_VANTAGE_API_KEY"]["present"] is True
    assert presence["MASSIVE_API_KEY"]["present"] is True
    assert presence["ALPHA_VANTAGE_API_KEY"]["value_exposed"] is False
    assert presence["MASSIVE_API_KEY"]["value_exposed"] is False
    assert presence["ALPHA_VANTAGE_API_KEY"]["value_stored"] is False
    assert presence["MASSIVE_API_KEY"]["value_stored"] is False
    assert rerun["authenticated_requests_status"] == "COMPLETED_WITH_CAPABILITY_LIMITATIONS"
    assert rerun["sanitized_request_metadata_created"] is True
    assert rerun["result"] == "SOURCE_ACCEPTANCE_FAIL"


def test_authenticated_endpoint_capabilities_and_history_depth_are_explicit() -> None:
    artifact = load_artifact()
    alpha = artifact["authenticated_endpoint_evidence"]["alpha_vantage"]
    assert alpha["TIME_SERIES_DAILY_ADJUSTED_QQQ"]["access"] == "FAIL_PREMIUM_ENDPOINT_RESTRICTION"
    assert alpha["TIME_SERIES_DAILY_QQQ_FULL"]["access"] == "FAIL_FULL_OUTPUTSIZE_PREMIUM_RESTRICTION"
    assert alpha["TIME_SERIES_DAILY_QLD_FULL"]["access"] == "FAIL_FULL_OUTPUTSIZE_PREMIUM_RESTRICTION"
    for symbol in ("QQQ", "QLD"):
        compact = alpha[f"TIME_SERIES_DAILY_{symbol}_COMPACT"]
        assert compact["access"] == "PASS_COMPACT_ONLY"
        assert compact["row_count"] == 100
        assert compact["row_count"] < 200
        assert compact["field_semantics"] == ["1. open", "2. high", "3. low", "4. close", "5. volume"]
    assert artifact["history_depth_adequate"] == "FAIL_100_COMPACT_ROWS_LT_200"


def test_corporate_action_access_and_field_semantics_are_explicit() -> None:
    alpha = load_artifact()["authenticated_endpoint_evidence"]["alpha_vantage"]
    assert alpha["SPLITS_QQQ"]["access"] == "PASS"
    assert alpha["SPLITS_QLD"]["access"] == "PASS"
    assert alpha["DIVIDENDS_QQQ"]["access"] == "PASS"
    assert alpha["DIVIDENDS_QLD"]["access"] == "PASS"
    assert alpha["SPLITS_QQQ"]["row_count"] == 1
    assert alpha["SPLITS_QLD"]["row_count"] == 6
    assert alpha["DIVIDENDS_QQQ"]["row_count"] == 88
    assert alpha["DIVIDENDS_QLD"]["row_count"] == 34
    assert alpha["DIVIDENDS_QQQ"]["field_semantics"] == [
        "amount",
        "declaration_date",
        "ex_dividend_date",
        "payment_date",
        "record_date",
    ]


def test_authenticated_raw_snapshots_are_reconstructed_without_credentials() -> None:
    artifact = load_artifact()
    alpha = artifact["authenticated_endpoint_evidence"]["alpha_vantage"]
    massive = artifact["authenticated_endpoint_evidence"]["massive"]
    for endpoint in (*alpha.values(), *massive.values()):
        assert endpoint["raw_archive_reconstruction"] == "PASS"
        assert endpoint["raw_byte_length"] > 0
        assert re.fullmatch(r"[a-f0-9]{64}", endpoint["raw_sha256"])
    snapshot = artifact["snapshot_reconstruction"]
    assert snapshot["authenticated_archive_mode"] == "EPHEMERAL_ISOLATED_TEMPORARY_DIRECTORY"
    assert snapshot["authenticated_raw_bytes_archived_before_parse"] is True
    assert snapshot["authenticated_raw_bytes_reconstructed"] is True
    assert snapshot["authenticated_archive_contains_credentials"] is False


def test_account_and_rate_limit_messages_are_sanitized() -> None:
    artifact = load_artifact()
    assert artifact["account_plan_classification"] == "FREE_KEY_PLAN_PREMIUM_ENDPOINTS_RESTRICTED"
    assert artifact["rate_limit_status"] == "OBSERVED_25_PER_DAY_1_REQUEST_PER_SECOND"
    assert artifact["rate_limit_evidence"]["per_second_burst"] == "1 request per second"
    assert artifact["rate_limit_evidence"]["daily_limit"] == "25 requests per day"
    text = json.dumps(artifact, sort_keys=True).lower()
    assert "apikey=" not in text
    assert "authorization:" not in text


def test_massive_is_reconciliation_only_and_authenticated_access_is_recorded() -> None:
    artifact = load_artifact()
    assert artifact["reconciliation_source_role"] == "RECONCILIATION_MARKET_DATA_SOURCE"
    assert artifact["reconciliation_source_status"] == "AUTHENTICATED_ACCESS_PASS_DELAYED_501_ROWS"
    assert artifact["execution_proxy_status"] == "NOT_OBSERVABLE_IN_PAPER_MODE"
    massive = artifact["authenticated_endpoint_evidence"]["massive"]
    for symbol in ("QQQ", "QLD"):
        entry = massive[f"DAY_AGGREGATES_{symbol}"]
        assert entry["access"] == "PASS"
        assert entry["http_status"] == 200
        assert entry["response_status"] == "DELAYED"
        assert entry["row_count"] == 501
        assert entry["requested_from"] == "2000-01-01"
        assert entry["requested_to"] == "2026-09-17"
    docs = (DOCS / "PAPER_TRADING_SOURCE_ACCOUNT_ACCEPTANCE.md").read_text(encoding="utf-8")
    assert "not promoted to the authoritative adjusted-close source" in docs


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
    assert load_artifact()["source_revision_id_null_supported"] == "PASS_BY_SCHEMA_AND_AUTHENTICATED_RESPONSES"
    text = (DOCS / "PAPER_TRADING_SOURCE_FREEZE_READINESS.md").read_text(encoding="utf-8")
    assert "no vendor ID is invented" in text


def test_publication_status_is_unresolved_without_fabricated_sla() -> None:
    artifact = load_artifact()
    assert artifact["publication_sla_classification"] == "UNRESOLVED"
    assert artifact["publication_deadline_status"] == "PUBLICATION_DEADLINE_NOT_READY"
    docs = (DOCS / "PAPER_TRADING_SOURCE_ACCOUNT_ACCEPTANCE.md").read_text(encoding="utf-8")
    assert "No deterministic after-close publication SLA was established" in docs
    assert "No polling deadline was invented" in docs


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


def test_source_role_and_account_gate_remain_fail_closed() -> None:
    artifact = load_artifact()
    assert artifact["authoritative_source"] == "Alpha Vantage"
    assert artifact["account_plan_classification"] == "FREE_KEY_PLAN_PREMIUM_ENDPOINTS_RESTRICTED"
    assert artifact["final_source_gate"] == "SOURCE_ACCEPTANCE_FAIL"
    assert artifact["adjusted_daily_access"] == "ACCOUNT_PLAN_RESTRICTION_PREMIUM_REQUIRED"
    assert artifact["raw_daily_access"] == "COMPACT_ACCESS_FULL_OUTPUTSIZE_RESTRICTED"


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


def test_source_acceptance_artifacts_exist_and_final_status_is_fail_closed() -> None:
    assert (DOCS / "PAPER_TRADING_SOURCE_ACCOUNT_ACCEPTANCE.md").is_file()
    assert ARTIFACT.is_file()
    assert (ROOT / "reports/paper_trading_source_account_acceptance_audit.md").is_file()
    report = (ROOT / "reports/paper_trading_source_account_acceptance_audit.md").read_text(encoding="utf-8")
    assert "SOURCE_ACCEPTANCE_FAIL" in report
    assert report.rstrip().endswith("PAPER TRADING SOURCE ACCOUNT ACCEPTANCE COMPLETE — AWAITING EXTERNAL SOURCE AUDIT")
