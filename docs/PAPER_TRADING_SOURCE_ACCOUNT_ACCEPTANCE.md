# Paper-Trading Protocol v1 — Authoritative Source Account Acceptance

**Status:** `ACCOUNT_CREDENTIALS_NOT_AVAILABLE`
**Scope:** pre-start account/API capability acceptance only; no historical
performance, backtest, parameter selection, paper trading, engine, scheduler,
official observation, or final freeze.

## 1. Gate outcome

The execution environment has no Alpha Vantage, Massive, or Polygon API
credential available through the approved environment-variable/secret-store
mechanism. No authenticated request was attempted, no price response was
retrieved, and no capability result was fabricated. Account-dependent
verification therefore stops at:

`ACCOUNT_CREDENTIALS_NOT_AVAILABLE`

The machine-readable result is
`docs/paper_trading_source_account_acceptance.json`. All account-dependent
fields remain `UNVERIFIED_CAPABILITY` or `ACCOUNT_CREDENTIALS_NOT_AVAILABLE`.

## 2. Public documentation inspection

The official Alpha Vantage documentation describes:

- `TIME_SERIES_DAILY_ADJUSTED` as supplying raw daily OHLCV, adjusted close,
  and historical split/dividend events, with JSON/CSV output and premium
  entitlement requirements;
- `TIME_SERIES_DAILY` as supplying raw daily OHLCV, with `full` history and
  JSON/CSV semantics dependent on the plan;
- `DIVIDENDS` as historical/future declared distributions;
- `SPLITS` as historical split events.

These public descriptions do not prove access for the intended account. They
also do not provide a verified deterministic after-close publication SLA for
the daily endpoint. The [Alpha Vantage API documentation](https://www.alphavantage.co/documentation/)
is recorded as evidence, but account entitlement is still required.

Massive's official overview documents plan-dependent trade/quote products and
does not make the intended reconciliation entitlement verifiable without the
account. Massive remains strictly
`RECONCILIATION_MARKET_DATA_SOURCE`; it is not promoted to the authoritative adjusted-close source.
See the [Massive Stocks overview](https://polygon.io/docs/rest/stocks/overview).

## 3. Capability acceptance table

| Capability | Result | Reason |
|---|---|---|
| Alpha Vantage adjusted QQQ daily | `UNVERIFIED_CAPABILITY` | No authenticated account request |
| Alpha Vantage raw QQQ daily | `UNVERIFIED_CAPABILITY` | No authenticated account request |
| Alpha Vantage raw QLD daily | `UNVERIFIED_CAPABILITY` | No authenticated account request |
| Alpha Vantage `SPLITS`/`DIVIDENDS` | `UNVERIFIED_CAPABILITY` | No authenticated account request |
| 200-observation history depth | `UNVERIFIED_CAPABILITY` | Plan entitlement not available to test |
| After-close publication SLA | `UNRESOLVED` | No authenticated timing observation and no verified vendor SLA |
| Publication deadline | `PUBLICATION_DEADLINE_NOT_READY` | No 15-minute SLA was invented; do not invent any other SLA |
| Intended-account rate limits | `UNVERIFIED_CAPABILITY` | Account/plan unavailable; gate remains `RATE_LIMIT_NOT_READY` |
| Massive QQQ/QLD reconciliation | `ACCOUNT_CREDENTIALS_NOT_AVAILABLE` | No authenticated request |
| Massive SIP execution proxy | `NOT_OBSERVABLE_IN_PAPER_MODE` | Optional diagnostic; never a freeze blocker |
| Vendor revision ID | `UNVERIFIED_CAPABILITY` | No authenticated account/support evidence |

## 4. Point-in-time snapshot reconstruction

The mandatory reconstruction test was run with a deterministic synthetic raw
response, not vendor data. The exact bytes were hashed before parsing;
`source_snapshot_id` was derived from the SHA-256 hash; 200 completed adjusted
closes were parsed; the parsed state was discarded; and the values, MA200, and
signal classification were reconstructed solely from the archived bytes.

Result:

`SOURCE_SNAPSHOT_RECONSTRUCTION_PASS`

The fixture is `SYNTHETIC_TEST_FIXTURE`, never enters `paper/observations/`,
and contains no official price or performance evidence. The protocol supports
`source_revision_id = null` when a vendor supplies no immutable revision ID;
the protocol-owned raw snapshot remains authoritative provenance.

## 5. Publication and rate-limit readiness

No after-close polling was run because credentials were unavailable. No
publication samples were used to choose a favorable deadline. The status is
`PUBLICATION_DEADLINE_NOT_READY`.

The request budget is an operational demand calculation only. For a conservative
12-month sum of weekly, monthly, bimonthly, and quarterly scheduled sessions
(52 + 12 + 6 + 4 = 74), the fixed per-session envelope is 16 requests:

- one scheduled-close control request;
- adjusted QQQ, raw QQQ, raw QLD;
- QQQ/QLD split and dividend checks;
- QQQ/QLD reconciliation requests;
- four bounded publication polls; and
- two fixed retry requests.

With a prospective 25% safety margin this is 20 requests per scheduled session,
or 1,480 requests per conservative 12-month sum. The intended account's actual
burst/day/month limits were not available, so rate-limit acceptance remains
`RATE_LIMIT_NOT_READY`. Unlimited retries are not permitted.

## 6. Synthetic source-disagreement fixture

A pre-start synthetic fixture supplies different raw OHLC values for the two
proposed sources. The fixture asserts that Alpha Vantage remains authoritative,
Massive remains reconciliation-only, the mismatch creates a source-disagreement
incident, no values are averaged, and an operator cannot choose whichever
vendor produces a better signal. No historical date was searched and no
strategy outcome was calculated.

## 7. Secret-leak audit and boundary checks

The remediation commit, tracked files, generated artifacts, and test artifacts
were scanned for credential material without printing or persisting any secret.
Result:

`SECRET_LEAK_SCAN_PASS`

The repository still has no official observation directory, prospective start
timestamp, production engine, scheduler, final acceptance manifest, or Phase 9
artifact. Research v1 freeze integrity and all closed prospective/statistical
contracts remain unchanged.

## 8. Final source gate

The correct outcome is:

`ACCOUNT_CREDENTIALS_NOT_AVAILABLE`

This is not a source acceptance pass and does not authorize Final Freeze. The
next account-enabled run must use sanitized authenticated requests, record
endpoint/history/corporate-action semantics, capture publication latency without
performance selection, compare the demand budget with actual limits, and then
re-audit the source gate.
