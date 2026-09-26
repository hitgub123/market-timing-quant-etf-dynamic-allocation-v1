# Paper-Trading Protocol v1 — Authoritative Source Account Acceptance

**Status:** `SOURCE_ACCEPTANCE_PENDING_OPERATIONAL_LATENCY_EVIDENCE`
**Scope:** pre-start EODHD Free account/API capability acceptance only; no
historical performance, backtest, signal, paper trading, engine, scheduler,
official observation, prospective clock, Final Freeze, or Phase 9 artifact.

## 1. Gate outcome

The acceptance resumed from commit
`e94326ae3f4b765bcf895de4684328ee756e6bd1`. The EODHD credential was read
only inside isolated processes from the user's external shell environment. Its
value was never printed, logged, hashed, serialized, persisted, or written to
an artifact.

Authenticated EODHD Free checks pass the account, field, history, corporate-
action, rate-limit, personal-use storage, and raw-reconstruction requirements.
The remaining gate is one account-observable PRE_START publication-latency
check on a future completed U.S. session. Therefore the exact gate is:

`SOURCE_ACCEPTANCE_PENDING_OPERATIONAL_LATENCY_EVIDENCE`

The historical Alpha Vantage `SOURCE_ACCEPTANCE_FAIL` remains preserved as
prior evidence. It is no longer the proposed current authority under the
free-source-only constraint.

## 2. Authenticated EODHD Free evidence

| Capability | Result | Sanitized evidence |
|---|---|---|
| Account plan | `PASS` | Authenticated `free` mode/type; 20 calls/day; 1,200 requests/minute header |
| QQQ.US EOD | `PASS` | 251 unique sessions; raw OHLCV and adjusted close; no required nulls or duplicates |
| QLD.US EOD | `PASS` | 251 unique sessions; raw OHLCV and adjusted close; no required nulls or duplicates |
| QQQ.US dividends/splits | `PASS` | Five dividends and zero splits in the tested one-year interval |
| QLD.US dividends/splits | `PASS` | Five dividends and one split in the tested one-year interval |
| 200-observation depth | `PASS` | 251 completed sessions per symbol |
| Exact raw-byte reconstruction | `PASS` | Seven endpoint responses reconstructed byte-identically |
| Exact adjusted-close-window reconstruction | `PASS` | The final 200 QQQ adjusted closes reproduced exactly from the archived bytes |

The free-plan warning explicitly limits history to one year. This is sufficient
for the frozen 200-session MA input but leaves only about 51 sessions of
warm-up margin, so every point-in-time source snapshot is mandatory.

## 3. Field and adjustment semantics

EODHD documents the response `close` and OHLC fields as as-traded values and
`adjusted_close` as adjusted for both splits and dividends. Historical adjusted
closes are recomputed following new dividends. Accordingly:

- the MA200 input is the exact EODHD QQQ.US `adjusted_close` captured in the
  decision's immutable source snapshot;
- execution/reference OHLC remains raw;
- a later vendor revision creates an append-only revision incident;
- EODHD and another vendor are never spliced, averaged, or selected according
  to a resulting signal; and
- numerical identity with the former proposed vendor is not claimed.

The source-data-only feasibility comparison found expected cross-vendor
adjustment differences. No signal or historical strategy result was evaluated.

## 4. Rate-limit acceptance

The authenticated account reports 20 calls per day. EODHD combines raw OHLCV
and adjusted close in one EOD response, reducing the conservative source
budget to 14 base calls and 18 calls after the fixed 25% margin. This includes
four publication polls, two fixed retries, both authoritative EOD responses,
four corporate-action responses, and two Massive reconciliation responses.
All frequency decisions on the same calendar date share the same immutable
source acquisition. The rate gate is therefore
`RATE_LIMIT_ACCEPTANCE_PASS_18_LE_20` with two calls of daily headroom.

## 5. Publication timing

Official EODHD documentation states that major U.S. exchanges are updated
within 15 minutes after market close. This supplies a documented candidate
publication boundary, but the account has not yet been observed across a real
future completed session. The PRE_START observation must record sanitized poll
times, response hashes, expected session date, first availability time, and
rate headers without calculating a signal.

Until that observation passes, publication status remains
`PENDING_PRE_START_ACCOUNT_LATENCY_OBSERVATION`. No official observation or
prospective start may be created.

## 6. Raw-response and revision provenance

Every authenticated response was archived before parsing in an isolated
temporary directory, read back byte-identically, and removed after the
collector exited. An additional QQQ reconstruction control reproduced the
same ordered 200 `(date, adjusted_close)` records. The raw snapshot ID is the
SHA-256 of the exact response bytes. EODHD supplied no immutable revision ID,
so `source_revision_id = null` remains valid and no vendor identifier is
invented.

EODHD's terms permit a non-professional user to store, manipulate, and analyze
data for private non-commercial use. Redistribution is not authorized by this
acceptance.

## 7. Source roles

EODHD Free is now the proposed `AUTHORITATIVE_MARKET_DATA_SOURCE`, pending
external audit and the latency check. Massive Basic Free remains strictly the
`RECONCILIATION_MARKET_DATA_SOURCE`; its split-only adjusted aggregates cannot
replace EODHD adjusted close. Alpha Vantage is retained only as historical
failed-account evidence and is not an operational dependency.

## 8. Freeze boundary

No engine, scheduler, official observation directory, prospective start
timestamp, acceptance manifest, Final Freeze, or Phase 9 artifact was created.
No strategy, MA200, schedule, cost, tax, metric, statistical method, threshold,
or closed research artifact changed.

## 9. Final source gate

`SOURCE_ACCEPTANCE_PENDING_OPERATIONAL_LATENCY_EVIDENCE`

Only the narrow PRE_START latency control and its external audit may advance
this source gate. It cannot be advanced from documentation alone.
