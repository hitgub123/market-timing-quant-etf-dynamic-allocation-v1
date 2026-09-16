# Paper-Trading Append-Only Ledger Schema

**Status:** `PROPOSED_NOT_FROZEN`  
**Scope:** machine-readable record contracts only; no official rows, paper engine, scheduler, or prospective clock are created by this document.

The normative requirement-to-schema mapping is maintained in
`docs/PAPER_TRADING_SCHEMA_CONTRACT_MATRIX.csv`. The eight JSON Schema
2020-12 files under `schemas/paper_trading/` are the validation surface; this
document defines the semantics that JSON Schema alone cannot express.

## 1. Shared record contract

Every ledger record, including a synthetic fixture, has these required fields:

| Field | Contract |
|---|---|
| immutable primary key | The schema's `x-primary-key`; unique within its ledger and never reused. |
| `schema_version` | Version of the individual JSON schema. |
| `protocol_version` | Paper-Trading Protocol v1 version. |
| `fixture_status` | Exactly `SYNTHETIC_TEST_FIXTURE` or `OFFICIAL_PROSPECTIVE`. |
| `source` | External source label, or an explicit deterministic `derived:<ledger>` label for derived ledgers; never omitted. |
| `code_commit` | Git commit that produced the record; a human-readable branch name is not sufficient. |
| `created_at` | Timezone-aware RFC-3339 timestamp. |
| `batch_id` | Immutable protocol-owned batch identifier. |
| `chain_scope` | Must equal the schema's declared `x-chain-scope`. |
| `chain_sequence` | Zero-based sequence within that chain scope. |
| `previous_record_hash` | SHA-256 of the predecessor's canonical bytes, or JSON `null` only for chain sequence 0. |
| `record_hash` | SHA-256 of the record's canonical bytes with `record_hash` omitted. |

Primary keys and hashes are references to immutable values, never row numbers.
All records are append-only. A correction is a new `paper_data_revisions`
record (and, where needed, a new replacement record); the original bytes,
primary key, and hash remain unchanged.

All machine date-times are RFC-3339 with an explicit offset and are normalized
to UTC `Z` for canonicalization. `session_date` is a New York exchange date
(`YYYY-MM-DD`), never a Japan-local date. Prices and quantities are positive
finite decimals when present; missing values are JSON `null`, never zero or a
forward fill. Monetary values are USD at scale 2, prices USD/share at scale 8,
weights and returns at scale 12, and basis points at scale 6. Counts and dates
are exact integers/date strings. NaN, Infinity, negative zero, locale-formatted
numbers, and timezone-naive timestamps are invalid; NaN and infinity are
rejected.

The timestamp ontology is explicit: `session_date`, `exchange_open_at`,
`exchange_close_at`, `signal_close_at`, `data_available_at`,
`data_acquired_at`, `decision_ready_at`, `order_created_at`,
`order_recorded_at`, `intended_execution_at`, `proxy_price_timestamp`,
`fill_recorded_at`, `tax_event_at`, `incident_at`, `discovery_at`,
`valuation_timestamp`, and `ledger_written_at`. Optional timestamps are
`null`, never naive.

## 2. Canonical serialization and hash chains

### 2.1 Canonical bytes

The hash input is one canonical UTF-8 JSON representation; CSV is a delivery
format and is never hashed in place of canonical JSON. The serializer must:

1. reject non-finite values, negative zero, and timezone-naive date-times;
2. normalize strings to Unicode NFC, encode UTF-8, and use `ensure_ascii=false`;
3. normalize every timestamp to UTC with exactly six fractional digits when a
   fraction is present (for example `2026-09-16T00:00:00.000000Z`);
4. serialize JSON `null` as the literal `null`;
5. sort object keys lexicographically at every nesting level (sorted keys) and use compact
   separators `(',', ':')`;
6. serialize field-aware numeric values as fixed-point JSON number tokens (no
   exponent): USD `0.00`, price `0.00000000`, weight/return `0.000000000000`,
   and bps `0.000000`; integer fields have no decimal point. A negative value
   is allowed only where the schema's units permit it; `-0` and `-0.000000`
   are rejected rather than normalized silently;
7. sort scalar identifier arrays (`order_hashes`, `raw_evidence_hashes`, and
   `affected_record_ids`) lexicographically after uniqueness validation; arrays
   with documented event order preserve that order.

Schema instances retain JSON numeric types for validation and downstream
analytics. The hash projection quantizes those numbers with exact decimal
arithmetic and emits fixed-point JSON number tokens (not locale strings), so
JSON float exponent formatting cannot change a hash.

The canonical projection contains every record field except `record_hash`.
`record_hash = SHA256(canonical_bytes(projection))`, rendered as lower-case
hex. The exact same input object therefore produces identical bytes and hash;
changing an economic field (price, target, quantity, tax, or NAV) changes the
hash. The raw vendor-object hash is computed over raw vendor bytes before
decompression/parsing;
`source_snapshot_id` is the protocol-owned identifier `sha256:<raw_hash>` (or
the SHA-256 of a sorted raw-hash manifest when one decision uses multiple
responses). A vendor revision identifier is optional and may remain `null`;
the protocol snapshot hash, not an invented vendor ID, is authoritative.

The canonical serializer uses sorted keys and compact separators exactly as
specified above. CSV exports use UTF-8, LF line endings, schema column order, comma delimiter,
RFC-4180 quoting, empty string for null, and the same decimal scales. CSV
exports are reproducible views of records, not the hash input.

### 2.2 Record-chain scope and ordering

The constants are normative:

```text
RECORD_CHAIN_SCOPE = one independent chain per ledger schema and protocol_version
BATCH_CHAIN_SCOPE  = one manifest chain across batches, ordered by batch_id
```

Each schema's `x-chain-scope` names its record stream. Within a stream the
auditor sorts deterministically by `(canonical_event_time_utc, primary_key,
created_at, chain_sequence)`. The writer assigns the next unused
`chain_sequence`; the tuple is an audit tie-breaker and never permits two
records to share a primary key. The first record is genesis:
`chain_sequence=0` and `previous_record_hash=null`; every later record must
point to the immediately preceding record hash. A batch manifest contains its
`batch_id`, first/last record IDs, first/last record hashes, previous batch
hash, current batch hash, protocol version, code commit, and creation time.
The first batch has `previous_batch_hash=null`; later batches are ordered by
`batch_id` and must point to the previous batch hash.

Corrections/revisions participate in the `paper_data_revisions` record chain;
they do not splice into or rewrite the original ledger chain. An auditor
reconstructs a chain by grouping records by `chain_scope`, checking sequence
0 genesis, sorting with the stated tuple, recomputing canonical bytes and
hashes, and verifying each predecessor link and batch-manifest link. Any
missing predecessor, duplicate primary key, sequence gap, or hash mismatch is
`HASH_CHAIN_BREAK` and stops writes.

## 3. Foreign-key and conditional-link contract

The machine-readable `x-foreign-keys` metadata in each schema is normative for
link shape; existence is checked against the immutable parent ledger, not a
row number.

```text
decision.observation_id -> observations.observation_id                 REQUIRED
order.decision_id      -> decisions.decision_id                       REQUIRED
fill.order_id          -> orders.order_id                              REQUIRED
tax.order_id           -> orders.order_id                              CONDITIONAL when trigger_type=ORDER
tax.fill_id            -> fills.fill_id                                CONDITIONAL when trigger_type=FILL
revision.original_record_id/hash -> original immutable record/hash     REQUIRED
revision.revised_record_id/hash  -> replacement record/hash            REQUIRED
nav.order_hashes       -> orders.record_hash                           CONDITIONAL; [] when no trade
incident.affected_record_ids     -> any known immutable record ID       CONDITIONAL; [] only when none exists
```

Tax events identify an actual triggering order or fill when one exists.
Corporate-action/distribution/other tax events use an explicit `trigger_type`
and null parent IDs; no fabricated parent is permitted. An incident with no
affected record uses an empty array and its raw evidence hashes instead. A
revision cannot be valid unless the original hash still exists byte-for-byte.
These cross-ledger existence checks are intentionally separate from JSON
Schema validation and are covered by the governance tests. Schema validation
failures are `SCHEMA_CONTRACT_FAILURE`; orphaned or overwritten parents are
`FOREIGN_KEY_VIOLATION`; neither is operator-resolvable by selecting a
favorable record.

## 4. Ledger-specific contracts

### `paper_observations`

One row per symbol/session/schedule observation. It carries source/raw hashes,
the required `source_snapshot_id`, raw and adjusted close, MA200, signal and
schedule flags, calendar version, and provenance. The MA200 input is exactly
the 200 completed adjusted QQQ closes available in that archived snapshot.

### `paper_decisions`

One row per scheduled decision, linked to exactly one observation. It stores
the signal, previous/new target, state-change flag, decision-ready time, and
next-eligible execution boundary. A decision cannot point to a future close or
same-session execution.

### `paper_orders`

Theoretical append-only orders carry symbol, side, target weight, quantity,
intended execution session/time, canonical fill convention, pre-trade NAV,
status, and skip reason. They are never deleted.

### `paper_fills`

This is a simulated fill ledger, not broker execution. It stores the canonical
unadjusted open reference, immutable 5-bps model cost, simulated fill,
optional quote proxy, proxy timestamp, and validity. Missing proxy fields are
`null` with `NOT_OBSERVABLE_IN_PAPER_MODE`.

### `paper_nav`

Daily pre-tax and tax-paid-to-date NAV, cash, holdings, cost basis, benchmark,
returns, paired excess, drawdown, turnover component, and order hashes. It
never creates a terminal liquidation sell.

### `paper_tax`

The frozen 20.315% simplified average-cost immediate-realized-tax semantics are
preserved. Each event carries `trigger_type` and links to its order or fill
when applicable; corporate-action events carry null parent IDs. It also stores
realized gain/loss, tax paid, cumulative paid, and tax-ledger provenance. Terminal
liquidation diagnostics are non-mutating and are not tax events.

### `paper_incidents`

Every data, clock, source, revision, duplicate, schema, FK, or operational
defect has an immutable incident ID, fixed taxonomy code/severity/action,
affected record IDs where applicable, raw evidence hashes, resolution, and
protocol-validity effect. Operators cannot choose severity after observing a
return.

### `paper_data_revisions`

Corrections reference original/revised immutable IDs and hashes, old/new
values, discovery time, optional vendor revision ID, affected sessions,
reconstructability, and auditor disposition. The original record is never
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

The directories are ignored by Git and remain empty until a separately frozen
protocol starts. API keys, access tokens, cookies, authorization headers, and
secret-store exports are never archived or hashed.

## 6. Machine-readable files

The supplied files are `paper_observations.schema.json`,
`paper_decisions.schema.json`, `paper_orders.schema.json`,
`paper_fills.schema.json`, `paper_nav.schema.json`, `paper_tax.schema.json`,
`paper_incidents.schema.json`, and `paper_data_revisions.schema.json`.
Every example record must carry `fixture_status = SYNTHETIC_TEST_FIXTURE` and
must not be copied into `paper/observations/` or another official directory.
