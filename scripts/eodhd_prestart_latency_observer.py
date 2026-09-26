#!/usr/bin/env python3
"""One-shot, manually triggered EODHD PRE_START publication observer.

This tool collects source-operability evidence only. It never calculates a
moving average, signal, return, order, fill, or official paper observation.
Raw response bytes are required to live outside the repository.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import tempfile
import time
from typing import Callable, Mapping, Sequence
import urllib.error
import urllib.parse
import urllib.request


POLL_OFFSETS_SECONDS = (0, 300, 600, 900)
REQUIRED_FIELDS = ("date", "open", "high", "low", "close", "adjusted_close", "volume")
SAFE_HEADER_NAMES = {"content-type", "date", "x-ratelimit-limit", "x-ratelimit-remaining", "retry-after"}
EVIDENCE_SCHEMA_VERSION = "1.0"


@dataclass(frozen=True)
class ObserverConfig:
    expected_session: date
    exchange_close_at: datetime
    archive_dir: Path
    poll_offsets_seconds: tuple[int, ...] = POLL_OFFSETS_SECONDS
    max_start_lateness_seconds: int = 60
    ticker: str = "QQQ.US"


@dataclass(frozen=True)
class FetchResult:
    http_status: int
    headers: Mapping[str, str]
    body: bytes


Clock = Callable[[], datetime]
Sleeper = Callable[[float], None]
Fetcher = Callable[[date], FetchResult]


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(value: datetime) -> str:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timestamps must be timezone-aware")
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _safe_headers(headers: Mapping[str, str]) -> dict[str, str]:
    return {key: value for key, value in headers.items() if key.lower() in SAFE_HEADER_NAMES}


def _atomic_json(path: Path, payload: Mapping[str, object]) -> None:
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")
        temporary = Path(handle.name)
    os.chmod(temporary, 0o600)
    temporary.replace(path)


def _wait_until(target: datetime, clock: Clock, sleeper: Sleeper) -> None:
    while True:
        remaining = (target - clock()).total_seconds()
        if remaining <= 0:
            return
        sleeper(min(remaining, 30.0))


def _validate_row(row: object, expected_session: date) -> tuple[bool, str]:
    if not isinstance(row, dict):
        return False, "ROW_NOT_OBJECT"
    if row.get("date") != expected_session.isoformat():
        return False, "WRONG_SESSION"
    if any(row.get(field) is None for field in REQUIRED_FIELDS):
        return False, "MISSING_REQUIRED_FIELD"
    try:
        prices = [float(row[field]) for field in ("open", "high", "low", "close", "adjusted_close")]
        volume = float(row["volume"])
    except (TypeError, ValueError):
        return False, "NON_NUMERIC_REQUIRED_FIELD"
    if any(value <= 0 for value in prices) or volume < 0:
        return False, "INVALID_REQUIRED_VALUE"
    if float(row["high"]) < max(float(row["open"]), float(row["low"]), float(row["close"])):
        return False, "INVALID_OHLC_RANGE"
    if float(row["low"]) > min(float(row["open"]), float(row["high"]), float(row["close"])):
        return False, "INVALID_OHLC_RANGE"
    return True, "VALID_COMPLETED_SESSION"


def _classify_body(body: bytes, expected_session: date) -> tuple[str, str | None, int]:
    try:
        payload = json.loads(body)
    except (UnicodeDecodeError, json.JSONDecodeError):
        return "INVALID_JSON", None, 0
    if not isinstance(payload, list):
        return "UNEXPECTED_RESPONSE_SHAPE", None, 0
    rows = [row for row in payload if isinstance(row, dict)]
    dates = [str(row["date"]) for row in rows if row.get("date") is not None]
    last_date = max(dates) if dates else None
    matches = [row for row in rows if row.get("date") == expected_session.isoformat()]
    if len(matches) > 1:
        return "DUPLICATE_EXPECTED_SESSION", last_date, len(rows)
    if not matches:
        return "EXPECTED_SESSION_NOT_AVAILABLE", last_date, len(rows)
    valid, classification = _validate_row(matches[0], expected_session)
    return classification if valid else classification, last_date, len(rows)


def run_observation(
    config: ObserverConfig,
    fetcher: Fetcher,
    *,
    clock: Clock = utc_now,
    sleeper: Sleeper = time.sleep,
) -> dict[str, object]:
    if config.exchange_close_at.tzinfo is None or config.exchange_close_at.utcoffset() is None:
        raise ValueError("exchange_close_at must be timezone-aware")
    if config.poll_offsets_seconds != POLL_OFFSETS_SECONDS:
        raise ValueError("poll schedule is frozen at 0, 5, 10, and 15 minutes")
    if config.archive_dir.exists():
        raise FileExistsError(f"archive directory already exists: {config.archive_dir}")

    start = clock().astimezone(timezone.utc)
    close = config.exchange_close_at.astimezone(timezone.utc)
    lateness = (start - close).total_seconds()
    if lateness > config.max_start_lateness_seconds:
        raise RuntimeError("START_TOO_LATE_FOR_LATENCY_EVIDENCE")

    config.archive_dir.mkdir(parents=True, mode=0o700)
    os.chmod(config.archive_dir, 0o700)
    deadline = close + timedelta(seconds=config.poll_offsets_seconds[-1])
    evidence: dict[str, object] = {
        "artifact": "eodhd_prestart_latency_evidence",
        "schema_version": EVIDENCE_SCHEMA_VERSION,
        "fixture_status": "PRE_START_NONOFFICIAL_SOURCE_EVIDENCE",
        "expected_session": config.expected_session.isoformat(),
        "ticker": config.ticker,
        "exchange_close_at": _iso(close),
        "documented_deadline_at": _iso(deadline),
        "observer_started_at": _iso(start),
        "poll_offsets_seconds": list(config.poll_offsets_seconds),
        "max_poll_count": len(config.poll_offsets_seconds),
        "credential_present": True,
        "credential_value_stored": False,
        "sanitized_request": {
            "method": "GET",
            "endpoint_path": f"/api/eod/{config.ticker}",
            "parameters": {
                "from": config.expected_session.isoformat(),
                "to": config.expected_session.isoformat(),
                "fmt": "json",
            },
        },
        "scope_controls": {
            "moving_average_calculated": False,
            "signal_calculated": False,
            "performance_calculated": False,
            "official_observation_created": False,
            "engine_or_scheduler_started": False,
        },
        "polls": [],
        "first_available_at": None,
        "latency_seconds": None,
        "final_status": "IN_PROGRESS",
    }
    evidence_path = config.archive_dir / "latency_evidence.json"
    _atomic_json(evidence_path, evidence)

    for ordinal, offset in enumerate(config.poll_offsets_seconds, start=1):
        target = close + timedelta(seconds=offset)
        _wait_until(target, clock, sleeper)
        request_started = clock().astimezone(timezone.utc)
        try:
            result = fetcher(config.expected_session)
            response_received = clock().astimezone(timezone.utc)
            raw_path = config.archive_dir / f"poll_{ordinal:02d}.raw"
            raw_path.write_bytes(result.body)
            os.chmod(raw_path, 0o600)
            reconstructed = raw_path.read_bytes()
            body_classification, returned_last_date, returned_row_count = _classify_body(
                reconstructed, config.expected_session
            )
            poll = {
                "ordinal": ordinal,
                "scheduled_at": _iso(target),
                "request_started_at": _iso(request_started),
                "response_received_at": _iso(response_received),
                "http_status": result.http_status,
                "safe_headers": _safe_headers(result.headers),
                "raw_filename": raw_path.name,
                "raw_byte_length": len(result.body),
                "raw_sha256": hashlib.sha256(result.body).hexdigest(),
                "raw_archive_reconstruction": "PASS" if reconstructed == result.body else "FAIL",
                "returned_last_date": returned_last_date,
                "returned_row_count": returned_row_count,
                "body_classification": body_classification,
            }
        except Exception as exc:  # evidence must retain a sanitized failure record
            response_received = clock().astimezone(timezone.utc)
            poll = {
                "ordinal": ordinal,
                "scheduled_at": _iso(target),
                "request_started_at": _iso(request_started),
                "response_received_at": _iso(response_received),
                "http_status": None,
                "safe_headers": {},
                "raw_filename": None,
                "raw_byte_length": 0,
                "raw_sha256": None,
                "raw_archive_reconstruction": "NOT_AVAILABLE",
                "returned_last_date": None,
                "returned_row_count": 0,
                "body_classification": "SANITIZED_REQUEST_ERROR",
                "error_type": type(exc).__name__,
            }
        evidence["polls"].append(poll)
        if (
            poll["body_classification"] == "VALID_COMPLETED_SESSION"
            and poll["http_status"] == 200
            and poll["raw_archive_reconstruction"] == "PASS"
        ):
            evidence["first_available_at"] = poll["response_received_at"]
            evidence["latency_seconds"] = (
                response_received - close
            ).total_seconds()
            evidence["final_status"] = (
                "PASS_WITHIN_DOCUMENTED_WINDOW"
                if request_started <= deadline
                else "FAIL_AVAILABLE_AFTER_DOCUMENTED_WINDOW"
            )
            _atomic_json(evidence_path, evidence)
            return evidence
        _atomic_json(evidence_path, evidence)

    evidence["final_status"] = "FAIL_NOT_AVAILABLE_BY_DOCUMENTED_DEADLINE"
    _atomic_json(evidence_path, evidence)
    return evidence


def build_fetcher(api_key: str, ticker: str) -> Fetcher:
    def fetch(expected_session: date) -> FetchResult:
        parameters = {
            "from": expected_session.isoformat(),
            "to": expected_session.isoformat(),
            "fmt": "json",
            "api_token": api_key,
        }
        url = f"https://eodhd.com/api/eod/{ticker}?{urllib.parse.urlencode(parameters)}"
        request = urllib.request.Request(url, headers={"User-Agent": "market-timing-prestart-latency/1.0"})
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return FetchResult(response.status, dict(response.headers), response.read())
        except urllib.error.HTTPError as exc:
            return FetchResult(exc.code, dict(exc.headers), exc.read())

    return fetch


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--expected-session", required=True, type=date.fromisoformat)
    parser.add_argument("--exchange-close-at", required=True, type=datetime.fromisoformat)
    parser.add_argument("--archive-dir", type=Path)
    parser.add_argument("--validate-only", action="store_true")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    api_key = os.environ.get("EODHD_API_KEY")
    print("EODHD_API_KEY_PRESENT=" + ("TRUE" if api_key else "FALSE"))
    if not api_key:
        return 2
    archive_dir = args.archive_dir or (
        Path.home() / ".local/share/market-timing-quant/prestart-latency" / args.expected_session.isoformat()
    )
    repository = Path(__file__).resolve().parents[1]
    resolved_archive = archive_dir.expanduser().resolve()
    if resolved_archive == repository or repository in resolved_archive.parents:
        print("ARCHIVE_LOCATION_VALID=FALSE")
        return 2
    config = ObserverConfig(
        expected_session=args.expected_session,
        exchange_close_at=args.exchange_close_at,
        archive_dir=resolved_archive,
    )
    print("ARCHIVE_LOCATION_VALID=TRUE")
    print("EXPECTED_SESSION=" + config.expected_session.isoformat())
    print("EXCHANGE_CLOSE_AT=" + _iso(config.exchange_close_at))
    print("POLL_COUNT_MAX=4")
    if args.validate_only:
        print("VALIDATION_ONLY=PASS")
        return 0
    try:
        evidence = run_observation(config, build_fetcher(api_key, config.ticker))
    except (FileExistsError, RuntimeError, ValueError) as exc:
        print("OBSERVER_START=FAIL")
        print("ERROR_CLASSIFICATION=" + str(exc))
        return 3
    print("FINAL_STATUS=" + str(evidence["final_status"]))
    print("POLL_COUNT=" + str(len(evidence["polls"])))
    print("EVIDENCE_PATH=" + str(resolved_archive / "latency_evidence.json"))
    return 0 if evidence["final_status"] == "PASS_WITHIN_DOCUMENTED_WINDOW" else 4


if __name__ == "__main__":
    raise SystemExit(main())
