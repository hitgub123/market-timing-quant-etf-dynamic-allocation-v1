"""Performance-blind source-remediation option audit controls.

These tests consume only sanitized prior acceptance evidence and public-doc
classification artifacts. They never call a vendor, calculate performance,
select a source from historical outcomes, or create prospective records.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
import re
import subprocess


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
MATRIX = DOCS / "paper_trading_source_remediation_matrix.csv"
REPORT = ROOT / "reports/paper_trading_source_remediation_options_audit.md"
ACCOUNT_ARTIFACT = DOCS / "paper_trading_source_account_acceptance.json"
BASELINE_COMMIT = "24a759da9a5246a468336dc9e7d11860883467ed"
RESEARCH_TAG = "2b2bf987f2e00540412d263a8ef39566af1d1e2a"
RESEARCH_MANIFEST_SHA = "dcb8f9d79de93c61e0bd7d93b743b0356be9eb3b1467acf5db9a58563889d400"


def rows() -> list[dict[str, str]]:
    with MATRIX.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def report_text() -> str:
    return REPORT.read_text(encoding="utf-8")


def test_matrix_has_required_options_and_classifications() -> None:
    entries = rows()
    assert len(entries) == 8
    assert {row["option_id"] for row in entries} == {
        "ALPHA_PREMIUM",
        "MASSIVE_BASIC",
        "MASSIVE_STARTER",
        "MASSIVE_DEVELOPER",
        "MASSIVE_ADVANCED",
        "EODHD_FREE",
        "TIINGO_FREE",
        "ALTERNATIVE_UNINVESTIGATED",
    }
    allowed = {
        "SOURCE_OPTION_READY_FOR_ACCEPTANCE_TEST",
        "SOURCE_OPTION_POTENTIALLY_VIABLE",
        "SOURCE_OPTION_NOT_VIABLE",
        "SOURCE_OPTION_INSUFFICIENT_EVIDENCE",
        "SOURCE_OPTION_ACCOUNT_CAPABILITY_PASS_PENDING_LATENCY",
    }
    assert {row["classification"] for row in entries} <= allowed
    assert sum(row["classification"] == "SOURCE_OPTION_ACCOUNT_CAPABILITY_PASS_PENDING_LATENCY" for row in entries) == 1
    assert sum(row["classification"] == "SOURCE_OPTION_POTENTIALLY_VIABLE" for row in entries) == 4
    assert sum(row["classification"] == "SOURCE_OPTION_NOT_VIABLE" for row in entries) == 2


def test_alpha_premium_option_preserves_failed_account_evidence() -> None:
    artifact = json.loads(ACCOUNT_ARTIFACT.read_text(encoding="utf-8"))
    alpha = next(row for row in rows() if row["option_id"] == "ALPHA_PREMIUM")
    assert artifact["final_source_gate"] == "SOURCE_ACCEPTANCE_FAIL"
    assert artifact["prior_alpha_vantage_acceptance"]["historical_gate"] == "SOURCE_ACCEPTANCE_FAIL"
    assert "premium" in alpha["adjusted_qqq"].lower()
    assert "price" in alpha["unresolved_blockers"].lower()
    assert "no purchase" in alpha["unresolved_blockers"].lower()
    assert alpha["classification"] == "SOURCE_OPTION_POTENTIALLY_VIABLE"


def test_massive_is_not_promoted_and_dividend_semantics_are_explicit() -> None:
    basic = next(row for row in rows() if row["option_id"] == "MASSIVE_BASIC")
    paid = [row for row in rows() if row["option_id"] in {"MASSIVE_STARTER", "MASSIVE_DEVELOPER", "MASSIVE_ADVANCED"}]
    assert "split-adjusted only" in basic["adjusted_qqq"]
    assert "dividend" in basic["frozen_signal_compatibility"].lower()
    assert basic["classification"] == "SOURCE_OPTION_NOT_VIABLE"
    for row in paid:
        assert "deterministic" in row["frozen_signal_compatibility"].lower()
        assert "acceptance" in row["unresolved_blockers"].lower()
        assert row["classification"] == "SOURCE_OPTION_POTENTIALLY_VIABLE"
    text = report_text().lower()
    assert "massive remains" in text
    assert "not promoted" in text


def test_remediation_is_not_a_parameter_or_performance_selection() -> None:
    text = report_text().lower()
    normalized = " ".join(text.split())
    assert "performance-blind" in text
    assert "no backtest" in text
    assert "no strategy code" in text
    assert "signal ranking" in text
    assert "tiingo end-of-day free completed authenticated capability acceptance" in normalized
    assert not re.search(r"\b(?:best|winner|optimal|selected)\s+(?:source|vendor|plan)\b", text)
    for row in rows():
        assert "historical" not in row["classification"].lower()


def test_public_documentation_and_publication_boundary_are_explicit() -> None:
    text = report_text()
    for url in (
        "https://www.alphavantage.co/documentation/",
        "https://www.alphavantage.co/premium/",
        "https://www.massive.com/docs/rest/stocks/aggregates/custom-bars",
        "https://massive.com/docs/rest/stocks/overview",
        "https://massive.com/pricing",
        "https://massive.com/knowledge-base/article/is-massives-stock-data-adjusted-for-splits-or-dividends",
        "https://www.massive.com/blog/new-splits-and-dividends-endpoints",
        "https://www.tiingo.com/products/end-of-day-stock-price-data",
        "https://www.tiingo.com/documentation/end-of-day",
    ):
        assert url in text
    assert "no deterministic after-close publication sla" in text.lower()
    assert "latency observation remains required" in text.lower()
    assert re.search(r"no polling deadline\s+is\s+selected", text.lower())


def test_final_gate_is_mechanical_and_no_acceptance_is_started() -> None:
    text = report_text()
    assert "SOURCE_REMEDIATION_REQUIRED" in text
    assert text.rstrip().endswith("PAPER TRADING SOURCE REMEDIATION OPTIONS AUDIT COMPLETE — AWAITING EXTERNAL AUDIT")
    assert not (ROOT / "paper_validation_v1_acceptance_manifest.json").exists()
    assert not (ROOT / "paper").exists()
    assert not (ROOT / "prospective_validation_v1").exists()
    assert not any("phase9" in path.name.lower() for path in (ROOT / "experiments").glob("*.py"))


def test_closed_research_and_prior_account_artifact_are_unchanged() -> None:
    artifact = json.loads(ACCOUNT_ARTIFACT.read_text(encoding="utf-8"))
    assert artifact["prior_alpha_vantage_acceptance"]["historical_gate"] == "SOURCE_ACCEPTANCE_FAIL"
    tagged = subprocess.check_output(["git", "rev-parse", "research-v1.0-final^{commit}"], cwd=ROOT, text=True).strip()
    assert tagged == RESEARCH_TAG
    manifest = ROOT / "reports/research_v1_freeze_manifest.json"
    import hashlib

    assert hashlib.sha256(manifest.read_bytes()).hexdigest() == RESEARCH_MANIFEST_SHA
    assert artifact["final_source_gate"] == "SOURCE_ACCEPTANCE_FAIL"


def test_matrix_has_no_secret_material_or_auth_headers() -> None:
    contents = MATRIX.read_text(encoding="utf-8") + report_text()
    assert ("ALPHA_VANTAGE_API_KEY" + "=") not in contents
    assert ("MASSIVE_API_KEY" + "=") not in contents
    assert "apikey=" not in contents.lower()
    assert "authorization:" not in contents.lower()
    assert "SOURCE_ACCEPTANCE_FAIL" in contents


def test_eodhd_failure_and_tiingo_candidate_are_mechanically_distinct() -> None:
    eodhd = next(row for row in rows() if row["option_id"] == "EODHD_FREE")
    tiingo = next(row for row in rows() if row["option_id"] == "TIINGO_FREE")
    assert eodhd["classification"] == "SOURCE_OPTION_NOT_VIABLE"
    assert "2026-10-01" in eodhd["publication_timing"]
    assert tiingo["classification"] == "SOURCE_OPTION_ACCOUNT_CAPABILITY_PASS_PENDING_LATENCY"
    assert tiingo["recurring_cost"].startswith("$0/month")
    assert "50 requests/hour" in tiingo["rate_limits"]
    assert "1000/day" in tiingo["rate_limits"]
    assert "5:30pm" in tiingo["publication_timing"]
    assert "publication observation" in tiingo["unresolved_blockers"].lower()
