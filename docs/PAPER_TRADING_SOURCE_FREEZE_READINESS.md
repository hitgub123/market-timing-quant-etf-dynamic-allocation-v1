# Paper-Trading Source Freeze Readiness

**Status:** `SOURCE_NOT_READY_FOR_FINAL_FREEZE`
**Source gate:** `SOURCE_ACCEPTANCE_PENDING_OPERATIONAL_LATENCY_EVIDENCE`
**Scope:** operational capability audit only; no historical performance,
signal, or official observation was created.

## Decision

EODHD Free passed the required endpoint, 200-session, corporate-action,
raw-byte, 200-value reconstruction, private-storage, and rate-limit controls.
It then failed the PRE_START account-observable publication-latency gate for
the 2026-10-01 U.S. session: the expected QQQ.US row was absent at close and
at +5, +10, and +15 minutes. Consequently EODHD Free is not accepted as the
authoritative source, the source is not ready for Final Freeze, and no official
observation may start.

Tiingo End-of-Day Free is the next documentation-qualified zero-cost candidate.
Its public materials describe raw and adjusted daily prices, dividends, splits,
free individual internal use, explicit request limits, and evening update
times. Authenticated QQQ and QLD capability now passes, but the future-session
publication observation has not run, so no source is promoted and Final Freeze
remains blocked.

Massive Basic Free remains reconciliation-only. Its split-only adjustment
cannot replace the authoritative EODHD adjusted close. The historical Alpha
Vantage free-account failure remains in Git history and the acceptance artifact
but is no longer an operational dependency.

## Capability register

| Capability | Classification | Evidence or remaining condition |
|---|---|---|
| EODHD Free account/plan | `VERIFIED_WITH_ACCOUNT` | Authenticated free mode/type and one-year warning |
| EODHD QQQ.US/QLD.US raw OHLCV | `VERIFIED_WITH_ACCOUNT` | 251 complete unique sessions per symbol |
| EODHD QQQ.US adjusted close | `VERIFIED_WITH_ACCOUNT` | 251 non-null split-and-dividend-adjusted values |
| EODHD splits/dividends | `VERIFIED_WITH_ACCOUNT` | Both per-ticker endpoint families authenticated |
| Minimum 200-value reconstruction | `VERIFIED_WITH_ACCOUNT` | Ordered final 200 QQQ adjusted closes rebuilt exactly from archived bytes |
| Daily/minute limits | `VERIFIED_WITH_ACCOUNT` | 20 calls/day and 1,200 requests/minute observed; 18-call envelope passes |
| Private data storage | `VERIFIED_BY_PUBLIC_TERMS` | Non-professional private non-commercial storage and analysis permitted |
| Daily after-close publication | `FAIL_NOT_AVAILABLE_BY_DOCUMENTED_DEADLINE` | Four HTTP-200 responses through +15 minutes contained no expected-session row |
| Immutable vendor revision ID | `NULL_ALLOWED` | Protocol raw snapshot hash is authoritative; no vendor ID invented |
| Massive raw reconciliation | `VERIFIED_WITH_ACCOUNT` | 501 completed raw/split-adjusted sessions per symbol |
| Massive execution proxy | `NOT_OBSERVABLE_IN_PAPER_MODE` | No quote entitlement is required for the canonical 5-bps model |
| Tiingo Free candidate | `VERIFIED_WITH_ACCOUNT_PENDING_LATENCY` | QQQ/QLD each returned 438 complete unique sessions with required raw/adjusted fields; future-session publication observation remains |

## Point-in-time source snapshot

At each scheduled decision, the exact accepted-authority raw response used for the MA200
input must be archived before parsing. `source_raw_hash` is SHA-256 over those
exact bytes. `source_snapshot_id` is `sha256:<source_raw_hash>` or the SHA-256
of a canonical sorted manifest when several raw objects are required.

The Tiingo authenticated acceptance reconstructed four exact response bodies
and verified 438 raw/adjusted daily rows for each ETF. Vendor-adjusted history
may later be corrected; the original snapshot remains immutable and any new
response is an append-only revision record. A lost or overwritten original
snapshot invalidates the affected evidence boundary.
The accepted adapter must deterministically reconstruct the ordered final 200
`(session_date, adjClose)` values from those exact bytes before any decision.

## Latency gate

The PRE_START latency check is not an official paper-trading observation and
must not calculate MA200 or a signal. On the next suitable completed U.S.
session it records:

1. canonical expected session date and exchange close time;
2. sanitized poll timestamps and fixed request ordinal;
3. HTTP status, safe rate headers, response byte hash, and returned last date;
4. first timestamp at which the expected completed session appears; and
5. whether availability was within the prospectively frozen Tiingo publication
   boundary derived from the documented 5:30 p.m. update and 8:00 p.m.
   correction window.

The check must stay within the accepted four-poll budget, archive each raw
response before parsing, and stop without creating an official observation.
Failure or ambiguity leaves the source gate pending or failed; it never creates
a favorable substitute deadline.

The exact Tiingo one-shot procedure, archive boundary, poll schedule, and
mechanical classifications must be frozen before the selected future U.S.
session. The failed EODHD runbook and evidence remain immutable historical
records and are not reused.

## Freeze checklist

Before an external Operational Freeze Audit can authorize a start, the auditor
must record:

1. a passing PRE_START publication-latency evidence artifact;
2. the exact Tiingo source adapter and snapshot reconstruction tests;
3. reconciliation and disagreement handling;
4. no-secret logs and immutable archive permissions;
5. updated environment and dry-run acceptance; and
6. the later final acceptance manifest binding all approved hashes.

While Tiingo latency evidence is pending, status remains
`SOURCE_NOT_READY_FOR_FINAL_FREEZE`. This document does not create an engine,
scheduler, acceptance manifest, prospective start, or official observation.
