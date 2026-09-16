"""Lightweight governance tests for the Research v1.0 freeze and draft."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "reports/research_v1_freeze_manifest.json"
PHASE8D_RUN = ROOT / "reports/runs/20260915_phase8d_final_research_verdict"
PROTOCOL_PATH = ROOT / "docs/PAPER_TRADING_VALIDATION_PROTOCOL_V1_DRAFT.md"
DECISIONS_PATH = ROOT / "docs/paper_trading_protocol_decision_table.csv"


def _manifest() -> dict:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_freeze_tag_resolves_to_accepted_commit() -> None:
    accepted = subprocess.check_output(["git", "rev-parse", "2b2bf98^{commit}"], cwd=ROOT, text=True).strip()
    tagged = subprocess.check_output(["git", "rev-parse", "research-v1.0-final^{commit}"], cwd=ROOT, text=True).strip()
    assert tagged == accepted
    assert subprocess.check_output(["git", "cat-file", "-t", "research-v1.0-final"], cwd=ROOT, text=True).strip() == "tag"


def test_manifest_records_accepted_commit_and_tag() -> None:
    manifest = _manifest()
    assert manifest["git_commit"] == subprocess.check_output(["git", "rev-parse", "2b2bf98^{commit}"], cwd=ROOT, text=True).strip()
    assert manifest["git_tag"] == "research-v1.0-final"
    assert manifest["git_tag_target"] == manifest["git_commit"]


def test_manifest_companion_hash_matches() -> None:
    expected = MANIFEST_PATH.with_suffix(".sha256").read_text(encoding="utf-8").split()[0]
    assert expected == _sha256(MANIFEST_PATH)


def test_manifest_contains_accepted_phase8d_hashes() -> None:
    manifest = _manifest()
    expected = {
        "final_evidence_matrix.csv": "ef35796946bfd587f14311003dfc4575f98657c70f5b9d79992ee70cafc78605",
        "original_goal_scorecard.csv": "ad3998d4291cb9a6f77c4a32d09aa6c07f3e82efe4ffdc1d2f087868169ae462",
        "complexity_incremental_evidence.csv": "b622514a52fbe60c25a63856684a03004a5a3041a06e1a9d7ca457dc8f8f180f",
        "final_claim_evidence_ledger.csv": "92a9c23854dd13302d4ee3f92aa8f37f44988389caa2c0b73bbb5faffe3ec8a5",
        "phase8d_configuration.json": "3bee1f2da9872c7338e0b39afadf7def0c13be327c678d835863e7780381362a",
        "phase8d_final_research_verdict.md": "4470e42756cb5f02e6cd551224250cd15dc8632463eec273c07b77c9db80b284",
        "phase8d_audit_diff.md": "fb9bc23354eb089157ea651c97991673e24e57e805a415295f67332f008e64a7",
    }
    assert manifest["accepted_hashes"]["phase8d"] == expected
    for name, digest in expected.items():
        assert _sha256(PHASE8D_RUN / name) == digest


def test_manifest_contains_all_accepted_source_groups() -> None:
    groups = _manifest()["accepted_hashes"]
    assert {"phase7b", "phase8a", "phase8b1", "phase8b2_remediation", "phase8c", "phase8d"} <= set(groups)
    assert len(groups["phase8a"]) == 9
    assert len(groups["phase8b1"]) == 7
    assert len(groups["phase8b2_remediation"]) == 11
    assert len(groups["phase8c"]) == 14


def test_raw_snapshot_hashes_are_present_and_current() -> None:
    manifest = _manifest()
    for name, digest in manifest["raw_data_snapshot_hashes"].items():
        assert _sha256(ROOT / "data" / name) == digest


def test_protocol_is_explicitly_draft_and_no_start_is_activated() -> None:
    text = PROTOCOL_PATH.read_text(encoding="utf-8")
    manifest = _manifest()
    assert "DRAFT FOR AUDIT" in text and "NOT FROZEN" in text
    assert "No prospective start timestamp is activated" in text
    assert manifest["freeze_scope"]["prospective_validation_started"] is False


def test_fixed_ma200_is_primary_and_phase7a_is_not() -> None:
    text = PROTOCOL_PATH.read_text(encoding="utf-8")
    assert "FIXED_MA200_QQQ_TO_QLD` is the **PRIMARY PROSPECTIVE MODEL**" in text
    assert "NON-DECISION SHADOW" in text
    assert "Phase7B Model A and Model B are not prospective candidates" in text


def test_no_frequency_is_selected() -> None:
    text = PROTOCOL_PATH.read_text(encoding="utf-8")
    manifest = _manifest()
    assert "did not select weekly, monthly, bimonthly, or quarterly" in text
    assert "no live-frequency choice in this draft" in text
    assert manifest["freeze_scope"]["historical_frequency_selected"] is False


def test_no_paper_observations_or_live_authorization() -> None:
    manifest = _manifest()
    text = PROTOCOL_PATH.read_text(encoding="utf-8")
    assert manifest["freeze_scope"]["paper_observations_present"] is False
    assert "no prospective observations collected" in text
    assert "authorizes no live capital" in text


def test_all_new_decisions_are_proposed_not_frozen() -> None:
    decisions = pd.read_csv(DECISIONS_PATH)
    assert len(decisions) >= 15
    assert decisions.status.eq("PROPOSED_NOT_FROZEN").all()
    protocol = PROTOCOL_PATH.read_text(encoding="utf-8")
    assert protocol.count("PROPOSED_NOT_FROZEN") >= 10


def test_research_v1_immutability_policy_is_explicit() -> None:
    text = (ROOT / "docs/RESEARCH_V1_FROZEN.md").read_text(encoding="utf-8")
    for phrase in (
        "historical strategy definitions",
        "historical signal definitions",
        "historical parameter values",
        "historical execution assumptions",
        "historical economic paths",
        "historical statistical tests",
        "historical canonical reports",
        "historical raw-data snapshots",
        "accepted research conclusions",
        "must not overwrite Research v1.0",
        "prospective_validation_v1/",
    ):
        assert phrase in text


def test_manifest_has_final_research_conclusions() -> None:
    conclusions = _manifest()["research_conclusions"]
    assert conclusions == {
        "final_classification": "PROMISING_BUT_INSUFFICIENT",
        "paper_validation_decision": "PROCEED_TO_PAPER_TRADING_VALIDATION",
        "fixed_ma200_evidence": "MODERATE",
        "phase7a_incremental_complexity": "NOT_JUSTIFIED",
        "phase7b": "NO_DEMONSTRATED_VALUE",
        "dsr_status": "DSR_NOT_IDENTIFIABLE_FROM_FROZEN_ARTIFACTS",
    }
