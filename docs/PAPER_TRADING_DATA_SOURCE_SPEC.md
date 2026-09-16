# Paper-Trading Data-Source Specification

**Status:** `PROPOSED_NOT_FROZEN`  
**Purpose:** operational freeze preparation only; no official prospective
observations are collected by this document.

## 1. Decision boundary

The source roles below are selected for prospective operational fitness, not
for any historical strategy result. The selection was reviewed on 2026-09-16
against the vendors' public documentation. Prices from this review are not
used and no historical performance was inspected.

| Role | Proposed source | Role boundary |
|---|---|---|
| `AUTHORITATIVE_MARKET_DATA_SOURCE` | Alpha Vantage `TIME_SERIES_DAILY_ADJUSTED` plus `TIME_SERIES_DAILY`, `SPLITS`, and `DIVIDENDS` for QQQ and QLD | Drives the adjusted QQQ close used by MA200 and supplies raw daily OHLC, adjusted close, split, and dividend fields. The daily endpoint has a session date but not a tick-level exchange event timestamp; the calendar supplies the event-time boundary. |
| `RECONCILIATION_MARKET_DATA_SOURCE` | Massive (formerly Polygon.io) U.S. Stocks REST/flat-file products | Independently reconciles raw daily OHLC, UTC timestamps, symbols, and, if entitled, quote/trade evidence. It never silently replaces an authoritative observation. |
| `EXECUTION_PROXY_SOURCE` | Massive U.S. Stocks SIP quotes, only when the account entitlement and timestamp/side fields are verified | Optional market-data proxy for `P_proxy_o`; not a broker fill and not part of the canonical economic model. If entitlement or executable-side semantics are not verified, status is `UNVERIFIED_CAPABILITY` and the metric is `NOT_OBSERVABLE_IN_PAPER_MODE`. |
| `CANONICAL_SESSION_CALENDAR` | `pandas_market_calendars` `NASDAQ` schedule, pinned at the repository dependency version, reconciled to Nasdaq and NYSE published calendars | Supplies eligible QQQ/QLD U.S. sessions, regular open/close, early closes, and the next-eligible-session function. It is an explicit dependency, never inferred from observed price rows. |

Alpha Vantage's public documentation states that its daily adjusted endpoint
returns raw OHLCV, adjusted close, and historical split/dividend events, and
that raw daily data are available through the separate daily endpoint. The
documentation also states that the adjusted endpoint is a premium product and
supports JSON or CSV output. See the [Alpha Vantage API
documentation](https://www.alphavantage.co/documentation/).

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

Proposed request products are explicit: Alpha Vantage uses
`function=TIME_SERIES_DAILY_ADJUSTED&symbol={QQQ|QLD}&outputsize=full` plus
`TIME_SERIES_DAILY`, `SPLITS`, and `DIVIDENDS`; Massive uses the day-aggregate
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

Alpha Vantage daily rows are keyed by exchange session date. The protocol
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

## 4. Corporate actions and revisions

The initial observation stores both the source's raw payload hash and the
parsed fields. A later change in an adjusted value or corporate-action event
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

## 5. Fail-closed and disagreement policy

| Condition | Deterministic action |
|---|---|
| scheduled close missing | `WAIT`; if not recovered by the stale deadline, `INCIDENT_AND_CONTINUE` with no signal |
| scheduled close stale | `INCIDENT_AND_CONTINUE`; no forward-fill or signal |
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
| revision after decision | append `DATA_REVISION_INCIDENT`; reconstruct or invalidate, never overwrite |
| execution proxy unavailable | record `NOT_OBSERVABLE_IN_PAPER_MODE`; canonical 5-bps model path is unchanged |

No operator may choose a price because it improves return, and no missing value
may be filled by interpolation, midpoint, last-known value, or a favorable
synthetic price.

## 6. Capability verification register

| Capability | Status | Evidence/acceptance condition |
|---|---|---|
| Alpha Vantage adjusted QQQ close | `VERIFIED_BY_PUBLIC_DOCS` | Daily adjusted endpoint documents adjusted close and split/dividend events. |
| Alpha Vantage raw QQQ/QLD OHLC | `VERIFIED_BY_PUBLIC_DOCS` | Separate daily endpoint documents raw OHLCV. |
| Alpha Vantage daily event timestamp | `UNVERIFIED_CAPABILITY` | Daily response is date-keyed; calendar-derived event time is used instead. |
| Alpha Vantage historical revision guarantees | `UNVERIFIED_CAPABILITY` | No immutable revision SLA is claimed; raw snapshots and correction ledger compensate. |
| Massive raw daily OHLCV | `VERIFIED_BY_PUBLIC_DOCS` | Day-aggregate documentation and flat-file archive. |
| Massive UTC timestamps | `VERIFIED_BY_PUBLIC_DOCS` | Stocks overview documents UTC timestamp semantics. |
| Massive split adjustment | `VERIFIED_BY_PUBLIC_DOCS` | Adjustment policy documents split adjustment and `adjusted=false`. |
| Massive dividend-adjusted close | `UNVERIFIED_CAPABILITY` | Public adjustment policy says dividend adjustment is not currently provided. |
| Massive NBBO quote timestamps | `VERIFIED_BY_PUBLIC_DOCS` | Quote flat-file documentation; plan entitlement remains an operational prerequisite. |
| Opening-auction executable price | `UNVERIFIED_CAPABILITY` | A quote stream is not asserted to be an executable auction fill. |
| Personal-research licensing/rate limits | `UNVERIFIED_CAPABILITY` | Account-specific terms and plan limits require acceptance before freeze. |
| QQQ and QLD symbol support | `VERIFIED_BY_PUBLIC_DOCS` | Both vendors document ETF/ticker query interfaces; symbol-level acceptance remains a pre-freeze check. |

Every `UNVERIFIED_CAPABILITY` blocks a claim that depends on it. It does not
silently become a verified feature at implementation time.

## 7. Raw snapshot policy

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
