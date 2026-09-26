# Paper-Trading Data-Source Specification

**Status:** `PROPOSED_NOT_FROZEN`  
**Purpose:** operational freeze preparation only; no official prospective
observations are collected by this document.

## 1. Decision boundary

The source roles below are selected for prospective operational fitness, not
for any historical strategy result. EODHD Free replaced the failed Alpha
Vantage free-account candidate on 2026-09-26 solely because the user required
a zero-cost source and authenticated EODHD supplied the frozen required fields.
No historical performance was inspected.

| Role | Proposed source | Role boundary |
|---|---|---|
| `AUTHORITATIVE_MARKET_DATA_SOURCE` | EODHD Free `/api/eod`, `/api/splits`, and `/api/div` for QQQ.US and QLD.US | Drives the adjusted QQQ close used by MA200 and supplies raw daily OHLCV, adjusted close, split, and dividend fields. The daily endpoint has a session date but not a tick-level exchange event timestamp; the calendar supplies the event-time boundary. Formal acceptance remains pending PRE_START latency evidence. |
| `RECONCILIATION_MARKET_DATA_SOURCE` | Massive (formerly Polygon.io) U.S. Stocks REST/flat-file products | Independently reconciles raw daily OHLC, UTC timestamps, symbols, and, if entitled, quote/trade evidence. It never silently replaces an authoritative observation. |
| `EXECUTION_PROXY_SOURCE` | Massive U.S. Stocks SIP quotes, only when the account entitlement and timestamp/side fields are verified | Optional market-data proxy for `P_proxy_o`; not a broker fill and not part of the canonical economic model. If entitlement or executable-side semantics are not verified, status is `UNVERIFIED_CAPABILITY` and the metric is `NOT_OBSERVABLE_IN_PAPER_MODE`. |
| `CANONICAL_SESSION_CALENDAR` | `pandas_market_calendars` `NASDAQ` schedule, pinned at the repository dependency version, reconciled to Nasdaq and NYSE published calendars | Supplies eligible QQQ/QLD U.S. sessions, regular open/close, early closes, and the next-eligible-session function. It is an explicit dependency, never inferred from observed price rows. |

EODHD's public documentation states that its EOD endpoint returns as-traded
OHLCV and a split-and-dividend-adjusted close. The authenticated Free account
returned 251 completed QQQ.US and QLD.US sessions plus per-ticker split and
dividend endpoints. Its terms permit private non-commercial storage and
analysis. See the [EOD endpoint](https://eodhd.com/financial-apis/api-for-historical-data-and-volumes),
[API limits](https://eodhd.com/financial-apis/api-limits), and
[terms](https://eodhd.com/financial-apis/terms-conditions).

Massive's public Stocks overview documents U.S. trade/quote coverage and UTC
timestamps. Its day-aggregate flat files provide daily OHLCV and its quote
files provide top-of-book quotes with nanosecond timestamps. Massive documents
that its historical adjustment is split-only, not dividend-adjusted; therefore
it is not used as the authoritative adjusted-close source. See the [Stocks
overview](https://polygon.io/docs/rest/stocks/overview), [day aggregate
documentation](https://polygon.io/docs/flat-files/stocks/day-aggregates/2023/08),
[quote flat-file documentation](https://polygon.io/docs/flat-files/stocks/quotes/2004/09),
and [adjustment policy](https://polygon.io/knowledge-base/article/is-polygons-stock-data-adjusted-for-splits-or-dividends).

NYSE publishes core-session and auction times and holiday/early-close
calendars. Nasdaq publishes its U.S. equities holiday schedule. See the
[NYSE hours and calendars](https://www.nyse.com/trade/hours-calendars),
[NYSE trading information](https://www.nyse.com/trade/trading-information),
and [Nasdaq trading calendar](https://nasdaqtrader.com/Trader.aspx?id=Calendar).

## 2. Required fields and source priority

Proposed request products are explicit: EODHD uses
`/api/eod/{QQQ.US|QLD.US}`, `/api/splits/{QQQ.US|QLD.US}`, and
`/api/div/{QQQ.US|QLD.US}` with JSON output; Massive uses the day-aggregate
product `/v2/aggs/ticker/{ticker}/range/1/day/{from}/{to}` with
`adjusted=false`, reference ticker lookup `/v3/reference/tickers`, and the
`us_stocks_sip/quotes_v1` quote product when entitled. Request parameters are
stored after removing the API key. Endpoint access, history, rate limits, and
terms remain account-specific pre-freeze acceptance items.

For each symbol (`QQQ`, `QLD`) the authoritative record must contain:

- vendor symbol, asset identifier, source request/response identifier;
- session date, raw open/high/low/close/volume;
- adjusted close, split coefficient, dividend amount, and source revision ID;
- acquisition timestamp, source-provided timestamp if present, timezone/offset;
- endpoint, request parameters excluding secrets, HTTP status, response bytes;
- raw-object SHA-256 and the local immutable archive path.

The reconciliation record must contain the same raw OHLC fields and a source
timestamp or an explicit `UNVERIFIED_CAPABILITY` marker. Comparisons use
unadjusted raw OHLC first; adjusted-close comparison is performed only after
documented corporate-action factors are aligned. No vendor values are averaged.

Priority is deterministic:

1. calendar eligibility comes from the canonical calendar;
2. signal adjusted close comes from the authoritative source;
3. raw open/close and source integrity are reconciled against Massive;
4. unresolved disagreement creates an incident and prevents the affected
   record from becoming official evidence;
5. a backup value may diagnose or support reconstruction, but cannot silently
   replace an authoritative value after seeing which is favorable. It cannot
   silently replace the authoritative observation. It cannot silently replace
   the authoritative observation under any condition.

## 3. Timestamp and adjustment semantics

EODHD daily rows are keyed by exchange session date. The protocol
assigns `session_date` using the canonical New York calendar and derives
`exchange_open_at`/`exchange_close_at` from that calendar. A vendor response
without an event timestamp is not represented as if it had one; its
`source_timestamp` remains null and `timestamp_capability` is
`UNVERIFIED_CAPABILITY` for intraday use.

Massive timestamps are stored as UTC and converted to `America/New_York` only
for session alignment. The original UTC integer is retained. Japan local time
never determines a U.S. session date.

The MA200 input is exactly the authoritative `QQQ.adjusted_close` field. Raw
execution/reference prices remain unadjusted official session prices. Splits,
dividends, and fund distributions are recorded as source corporate-action
events; they are not silently back-applied to an already frozen decision.

## 4. Point-in-time adjusted-close and revisions

The initial observation stores both the source's raw payload hash and the
parsed fields. At every decision the exact raw response used to construct the
QQQ MA200 window is archived before parsing. The observation's
`source_snapshot_id` is the protocol-owned immutable `sha256:<raw_hash>` (or
the SHA-256 of a sorted manifest of all raw hashes used for that window). A
later change in an adjusted value or corporate-action event
creates `DATA_REVISION_INCIDENT` and a row in `paper_data_revisions` containing
the original value, revised value, original raw hash, revised raw hash,
original/revised raw hashes, discovery
timestamp, affected sessions, and reconstructability assessment.

- **Informational:** a revision concerns a future/unobserved session and does
  not alter any already accepted record.
- **Recoverable incident:** the original raw payload, decision, and hash chain
  remain reconstructable; the correction is appended and the original remains
  immutable.
- **`PROTOCOL_INVALID`:** the original decision cannot be reconstructed, a
  record was silently overwritten, or a revision changes a decision without an
  append-only correction and audit disposition.
The original record is never overwritten.

QLD distributions are retained in the authoritative corporate-action fields
and flow into the frozen average-cost/tax policy only through an explicitly
audited accounting transformation. No distribution is treated as an
unlogged price change.

If EODHD supplies no immutable vendor revision identifier, the field
`source_revision_id` remains `null`; no vendor ID is invented. The protocol
snapshot hash is authoritative for provenance and permits an auditor to
reconstruct the exact 200 adjusted closes, raw hashes, MA200, and signal that
were available at decision time. A vendor revision can therefore create an
append-only correction without retroactively changing the official decision.

## 5. Publication, acquisition, and stale-data semantics

`data_available_at` is the vendor publication/availability time when the
vendor supplies one; `data_acquired_at` is the local retrieval time. Neither
is the exchange event time. A valid completed-session close acquired 16 minutes
after the exchange close is not stale merely because 15 minutes elapsed.

An observation is mechanically `STALE` only when one of these conditions holds:

1. its vendor session key is not exactly the expected calendar `session_date`;
2. the payload is a duplicate of a prior session while the expected session is
   still absent; or
3. a predeclared, vendor-compatible publication deadline has expired and the
   expected session remains unavailable.

Publication delay and acquisition delay are recorded separately and do not by
themselves invalidate a close. EODHD documents that major U.S. exchanges are
updated within 15 minutes after close, but the intended Free account has not
yet completed the required PRE_START latency observation. The deadline is
therefore `PENDING_PRE_START_ACCOUNT_LATENCY_OBSERVATION` and is not freeze-ready. Any
future change to that grace is classified `OPERATIONAL_SOURCE_COMPATIBILITY_REMEDIATION`,
not statistical or economic redesign. The
proposed deterministic replacement is a vendor-compatible deadline recorded
in the source acceptance manifest (exchange close plus the documented vendor
publication SLA, with a fixed polling cutoff); until that SLA is verified,
the affected record is held without a signal and receives
`STALE_SEMANTICS_UNVERIFIED`. No forward-fill, interpolation, or favorable
source substitution is permitted.

## 6. Fail-closed and disagreement policy

| Condition | Deterministic action |
|---|---|
| scheduled close missing | `WAIT`; if not recovered by the stale deadline, `INCIDENT_AND_CONTINUE` with no signal |
| scheduled close has wrong session/duplicate prior session | `INCIDENT_AND_CONTINUE`; no forward-fill or signal |
| next open missing/delayed | `WAIT`; then `SKIP` the intended execution and record the reason |
| non-positive/invalid price | `PROTOCOL_INVALID` for a malformed authoritative record, otherwise `SKIP` with incident before official use |
| duplicate observation/order | `INCIDENT_AND_RECONSTRUCT`; duplicate immutable ID never creates a second economic event |
| source disagreement within documented corporate-action exception | `INCIDENT_AND_RECONSTRUCT`; preserve both raw payloads |
| unresolved source disagreement | `PROTOCOL_INVALID` for the affected evidence boundary |
| partial or halted session | `INCIDENT_AND_CONTINUE`; no synthetic price |
| early close | `INCIDENT_AND_CONTINUE` only if the calendar marks it; use that day's official close and next eligible open |
| unscheduled closure/vendor outage | `WAIT`, then `INCIDENT_AND_CONTINUE`; no backdated fill |
| corporate-action ambiguity | `INCIDENT_AND_RECONSTRUCT`; no signal until factors are resolved |
| timestamp ambiguity | `SKIP` the affected record; unresolved boundary ambiguity is `PROTOCOL_INVALID` |
| source capability or publication SLA unverified | hold the affected boundary; `SOURCE_CAPABILITY_UNVERIFIED` or `STALE_SEMANTICS_UNVERIFIED` |
| revision after decision | append `DATA_REVISION_INCIDENT`; reconstruct or invalidate, never overwrite |
| execution proxy unavailable | record `NOT_OBSERVABLE_IN_PAPER_MODE`; canonical 5-bps model path is unchanged |

No operator may choose a price because it improves return, and no missing value
may be filled by interpolation, midpoint, last-known value, or a favorable
synthetic price.

## 7. Capability verification register

| Capability | Status | Evidence/acceptance condition |
|---|---|---|
| EODHD adjusted QQQ close | `VERIFIED_WITH_ACCOUNT` | Authenticated Free EOD response returned 251 non-null split-and-dividend-adjusted closes. |
| EODHD raw QQQ/QLD OHLCV | `VERIFIED_WITH_ACCOUNT` | Authenticated Free EOD responses returned 251 complete raw rows per symbol. |
| EODHD splits/dividends | `VERIFIED_WITH_ACCOUNT` | Authenticated per-ticker endpoints returned typed event fields. |
| EODHD daily event timestamp | `UNVERIFIED_CAPABILITY` | Daily response is date-keyed; calendar-derived event time is used instead. |
| EODHD historical revision guarantees | `COMPENSATING_CONTROL_VERIFIED` | Adjusted history may be recomputed; exact raw snapshots and the correction ledger preserve point-in-time decisions. |
| EODHD after-close publication SLA | `PENDING_OPERATIONAL_LATENCY_EVIDENCE` | Documentation says major U.S. exchanges update within 15 minutes; account observation is still required. |
| EODHD response/request revision identifier | `NULL_ALLOWED` | No immutable vendor ID is required; protocol snapshot hash is authoritative. |
| Massive raw daily OHLCV | `VERIFIED_BY_PUBLIC_DOCS` | Day-aggregate documentation and flat-file archive. |
| Massive UTC timestamps | `VERIFIED_BY_PUBLIC_DOCS` | Stocks overview documents UTC timestamp semantics. |
| Massive split adjustment | `VERIFIED_BY_PUBLIC_DOCS` | Adjustment policy documents split adjustment and `adjusted=false`. |
| Massive dividend-adjusted close | `UNVERIFIED_CAPABILITY` | Public adjustment policy says dividend adjustment is not currently provided. |
| Massive NBBO quote timestamps | `VERIFIED_BY_PUBLIC_DOCS` | Quote flat-file documentation; plan entitlement remains an operational prerequisite. |
| Opening-auction executable price | `UNVERIFIED_CAPABILITY` | A quote stream is not asserted to be an executable auction fill. |
| Personal-research licensing/rate limits | `VERIFIED_WITH_ACCOUNT` | Terms allow private non-commercial storage/analysis; account reported 20 calls/day and the 18-call envelope passed. |
| QQQ and QLD symbol support | `VERIFIED_WITH_ACCOUNT` | Authenticated EODHD and Massive responses returned both ETFs. |

Every `UNVERIFIED_CAPABILITY` or `VERIFIED_WITH_ACCOUNT_DEPENDENCY` blocks a claim that depends on it until the intended account/plan is tested. It does not
silently become a verified feature at implementation time.

## 8. Raw snapshot policy

Raw vendor bytes are archived exactly as received before parsing. Each request
stores endpoint, method, sanitized parameters, response headers that are safe
to retain, retrieval timestamp, vendor revision identifier, compression type,
and SHA-256. Secrets and authorization headers are excluded from both files
and manifests. The proposed directory layout and canonicalization rules are in
`PAPER_TRADING_LEDGER_SCHEMA.md` and
`PAPER_TRADING_ACCEPTANCE_MANIFEST_SPEC.md`.

This source decision is operational preparation only. All rows in the companion
CSV remain `PROPOSED_NOT_FROZEN`; an external Operational Freeze Audit must
approve the vendor account, plan, terms, exact endpoint versions, and source
acceptance hashes before any official prospective observation.
