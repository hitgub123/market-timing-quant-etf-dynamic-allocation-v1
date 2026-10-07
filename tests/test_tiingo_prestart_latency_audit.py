"""Offline controls for the frozen Tiingo PRE_START publication sample."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from scripts.tiingo_prestart_latency_audit import LatencyAuditError, audit
from scripts.tiingo_prestart_latency_observer import REQUIRED, SCHEDULE, SESSION, SESSION_OPEN, SYMBOLS


ROOT = Path(__file__).resolve().parents[1]
COMMITTED = ROOT / "reports/tiingo_prestart_latency_evidence.json"
SCHEMA = ROOT / "schemas/source_acceptance/tiingo_prestart_latency_evidence.schema.json"
READINESS = ROOT / "docs/PAPER_TRADING_SOURCE_FREEZE_READINESS.md"
ACCOUNT = ROOT / "reports/tiingo_free_account_acceptance.json"


def _row() -> dict[str, object]:
    row: dict[str, object] = {
        "date": f"{SESSION}T00:00:00.000Z", "open": 100.0, "high": 102.0,
        "low": 99.0, "close": 101.0, "volume": 1000,
        "adjOpen": 99.0, "adjHigh": 101.0, "adjLow": 98.0,
        "adjClose": 100.0, "adjVolume": 1000, "divCash": 0.0,
        "splitFactor": 1.0,
    }
    assert set(REQUIRED) == set(row)
    return row


def _fixture(tmp_path: Path) -> tuple[dict, Path]:
    evidence = json.loads(COMMITTED.read_text(encoding="utf-8"))
    archive = tmp_path / "private"
    archive.mkdir(mode=0o700)
    for poll in evidence["polls"]:
        body = json.dumps([_row()] if poll["poll"] >= 2 else [], separators=(",", ":")).encode()
        raw = archive / poll["raw_file"]
        raw.write_bytes(body)
        raw.chmod(0o600)
        poll["raw_bytes"] = len(body)
        poll["raw_sha256"] = hashlib.sha256(body).hexdigest()
        poll["row_count"] = 1 if poll["poll"] >= 2 else 0
    return evidence, archive


def test_frozen_session_schedule_and_scope_are_explicit() -> None:
    evidence = json.loads(COMMITTED.read_text(encoding="utf-8"))
    assert evidence["expected_session"] == SESSION == "2026-10-06"
    assert evidence["session_open_at"] == SESSION_OPEN
    assert evidence["schedule_utc"] == list(SCHEDULE)
    assert evidence["symbols"] == list(SYMBOLS)
    assert len(evidence["polls"]) == 10
    assert len({(p["poll"], p["symbol"]) for p in evidence["polls"]}) == 10
    assert evidence["performance_calculated"] is False
    assert evidence["official_observation_created"] is False
    assert evidence["source_promoted"] is False
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    assert schema["properties"]["credential_value_stored"]["const"] is False
    assert schema["properties"]["status"]["const"] == "OBSERVATION_COMPLETE"


def test_complete_private_synthetic_archive_passes_integrity_but_not_gate(tmp_path: Path) -> None:
    evidence, archive = _fixture(tmp_path)
    result = audit(evidence, archive)
    assert result["final_gate"] == "SOURCE_ACCEPTANCE_PENDING_OPERATIONAL_LATENCY_EVIDENCE"
    assert result["observation_integrity"] == "PASS"
    assert result["availability_by_frozen_deadline"] is True
    assert result["frozen_budget_conflict"] is True
    assert result["readiness_poll_budget"] == 4
    assert result["executed_poll_times"] == 5
    assert result["poll_count"] == result["raw_hash_matches"] == 10
    assert {symbol: value["poll"] for symbol, value in result["first_valid"].items()} == {
        "QQQ": 2, "QLD": 2,
    }
    assert result["publication_time_exactly_known"] is False
    assert result["source_promoted"] is False


@pytest.mark.parametrize("mutation", [
    "missing_raw", "changed_raw", "wrong_mode", "missing_poll", "wrong_schedule",
    "late_resume", "wrong_row_count", "wrong_classification", "scope_violation",
])
def test_integrity_or_boundary_defect_fails_closed(tmp_path: Path, mutation: str) -> None:
    evidence, archive = _fixture(tmp_path)
    if mutation == "missing_raw":
        (archive / evidence["polls"][0]["raw_file"]).unlink()
    elif mutation == "changed_raw":
        (archive / evidence["polls"][2]["raw_file"]).write_bytes(b"[]")
    elif mutation == "wrong_mode":
        (archive / evidence["polls"][0]["raw_file"]).chmod(0o644)
    elif mutation == "missing_poll":
        evidence["polls"].pop()
    elif mutation == "wrong_schedule":
        evidence["schedule_utc"][1] = "2026-10-06T22:00:00Z"
    elif mutation == "late_resume":
        evidence["observer_resumed_at"] = SCHEDULE[0]
    elif mutation == "wrong_row_count":
        evidence["polls"][2]["row_count"] = 2
    elif mutation == "wrong_classification":
        evidence["polls"][2]["classification"] = "SESSION_UNAVAILABLE_OR_INVALID"
    else:
        evidence["source_promoted"] = True
    with pytest.raises(LatencyAuditError):
        audit(evidence, archive)


def test_original_schedule_was_pre_session_and_resume_was_pre_first_poll(tmp_path: Path) -> None:
    evidence, archive = _fixture(tmp_path)
    assert evidence["observer_started_at"] < SESSION_OPEN
    assert evidence["observer_resumed_at"] < SCHEDULE[0]
    assert evidence["interruption_recorded"] is True
    assert audit(evidence, archive)["interruption_recorded"] is True


def test_committed_evidence_has_no_secret_or_auth_header() -> None:
    text = COMMITTED.read_text(encoding="utf-8")
    assert '"credential_value_stored": false' in text
    assert "Authorization" not in text
    assert "Token " not in text
    assert "apiKey=" not in text


def test_conflicting_four_poll_budget_blocks_source_pass() -> None:
    readiness = READINESS.read_text(encoding="utf-8")
    account = json.loads(ACCOUNT.read_text(encoding="utf-8"))
    assert "accepted four-poll budget" in readiness
    assert len(SCHEDULE) == 5
    assert account["publication_latency"]["executed_poll_times"] == 5
    assert account["publication_latency"]["external_adjudication_required"] is True
    assert account["final_gate"] == "SOURCE_ACCEPTANCE_PENDING_OPERATIONAL_LATENCY_EVIDENCE"
