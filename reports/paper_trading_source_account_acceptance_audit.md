# Paper Trading Protocol v1 — Source Account Acceptance Audit

**Scope:** authoritative-source account/API capability acceptance
**Prior account-gated commit:** `1cec7f42a6942043a9a227349762d8e033890f2e`
**Date:** 2026-09-17

## A. Exact source-gate outcome

`SOURCE_ACCEPTANCE_FAIL`

Both temporary credential variables were present only inside the isolated
acceptance process. Their values were never printed, logged, hashed, saved,
serialized, or committed. No historical performance, backtest, optimization,
signal evaluation, or paper-trading observation was performed.

The gate fails because the authenticated Alpha Vantage account does not expose
the premium adjusted endpoint or full raw daily history, and its compact raw
daily response has only 100 rows, below the required 200-observation depth.

## B. Alpha Vantage authenticated endpoint audit

| Required capability | Result | Sanitized evidence |
|---|---|---|
| `TIME_SERIES_DAILY_ADJUSTED` QQQ | `FAIL_PREMIUM_ENDPOINT_RESTRICTION` | HTTP 200 premium restriction; 215 response bytes |
| `TIME_SERIES_DAILY` QQQ, full | `FAIL_FULL_OUTPUTSIZE_PREMIUM_RESTRICTION` | HTTP 200 full-outputsize premium restriction; 279 response bytes |
| `TIME_SERIES_DAILY` QLD, full | `FAIL_FULL_OUTPUTSIZE_PREMIUM_RESTRICTION` | HTTP 200 full-outputsize premium restriction; 279 response bytes |
| `TIME_SERIES_DAILY` QQQ, compact | `PASS_COMPACT_ONLY` | 100 rows; fields `open`, `high`, `low`, `close`, `volume` |
| `TIME_SERIES_DAILY` QLD, compact | `PASS_COMPACT_ONLY` | 100 rows; fields `open`, `high`, `low`, `close`, `volume` |
| `SPLITS` QQQ / QLD | `PASS` | 1 / 6 rows; `effective_date`, `split_factor` |
| `DIVIDENDS` QQQ / QLD | `PASS` | 88 / 34 rows; declaration, ex-dividend, record, payment, amount |

The response messages explicitly identified premium entitlement and the free
key's 1-request-per-second / 25-requests-per-day policy. No secret-bearing URL,
header, or response body was retained.

## C. Rate-limit and publication evidence

The existing conservative demand calculation remains 74 scheduled-session
units, 16 base requests per unit, 20 with the 25% safety margin, and 1,480
requests across the conservative annual sum. Account-observable Alpha Vantage
messages reported 1 request per second and 25 requests per day. No rate-limit
headers were returned. Operational acceptance remains
`RATE_LIMIT_NOT_READY`.

No deterministic after-close publication SLA was established. No polling
deadline was invented and no publication latency observation was run. The
publication classification remains `UNRESOLVED` and the deadline remains
`PUBLICATION_DEADLINE_NOT_READY`.

## D. Massive reconciliation audit

Massive authenticated day-aggregate calls for QQQ and QLD returned HTTP 200,
response status `DELAYED`, 501 rows each, and fields `o`, `h`, `l`, `c`, `v`,
`vw`, `t`, and `n`. The requested 2000-01-01 to 2026-09-17 range yielded rows
corresponding to 2024-09-16 through 2026-09-15. No explicit plan error explained
the older-history boundary; it is recorded as an observed limitation only.
Massive remains reconciliation-only and was not promoted to authoritative
adjusted-close status.

## E. Raw snapshot reconstruction and provenance

Every authenticated response was written to an isolated temporary archive
before parsing, read back, and verified byte-identical. Endpoint-specific raw
byte lengths and SHA-256 hashes are recorded in
`docs/paper_trading_source_account_acceptance.json`; no raw archive contains a
credential and no official observation directory was written. The existing
synthetic 200-observation reconstruction control remains unchanged and passes.
No vendor revision ID was invented; a null `source_revision_id` remains valid.

## F. Source-role and boundary audit

Alpha Vantage remains the proposed authoritative source by frozen role, but the
tested account cannot support the required adjusted/full-history MA200 input.
Massive is reconciliation-only. No values were averaged or substituted, and
no strategy, cost, tax, schedule, statistic, threshold, or closed research
artifact changed. No engine, scheduler, start timestamp, official observation,
Final Freeze, or Phase 9 artifact was created.

## G. Secret-leak audit

The temporary credentials were injected only into the isolated process. The
secret scan covers tracked files, Git diff, reports, generated metadata,
acceptance output, and sanitized request metadata. No key value was printed or
persisted. Result: `SECRET_LEAK_SCAN_PASS`.

## H. Tests

The dedicated source-acceptance suite passed 21 tests. The source-acceptance
plus prospective governance suites passed 161 tests. The full pytest suite
passed 545 tests. The dedicated secret-leak test covers
tracked files, Git diff, reports, generated metadata, acceptance output, and
sanitized request metadata. This remains a pre-start source acceptance and is
not Final Freeze.

PAPER TRADING SOURCE ACCOUNT ACCEPTANCE COMPLETE — AWAITING EXTERNAL SOURCE AUDIT
