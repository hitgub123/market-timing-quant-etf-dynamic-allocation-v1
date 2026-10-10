#!/usr/bin/env python3
"""Single-poll Tiingo PRE_START re-observation (V4, cron-triggered).

Frozen contract: docs/PAPER_TRADING_TIINGO_PRESTART_REOBSERVATION_PLAN_V4_FROZEN.md
Performance-blind: no MA200, signal, return, or source-ranking computation.

Each run executes exactly ONE poll (POLL_INDEX=1 or 2, from the environment),
then exits. No long sleep: the runtime cron fires at the scheduled time, so a
VM replacement between polls cannot kill the observation (the failure mode that
compromised V2 and V3).

TLS 1.2 is forced: on 2026-10-10 it was diagnosed that the default TLS 1.3
handshake to api.tiingo.com hangs indefinitely on this egress path (proxy
CONNECT succeeds, then no Server Hello), while TLS 1.2 returns HTTP 200 in
<1s for an authenticated request. Verified 2026-10-10 ~12:3x JST.
"""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request


SESSION = "2026-10-12"
SESSION_OPEN = "2026-10-12T13:30:00Z"  # 09:30 America/New_York (EDT, UTC-4, verified)
SCHEDULE = (
    "2026-10-12T21:30:00Z",  # documented usual update, 17:30 ET (= 10-13 06:30 JST)
    "2026-10-13T00:00:00Z",  # documented correction-window end, 20:00 ET (= 10-13 09:00 JST)
)
SYMBOLS = ("QQQ", "QLD")
TOTAL_REQUEST_BUDGET = 4  # strictest reading: total across both polls, not per poll/symbol
REQUIRED = ("date", "open", "high", "low", "close", "volume", "adjOpen", "adjHigh", "adjLow", "adjClose", "adjVolume", "divCash", "splitFactor")
HEADER_ALLOWLIST = ("date", "content-type",
                    "x-ratelimit-limit", "x-ratelimit-remaining", "x-ratelimit-reset",
                    "ratelimit-limit", "ratelimit-remaining", "ratelimit-reset")
ARCHIVE = Path.home() / ".local/share/market-timing-quant/tiingo-prestart-latency" / SESSION
EVIDENCE_PATH = ARCHIVE / "latency_evidence.json"
MAX_LATE_SECONDS = 300


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
    temporary = ARCHIVE / "latency_evidence.tmp"
    data = (json.dumps(evidence, indent=2, sort_keys=True) + "\n").encode()
    with open(temporary, "wb") as handle:
        handle.write(data)
    os.chmod(temporary, 0o600)
    temporary.replace(EVIDENCE_PATH)


def safe_headers_of(headers) -> dict:
    return {name: headers.get(name) for name in HEADER_ALLOWLIST}


def blank_headers() -> dict:
    return {name: None for name in HEADER_ALLOWLIST}


def tls12_context() -> ssl.SSLContext:
    """Force TLS 1.2: TLS 1.3 handshake to api.tiingo.com hangs on this egress path."""
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    context.maximum_version = ssl.TLSVersion.TLSv1_2
    context.load_default_certs()
    return context


def mark_compromised(evidence: dict, reason: str) -> None:
    evidence["status"] = "OBSERVATION_COMPROMISED"
    evidence["completed_at"] = stamp()
    evidence["compromise_reason"] = reason
    save_evidence(evidence)


def do_poll(evidence: dict, poll_index: int, scheduled: str, key: str, context: ssl.SSLContext) -> None:
    for symbol in SYMBOLS:
        params = urllib.parse.urlencode({"startDate": SESSION, "endDate": SESSION, "resampleFreq": "daily"})
        url = f"https://api.tiingo.com/tiingo/daily/{symbol}/prices?{params}"
        request = urllib.request.Request(url, headers={"Authorization": f"Token {key}", "Accept": "application/json"})
        requested_at = stamp()
        try:
            with urllib.request.urlopen(request, timeout=30, context=context) as response:
                status, body = response.status, response.read()
                headers = safe_headers_of(response.headers)
                content_type = response.headers.get("content-type", "")
        except urllib.error.HTTPError as exc:
            status, body = exc.code, exc.read()
            headers = safe_headers_of(exc.headers)
            content_type = exc.headers.get("content-type", "")
        except Exception as exc:
            evidence["polls"].append({"poll": poll_index, "symbol": symbol, "scheduled_at": scheduled, "requested_at": requested_at, "classification": "TRANSPORT_ERROR", "error_class": type(exc).__name__, "safe_headers": blank_headers(), "returned_last_date": None})
            save_evidence(evidence)
            print(f"POLL={poll_index} SYMBOL={symbol} CLASS=TRANSPORT_ERROR", flush=True)
            continue
        raw_name = f"poll_{poll_index:02d}_{symbol}.raw"
        private_write(ARCHIVE / raw_name, body)
        try:
            parsed = json.loads(body)
            rows = [row for row in parsed if isinstance(row, dict)] if isinstance(parsed, list) else []
            matching = [row for row in rows if str(row.get("date", ""))[:10] == SESSION]
            valid = len(matching) == 1 and all(matching[0].get(field) is not None for field in REQUIRED)
            classification = "VALID_SESSION" if valid else "SESSION_UNAVAILABLE_OR_INVALID"
            row_count: int | None = len(parsed) if isinstance(parsed, list) else None
            last_date = max((str(row.get("date", ""))[:10] for row in rows), default=None) or None
        except (UnicodeError, ValueError, TypeError):
            classification, row_count, last_date = "INVALID_JSON", None, None
        evidence["polls"].append({"poll": poll_index, "symbol": symbol, "scheduled_at": scheduled, "requested_at": requested_at, "received_at": stamp(), "http_status": status, "content_type": content_type, "safe_headers": headers, "returned_last_date": last_date, "raw_file": raw_name, "raw_bytes": len(body), "raw_sha256": hashlib.sha256(body).hexdigest(), "raw_reconstruction": (ARCHIVE / raw_name).read_bytes() == body, "row_count": row_count, "classification": classification})
        save_evidence(evidence)
        print(f"POLL={poll_index} SYMBOL={symbol} STATUS={status} CLASS={classification}", flush=True)


def main() -> int:
    key = os.environ.get("TIINGO_API_KEY", "")
    print("TIINGO_API_KEY_PRESENT=" + ("TRUE" if key else "FALSE"), flush=True)
    if not key:
        return 3
    try:
        poll_index = int(os.environ.get("POLL_INDEX", ""))
    except ValueError:
        print("POLL_INDEX_INVALID", flush=True)
        return 2
    if poll_index not in (1, 2):
        print("POLL_INDEX_INVALID", flush=True)
        return 2
    assert len(SCHEDULE) * len(SYMBOLS) == TOTAL_REQUEST_BUDGET, "schedule exceeds frozen request budget"
    scheduled = SCHEDULE[poll_index - 1]
    due = datetime.fromisoformat(scheduled.replace("Z", "+00:00"))
    session_open = datetime.fromisoformat(SESSION_OPEN.replace("Z", "+00:00"))
    start = now()
    context = tls12_context()

    if poll_index == 1:
        if ARCHIVE.exists():
            print("POLL1_ARCHIVE_EXISTS=REFUSE", flush=True)
            return 2
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
            "total_request_budget": TOTAL_REQUEST_BUDGET,
            "observer_started_at": stamp(),
            "observer_resumed_at": None,
            "interruption_recorded": False,
            "credential_present": True,
            "credential_value_stored": False,
            "raw_archive_outside_repository": True,
            "performance_calculated": False,
            "official_observation_created": False,
            "source_promoted": False,
            "runner": "cron-single-poll",
            "polls": [],
            "status": "IN_PROGRESS",
        }
        save_evidence(evidence)
        print("PRESTART_ELIGIBLE=TRUE", flush=True)
    else:
        if not EVIDENCE_PATH.is_file():
            print("POLL2_PRECONDITION=FALSE (no evidence)", flush=True)
            return 2
        evidence = json.loads(EVIDENCE_PATH.read_text(encoding="utf-8"))
        prior = evidence.get("polls", [])
        if (evidence.get("expected_session") != SESSION
                or evidence.get("session_open_at") != SESSION_OPEN
                or evidence.get("schedule_utc") != list(SCHEDULE)
                or evidence.get("status") != "IN_PROGRESS"
                or len(prior) != len(SYMBOLS)
                or any(p.get("poll") != 1 for p in prior)
                or list(ARCHIVE.glob("poll_01_*.raw")) == []):
            evidence["status"] = "OBSERVATION_COMPROMISED"
            evidence["completed_at"] = stamp()
            evidence["compromise_reason"] = "poll2-precondition-failed"
            save_evidence(evidence)
            print("POLL2_PRECONDITION=FALSE CLASS=OBSERVATION_COMPROMISED", flush=True)
            return 4

    while now() < due:
        time.sleep(min((due - now()).total_seconds(), 10))
    late_by = (now() - due).total_seconds()
    if late_by > MAX_LATE_SECONDS:
        mark_compromised(evidence, f"late-poll-{poll_index}")
        print(f"LATE_POLL={poll_index} LATE_BY_S={late_by:.0f} CLASS=OBSERVATION_COMPROMISED", flush=True)
        return 4

    do_poll(evidence, poll_index, scheduled, key, context)

    if poll_index == 2:
        evidence["status"] = "OBSERVATION_COMPLETE"
        evidence["completed_at"] = stamp()
        save_evidence(evidence)
    print(f"POLL={poll_index} DONE", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
