# Paper-Validation Acceptance Manifest Specification

**Status:** `PROPOSED_NOT_FROZEN`  
**Important:** this is a design for a future manifest. The final
`paper_validation_v1_acceptance_manifest.json` is deliberately not created.
The final `paper_validation_v1_acceptance_manifest.json` is deliberately not created.

## 1. Purpose and boundary

At final protocol freeze, a manifest will bind the exact prospective protocol,
operational specifications, implementation-acceptance evidence, source
acceptance hashes, environment, and dry-run result. It will not contain API
keys, tokens, cookies, raw credentials, or unapproved official observations.
The manifest itself becomes immutable before prospective start.

## 2. Required entries

Each entry has canonical repository-relative `path`, `sha256`, `byte_length`,
`media_type`, `role`, and `freeze_status`. The future manifest must include at
least:

- `docs/PAPER_TRADING_VALIDATION_PROTOCOL_V1_DRAFT.md`;
- `docs/PAPER_TRADING_PROTOCOL_V1_DESIGN_RATIONALE.md`;
- `docs/PAPER_TRADING_PROTOCOL_V1_STATISTICAL_DESIGN.md`;
- `docs/PAPER_TRADING_OUTCOME_DECISION_SPEC.md`;
- `docs/paper_trading_outcome_decision_table.csv`;
- `docs/paper_trading_threshold_registry.csv`;
- `docs/PAPER_TRADING_DATA_SOURCE_SPEC.md`;
- `docs/paper_trading_data_source_decision.csv`;
- `docs/PAPER_TRADING_CALENDAR_SPEC.md`;
- `docs/PAPER_TRADING_LEDGER_SCHEMA.md`;
- every JSON schema under `schemas/paper_trading/`;
- `docs/PAPER_TRADING_OPERATIONAL_RUNBOOK.md`;
- `docs/paper_trading_incident_taxonomy.csv`;
- `docs/PAPER_TRADING_ENVIRONMENT_SPEC.md`;
- `docs/PAPER_TRADING_DRY_RUN_ACCEPTANCE.md`;
- `docs/PAPER_TRADING_IMPLEMENTATION_ACCEPTANCE_SPEC.md`;
- `docs/PAPER_TRADING_GOLDEN_FIXTURE_SPEC.md`;
- the external/manual audit decision and dry-run evidence.

## 3. Canonical hashing

SHA-256 is computed over exact file bytes. Paths use POSIX `/`, UTF-8 text
uses LF line endings, and the manifest entries are sorted lexicographically by
path. JSON manifest serialization uses UTF-8, sorted keys, compact separators,
and no NaN/Infinity. A top-level `manifest_hash` is the SHA-256 of the
canonical manifest with the `manifest_hash` field omitted. The manifest stores
its Git commit, protocol version, generation timestamp in UTC, environment
tuple, parent manifest hash if any, and acceptance-audit ID.

## 4. Immutability and corrections

No frozen entry is edited in place. A changed operational decision requires a
new protocol version, new commit/tag, new manifest, and new external audit.
Raw source responses are referenced by immutable SHA-256 and remain outside
Git/official manifests if licensing requires; their manifest contains only
approved metadata and hashes. Secret material is excluded before hashing.

## 5. Pre-start gates

The manifest cannot be finalized until source capability gaps, calendar
version, environment mismatch, implementation acceptance, and uncounted dry
run are all externally accepted. A manifest design or draft hash does not
freeze the protocol or start the prospective clock.
