# Paper Trading Protocol v1 — Source Account Acceptance Audit

**Scope:** authoritative-source account/API capability acceptance
**Prior remediation commit:** `f5ccb4fae9bab405ec23bee1abf35275fe18c21f`
**Date:** 2026-09-16

## A. Exact source-gate outcome

`ACCOUNT_CREDENTIALS_NOT_AVAILABLE`

The approved execution environment contained none of the checked credential
names (`ALPHA_VANTAGE_API_KEY`, `MASSIVE_API_KEY`, `POLYGON_API_KEY`). No
authenticated vendor request was made. No API key, price response, historical
metric, strategy return, or signal was fabricated.

## B. Alpha Vantage endpoint entitlement

| Required capability | Result | Evidence |
|---|---|---|
| `TIME_SERIES_DAILY_ADJUSTED` QQQ | `UNVERIFIED_CAPABILITY` | Account credential unavailable |
| `TIME_SERIES_DAILY` QQQ | `UNVERIFIED_CAPABILITY` | Account credential unavailable |
| `TIME_SERIES_DAILY` QLD | `UNVERIFIED_CAPABILITY` | Account credential unavailable |
| `SPLITS`/`DIVIDENDS` | `UNVERIFIED_CAPABILITY` | Account credential unavailable |
| 200-observation history | `UNVERIFIED_CAPABILITY` | Account/plan entitlement unavailable |

Public documentation was inspected only for endpoint semantics. It is not
treated as account entitlement. No official source response was retrieved.

## C. Publication and rate limits

Publication SLA classification: `UNRESOLVED`.
Publication deadline: `PUBLICATION_DEADLINE_NOT_READY`.
No after-close latency sample was collected because credentials were absent; no
15-minute SLA was invented.

The conservative request-demand calculation is 74 scheduled-session units per
12 months, 16 requests per unit, a 25% safety margin, 20 requests per unit,
and 1,480 requests for the conservative annual sum. Actual account limits
could not be compared, so the rate gate is `RATE_LIMIT_NOT_READY`. Retries are
bounded and deterministic.

## D. Snapshot reconstruction

`SOURCE_SNAPSHOT_RECONSTRUCTION_PASS` was demonstrated using only a synthetic
fixture. Exact raw bytes were hashed before parsing, 200 adjusted values were
reloaded from the immutable bytes, and the test-only MA200/signal reproduced
exactly. No fixture entered an official directory.

## E. Massive reconciliation and optional proxy

Massive remained `RECONCILIATION_MARKET_DATA_SOURCE`. Its QQQ/QLD endpoint
access and plan/rate-limit constraints are
`ACCOUNT_CREDENTIALS_NOT_AVAILABLE`. The optional execution proxy remains
`NOT_OBSERVABLE_IN_PAPER_MODE`; this does not block source acceptance and does
not replace the frozen 5-bps simulated path.

## F. Revision semantics

Vendor revision capability is `UNVERIFIED_CAPABILITY`. The protocol-owned raw
snapshot remains authoritative, and the schema/fixture confirm that
`source_revision_id = null` is valid. No vendor revision ID was invented.

## G. Source disagreement and secret audit

The synthetic disagreement fixture passed: Alpha Vantage stays authoritative,
Massive stays reconciliation-only, mismatch creates an incident, values are
never averaged, and operator choice cannot depend on favorable signal/outcome.

`SECRET_LEAK_SCAN_PASS` — no credential was printed, stored, committed, or
placed in request metadata, raw archives, test fixtures, or this report.

## H. Integrity and boundary checks

No strategy/statistical/ledger redesign occurred. No historical performance,
backtest, optimizer, paper engine, scheduler, official observation, prospective
start timestamp, 36-month clock, final acceptance manifest, or Phase 9 artifact
was created. Research v1 freeze integrity and closed prospective design
integrity remain unchanged.

## I. Tests

Dedicated source-acceptance tests (17 passed) cover credential absence, snapshot byte
reconstruction, exact 200-value/MA reconstruction, artifact statuses and
schema, request-budget arithmetic, no-performance use, reconciliation-only
Massive, no favorable substitution, optional proxy behavior, secret leakage,
no-start boundaries, and frozen-integrity checks.

The source-acceptance plus prospective governance suites passed 157 tests; the
full pytest suite passed 541 tests. The remediation is committed separately;
the exact commit hash is reported in the final handoff. This phase remains an
account-gated acceptance, not Final Freeze.

PAPER TRADING SOURCE ACCOUNT ACCEPTANCE COMPLETE — AWAITING EXTERNAL SOURCE AUDIT
