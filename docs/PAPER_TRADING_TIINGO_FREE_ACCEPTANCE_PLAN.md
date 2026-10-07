# Tiingo Free Source-Account Acceptance Plan

**Status:** `SOURCE_ACCEPTANCE_PENDING_OPERATIONAL_LATENCY_EVIDENCE` — frozen poll-budget conflict
**Classification:** performance-blind source remediation preparation only

## Boundary

Tiingo Free entered as a candidate for authenticated acceptance. It is not
the authoritative source, does not repair the failed EODHD observation, and
does not authorize Final Freeze, an engine, scheduler, official observation,
prospective start, acceptance manifest, or Phase 9.

No historical performance, MA200 value, signal, trade, return, or source
ranking by investment outcome may be calculated during acceptance.

## Why this candidate can enter acceptance

Tiingo's official End-of-Day product page documents a free individual plan,
60+ years of history, raw and adjusted prices, dividends, splits, 50 requests
per hour, 1,000 requests per day, and 1 GB per month. It documents an equity
and ETF update frequency of 5:30 p.m. U.S. Eastern time with corrections
through 8:00 p.m. Eastern time.

The official EOD API documentation exposes raw `open`, `high`, `low`, `close`,
and `volume`, adjusted `adjOpen`, `adjHigh`, `adjLow`, `adjClose`, and
`adjVolume`, plus `divCash` and `splitFactor`. It states that the adjustment
method follows CRSP-style calculations. These documented semantics are
compatible enough to justify an account test; they are not authenticated
evidence and do not yet pass the source gate.

Official references:

- `https://www.tiingo.com/products/end-of-day-stock-price-data`
- `https://www.tiingo.com/documentation/end-of-day`

## Credential boundary

The acceptance process reads only `TIINGO_API_KEY` from the execution-process
environment. The value must never be printed, logged, hashed, serialized,
placed in a URL, written to the repository, or committed. Requests use an
authorization header inside the isolated process; sanitized metadata records
only the method, endpoint path, non-secret parameters, and allow-listed
response headers.

The variable was present in the isolated 2026-10-02 acceptance process. Its
value was not printed or retained.

## Authenticated acceptance checks

Once the credential is available, one isolated acceptance must verify:

1. QQQ and QLD metadata access and supported asset semantics;
2. QQQ and QLD daily price access with at least 200 complete unique sessions;
3. raw OHLCV plus `adjClose`, `divCash`, and `splitFactor` field availability;
4. no null, duplicate, non-positive, or invalid OHLC records in required data;
5. exact raw response bytes archived before parsing and reconstructed by
   SHA-256;
6. account-observable restriction, rate-limit, and error messages;
7. free-plan/internal-use terms and operational request-budget compatibility;
8. absence of credentials and authorization material from every artifact; and
9. no strategy, signal, performance, official observation, or prospective
   start side effect.

Cross-vendor numerical identity is not required and must not be optimized.
Tiingo values cannot be spliced with EODHD, Alpha Vantage, or Massive values.

## Publication acceptance

The documented publication controls are 5:30 p.m. `America/New_York` for the
normal equity/ETF update and 8:00 p.m. for the end of the documented correction
window. A separate PRE_START observation must be fixed before a future U.S.
session and must record the first availability of that exact session without
calculating a signal.

The account acceptance must not use the failed EODHD session as a Tiingo
latency sample. Poll times, maximum requests, and the mechanical deadline must
be frozen before the chosen future session. Failure cannot be converted to a
pass by extending the deadline after observing the response.

## Gate transitions

- Missing credential: `ACCOUNT_CREDENTIALS_NOT_AVAILABLE`
- Authenticated capability defect: `SOURCE_ACCEPTANCE_FAIL`
- Capability pass but future latency not yet observed:
  `SOURCE_ACCEPTANCE_PENDING_OPERATIONAL_LATENCY_EVIDENCE`
- Capability and prospectively frozen latency controls pass:
  `SOURCE_ACCEPTANCE_PASS`, still awaiting external source audit

No result from this plan creates Final Freeze or starts prospective evidence.

## Authenticated result

The isolated account run returned HTTP 200 for QQQ and QLD metadata and price
endpoints. Each price series contained 438 complete unique sessions from
2025-01-02 through 2026-10-01 with every required raw and adjusted field,
`divCash`, and `splitFactor`. Four raw bodies were archived before parsing and
reconstructed byte-identically. The sanitized evidence is
`reports/tiingo_free_account_acceptance.json`.

Account capability passed. The separately required 2026-10-06 future-session
publication observation was frozen before that session opened. QQQ and QLD
were absent at the 16:00 New York close poll and both available by the fixed
17:30 poll; both remained available at the 18:00, 19:00, and 20:00 polls.
All ten raw responses were archived privately and reconstructed exactly.
The original process stopped before any poll and was safely resumed before
the first fixed poll; the schedule and deadline were not changed. See
`reports/tiingo_prestart_latency_evidence.json` and
`reports/paper_trading_tiingo_free_account_acceptance_audit.md`.

However, the pre-existing source-freeze readiness document requires an
accepted four-poll budget, while this Tiingo-specific plan did not explicitly
supersede it and the observed run used five poll times. It also called for
returned last date and safe rate headers, which the publication observer did
not place in the sanitized record. These cannot be retroactively cured by
renaming polls or inventing headers. The mechanical account gate remains:

`SOURCE_ACCEPTANCE_PENDING_OPERATIONAL_LATENCY_EVIDENCE`

This does not promote Tiingo to authoritative source or authorize Final Freeze,
an engine, scheduler, official prospective observation, or Phase 9. External
source audit remains required. Exact publication time is not known; only the
frozen-poll availability interval is claimed.
