"""Performance-blind Tiingo Free source-account capability acceptance."""

from __future__ import annotations

import argparse
from datetime import date
import hashlib
import json
import os
from pathlib import Path
import stat
from typing import Callable
import urllib.parse
import urllib.request


API_BASE = "https://api.tiingo.com/tiingo/daily"
SYMBOLS = ("QQQ", "QLD")
REQUIRED_PRICE_FIELDS = (
    "date", "open", "high", "low", "close", "volume",
    "adjOpen", "adjHigh", "adjLow", "adjClose", "adjVolume",
    "divCash", "splitFactor",
)
SAFE_HEADERS = {
    "content-type",
    "date",
    "x-ratelimit-limit",
    "x-ratelimit-remaining",
    "x-ratelimit-reset",
}


class AcceptanceError(RuntimeError):
    """A sanitized capability-acceptance failure."""


def _write_private(path: Path, body: bytes) -> None:
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "wb") as handle:
        handle.write(body)
        handle.flush()
        os.fsync(handle.fileno())


def _inside(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def _safe_headers(headers: dict[str, str]) -> dict[str, str]:
    return {key: value for key, value in headers.items() if key.lower() in SAFE_HEADERS}


def _validate_prices(rows: object) -> dict[str, object]:
    if not isinstance(rows, list):
        raise AcceptanceError("PRICE_BODY_NOT_ARRAY")
    if len(rows) < 200:
        raise AcceptanceError("PRICE_HISTORY_LT_200")
    dates: list[str] = []
    for row in rows:
        if not isinstance(row, dict):
            raise AcceptanceError("PRICE_ROW_NOT_OBJECT")
        missing = [field for field in REQUIRED_PRICE_FIELDS if field not in row or row[field] is None]
        if missing:
            raise AcceptanceError("PRICE_REQUIRED_FIELD_MISSING")
        session = str(row["date"])[:10]
        date.fromisoformat(session)
        dates.append(session)
        for field in ("open", "high", "low", "close", "adjOpen", "adjHigh", "adjLow", "adjClose"):
            if float(row[field]) <= 0:
                raise AcceptanceError("PRICE_NONPOSITIVE_OHLC")
        if float(row["volume"]) < 0 or float(row["adjVolume"]) < 0:
            raise AcceptanceError("PRICE_NEGATIVE_VOLUME")
        if float(row["low"]) > min(float(row["open"]), float(row["close"])):
            raise AcceptanceError("PRICE_INVALID_RAW_LOW")
        if float(row["high"]) < max(float(row["open"]), float(row["close"])):
            raise AcceptanceError("PRICE_INVALID_RAW_HIGH")
        if float(row["adjLow"]) > min(float(row["adjOpen"]), float(row["adjClose"])):
            raise AcceptanceError("PRICE_INVALID_ADJUSTED_LOW")
        if float(row["adjHigh"]) < max(float(row["adjOpen"]), float(row["adjClose"])):
            raise AcceptanceError("PRICE_INVALID_ADJUSTED_HIGH")
        if float(row["splitFactor"]) <= 0 or float(row["divCash"]) < 0:
            raise AcceptanceError("PRICE_INVALID_CORPORATE_ACTION")
    if len(dates) != len(set(dates)):
        raise AcceptanceError("PRICE_DUPLICATE_SESSION")
    ordered = sorted(dates)
    return {
        "row_count": len(rows),
        "unique_session_count": len(set(dates)),
        "first_date": ordered[0],
        "last_date": ordered[-1],
        "field_semantics": list(REQUIRED_PRICE_FIELDS),
        "required_field_null_count": 0,
    }


def _validate_metadata(body: object, symbol: str) -> dict[str, object]:
    if not isinstance(body, dict):
        raise AcceptanceError("METADATA_BODY_NOT_OBJECT")
    ticker = str(body.get("ticker", "")).upper()
    if ticker != symbol:
        raise AcceptanceError("METADATA_TICKER_MISMATCH")
    return {
        "ticker": ticker,
        "name": body.get("name"),
        "exchange_code": body.get("exchangeCode"),
        "start_date": body.get("startDate"),
        "end_date": body.get("endDate"),
    }


Fetcher = Callable[[str, dict[str, str], str], tuple[int, dict[str, str], bytes]]


def run_acceptance(
    *,
    archive: Path,
    repository: Path,
    start_date: str,
    end_date: str,
    fetcher: Fetcher,
) -> dict[str, object]:
    if _inside(archive, repository):
        raise AcceptanceError("ARCHIVE_INSIDE_REPOSITORY")
    if archive.exists():
        raise AcceptanceError("ARCHIVE_ALREADY_EXISTS")
    archive.mkdir(parents=True, mode=0o700)
    archive.chmod(0o700)
    endpoints: dict[str, object] = {}
    failure: str | None = None

    for symbol in SYMBOLS:
        for kind in ("metadata", "prices"):
            name = f"{kind}_{symbol}"
            path = f"/tiingo/daily/{symbol}" + ("/prices" if kind == "prices" else "")
            parameters = ({"startDate": start_date, "endDate": end_date, "resampleFreq": "daily"}
                          if kind == "prices" else {})
            try:
                status, headers, raw = fetcher(path, parameters, name)
                raw_path = archive / f"{name}.raw"
                _write_private(raw_path, raw)
                reread = raw_path.read_bytes()
                reconstruction = reread == raw
                parsed = json.loads(reread)
                result = (_validate_prices(parsed) if kind == "prices"
                          else _validate_metadata(parsed, symbol))
                endpoints[name] = {
                    "access": "PASS",
                    "http_status": status,
                    "safe_headers": _safe_headers(headers),
                    "raw_byte_length": len(raw),
                    "raw_sha256": hashlib.sha256(raw).hexdigest(),
                    "raw_filename": raw_path.name,
                    "raw_archive_reconstruction": "PASS" if reconstruction else "FAIL",
                    **result,
                }
                if status != 200 or not reconstruction:
                    raise AcceptanceError("HTTP_OR_RECONSTRUCTION_FAILURE")
            except Exception as exc:  # evidence keeps only the exception class and sanitized code
                failure = exc.args[0] if isinstance(exc, AcceptanceError) and exc.args else type(exc).__name__
                endpoints.setdefault(name, {"access": "FAIL", "sanitized_error": failure})
                break
        if failure:
            break

    evidence: dict[str, object] = {
        "artifact": "tiingo_free_account_acceptance",
        "schema_version": "1.0",
        "credential_present": True,
        "credential_value_stored": False,
        "source_promoted": False,
        "start_date": start_date,
        "end_date": end_date,
        "symbols": list(SYMBOLS),
        "authenticated_endpoints": endpoints,
        "raw_archive_mode": oct(stat.S_IMODE(archive.stat().st_mode))[2:],
        "raw_bytes_archived_before_parse": True,
        "historical_performance_calculated": False,
        "signal_calculated": False,
        "official_observation_created": False,
        "engine_or_scheduler_started": False,
        "publication_latency_observation_completed": False,
        "failure_reason": failure,
        "final_gate": (
            "SOURCE_ACCEPTANCE_PENDING_OPERATIONAL_LATENCY_EVIDENCE"
            if failure is None and len(endpoints) == 4
            else "SOURCE_ACCEPTANCE_FAIL"
        ),
    }
    evidence_path = archive / "tiingo_account_acceptance.json"
    _write_private(evidence_path, json.dumps(evidence, indent=2, sort_keys=True).encode("utf-8") + b"\n")
    return evidence


def _live_fetcher(api_key: str) -> Fetcher:
    def fetch(path: str, parameters: dict[str, str], _: str) -> tuple[int, dict[str, str], bytes]:
        query = urllib.parse.urlencode(parameters)
        url = API_BASE.replace("/tiingo/daily", path) + (f"?{query}" if query else "")
        request = urllib.request.Request(
            url,
            headers={"Authorization": f"Token {api_key}", "Accept": "application/json"},
            method="GET",
        )
        with urllib.request.urlopen(request, timeout=30) as response:
            return response.status, dict(response.headers.items()), response.read()
    return fetch


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive-dir", type=Path, required=True)
    parser.add_argument("--start-date", required=True)
    parser.add_argument("--end-date", required=True)
    parser.add_argument("--validate-only", action="store_true")
    arguments = parser.parse_args()
    repository = Path(__file__).resolve().parents[1]
    key = os.environ.get("TIINGO_API_KEY", "")
    print(f"TIINGO_API_KEY_PRESENT={'TRUE' if bool(key) else 'FALSE'}")
    if not key:
        return 3
    if _inside(arguments.archive_dir, repository):
        print("ARCHIVE_LOCATION_VALID=FALSE")
        return 2
    print("ARCHIVE_LOCATION_VALID=TRUE")
    if arguments.validate_only:
        print("VALIDATION_ONLY=PASS")
        return 0
    evidence = run_acceptance(
        archive=arguments.archive_dir,
        repository=repository,
        start_date=arguments.start_date,
        end_date=arguments.end_date,
        fetcher=_live_fetcher(key),
    )
    print(f"FINAL_GATE={evidence['final_gate']}")
    print(f"EVIDENCE_PATH={arguments.archive_dir / 'tiingo_account_acceptance.json'}")
    return 0 if evidence["final_gate"] != "SOURCE_ACCEPTANCE_FAIL" else 1


if __name__ == "__main__":
    raise SystemExit(main())
