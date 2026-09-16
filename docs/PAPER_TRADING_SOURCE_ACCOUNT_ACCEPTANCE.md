# Paper-Trading Protocol v1 — Authoritative Source Account Acceptance

**Status:** `SOURCE_ACCEPTANCE_FAIL`
**Scope:** pre-start account/API capability acceptance only; no historical
performance, backtest, parameter selection, paper trading, engine, scheduler,
official observation, 36-month clock, final freeze, or Phase 9 artifact.

## 1. Gate outcome

The acceptance was resumed from commit
`1cec7f42a6942043a9a227349762d8e033890f2e` in one isolated process. Both
credential variables were present for that process. Their values were not
printed, logged, hashed, serialized, persisted, or written to any artifact.

Authenticated endpoint checks were performed with sanitized request metadata and
temporary raw-response archives. The account does not provide the critical
authoritative capabilities required by the frozen protocol:

- `TIME_SERIES_DAILY_ADJUSTED` for QQQ returned an HTTP 200 premium-endpoint
  restriction message;
- `TIME_SERIES_DAILY` with `outputsize=full` for QQQ and QLD returned an HTTP
  200 premium `outputsize=full` restriction message;
- compact raw daily access returned only 100 rows for each symbol, below the
  required 200-observation depth.

SPLITS and DIVIDENDS were accessible, and Massive day aggregates were
accessible for reconciliation, but those results cannot replace the frozen
authoritative adjusted-close source. The mechanically correct source gate is:

`SOURCE_ACCEPTANCE_FAIL`

No historical performance or strategy result was calculated.

## 2. Authenticated Alpha Vantage evidence

All requests used JSON responses. Exact response bytes were archived in an
isolated temporary directory before parsing, re-read, and verified byte
identical. Only hashes, lengths, sanitized parameters, field names, counts,
and sanitized vendor messages are recorded here.

| Endpoint/check | Observed result | Evidence |
|---|---|---|
| `TIME_SERIES_DAILY_ADJUSTED` QQQ, `outputsize=full` | `FAIL_PREMIUM_ENDPOINT_RESTRICTION` | HTTP 200; vendor said the endpoint is premium; no time-series rows |
| `TIME_SERIES_DAILY` QQQ, `outputsize=full` | `FAIL_FULL_OUTPUTSIZE_PREMIUM_RESTRICTION` | HTTP 200; vendor said `outputsize=full` is premium |
| `TIME_SERIES_DAILY` QLD, `outputsize=full` | `FAIL_FULL_OUTPUTSIZE_PREMIUM_RESTRICTION` | HTTP 200; same premium restriction |
| `TIME_SERIES_DAILY` QQQ, `outputsize=compact` | `PASS_COMPACT_ONLY` | 100 rows, 2026-04-23 through 2026-09-15; fields `open`, `high`, `low`, `close`, `volume` |
| `TIME_SERIES_DAILY` QLD, `outputsize=compact` | `PASS_COMPACT_ONLY` | 100 rows, 2026-04-23 through 2026-09-15; fields `open`, `high`, `low`, `close`, `volume` |
| `SPLITS` QQQ | `PASS` | 1 row; `effective_date`, `split_factor` |
| `SPLITS` QLD | `PASS` | 6 rows; `effective_date`, `split_factor` |
| `DIVIDENDS` QQQ | `PASS` | 88 rows; declaration, ex-dividend, record, payment, and amount fields |
| `DIVIDENDS` QLD | `PASS` | 34 rows; declaration, ex-dividend, record, payment, and amount fields |

The raw daily endpoint is therefore authenticated but not usable for the
required 200-observation MA window under this account. The adjusted endpoint
is not entitled at all.

## 3. Account/plan and rate-limit evidence

The vendor returned the following account-observable messages, with no secret
material retained:

- adjusted endpoint: premium plan required;
- full raw daily history: `outputsize=full` is a premium feature;
- free-key request policy: one request per second and 25 requests per day.

No rate-limit response headers were exposed. The observed limits are recorded
as evidence, not as accepted operational headroom. The existing conservative
envelope remains 16 base requests per scheduled session, 20 with its safety
margin, and 1,480 requests for the conservative annual sum. The rate-limit gate
remains `RATE_LIMIT_NOT_READY`.

## 4. Massive reconciliation evidence

Massive day aggregates were queried for QQQ and QLD with `adjusted=false` over
the requested 2000-01-01 through 2026-09-17 range. Both authenticated requests
returned HTTP 200, response status `DELAYED`, 501 rows, and fields `o`, `h`,
`l`, `c`, `v`, `vw`, `t`, and `n`. The observed rows ran from timestamps
corresponding to 2024-09-16 through 2026-09-15; the requested older range was
not returned. No explicit plan-error message identified the reason for that
history boundary, so the limitation is recorded as observed rather than
invented. Massive remains strictly
`RECONCILIATION_MARKET_DATA_SOURCE`; it is not promoted to the authoritative adjusted-close source and no quote/execution proxy was claimed.

## 5. Raw-response snapshot and reconstruction

The authenticated run archived each exact response before parsing and
reconstructed every archived byte sequence successfully. The machine-readable
artifact records the endpoint-specific SHA-256 hashes and byte lengths. The
temporary archive contained no credentials and was not placed in the official
observation directory. The pre-existing synthetic 200-value reconstruction
control also remains unchanged and passing.

No vendor revision identifier was invented. `source_revision_id = null` remains
valid when the vendor does not supply an immutable revision ID; the protocol
snapshot hash remains the provenance identifier.

## 6. Publication timing

No deterministic after-close publication SLA was established by the account
responses or public documentation. No polling deadline was invented and no
latency samples were used to select a favorable outcome. Publication remains
`UNRESOLVED` with `PUBLICATION_DEADLINE_NOT_READY`; no official observation can
start from this acceptance.

## 7. Source roles and boundaries

Alpha Vantage remains the proposed authoritative source by protocol role, but
the authenticated account failed the critical adjusted/full-history and
200-observation requirements. Massive remains reconciliation-only. No source
values were averaged, substituted, or used to improve a signal. No strategy,
cost, tax, schedule, statistic, threshold, or closed research artifact was
changed.

## 8. Secret-leak and freeze boundary

The temporary credentials were supplied only to the isolated process. They are
absent from request metadata, raw-response archives, JSON, reports, tests, and
Git diff. The secret-leak scan is required to remain
`SECRET_LEAK_SCAN_PASS`.

No engine, scheduler, official observation directory, prospective start
timestamp, acceptance manifest, Final Freeze, or Phase 9 artifact was created.

## 9. Final source gate

`SOURCE_ACCEPTANCE_FAIL`

This failure is due to account/plan capability limitations, not a strategy or
historical-performance result. A later run may re-audit the source only after
an account with the required adjusted/full-history entitlement and acceptable
operational limits is supplied.
