"""Offline controls for the Tiingo Free source-acceptance candidate."""

from __future__ import annotations

import csv
import json
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
PLAN = DOCS / "PAPER_TRADING_TIINGO_FREE_ACCEPTANCE_PLAN.md"
MATRIX = DOCS / "paper_trading_source_remediation_matrix.csv"
ACCOUNT = DOCS / "paper_trading_source_account_acceptance.json"


def candidate() -> dict[str, str]:
    with MATRIX.open(newline="", encoding="utf-8") as handle:
        return next(row for row in csv.DictReader(handle) if row["option_id"] == "TIINGO_FREE")


def test_candidate_is_free_and_only_ready_for_account_test() -> None:
    row = candidate()
    assert row["source_plan"] == "Tiingo End-of-Day Free"
    assert row["recurring_cost"].startswith("$0/month")
    assert row["classification"] == "SOURCE_OPTION_READY_FOR_ACCEPTANCE_TEST"
    assert "account acceptance" in row["unresolved_blockers"].lower()


def test_documented_fields_cover_frozen_source_categories() -> None:
    row = candidate()
    for field in ("adjClose", "raw", "adjusted"):
        assert field.lower() in (row["adjusted_qqq"] + row["raw_qqq"]).lower()
    assert "divCash" in row["corporate_actions"]
    assert "splitFactor" in row["corporate_actions"]
    assert "dividend reconstruction algorithm" in row["frozen_signal_compatibility"]


def test_documented_limits_and_timing_are_explicit_but_not_authenticated() -> None:
    row = candidate()
    assert "50 requests/hour" in row["rate_limits"]
    assert "1000/day" in row["rate_limits"]
    assert "1 GB/month" in row["rate_limits"]
    assert "5:30pm" in row["publication_timing"]
    assert "8:00pm" in row["publication_timing"]
    plan = PLAN.read_text(encoding="utf-8")
    assert "ACCOUNT_CREDENTIALS_NOT_AVAILABLE" in plan
    assert "account-observable PRE_START verification remains required" in row["publication_timing"]


def test_plan_preserves_failed_gate_and_no_source_promotion() -> None:
    account = json.loads(ACCOUNT.read_text(encoding="utf-8"))
    assert account["final_source_gate"] == "SOURCE_ACCEPTANCE_FAIL"
    plan = PLAN.read_text(encoding="utf-8")
    assert "is not the authoritative source" in " ".join(plan.lower().split())
    assert "does not repair the failed EODHD observation" in plan
    assert "must not use the failed EODHD session" in plan
    assert "No result from this plan creates Final Freeze" in plan


def test_plan_requires_raw_before_parse_and_no_strategy_work() -> None:
    plan = PLAN.read_text(encoding="utf-8")
    assert "raw response bytes archived before parsing" in plan
    for phrase in ("historical performance", "MA200 value", "signal", "trade", "return"):
        assert phrase in plan
    for path in (ROOT / "paper", ROOT / "prospective_validation_v1", ROOT / "paper_validation_v1_acceptance_manifest.json"):
        assert not path.exists()


def test_candidate_artifacts_contain_no_secret_value_or_auth_material() -> None:
    contents = PLAN.read_text(encoding="utf-8") + MATRIX.read_text(encoding="utf-8")
    prohibited = re.compile(r"TIINGO_API_KEY\s*[=:]\s*[^\s,}\]]+")
    assert not prohibited.search(contents)
    assert "Authorization:" not in contents
    assert "token=" not in contents.lower()


def test_official_tiingo_references_are_present() -> None:
    plan = PLAN.read_text(encoding="utf-8")
    assert "https://www.tiingo.com/products/end-of-day-stock-price-data" in plan
    assert "https://www.tiingo.com/documentation/end-of-day" in plan
