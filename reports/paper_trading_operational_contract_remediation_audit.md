# Paper Trading Protocol v1 — Operational Contract Remediation Audit

**Date:** 2026-09-16
**Scope:** operational contract remediation only
**Status:** `PROPOSED_NOT_FROZEN`
**Critical gate:** `SOURCE_NOT_READY_FOR_FINAL_FREEZE`

## Outcome

The eight machine schemas and the normative ledger contract were audited and
remediated without changing strategy logic, statistical/economic design,
thresholds, horizon, tax semantics, schedule, or the historical Research v1
artifacts. No engine, scheduler, official observation, acceptance manifest, or
Phase 9 artifact was created.

## Schema-contract mismatches found and fixed

The prior schemas did not carry a uniform `source`, `code_commit`, or explicit
batch/record-chain scope on every ledger. The tax schema had no optional fill
link, and cross-ledger foreign-key semantics were prose-only. The remediation
adds the shared provenance fields to all eight schemas, explicit
`x-chain-scope`, ordering and genesis metadata, `x-foreign-keys`, and the
observation `source_snapshot_id`. `docs/PAPER_TRADING_SCHEMA_CONTRACT_MATRIX.csv`
now maps every shared field, unit/timezone rule, enum/nullability rule,
foreign-key condition, and canonical-serialization rule to its schema property.

Final shared record contract:

```text
primary key, schema_version, protocol_version, fixture_status, source,
code_commit, created_at, batch_id, chain_scope, chain_sequence,
previous_record_hash, record_hash
```

Tax events carry an explicit trigger type and link to an order or fill when
applicable; corporate-action events may have null parent IDs without a fake FK.
Decisions, orders, and fills require observation, decision, and order parents respectively.
Revisions require original/revised IDs and hashes. NAV order hashes and incident
affected IDs are conditional and may be empty only when no parent exists.

## Hash-chain and canonical serialization audit

`RECORD_CHAIN_SCOPE` is one independent chain per ledger schema and
`protocol_version`; `BATCH_CHAIN_SCOPE` is one manifest chain ordered by
`batch_id`. Ordering is `(canonical_event_time_utc, primary_key, created_at,
chain_sequence)`. Genesis is sequence zero with a null predecessor. Corrections
participate in the revision chain and never splice into the original chain.

Canonical bytes are UTF-8 NFC JSON with sorted keys, compact separators,
timezone-normalized UTC timestamps, literal JSON null, field-aware fixed-point
numeric tokens (USD 2, prices 8, weights/returns 12, bps 6), sorted scalar ID
arrays, and no exponent, NaN, Infinity, or negative zero. `record_hash` is
SHA-256 of the projection without `record_hash`; raw vendor bytes are hashed
before parsing. The protocol-owned `source_snapshot_id` is
`sha256:<raw_hash>` or the hash of a sorted raw-hash manifest. No vendor
revision ID is invented.

## Environment lock and calendar result

An isolated rebuild from the pinned `requirements.txt` was verified on Linux
WSL2 x86_64 with Python 3.14.4, NumPy 2.5.0, pandas 3.0.3, PyArrow 24.0.0,
PyYAML 6.0.3, pytest 9.1.1, pandas-market-calendars 5.4.0, Matplotlib 3.10.6,
and tzdata 2026.4. The host Matplotlib 3.11.0 drift remains explicitly
classified `ENVIRONMENT_MISMATCH` outside that isolated environment. NASDAQ
calendar fixtures passed for Monday holidays, early close, both DST changes,
month/bimonthly/quarter/year boundaries, and next-session semantics.

## Alpha Vantage source freeze readiness

Public documentation verifies endpoint roles, but intended account/plan access,
rate limits, after-close publication SLA, and immutable revision behavior were
not authenticated in this remediation. Adjusted daily, raw daily,
split/dividend, and symbol-level capabilities are therefore
`VERIFIED_WITH_ACCOUNT_DEPENDENCY` or `UNVERIFIED_CAPABILITY`. Massive remains
reconciliation-only. The critical result is:

`SOURCE_NOT_READY_FOR_FINAL_FREEZE`

The authoritative point-in-time rule is resolved at the protocol level: archive
the exact raw response before parsing, derive `source_snapshot_id`, and
reconstruct the exact 200 adjusted closes/MA200/signal. A vendor revision ID
is optional and remains null if unavailable.

## Stale-data and incident audit

Publication delay and acquisition delay are separate fields. A close retrieved
16 minutes after close is not stale merely because a fixed 15-minute timer
elapsed. `STALE` means wrong session key, duplicate prior-session data while
the expected session is absent, or an expired predeclared vendor-compatible
deadline. Alpha Vantage's deadline is unverified, so the fixed rule is
`STALE_SEMANTICS_UNVERIFIED` and cannot authorize an official signal. Any
future grace adjustment is `OPERATIONAL_SOURCE_COMPATIBILITY_REMEDIATION`, not
statistical/economic redesign.

Every fail-closed branch in the source, calendar, runbook, ledger, and
environment documents maps to exactly one row in
`paper_trading_incident_taxonomy.csv`; new rows cover source capability,
stale semantics, environment/schema/FK failures, calendar fixtures, raw archive,
and source-snapshot reconstruction. No branch grants return-dependent operator
discretion.

## Governance and immutability checks

- Dedicated remediation tests (23 passed) cover all eight schemas, shared fields, primary
  keys, foreign keys, chain/genesis/order rules, canonical decimal safety,
  snapshot reconstruction, stale semantics, taxonomy, isolated lock/calendar,
  source readiness, closed-threshold byte identity, and no-start boundaries.
- Existing prospective design, outcome, and operational-preparation suites
  remain in force; closed statistical/economic documents remain byte-identical
  to the design-close commit.
- Research v1 tag and freeze manifest SHA-256 remain unchanged.
- No production engine, scheduler, official observation, backtest, optimizer,
  Phase 9, or final acceptance manifest exists.

The remediation is operationally complete for external review, but the source
and host gates remain deliberately unresolved. This is not a protocol freeze.

PAPER TRADING OPERATIONAL CONTRACT REMEDIATION COMPLETE — AWAITING EXTERNAL FREEZE AUDIT
