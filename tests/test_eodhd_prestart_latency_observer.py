"""Deterministic controls for the nonofficial EODHD latency observer."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
import json
import os
from pathlib import Path
import subprocess
from zoneinfo import ZoneInfo

import pytest

from scripts.eodhd_prestart_latency_observer import (
    FetchResult,
    ObserverConfig,
    POLL_OFFSETS_SECONDS,
    run_observation,
)


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/eodhd_prestart_latency_observer.py"
SCHEMA = ROOT / "schemas/source_acceptance/eodhd_prestart_latency_evidence.schema.json"
RUNBOOK = ROOT / "docs/PAPER_TRADING_EODHD_PRESTART_LATENCY_RUNBOOK.md"
SESSION = date(2026, 9, 28)
CLOSE = datetime(2026, 9, 28, 20, 0, tzinfo=timezone.utc)


class MutableClock:
    def __init__(self, value: datetime):
        self.value = value

    def now(self) -> datetime:
        return self.value

    def sleep(self, seconds: float) -> None:
        self.value += timedelta(seconds=seconds)


def valid_row(session: date = SESSION) -> dict[str, object]:
    return {
        "date": session.isoformat(),
        "open": 600.0,
        "high": 605.0,
        "low": 598.0,
        "close": 603.0,
        "adjusted_close": 602.5,
        "volume": 123456,
    }


def result(rows: object, status: int = 200) -> FetchResult:
    return FetchResult(
        status,
        {
            "Content-Type": "application/json",
            "X-RateLimit-Limit": "1200",
            "X-RateLimit-Remaining": "1199",
            "Authorization": "must-not-survive",
        },
        json.dumps(rows, separators=(",", ":")).encode(),
    )


def config(tmp_path: Path, name: str = "evidence") -> ObserverConfig:
    return ObserverConfig(SESSION, CLOSE, tmp_path / name)


def run_with_sequence(tmp_path: Path, sequence: list[FetchResult]) -> tuple[dict, MutableClock]:
    clock = MutableClock(CLOSE - timedelta(minutes=5))
    calls = iter(sequence)
    evidence = run_observation(
        config(tmp_path),
        lambda _session: next(calls),
        clock=clock.now,
        sleeper=clock.sleep,
    )
    return evidence, clock


def test_poll_schedule_and_japan_conversion_are_exact() -> None:
    assert POLL_OFFSETS_SECONDS == (0, 300, 600, 900)
    assert CLOSE.astimezone(ZoneInfo("Asia/Tokyo")) == datetime(
        2026, 9, 29, 5, 0, tzinfo=ZoneInfo("Asia/Tokyo")
    )


@pytest.mark.parametrize("available_poll,expected_latency", [(1, 0), (2, 300), (3, 600), (4, 900)])
def test_valid_session_passes_at_each_frozen_poll(
    tmp_path: Path, available_poll: int, expected_latency: int
) -> None:
    sequence = [result([]) for _ in range(available_poll - 1)] + [result([valid_row()])]
    evidence, _clock = run_with_sequence(tmp_path, sequence)
    assert evidence["final_status"] == "PASS_WITHIN_DOCUMENTED_WINDOW"
    assert evidence["latency_seconds"] == expected_latency
    assert len(evidence["polls"]) == available_poll
    assert evidence["polls"][-1]["returned_last_date"] == SESSION.isoformat()


def test_no_session_by_fourth_poll_fails_closed(tmp_path: Path) -> None:
    evidence, _clock = run_with_sequence(tmp_path, [result([]) for _ in range(4)])
    assert evidence["final_status"] == "FAIL_NOT_AVAILABLE_BY_DOCUMENTED_DEADLINE"
    assert evidence["first_available_at"] is None
    assert evidence["latency_seconds"] is None
    assert len(evidence["polls"]) == 4


def test_wrong_session_never_becomes_available(tmp_path: Path) -> None:
    wrong = valid_row(date(2026, 9, 25))
    evidence, _clock = run_with_sequence(tmp_path, [result([wrong]) for _ in range(4)])
    assert evidence["final_status"] == "FAIL_NOT_AVAILABLE_BY_DOCUMENTED_DEADLINE"
    assert {poll["body_classification"] for poll in evidence["polls"]} == {
        "EXPECTED_SESSION_NOT_AVAILABLE"
    }


def test_duplicate_expected_session_fails_closed(tmp_path: Path) -> None:
    duplicate = [valid_row(), valid_row()]
    evidence, _clock = run_with_sequence(tmp_path, [result(duplicate) for _ in range(4)])
    assert evidence["final_status"] == "FAIL_NOT_AVAILABLE_BY_DOCUMENTED_DEADLINE"
    assert {poll["body_classification"] for poll in evidence["polls"]} == {
        "DUPLICATE_EXPECTED_SESSION"
    }


@pytest.mark.parametrize(
    "mutation,classification",
    [
        ({"adjusted_close": None}, "MISSING_REQUIRED_FIELD"),
        ({"close": "not-a-number"}, "NON_NUMERIC_REQUIRED_FIELD"),
        ({"open": -1}, "INVALID_REQUIRED_VALUE"),
        ({"high": 590}, "INVALID_OHLC_RANGE"),
    ],
)
def test_invalid_required_data_fails_closed(
    tmp_path: Path, mutation: dict[str, object], classification: str
) -> None:
    row = valid_row()
    row.update(mutation)
    evidence, _clock = run_with_sequence(tmp_path, [result([row]) for _ in range(4)])
    assert evidence["final_status"] == "FAIL_NOT_AVAILABLE_BY_DOCUMENTED_DEADLINE"
    assert {poll["body_classification"] for poll in evidence["polls"]} == {classification}


def test_invalid_json_and_request_errors_are_sanitized(tmp_path: Path) -> None:
    clock = MutableClock(CLOSE - timedelta(minutes=5))
    calls = 0

    def fetcher(_session: date) -> FetchResult:
        nonlocal calls
        calls += 1
        if calls == 1:
            return FetchResult(200, {}, b"not-json")
        raise TimeoutError("message may contain operational detail")

    evidence = run_observation(config(tmp_path), fetcher, clock=clock.now, sleeper=clock.sleep)
    assert evidence["polls"][0]["body_classification"] == "INVALID_JSON"
    for poll in evidence["polls"][1:]:
        assert poll["body_classification"] == "SANITIZED_REQUEST_ERROR"
        assert poll["error_type"] == "TimeoutError"
        assert "message" not in poll


def test_raw_bytes_are_archived_before_parse_with_safe_permissions(tmp_path: Path) -> None:
    evidence, _clock = run_with_sequence(tmp_path, [result([valid_row()])])
    archive = tmp_path / "evidence"
    raw_path = archive / evidence["polls"][0]["raw_filename"]
    saved = json.loads((archive / "latency_evidence.json").read_text(encoding="utf-8"))
    assert raw_path.read_bytes() == json.dumps([valid_row()], separators=(",", ":")).encode()
    assert evidence == saved
    assert oct(archive.stat().st_mode & 0o777) == "0o700"
    assert oct(raw_path.stat().st_mode & 0o777) == "0o600"
    assert oct((archive / "latency_evidence.json").stat().st_mode & 0o777) == "0o600"
    assert "Authorization" not in evidence["polls"][0]["safe_headers"]


def test_existing_archive_is_never_overwritten(tmp_path: Path) -> None:
    target = tmp_path / "existing"
    target.mkdir()
    clock = MutableClock(CLOSE - timedelta(minutes=5))
    with pytest.raises(FileExistsError):
        run_observation(config(tmp_path, "existing"), lambda _session: result([]), clock=clock.now, sleeper=clock.sleep)


def test_late_start_refuses_before_creating_archive_or_request(tmp_path: Path) -> None:
    clock = MutableClock(CLOSE + timedelta(seconds=61))
    called = False

    def fetcher(_session: date) -> FetchResult:
        nonlocal called
        called = True
        return result([valid_row()])

    with pytest.raises(RuntimeError, match="START_TOO_LATE"):
        run_observation(config(tmp_path), fetcher, clock=clock.now, sleeper=clock.sleep)
    assert called is False
    assert not (tmp_path / "evidence").exists()


def test_poll_schedule_cannot_be_changed(tmp_path: Path) -> None:
    clock = MutableClock(CLOSE - timedelta(minutes=5))
    changed = ObserverConfig(SESSION, CLOSE, tmp_path / "changed", (0, 60, 120, 180))
    with pytest.raises(ValueError, match="poll schedule is frozen"):
        run_observation(changed, lambda _session: result([]), clock=clock.now, sleeper=clock.sleep)


def test_scope_controls_prohibit_strategy_or_official_use(tmp_path: Path) -> None:
    evidence, _clock = run_with_sequence(tmp_path, [result([valid_row()])])
    assert evidence["fixture_status"] == "PRE_START_NONOFFICIAL_SOURCE_EVIDENCE"
    assert evidence["scope_controls"] == {
        "moving_average_calculated": False,
        "signal_calculated": False,
        "performance_calculated": False,
        "official_observation_created": False,
        "engine_or_scheduler_started": False,
    }


def test_schema_and_runbook_freeze_required_contract() -> None:
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    assert schema["properties"]["poll_offsets_seconds"]["const"] == [0, 300, 600, 900]
    assert schema["properties"]["max_poll_count"]["const"] == 4
    assert schema["properties"]["fixture_status"]["const"] == "PRE_START_NONOFFICIAL_SOURCE_EVIDENCE"
    assert schema["properties"]["credential_value_stored"]["const"] is False
    assert schema["properties"]["polls"]["maxItems"] == 4
    runbook = RUNBOOK.read_text(encoding="utf-8")
    assert "2026-10-02 05:00:00 JST" in runbook
    assert "05:00`, `05:05`, `05:10`, `05:15" in runbook
    assert "It does not" in runbook and "calculate MA200" in runbook


def test_validate_only_makes_no_archive_and_prints_no_value(tmp_path: Path) -> None:
    target = tmp_path / "validate-only"
    environment = dict(os.environ)
    environment["EODHD_API_KEY"] = "synthetic-test-value"
    completed = subprocess.run(
        [
            "python3",
            str(SCRIPT),
            "--expected-session",
            SESSION.isoformat(),
            "--exchange-close-at",
            CLOSE.isoformat(),
            "--archive-dir",
            str(target),
            "--validate-only",
        ],
        cwd=ROOT,
        env=environment,
        check=True,
        capture_output=True,
        text=True,
    )
    assert "EODHD_API_KEY_PRESENT=TRUE" in completed.stdout
    assert "VALIDATION_ONLY=PASS" in completed.stdout
    assert "synthetic-test-value" not in completed.stdout
    assert not target.exists()


def test_cli_rejects_repository_archive_path_without_request() -> None:
    environment = dict(os.environ)
    environment["EODHD_API_KEY"] = "synthetic-test-value"
    completed = subprocess.run(
        [
            "python3",
            str(SCRIPT),
            "--expected-session",
            SESSION.isoformat(),
            "--exchange-close-at",
            CLOSE.isoformat(),
            "--archive-dir",
            str(ROOT / "forbidden-evidence"),
            "--validate-only",
        ],
        cwd=ROOT,
        env=environment,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 2
    assert "ARCHIVE_LOCATION_VALID=FALSE" in completed.stdout
    assert "synthetic-test-value" not in completed.stdout
    assert not (ROOT / "forbidden-evidence").exists()
