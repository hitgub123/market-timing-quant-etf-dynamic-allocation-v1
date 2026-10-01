# Paper Trading Protocol v1 — EODHD Free Source Account Acceptance Audit

**Scope:** authoritative-source account/API capability acceptance
**Resume commit:** `e94326ae3f4b765bcf895de4684328ee756e6bd1`
**Date:** 2026-10-02

## A. Exact source-gate outcome

`SOURCE_ACCEPTANCE_FAIL`

The EODHD Free account passed authenticated plan, endpoint, 200-observation,
field, corporate-action, raw-byte reconstruction, 200-value reconstruction,
rate-limit, and private-storage checks. It failed the frozen publication-
latency gate because the 2026-10-01 QQQ.US row was unavailable at all four
polls through the documented +15-minute deadline.

The credential remained external to the repository and was read only in
isolated processes. No historical performance, backtest, signal, optimization,
paper-trading row, engine, scheduler, start timestamp, Final Freeze, or Phase 9
artifact was created.

## B. Authenticated account and endpoints

The account endpoint reported subscription mode/type `free`, 20 calls per day,
and a 1,200-request minute header. QQQ.US and QLD.US each returned 251 unique
completed sessions from 2025-09-26 through 2026-09-25. Required raw OHLCV and
`adjusted_close` fields were non-null and session dates contained no duplicates.

Authenticated per-ticker corporate-action responses returned five dividends
for each ETF, no QQQ split, and one QLD split dated 2025-11-20. The free plan's
one-year history restriction was explicitly returned and is recorded rather
than inferred.

## C. Semantics and source transition

Official EODHD documentation defines raw OHLC as as-traded and
`adjusted_close` as split-and-dividend adjusted. This matches the required
field semantics, but adjusted values are vendor-specific and may be recomputed
after new dividends. The protocol therefore freezes the exact point-in-time
EODHD bytes for each future decision and never combines adjusted values across
vendors.

EODHD Free becomes the proposed authoritative source because the user imposed
a free-only operational constraint and it satisfies the required fields. No
historical result was used. Massive Basic Free remains reconciliation-only.
The prior Alpha Vantage `SOURCE_ACCEPTANCE_FAIL` is preserved as historical
evidence and Alpha is removed as a prospective operational dependency.

## D. Rate-limit audit

The EODHD request shape combines raw and adjusted fields. The conservative
budget is 14 base calls and 18 after the fixed 25% margin, including four polls,
two retries, authoritative QQQ/QLD responses, four corporate-action responses,
and two reconciliation responses. One acquisition is shared across frequency
decisions on the same date. The 18-call budget is within the authenticated
20-call daily limit, leaving two calls of headroom.

## E. Reconstruction and revisions

Seven authenticated endpoint responses were archived before parsing and
reconstructed byte-identically. A separate authenticated QQQ control rebuilt
the ordered final 200 adjusted closes exactly from the archived bytes. The
window ran from 2025-12-09 through 2026-09-25. No MA, signal, or return was
calculated.

No immutable vendor revision identifier was observed. The protocol-owned raw
SHA-256 remains the snapshot identifier, `source_revision_id` may remain null,
and later changes require append-only revision incidents.

## F. Publication and remaining blocker

Official documentation states that major U.S. exchanges are updated within 15
minutes after close. The exact account was observed for the future 2026-10-01
session. Requests began at close, +5, +10, and +15 minutes; all returned HTTP
200, but each body was an empty two-byte JSON array and the expected session
never appeared. The mechanical result is
`FAIL_NOT_AVAILABLE_BY_DOCUMENTED_DEADLINE`. The source is not ready for Final
Freeze.

## G. Licensing and secrets

Official terms allow private non-commercial storage, manipulation, and analysis
by a non-professional user and prohibit redistribution. The secret scan covers
tracked files, Git diff, reports, generated metadata, exception output, and
sanitized request metadata. No credential value or secret-bearing URL was
retained.

## H. Test result

The dedicated PRE_START observer suite passed **21 tests**, and the dedicated
source-account acceptance suite passed **23 tests**. The combined source,
remediation, prospective-governance, and operational-contract controls passed
**179 tests**. The full pytest suite passed **595 tests**. The staged
secret-leak control passed after scanning tracked files, Git diff, reports,
generated metadata, and sanitized request metadata. The source remains
pre-start and no acceptance manifest is created.

## I. PRE_START observer result

The one-shot observer started at `2026-10-01T19:59:55.543893Z`, before the
exchange close. It used the frozen offsets `0`, `300`, `600`, and `900` seconds
and made exactly four requests. Every raw response was archived before parsing,
re-read byte-identically, and retained outside Git with mode 600 under a
mode-700 directory. The sanitized evidence is
`reports/eodhd_prestart_latency_evidence.json`. No MA, signal, performance,
official observation, engine, or scheduler was created. The result cannot be
changed by extending the observed deadline or rerunning the same session.
The sanitized evidence SHA-256 is
`c23839b3e3a8624eeacb4bb210d45f98b92819fa4f6c188fdcda20b6b1c5dab4`.

`SOURCE_ACCEPTANCE_FAIL`

PAPER TRADING SOURCE ACCOUNT ACCEPTANCE COMPLETE — AWAITING EXTERNAL SOURCE AUDIT
