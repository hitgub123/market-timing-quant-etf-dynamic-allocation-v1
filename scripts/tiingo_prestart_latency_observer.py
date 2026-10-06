#!/usr/bin/env python3
"""One-shot, nonofficial Tiingo publication observation; no investment calculations."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import time
import urllib.error
import urllib.parse
import urllib.request


SESSION = "2026-10-06"
SESSION_OPEN = "2026-10-06T13:30:00Z"  # 09:30 America/New_York
SCHEDULE = (
    "2026-10-06T20:00:00Z",  # US equity close, 16:00 ET
    "2026-10-06T21:30:00Z",  # documented usual update, 17:30 ET
    "2026-10-06T22:00:00Z",
    "2026-10-06T23:00:00Z",
    "2026-10-07T00:00:00Z",  # documented correction-window end, 20:00 ET
)
SYMBOLS = ("QQQ", "QLD")
REQUIRED = ("date", "open", "high", "low", "close", "volume", "adjOpen", "adjHigh", "adjLow", "adjClose", "adjVolume", "divCash", "splitFactor")
ARCHIVE = Path.home() / ".local/share/market-timing-quant/tiingo-prestart-latency" / SESSION


def now() -> datetime:
    return datetime.now(timezone.utc)


def stamp() -> str:
    return now().isoformat().replace("+00:00", "Z")


def private_write(path: Path, payload: bytes) -> None:
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "wb") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())


def save_evidence(evidence: dict) -> None:
    path = ARCHIVE / "latency_evidence.json"
    temporary = ARCHIVE / "latency_evidence.tmp"
    data = (json.dumps(evidence, indent=2, sort_keys=True) + "\n").encode()
    with open(temporary, "wb") as handle:
        handle.write(data)
    os.chmod(temporary, 0o600)
    temporary.replace(path)


def main() -> int:
    key = os.environ.get("TIINGO_API_KEY", "")
    print("TIINGO_API_KEY_PRESENT=" + ("TRUE" if key else "FALSE"), flush=True)
    if not key:
        return 3
    start = now()
    session_open = datetime.fromisoformat(SESSION_OPEN.replace("Z", "+00:00"))
    if ARCHIVE.exists():
        evidence_path = ARCHIVE / "latency_evidence.json"
        if not evidence_path.is_file() or list(ARCHIVE.glob("*.raw")):
            print("SAFE_RESUME_ELIGIBLE=FALSE", flush=True)
            return 2
        evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
        original_start = datetime.fromisoformat(evidence.get("observer_started_at", "").replace("Z", "+00:00"))
        if (evidence.get("expected_session") != SESSION
                or evidence.get("session_open_at") != SESSION_OPEN
                or evidence.get("schedule_utc") != list(SCHEDULE)
                or evidence.get("polls") != []
                or original_start >= session_open
                or start >= datetime.fromisoformat(SCHEDULE[0].replace("Z", "+00:00"))):
            print("SAFE_RESUME_ELIGIBLE=FALSE", flush=True)
            return 2
        evidence["observer_resumed_at"] = stamp()
        evidence["interruption_recorded"] = True
        save_evidence(evidence)
        print("SAFE_RESUME_ELIGIBLE=TRUE", flush=True)
    else:
        if start >= session_open:
            print("PRESTART_ELIGIBLE=FALSE", flush=True)
            return 2
        ARCHIVE.mkdir(parents=True, mode=0o700)
        os.chmod(ARCHIVE, 0o700)
        evidence = {
        "artifact": "tiingo_prestart_latency_evidence",
        "fixture_status": "PRE_START_NONOFFICIAL_SOURCE_EVIDENCE",
        "expected_session": SESSION,
        "session_open_at": SESSION_OPEN,
        "symbols": list(SYMBOLS),
        "schedule_utc": list(SCHEDULE),
        "observer_started_at": stamp(),
        "credential_present": True,
        "credential_value_stored": False,
        "raw_archive_outside_repository": True,
        "performance_calculated": False,
        "official_observation_created": False,
        "source_promoted": False,
        "polls": [],
        "status": "IN_PROGRESS",
        }
        save_evidence(evidence)
        print("PRESTART_ELIGIBLE=TRUE", flush=True)
    for index, scheduled in enumerate(SCHEDULE, 1):
        due = datetime.fromisoformat(scheduled.replace("Z", "+00:00"))
        while now() < due:
            time.sleep(min((due - now()).total_seconds(), 30))
        for symbol in SYMBOLS:
            params = urllib.parse.urlencode({"startDate": SESSION, "endDate": SESSION, "resampleFreq": "daily"})
            url = f"https://api.tiingo.com/tiingo/daily/{symbol}/prices?{params}"
            request = urllib.request.Request(url, headers={"Authorization": f"Token {key}", "Accept": "application/json"})
            requested_at = stamp()
            try:
                with urllib.request.urlopen(request, timeout=30) as response:
                    status, body = response.status, response.read()
                    content_type = response.headers.get("content-type", "")
            except urllib.error.HTTPError as exc:
                status, body, content_type = exc.code, exc.read(), exc.headers.get("content-type", "")
            except Exception as exc:
                evidence["polls"].append({"poll": index, "symbol": symbol, "scheduled_at": scheduled, "requested_at": requested_at, "classification": "TRANSPORT_ERROR", "error_class": type(exc).__name__})
                save_evidence(evidence)
                continue
            raw_name = f"poll_{index:02d}_{symbol}.raw"
            private_write(ARCHIVE / raw_name, body)
            try:
                parsed = json.loads(body)
                matching = [row for row in parsed if isinstance(row, dict) and str(row.get("date", ""))[:10] == SESSION] if isinstance(parsed, list) else []
                valid = len(matching) == 1 and all(matching[0].get(field) is not None for field in REQUIRED)
                classification = "VALID_SESSION" if valid else "SESSION_UNAVAILABLE_OR_INVALID"
                row_count = len(parsed) if isinstance(parsed, list) else None
            except (UnicodeError, ValueError, TypeError):
                classification, row_count = "INVALID_JSON", None
            evidence["polls"].append({"poll": index, "symbol": symbol, "scheduled_at": scheduled, "requested_at": requested_at, "received_at": stamp(), "http_status": status, "content_type": content_type, "raw_file": raw_name, "raw_bytes": len(body), "raw_sha256": hashlib.sha256(body).hexdigest(), "raw_reconstruction": (ARCHIVE / raw_name).read_bytes() == body, "row_count": row_count, "classification": classification})
            save_evidence(evidence)
            print(f"POLL={index} SYMBOL={symbol} STATUS={status} CLASS={classification}", flush=True)
    evidence["status"] = "OBSERVATION_COMPLETE"
    evidence["completed_at"] = stamp()
    save_evidence(evidence)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
