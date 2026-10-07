"""Dedicated Tiingo Free account-acceptance collector controls."""

from __future__ import annotations

from datetime import date, timedelta
import json
import os
from pathlib import Path
import subprocess

import pytest

from scripts.tiingo_free_account_acceptance import (
    AcceptanceError,
    REQUIRED_PRICE_FIELDS,
    run_acceptance,
)


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/tiingo_free_account_acceptance.py"
COMMITTED_EVIDENCE = ROOT / "reports/tiingo_free_account_acceptance.json"
SCHEMA = ROOT / "schemas/source_acceptance/tiingo_free_account_acceptance.schema.json"
AUDIT = ROOT / "reports/paper_trading_tiingo_free_account_acceptance_audit.md"


def rows(count: int = 210) -> list[dict[str, object]]:
    first = date(2025, 1, 1)
    result = []
    for offset in range(count):
        session = first + timedelta(days=offset)
        result.append({
            "date": f"{session.isoformat()}T00:00:00.000Z",
            "open": 100.0,
            "high": 102.0,
            "low": 99.0,
            "close": 101.0,
            "volume": 1000,
            "adjOpen": 99.0,
            "adjHigh": 101.0,
            "adjLow": 98.0,
            "adjClose": 100.0,
            "adjVolume": 1010,
            "divCash": 0.0,
            "splitFactor": 1.0,
        })
    return result


def fetcher(price_rows: list[dict[str, object]] | None = None):
    prices = price_rows if price_rows is not None else rows()

    def fetch(path: str, parameters: dict[str, str], _: str):
        symbol = path.split("/")[3]
        body = prices if path.endswith("/prices") else {
            "ticker": symbol,
            "name": f"{symbol} ETF",
            "exchangeCode": "NASDAQ",
            "startDate": "1999-01-01",
            "endDate": "2026-10-01",
        }
        return 200, {
            "Content-Type": "application/json",
            "Date": "Thu, 01 Oct 2026 21:30:00 GMT",
            "Authorization": "must-not-survive",
        }, json.dumps(body, separators=(",", ":")).encode()

    return fetch


def test_synthetic_capability_pass_is_pending_latency(tmp_path: Path) -> None:
    archive = tmp_path / "external"
    evidence = run_acceptance(
        archive=archive,
        repository=ROOT,
        start_date="2025-01-01",
        end_date="2026-10-01",
        fetcher=fetcher(),
    )
    assert evidence["final_gate"] == "SOURCE_ACCEPTANCE_PENDING_OPERATIONAL_LATENCY_EVIDENCE"
    assert evidence["failure_reason"] is None
    assert set(evidence["authenticated_endpoints"]) == {
        "metadata_QQQ", "prices_QQQ", "metadata_QLD", "prices_QLD"
    }


def test_required_fields_and_history_are_preserved(tmp_path: Path) -> None:
    evidence = run_acceptance(
        archive=tmp_path / "external",
        repository=ROOT,
        start_date="2025-01-01",
        end_date="2026-10-01",
        fetcher=fetcher(),
    )
    for symbol in ("QQQ", "QLD"):
        prices = evidence["authenticated_endpoints"][f"prices_{symbol}"]
        assert prices["row_count"] == prices["unique_session_count"] == 210
        assert prices["field_semantics"] == list(REQUIRED_PRICE_FIELDS)
        assert prices["required_field_null_count"] == 0


def test_raw_bytes_are_written_before_parse_and_private(tmp_path: Path) -> None:
    archive = tmp_path / "external"
    evidence = run_acceptance(
        archive=archive,
        repository=ROOT,
        start_date="2025-01-01",
        end_date="2026-10-01",
        fetcher=fetcher(),
    )
    assert oct(archive.stat().st_mode & 0o777) == "0o700"
    assert oct((archive / "tiingo_account_acceptance.json").stat().st_mode & 0o777) == "0o600"
    for endpoint in evidence["authenticated_endpoints"].values():
        raw = archive / endpoint["raw_filename"]
        assert oct(raw.stat().st_mode & 0o777) == "0o600"
        assert endpoint["raw_archive_reconstruction"] == "PASS"
        assert len(raw.read_bytes()) == endpoint["raw_byte_length"]


def test_authorization_header_is_not_retained(tmp_path: Path) -> None:
    evidence = run_acceptance(
        archive=tmp_path / "external",
        repository=ROOT,
        start_date="2025-01-01",
        end_date="2026-10-01",
        fetcher=fetcher(),
    )
    serialized = json.dumps(evidence)
    assert "Authorization" not in serialized
    assert "must-not-survive" not in serialized


@pytest.mark.parametrize("mutation", ["short", "duplicate", "missing", "bad_ohlc"])
def test_invalid_price_evidence_fails_closed(tmp_path: Path, mutation: str) -> None:
    price_rows = rows()
    if mutation == "short":
        price_rows = price_rows[:199]
    elif mutation == "duplicate":
        price_rows[-1]["date"] = price_rows[0]["date"]
    elif mutation == "missing":
        price_rows[-1].pop("adjClose")
    else:
        price_rows[-1]["high"] = 1.0
    evidence = run_acceptance(
        archive=tmp_path / "external",
        repository=ROOT,
        start_date="2025-01-01",
        end_date="2026-10-01",
        fetcher=fetcher(price_rows),
    )
    assert evidence["final_gate"] == "SOURCE_ACCEPTANCE_FAIL"
    assert evidence["failure_reason"] is not None


def test_archive_inside_repository_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(AcceptanceError, match="ARCHIVE_INSIDE_REPOSITORY"):
        run_acceptance(
            archive=ROOT / "forbidden-tiingo-archive",
            repository=ROOT,
            start_date="2025-01-01",
            end_date="2026-10-01",
            fetcher=fetcher(),
        )


def test_validate_only_prints_presence_not_value_and_writes_nothing(tmp_path: Path) -> None:
    archive = tmp_path / "unused"
    environment = dict(os.environ)
    environment["TIINGO_API_KEY"] = "synthetic-secret-value"
    completed = subprocess.run(
        [
            "python3", str(SCRIPT), "--archive-dir", str(archive),
            "--start-date", "2025-01-01", "--end-date", "2026-10-01",
            "--validate-only",
        ],
        cwd=ROOT,
        env=environment,
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 0
    assert "TIINGO_API_KEY_PRESENT=TRUE" in completed.stdout
    assert "synthetic-secret-value" not in completed.stdout + completed.stderr
    assert not archive.exists()


def test_scope_controls_never_start_prospective_work(tmp_path: Path) -> None:
    evidence = run_acceptance(
        archive=tmp_path / "external",
        repository=ROOT,
        start_date="2025-01-01",
        end_date="2026-10-01",
        fetcher=fetcher(),
    )
    assert evidence["source_promoted"] is False
    assert evidence["historical_performance_calculated"] is False
    assert evidence["signal_calculated"] is False
    assert evidence["official_observation_created"] is False
    assert evidence["engine_or_scheduler_started"] is False
    assert evidence["publication_latency_observation_completed"] is False


def test_committed_authenticated_evidence_has_capability_and_pending_latency_audit() -> None:
    evidence = json.loads(COMMITTED_EVIDENCE.read_text(encoding="utf-8"))
    assert evidence["final_gate"] == "SOURCE_ACCEPTANCE_PENDING_OPERATIONAL_LATENCY_EVIDENCE"
    assert evidence["failure_reason"] is None
    assert evidence["publication_latency_observation_completed"] is True
    latency = evidence["publication_latency"]
    assert latency["sample_session"] == "2026-10-06"
    assert latency["poll_count"] == latency["raw_response_hash_matches"] == 10
    assert latency["last_unavailable_poll"] == 1
    assert latency["first_valid_poll"] == 2
    assert latency["first_valid_scheduled_offset_seconds_after_close"] == 5400
    assert latency["publication_time_exactly_known"] is False
    assert latency["interruption_recorded"] is True
    assert latency["frozen_readiness_poll_budget"] == 4
    assert latency["executed_poll_times"] == 5
    assert latency["external_adjudication_required"] is True
    assert evidence["source_promoted"] is False
    assert evidence["official_observation_created"] is False
    assert evidence["symbols"] == ["QQQ", "QLD"]
    for symbol in evidence["symbols"]:
        metadata = evidence["authenticated_endpoints"][f"metadata_{symbol}"]
        prices = evidence["authenticated_endpoints"][f"prices_{symbol}"]
        assert metadata["access"] == prices["access"] == "PASS"
        assert metadata["http_status"] == prices["http_status"] == 200
        assert prices["row_count"] == prices["unique_session_count"] == 438
        assert prices["first_date"] == "2025-01-02"
        assert prices["last_date"] == "2026-10-01"
        assert prices["raw_archive_reconstruction"] == "PASS"
        assert len(prices["raw_sha256"]) == 64


def test_committed_schema_and_audit_preserve_external_audit_boundary() -> None:
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    assert schema["properties"]["credential_value_stored"]["const"] is False
    assert schema["properties"]["source_promoted"]["const"] is False
    assert schema["properties"]["publication_latency_observation_completed"]["type"] == "boolean"
    assert "SOURCE_ACCEPTANCE_PASS" not in schema["properties"]["final_gate"]["enum"]
    audit = AUDIT.read_text(encoding="utf-8")
    assert "accepted four-poll budget" in audit
    assert audit.rstrip().endswith(
        "PAPER TRADING TIINGO FREE ACCOUNT ACCEPTANCE PENDING — FROZEN POLL-BUDGET CONFLICT"
    )
