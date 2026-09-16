# Paper-Trading Append-Only Ledger Schema

**Status:** `PROPOSED_NOT_FROZEN`  
**Scope:** schema design only; no official rows or paper engine are created.

## 1. Shared rules

Every record has an immutable primary key, `schema_version`, `protocol_version`,
`created_at`, `code_commit`, `source`, and a `record_hash`. Foreign keys refer
to immutable IDs, never row numbers. A record is append-only: corrections are
new records in the revision/correction ledger and the original record remains
byte-identical. Official directories are not populated in this preparation
phase.

Machine timestamps are timezone-aware ISO-8601 strings with an explicit offset;
canonical storage also keeps UTC `Z`. `session_date` is a New York exchange
date (`YYYY-MM-DD`), never a Japan-local date. Prices and quantities are
positive finite decimals when present. Missing values use JSON `null` and CSV
empty fields; missing data are not zero-filled.

Monetary values are USD and canonicalized to two decimal places. Prices are
USD/share and canonicalized to eight decimal places. Weights and returns use
decimal units and twelve decimal places. Basis points use six decimal places.
NaN, infinity, negative zero, and locale-formatted numbers are rejected.

The timestamp ontology is explicit: `session_date`, `exchange_open_at`,
`exchange_close_at`, `signal_close_at`, `data_available_at`, `data_acquired_at`,
`decision_ready_at`, `order_created_at`, `order_recorded_at`,
`intended_execution_at`, `proxy_price_timestamp`, `fill_recorded_at`,
`valuation_timestamp`, and `ledger_written_at`. Every machine timestamp is
timezone-aware; a missing optional timestamp is JSON `null`, never a naive
datetime.

## 2. Canonical serialization and hash chain

JSON records use UTF-8, `ensure_ascii=false`, lexicographically sorted keys,
compact separators `(',', ':')`, and deterministic fixed-point decimal
serialization. CSV records use UTF-8, LF line endings, the schema's column
order, a single header row, `,` delimiter, double-quoted fields only when
required by RFC 4180, empty string for null, and the numeric scales above.
The raw vendor-object hash is SHA-256 over the exact bytes received before
decompression/parsing; the parsed record hash is SHA-256 over canonical JSON.

Each record stores `previous_record_hash` (or null only for the first record in
a chain) and `record_hash`. A batch manifest stores the first/last record IDs,
previous batch hash, current batch hash, source raw hashes, protocol version,
code commit, and creation timestamp. A missing predecessor, duplicate primary
key, hash mismatch, or non-append correction is a pre-start acceptance failure
and later a `PROTOCOL_INVALIDATING` incident.

## 3. Ledger relationships

```text
paper_observations 1 ──< paper_decisions 1 ──< paper_orders 1 ──< paper_fills
paper_nav           references session_date and strategy/order IDs
paper_tax           references fill/order IDs and tax lots
paper_incidents     references any affected record IDs and raw hashes
paper_data_revisions references the original immutable record and replacement
```

The schemas are machine-readable JSON Schema files under
`schemas/paper_trading/`. The files use JSON Schema 2020-12 and include
`x-units`, `x-timezone`, `x-append-only`, and `x-primary-key` metadata for the
auditor.

## 4. Ledger-specific contracts

### `paper_observations`

One row per symbol/session/schedule observation. Required fields include the
immutable observation ID, source and raw hash, QQQ raw and adjusted close,
MA200, signal/target state, schedule flags, all timestamp fields available for
the observation, revision identifier, calendar version, and provenance.
The MA200 field is derived only from 200 completed adjusted QQQ closes and is
not persisted as an official value until the source and hash checks pass.

### `paper_decisions`

One row per scheduled decision. It links to exactly one observation and stores
strategy ID, schedule, signal, previous/new target, state-change boolean,
decision-ready timestamp, close-to-next-open boundary, and code/version hash.
No decision row can point to a future close or same-day execution.

### `paper_orders`

Theoretical orders are append-only records with symbol, side, target weight,
quantity, intended execution session/timestamp, canonical fill convention,
pre-trade NAV, status, and skip reason. An order can be `CREATED`, `SKIPPED`,
or `CANCELLED_BY_INCIDENT`; it is never deleted.

### `paper_fills`

This is a simulated fill ledger, not broker execution. It stores canonical
unadjusted open reference, 5-bps model cost, simulated fill, optional market-data
proxy, proxy source/timestamp, signed/absolute slippage proxy, tracking
difference, validity, and recording timestamps. Missing proxy fields are null
with `NOT_OBSERVABLE_IN_PAPER_MODE` status.

### `paper_nav`

Daily pre-tax and tax-paid-to-date NAV, cash, holdings, cost basis, benchmark
NAV, daily returns, paired excess, drawdown, and turnover components. It links
to the relevant fill/order hashes and never creates a terminal liquidation sell.

### `paper_tax`

The frozen 20.315% simplified average-cost immediate-realized-tax semantics are
preserved. Each tax event links to the triggering fill/order, realized gain or
loss, tax paid, cumulative tax paid, and tax-ledger hash. Terminal diagnostics
are not tax events.

### `paper_incidents`

Every data, clock, source, revision, duplicate, or operational defect has an
immutable incident ID, severity from the fixed taxonomy, trigger, affected
records, raw hashes, action, resolution, and protocol-validity effect.

### `paper_data_revisions`

Corrections reference the original immutable record ID and hash, revised record
ID/hash, old/new values, discovery timestamp, vendor revision ID, affected
sessions, reconstructability, and auditor disposition. The original is never
overwritten.

## 5. Archive layout (future only)

```text
paper/
  raw/{vendor}/{YYYY}/{MM}/{DD}/
  observations/{YYYY}/{MM}/
  decisions/{YYYY}/{MM}/
  orders/{YYYY}/{MM}/
  fills/{YYYY}/{MM}/
  nav/{YYYY}/{MM}/
  tax/{YYYY}/{MM}/
  incidents/{YYYY}/{MM}/
  revisions/{YYYY}/{MM}/
  manifests/{YYYY}/{MM}/
```

The directories are intentionally ignored by Git and remain empty until a
future, separately frozen protocol starts. API keys, access tokens, cookies,
authorization headers, and secret-store exports are never archived or hashed.

## 6. Machine-readable files

The following schemas are required and supplied in this preparation commit:

`paper_observations.schema.json`, `paper_decisions.schema.json`,
`paper_orders.schema.json`, `paper_fills.schema.json`, `paper_nav.schema.json`,
`paper_tax.schema.json`, `paper_incidents.schema.json`, and
`paper_data_revisions.schema.json`.

Any example record in tests or documentation must carry
`fixture_status = SYNTHETIC_TEST_FIXTURE` and must not be copied into
`paper/observations/` or another official prospective directory.
