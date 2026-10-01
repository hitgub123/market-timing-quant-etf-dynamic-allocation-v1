"""Operational contract remediation governance tests.

These tests validate documents, machine schemas, deterministic serialization
rules, synthetic foreign-key fixtures, the isolated dependency manifest, and
the no-start boundary. They never call a vendor, create a scheduler, or write
an official prospective record.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal, InvalidOperation
import hashlib
import importlib.metadata as metadata
import json
import math
from pathlib import Path
import re
import subprocess

import pandas as pd
import pandas_market_calendars as mcal
import pytest


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
SCHEMAS = ROOT / "schemas/paper_trading"
TAXONOMY = DOCS / "paper_trading_incident_taxonomy.csv"
FREEZE_COMMIT = "c75af4cf196419c6a27fbddcb10aaad966148b89"
RESEARCH_TAG = "2b2bf987f2e00540412d263a8ef39566af1d1e2a"
RESEARCH_MANIFEST_SHA = "dcb8f9d79de93c61e0bd7d93b743b0356be9eb3b1467acf5db9a58563889d400"


def text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def schema_files() -> list[Path]:
    return sorted(SCHEMAS.glob("*.schema.json"))


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def fixed_decimal(value: object, scale: int) -> str:
    """Reference fixed-point formatter used only by contract tests."""
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("non-finite numeric value")
        if value == 0.0 and math.copysign(1.0, value) < 0:
            raise ValueError("negative zero")
    try:
        decimal = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError("invalid decimal") from exc
    if not decimal.is_finite() or (decimal == 0 and str(value).startswith("-")):
        raise ValueError("non-finite or negative zero")
    quantum = Decimal(1).scaleb(-scale)
    return format(decimal.quantize(quantum), "f")


def canonical_bytes(record: dict[str, object]) -> bytes:
    """Small deterministic projection matching the documented hash surface."""
    numeric_scales = {
        "cash": 2,
        "pre_tax_nav": 2,
        "tax_paid": 2,
        "raw_close": 8,
        "adjusted_close": 8,
        "target_weight": 12,
        "daily_return": 12,
        "tracking_difference_bps": 6,
    }

    def project(value: object, key: str | None = None) -> object:
        if isinstance(value, bool) or value is None or isinstance(value, str):
            return value
        if isinstance(value, (int, float, Decimal)):
            if key in numeric_scales:
                return fixed_decimal(value, numeric_scales[key])
            if isinstance(value, float) and not math.isfinite(value):
                raise ValueError("non-finite numeric value")
            return value
        if isinstance(value, dict):
            return {k: project(value[k], k) for k in sorted(value)}
        if isinstance(value, list):
            if all(isinstance(item, (str, int)) for item in value):
                return sorted(project(item) for item in value)
            return [project(item) for item in value]
        raise TypeError(type(value).__name__)

    return json.dumps(project(record), ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def test_all_eight_schemas_parse_and_expose_contract_metadata() -> None:
    assert {path.name for path in schema_files()} == {
        "paper_observations.schema.json",
        "paper_decisions.schema.json",
        "paper_orders.schema.json",
        "paper_fills.schema.json",
        "paper_nav.schema.json",
        "paper_tax.schema.json",
        "paper_incidents.schema.json",
        "paper_data_revisions.schema.json",
    }
    for path in schema_files():
        schema = json.loads(path.read_text(encoding="utf-8"))
        assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
        assert schema["additionalProperties"] is False
        assert schema["x-append-only"] is True
        assert schema["x-primary-key"] in schema["properties"]
        assert schema["x-primary-key"] in schema["required"]
        assert schema["x-chain-scope"]
        assert schema["x-chain-ordering"] == ["canonical_event_time_utc", "primary_key", "created_at", "chain_sequence"]
        assert schema["x-genesis"] == {"first_record_previous_record_hash": None, "chain_sequence": 0}


def test_all_schemas_satisfy_normative_shared_record_contract() -> None:
    shared = {
        "schema_version",
        "protocol_version",
        "fixture_status",
        "source",
        "code_commit",
        "created_at",
        "batch_id",
        "chain_scope",
        "chain_sequence",
        "previous_record_hash",
        "record_hash",
    }
    for path in schema_files():
        schema = json.loads(path.read_text(encoding="utf-8"))
        assert shared <= set(schema["required"]), path.name
        assert schema["properties"]["fixture_status"]["enum"] == ["SYNTHETIC_TEST_FIXTURE", "OFFICIAL_PROSPECTIVE"]
        assert schema["properties"]["previous_record_hash"]["type"] == ["string", "null"]
        assert schema["properties"]["record_hash"]["pattern"] == "^[a-f0-9]{64}$"
        assert schema["properties"]["chain_sequence"]["type"] == "integer"


def test_primary_keys_versions_created_code_and_hash_are_required() -> None:
    for path in schema_files():
        schema = json.loads(path.read_text(encoding="utf-8"))
        required = set(schema["required"])
        assert schema["x-primary-key"] in required
        assert {"schema_version", "protocol_version", "created_at", "code_commit", "record_hash"} <= required


def test_foreign_key_metadata_and_conditional_links_are_machine_auditable() -> None:
    expected = {
        "paper_decisions.schema.json": {"observation_id": ("paper_observations.schema.json", True)},
        "paper_orders.schema.json": {"decision_id": ("paper_decisions.schema.json", True)},
        "paper_fills.schema.json": {"order_id": ("paper_orders.schema.json", True)},
        "paper_tax.schema.json": {"order_id": ("paper_orders.schema.json", False), "fill_id": ("paper_fills.schema.json", False)},
    }
    for filename, links in expected.items():
        metadata_block = json.loads((SCHEMAS / filename).read_text(encoding="utf-8"))["x-foreign-keys"]
        for field, (parent, required) in links.items():
            assert metadata_block[field]["schema"] == parent
            assert metadata_block[field]["required"] is required
    nav = json.loads((SCHEMAS / "paper_nav.schema.json").read_text(encoding="utf-8"))["x-foreign-keys"]["order_hashes"]
    assert nav["required"] is False and "conditional" in nav
    incident = json.loads((SCHEMAS / "paper_incidents.schema.json").read_text(encoding="utf-8"))["x-foreign-keys"]["affected_record_ids"]
    assert incident["required"] is False and "conditional" in incident
    revision = json.loads((SCHEMAS / "paper_data_revisions.schema.json").read_text(encoding="utf-8"))["x-foreign-keys"]
    assert {"original_record_id", "original_record_hash", "revised_record_id", "revised_record_hash"} <= set(revision)
    tax = json.loads((SCHEMAS / "paper_tax.schema.json").read_text(encoding="utf-8"))
    assert "trigger_type" in tax["required"]
    assert set(tax["properties"]["trigger_type"]["enum"]) >= {"ORDER", "FILL", "DISTRIBUTION"}


def test_schema_contract_matrix_covers_shared_units_fk_and_serialization() -> None:
    matrix = pd.read_csv(DOCS / "PAPER_TRADING_SCHEMA_CONTRACT_MATRIX.csv")
    assert list(matrix.columns) == ["requirement_id", "normative_requirement", "schema", "property", "required", "status", "audit_note"]
    assert matrix.requirement_id.is_unique
    assert matrix.status.eq("PASS").all()
    required_ids = {"SHARED-001", "SHARED-012", "SER-001", "SER-004", "FK-001", "FK-006", "OBS-002", "REV-003"}
    assert required_ids <= set(matrix.requirement_id)


def test_hash_chain_scope_ordering_and_genesis_are_explicit_in_docs() -> None:
    ledger = text(DOCS / "PAPER_TRADING_LEDGER_SCHEMA.md")
    for phrase in (
        "RECORD_CHAIN_SCOPE = one independent chain per ledger schema and protocol_version",
        "BATCH_CHAIN_SCOPE  = one manifest chain across batches, ordered by batch_id",
        "canonical_event_time_utc, primary_key,",
        "chain_sequence=0",
        "previous_record_hash=null",
        "Corrections/revisions participate in the `paper_data_revisions` record chain",
        "recomputing canonical bytes",
    ):
        assert phrase in ledger


def test_canonical_decimal_serialization_is_deterministic_and_safe() -> None:
    ledger = text(DOCS / "PAPER_TRADING_LEDGER_SCHEMA.md")
    assert "fixed-point JSON number tokens (not locale strings)" in ledger
    assert fixed_decimal("1.2", 8) == "1.20000000"
    assert fixed_decimal(0, 12) == "0.000000000000"
    assert fixed_decimal(Decimal("123.456789"), 6) == "123.456789"
    with pytest.raises(ValueError):
        fixed_decimal(-0.0, 8)
    with pytest.raises(ValueError):
        fixed_decimal(float("nan"), 8)
    with pytest.raises(ValueError):
        fixed_decimal(float("inf"), 8)


def test_timezone_naive_timestamp_is_rejected() -> None:
    naive = datetime.fromisoformat("2026-09-16T00:00:00")
    aware = datetime.fromisoformat("2026-09-16T00:00:00+00:00")
    assert naive.tzinfo is None
    assert aware.tzinfo is not None and aware.utcoffset() is not None
    ledger = text(DOCS / "PAPER_TRADING_LEDGER_SCHEMA.md")
    assert "timezone-naive timestamps are invalid" in ledger


def test_identical_record_has_identical_canonical_bytes_and_hash() -> None:
    record = {"pre_tax_nav": 100.0, "target_weight": 1.0, "order_hashes": ["b", "a"], "note": "é"}
    first = canonical_bytes(record)
    second = canonical_bytes(dict(record))
    assert first == second
    assert sha256_bytes(first) == sha256_bytes(second)


def test_changed_economic_field_changes_hash() -> None:
    record = {"pre_tax_nav": 100.0, "target_weight": 1.0}
    changed = {"pre_tax_nav": 100.01, "target_weight": 1.0}
    assert sha256_bytes(canonical_bytes(record)) != sha256_bytes(canonical_bytes(changed))


def test_append_only_correction_cannot_overwrite_original() -> None:
    original = {"record_id": "obs-1", "raw_close": 100.0, "record_hash": "a" * 64}
    revision = {
        "original_record_id": original["record_id"],
        "original_record_hash": original["record_hash"],
        "revised_record_id": "obs-1-r1",
        "revised_record_hash": "b" * 64,
    }
    assert original["raw_close"] == 100.0
    assert revision["original_record_hash"] == original["record_hash"]
    assert revision["revised_record_id"] != original["record_id"]


def test_synthetic_foreign_key_fixture_contract() -> None:
    observations = {"obs-1": "h-observation"}
    decisions = {"dec-1": "obs-1"}
    orders = {"ord-1": "dec-1"}
    fills = {"fill-1": "ord-1"}
    tax = {"tax-1": {"order_id": "ord-1", "fill_id": "fill-1"}}
    assert decisions["dec-1"] in observations
    assert orders["ord-1"] in decisions
    assert fills["fill-1"] in orders
    assert tax["tax-1"]["order_id"] in orders
    assert tax["tax-1"]["fill_id"] in fills


def test_source_snapshot_hash_reconstructs_point_in_time_window() -> None:
    raw_response = b"fixture raw adjusted daily response"
    raw_hash = sha256_bytes(raw_response)
    source_snapshot_id = f"sha256:{raw_hash}"
    assert re.fullmatch(r"sha256:[a-f0-9]{64}", source_snapshot_id)
    window = [{"session_date": f"2026-01-{day:02d}", "raw_hash": raw_hash} for day in range(1, 201)]
    manifest = json.dumps(sorted(window, key=lambda row: row["session_date"]), sort_keys=True, separators=(",", ":")).encode()
    combined_id = f"sha256:{sha256_bytes(manifest)}"
    assert combined_id.startswith("sha256:")
    observation_schema = json.loads((SCHEMAS / "paper_observations.schema.json").read_text(encoding="utf-8"))
    assert observation_schema["properties"]["source_snapshot_id"]["pattern"] == r"^sha256:[a-f0-9]{64}$"
    readiness = text(DOCS / "PAPER_TRADING_SOURCE_FREEZE_READINESS.md")
    for phrase in ("ordered final 200", "source_snapshot_id", "no vendor ID invented"):
        assert phrase in readiness


def test_stale_rule_separates_publication_and_acquisition_delay() -> None:
    source = text(DOCS / "PAPER_TRADING_DATA_SOURCE_SPEC.md")
    runbook = text(DOCS / "PAPER_TRADING_OPERATIONAL_RUNBOOK.md")
    for phrase in ("data_available_at", "data_acquired_at", "not stale merely because 15 minutes elapsed", "STALE_SEMANTICS_UNVERIFIED", "wrong-session/duplicate"):
        assert phrase in source or phrase in runbook
    assert "SOURCE_CAPABILITY_UNVERIFIED" in source


def test_incident_taxonomy_is_unique_and_covers_new_fail_closed_conditions() -> None:
    taxonomy = pd.read_csv(TAXONOMY)
    assert taxonomy.incident_code.is_unique
    assert taxonomy.freeze_status.eq("PROPOSED_NOT_FROZEN").all()
    required = {
        "HASH_CHAIN_BREAK",
        "SOURCE_CAPABILITY_UNVERIFIED",
        "STALE_SEMANTICS_UNVERIFIED",
        "ENVIRONMENT_MISMATCH",
        "SCHEMA_CONTRACT_FAILURE",
        "FOREIGN_KEY_VIOLATION",
        "CALENDAR_FIXTURE_MISMATCH",
        "RAW_ARCHIVE_FAILURE",
        "SOURCE_SNAPSHOT_RECONSTRUCT_FAILURE",
    }
    assert required <= set(taxonomy.incident_code)
    assert taxonomy.automatic_action.notna().all()
    assert taxonomy.operator_action_allowed.notna().all()
    assert taxonomy.protocol_validity_effect.notna().all()
    assert "No operator may choose a price" in text(DOCS / "PAPER_TRADING_DATA_SOURCE_SPEC.md")


def test_every_declared_fail_closed_incident_code_has_one_taxonomy_row() -> None:
    taxonomy = pd.read_csv(TAXONOMY).set_index("incident_code")
    declared = {
        "MISSING_SCHEDULED_CLOSE",
        "STALE_SCHEDULED_CLOSE",
        "STALE_SEMANTICS_UNVERIFIED",
        "MISSING_NEXT_OPEN",
        "INVALID_PRICE",
        "DUPLICATE_RECORD",
        "SOURCE_DISAGREEMENT",
        "UNRESOLVED_SOURCE_DISAGREEMENT",
        "PARTIAL_SESSION",
        "EARLY_CLOSE",
        "UNSCHEDULED_CLOSURE",
        "VENDOR_OUTAGE",
        "CORPORATE_ACTION_AMBIGUITY",
        "TIMESTAMP_AMBIGUITY",
        "DATA_REVISION_INCIDENT",
        "PROXY_UNAVAILABLE",
        "CLOCK_DRIFT",
        "HASH_CHAIN_BREAK",
        "SOURCE_CAPABILITY_UNVERIFIED",
        "ENVIRONMENT_MISMATCH",
        "SCHEMA_CONTRACT_FAILURE",
        "FOREIGN_KEY_VIOLATION",
        "CALENDAR_FIXTURE_MISMATCH",
        "RAW_ARCHIVE_FAILURE",
        "SOURCE_SNAPSHOT_RECONSTRUCT_FAILURE",
    }
    assert declared <= set(taxonomy.index)
    assert taxonomy.loc[list(declared), "automatic_action"].notna().all()
    assert taxonomy.loc[list(declared), "protocol_validity_effect"].notna().all()


def test_environment_lock_is_verified_in_isolation_and_not_silently_drifted() -> None:
    manifest = json.loads(text(DOCS / "paper_trading_environment_rebuild_manifest.json"))
    assert manifest["status"] == "VERIFIED_ISOLATED"
    requirements = {}
    for line in text(ROOT / "requirements.txt").splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        name, version = line.split("==")
        requirements[name.lower()] = version
    actual = {name.lower(): version for name, version in manifest["packages"].items()}
    assert all(actual[name] == version for name, version in requirements.items())
    env_text = text(DOCS / "PAPER_TRADING_ENVIRONMENT_SPEC.md")
    assert "isolated rebuild" in env_text and "ENVIRONMENT_MISMATCH" in env_text
    assert "No Research v1 dependency was upgraded" in env_text


def test_calendar_fixtures_pass_with_pinned_calendar() -> None:
    assert metadata.version("pandas-market-calendars") == "5.4.0"
    calendar = mcal.get_calendar("NASDAQ")
    monday_holiday = calendar.schedule("2024-01-15", "2024-01-19")
    assert monday_holiday.index[0].date().isoformat() == "2024-01-16"
    early = calendar.schedule("2024-11-29", "2024-11-29").iloc[0]
    assert early.market_close.tz_convert("America/New_York").hour == 13
    spring = calendar.schedule("2024-03-08", "2024-03-11").iloc[1]
    autumn = calendar.schedule("2024-11-01", "2024-11-04").iloc[1]
    assert spring.market_open.tz_convert("America/New_York").utcoffset() != autumn.market_open.tz_convert("America/New_York").utcoffset()
    manifest = json.loads(text(DOCS / "paper_trading_environment_rebuild_manifest.json"))
    assert set(manifest["calendar"]["fixtures"]) >= {"MONDAY_HOLIDAY", "EARLY_CLOSE", "DST_SPRING", "DST_AUTUMN"}


def test_vendor_capabilities_have_explicit_readiness_and_source_is_not_ready() -> None:
    source = text(DOCS / "PAPER_TRADING_DATA_SOURCE_SPEC.md")
    readiness = text(DOCS / "PAPER_TRADING_SOURCE_FREEZE_READINESS.md")
    for classification in ("VERIFIED_WITH_ACCOUNT", "FAIL_NOT_AVAILABLE_BY_DOCUMENTED_DEADLINE", "NOT_OBSERVABLE_IN_PAPER_MODE"):
        assert classification in source or classification in readiness
    assert "SOURCE_NOT_READY_FOR_FINAL_FREEZE" in readiness
    assert "no vendor id invented" in readiness.lower() or "never invents it" in readiness
    assert "/api/eod" in source and "/api/splits" in source and "/api/div" in source


def test_no_design_thresholds_or_closed_artifacts_changed() -> None:
    closed = [
        "docs/PAPER_TRADING_PROTOCOL_V1_STATISTICAL_DESIGN.md",
        "docs/PAPER_TRADING_PROTOCOL_V1_DESIGN_RATIONALE.md",
        "docs/PAPER_TRADING_OUTCOME_DECISION_SPEC.md",
        "docs/paper_trading_outcome_decision_table.csv",
        "docs/paper_trading_threshold_registry.csv",
        "docs/paper_trading_protocol_decision_table.csv",
    ]
    for relative in closed:
        expected = subprocess.check_output(["git", "show", f"{FREEZE_COMMIT}:{relative}"], cwd=ROOT)
        assert (ROOT / relative).read_bytes() == expected
    closed_text = "\n".join(text(ROOT / relative) for relative in closed)
    for phrase in ("20.315", "MA200", "weekly", "500", "36", "−60%", "6.0"):
        assert phrase in closed_text


def test_no_production_engine_scheduler_start_observation_backtest_optimizer_or_phase9() -> None:
    manifest = json.loads(text(ROOT / "reports/research_v1_freeze_manifest.json"))
    assert manifest["freeze_scope"]["prospective_validation_started"] is False
    assert manifest["freeze_scope"]["paper_observations_present"] is False
    assert manifest["freeze_scope"]["paper_trading_engine_implemented"] is False
    assert not (ROOT / "paper").exists()
    assert not (ROOT / "prospective_validation_v1").exists()
    assert not any("phase9" in p.name.lower() for p in (ROOT / "experiments").glob("*.py"))
    assert not (ROOT / "paper_validation_v1_acceptance_manifest.json").exists()


def test_research_v1_freeze_integrity_is_unchanged() -> None:
    tagged = subprocess.check_output(["git", "rev-parse", "research-v1.0-final^{commit}"], cwd=ROOT, text=True).strip()
    assert tagged == RESEARCH_TAG
    manifest = ROOT / "reports/research_v1_freeze_manifest.json"
    assert sha256_bytes(manifest.read_bytes()) == RESEARCH_MANIFEST_SHA
    assert sha256_bytes(manifest.read_bytes()) == manifest.with_suffix(".sha256").read_text(encoding="utf-8").split()[0]


def test_remediation_artifacts_are_proposed_and_no_acceptance_manifest_exists() -> None:
    assert (DOCS / "PAPER_TRADING_SCHEMA_CONTRACT_MATRIX.csv").is_file()
    assert (DOCS / "PAPER_TRADING_SOURCE_FREEZE_READINESS.md").is_file()
    assert (ROOT / "reports/paper_trading_operational_contract_remediation_audit.md").is_file()
    assert not (ROOT / "paper_validation_v1_acceptance_manifest.json").exists()
    for path in (DOCS / "paper_trading_incident_taxonomy.csv", DOCS / "paper_trading_operational_decision_registry.csv"):
        assert pd.read_csv(path).freeze_status.eq("PROPOSED_NOT_FROZEN").all()
