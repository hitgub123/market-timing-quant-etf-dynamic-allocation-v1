# Paper-Trading Source Freeze Readiness

**Status:** `SOURCE_NOT_READY_FOR_FINAL_FREEZE`
**Source gate:** `SOURCE_ACCEPTANCE_PENDING_OPERATIONAL_LATENCY_EVIDENCE`
**Scope:** operational capability audit only; no historical performance,
signal, or official observation was created.

## Decision

EODHD Free is the proposed authoritative source for adjusted QQQ close and raw
QQQ/QLD fields. The choice is based only on the user's free-source constraint
and authenticated field capability, not a historical strategy outcome. The
account passed the required endpoint, 200-session, corporate-action, raw-byte,
200-value reconstruction, private-storage, and rate-limit controls.

The only remaining source blocker is a PRE_START account-observable
publication-latency check on a future completed U.S. session. Consequently the
source is not ready for Final Freeze and no official observation may start.

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
| Daily after-close publication | `PENDING_OPERATIONAL_LATENCY_EVIDENCE` | Documentation says major U.S. exchanges update within 15 minutes; intended account sample required |
| Immutable vendor revision ID | `NULL_ALLOWED` | Protocol raw snapshot hash is authoritative; no vendor ID invented |
| Massive raw reconciliation | `VERIFIED_WITH_ACCOUNT` | 501 completed raw/split-adjusted sessions per symbol |
| Massive execution proxy | `NOT_OBSERVABLE_IN_PAPER_MODE` | No quote entitlement is required for the canonical 5-bps model |

## Point-in-time source snapshot

At each scheduled decision, the exact EODHD raw response used for the MA200
input must be archived before parsing. `source_raw_hash` is SHA-256 over those
exact bytes. `source_snapshot_id` is `sha256:<source_raw_hash>` or the SHA-256
of a canonical sorted manifest when several raw objects are required.

The authenticated acceptance reconstructed the exact response bytes and the
ordered final 200 `(date, adjusted_close)` values. EODHD adjusted history may
change after a later dividend; the original snapshot remains immutable and any
new response is an append-only revision record. A lost or overwritten original
snapshot invalidates the affected evidence boundary.

## Latency gate

The PRE_START latency check is not an official paper-trading observation and
must not calculate MA200 or a signal. On the next suitable completed U.S.
session it records:

1. canonical expected session date and exchange close time;
2. sanitized poll timestamps and fixed request ordinal;
3. HTTP status, safe rate headers, response byte hash, and returned last date;
4. first timestamp at which the expected completed session appears; and
5. whether availability was within the documented 15-minute boundary.

The check must stay within the accepted four-poll budget, archive each raw
response before parsing, and stop without creating an official observation.
Failure or ambiguity leaves the source gate pending or failed; it never creates
a favorable substitute deadline.

The exact one-shot procedure, archive boundary, and mechanical classifications
are frozen in `PAPER_TRADING_EODHD_PRESTART_LATENCY_RUNBOOK.md`; the sanitized
artifact contract is
`schemas/source_acceptance/eodhd_prestart_latency_evidence.schema.json`.

## Freeze checklist

Before an external Operational Freeze Audit can authorize a start, the auditor
must record:

1. a passing PRE_START publication-latency evidence artifact;
2. the exact EODHD source adapter and snapshot reconstruction tests;
3. reconciliation and disagreement handling;
4. no-secret logs and immutable archive permissions;
5. updated environment and dry-run acceptance; and
6. the later final acceptance manifest binding all approved hashes.

Until the latency evidence and external audit pass, status remains
`SOURCE_NOT_READY_FOR_FINAL_FREEZE`. This document does not create an engine,
scheduler, acceptance manifest, prospective start, or official observation.
