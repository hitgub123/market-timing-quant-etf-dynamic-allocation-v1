"""Offline audit of the frozen, nonofficial Tiingo publication observation."""

from __future__ import annotations

from datetime import datetime
import hashlib
import json
from pathlib import Path
import stat
from typing import Any, Mapping

from scripts.tiingo_prestart_latency_observer import REQUIRED, SCHEDULE, SESSION, SESSION_OPEN, SYMBOLS


class LatencyAuditError(ValueError):
    """The archived observation does not prove the frozen source gate."""


def _at(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _valid_session(body: bytes, expected_session: str) -> bool:
    try:
        rows = json.loads(body)
        if not isinstance(rows, list) or len(rows) != 1:
            return False
        row = rows[0]
        if not isinstance(row, dict) or str(row.get("date", ""))[:10] != expected_session:
            return False
        if any(row.get(field) is None for field in REQUIRED):
            return False
        raw = [float(row[field]) for field in ("open", "high", "low", "close")]
        adj = [float(row[field]) for field in ("adjOpen", "adjHigh", "adjLow", "adjClose")]
        if any(value <= 0 for value in raw + adj):
            return False
        if raw[1] < max(raw[0], raw[2], raw[3]) or raw[2] > min(raw[0], raw[1], raw[3]):
            return False
        if adj[1] < max(adj[0], adj[2], adj[3]) or adj[2] > min(adj[0], adj[1], adj[3]):
            return False
        if float(row["volume"]) < 0 or float(row["adjVolume"]) < 0:
            return False
        if float(row["splitFactor"]) <= 0 or float(row["divCash"]) < 0:
            return False
        return True
    except (UnicodeError, ValueError, TypeError, KeyError):
        return False


def audit(evidence: Mapping[str, Any], archive: Path) -> dict[str, Any]:
    """Require every frozen poll and every exact private raw response."""
    if evidence.get("artifact") != "tiingo_prestart_latency_evidence":
        raise LatencyAuditError("WRONG_ARTIFACT")
    if evidence.get("status") != "OBSERVATION_COMPLETE":
        raise LatencyAuditError("INCOMPLETE_OBSERVATION")
    if evidence.get("expected_session") != SESSION or evidence.get("symbols") != list(SYMBOLS):
        raise LatencyAuditError("FROZEN_TARGET_MISMATCH")
    if evidence.get("session_open_at") != SESSION_OPEN or evidence.get("schedule_utc") != list(SCHEDULE):
        raise LatencyAuditError("FROZEN_SCHEDULE_MISMATCH")
    if (_at(evidence["observer_started_at"]) >= _at(SESSION_OPEN)
            or _at(evidence["observer_resumed_at"]) >= _at(SCHEDULE[0])
            or evidence.get("interruption_recorded") is not True):
        raise LatencyAuditError("PRESTART_OR_RESUME_BOUNDARY_FAIL")
    if (evidence.get("credential_value_stored") is not False
            or evidence.get("performance_calculated") is not False
            or evidence.get("official_observation_created") is not False
            or evidence.get("source_promoted") is not False):
        raise LatencyAuditError("SCOPE_CONTROL_FAIL")
    if not archive.is_dir() or stat.S_IMODE(archive.stat().st_mode) != 0o700:
        raise LatencyAuditError("ARCHIVE_NOT_PRIVATE")
    polls = evidence.get("polls")
    if not isinstance(polls, list) or len(polls) != len(SCHEDULE) * len(SYMBOLS):
        raise LatencyAuditError("POLL_COUNT_MISMATCH")
    if len(list(archive.glob("*.raw"))) != len(polls):
        raise LatencyAuditError("RAW_COUNT_MISMATCH")
    first_valid: dict[str, dict[str, Any]] = {}
    for index, row in enumerate(polls):
        ordinal = index // len(SYMBOLS) + 1
        symbol = SYMBOLS[index % len(SYMBOLS)]
        scheduled = SCHEDULE[ordinal - 1]
        if (row.get("poll") != ordinal or row.get("symbol") != symbol
                or row.get("scheduled_at") != scheduled):
            raise LatencyAuditError("POLL_ORDER_OR_SCHEDULE_MISMATCH")
        requested = _at(row["requested_at"])
        received = _at(row["received_at"])
        if requested < _at(scheduled) or received < requested:
            raise LatencyAuditError("POLL_TIME_INVALID")
        if row.get("http_status") != 200 or row.get("content_type") != "application/json":
            raise LatencyAuditError("HTTP_OR_CONTENT_TYPE_FAIL")
        filename = f"poll_{ordinal:02d}_{symbol}.raw"
        if row.get("raw_file") != filename:
            raise LatencyAuditError("RAW_FILENAME_MISMATCH")
        path = archive / filename
        if not path.is_file() or stat.S_IMODE(path.stat().st_mode) != 0o600:
            raise LatencyAuditError("RAW_FILE_MISSING_OR_NOT_PRIVATE")
        body = path.read_bytes()
        if (len(body) != row.get("raw_bytes")
                or hashlib.sha256(body).hexdigest() != row.get("raw_sha256")
                or row.get("raw_reconstruction") is not True):
            raise LatencyAuditError("RAW_BYTE_RECONSTRUCTION_FAIL")
        try:
            decoded = json.loads(body)
        except (UnicodeError, ValueError):
            raise LatencyAuditError("RAW_JSON_INVALID") from None
        if not isinstance(decoded, list) or len(decoded) != row.get("row_count"):
            raise LatencyAuditError("RAW_ROW_COUNT_MISMATCH")
        valid = _valid_session(body, SESSION)
        if valid != (row.get("classification") == "VALID_SESSION"):
            raise LatencyAuditError("SESSION_CLASSIFICATION_MISMATCH")
        if valid and symbol not in first_valid:
            first_valid[symbol] = {
                "poll": ordinal,
                "observed_at": row["received_at"],
                "scheduled_offset_seconds_after_close": int((_at(scheduled) - _at(SCHEDULE[0])).total_seconds()),
            }
    if set(first_valid) != set(SYMBOLS):
        raise LatencyAuditError("NOT_AVAILABLE_BY_FROZEN_DEADLINE")
    # The older source-readiness document retained a four-poll ceiling when
    # the Tiingo-specific plan later required a pre-session-frozen budget.
    # This observed five-poll run cannot resolve that conflict retroactively.
    return {
        "final_gate": "SOURCE_ACCEPTANCE_PENDING_OPERATIONAL_LATENCY_EVIDENCE",
        "observation_integrity": "PASS",
        "availability_by_frozen_deadline": True,
        "frozen_budget_conflict": len(SCHEDULE) > 4,
        "readiness_poll_budget": 4,
        "executed_poll_times": len(SCHEDULE),
        "expected_session": SESSION,
        "poll_count": len(polls),
        "raw_hash_matches": len(polls),
        "first_valid": first_valid,
        "interruption_recorded": True,
        "publication_time_exactly_known": False,
        "source_promoted": False,
    }
