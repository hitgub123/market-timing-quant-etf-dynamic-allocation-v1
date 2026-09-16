# Paper Trading Protocol v1 Operational Freeze Preparation Audit

**Preparation status:** `PROPOSED_NOT_FROZEN`  
**Design status:** `FINAL DESIGN CLARIFICATION PASS — DESIGN CLOSED`  
**Preparation date:** 2026-09-16  
**Scope:** operational preparation only; no prospective start or engine

## 1. Immutable boundary and design-closure audit

The accepted prospective statistical/economic design from
`c75af4cf196419c6a27fbddcb10aaad966148b89` remains unchanged. Fixed MA200 is
the primary model, WEEKLY is the sole primary inferential schedule, the three
other frequencies are descriptive shadows, and the 36/48-month rule,
HAC/one-sided PASS condition, −2pp harm floor, mechanism rule, severe-risk
limits, turnover limit, tax semantics, and Goal A/B/C definitions are not
modified. The accepted outcome decision spec/table and threshold registry are
byte-identical to that design-close commit.

Research v1.0 remains frozen: `research-v1.0-final` resolves to
`2b2bf987f2e00540412d263a8ef39566af1d1e2a`, and
`reports/research_v1_freeze_manifest.json` retains SHA-256
`dcb8f9d79de93c61e0bd7d93b743b0356be9eb3b1467acf5db9a58563889d400`.

This phase did not select a live credential, create a scheduler, activate a
start timestamp, create official observation/NAV #1, populate any official
paper directory, run a backtest, inspect historical performance, implement a
production paper engine, start Phase 9, or authorize live capital.

## 2. Data-source decision

The proposed roles are documented in
`docs/PAPER_TRADING_DATA_SOURCE_SPEC.md` and
`docs/paper_trading_data_source_decision.csv`:

- **Authoritative:** Alpha Vantage daily adjusted/raw endpoints plus SPLITS
  and DIVIDENDS for QQQ/QLD. Public documentation verifies raw OHLCV,
  adjusted close, and split/dividend event fields. The daily response is
  session-date keyed; an intraday event timestamp and immutable revision SLA
  remain `UNVERIFIED_CAPABILITY`.
- **Reconciliation:** Massive (formerly Polygon.io) day aggregates/reference
  products. Public documentation verifies raw daily OHLCV, UTC timestamps, and
  flat-file reproducibility. Its documented adjustment is split-only, not
  dividend-adjusted, so it does not replace the authoritative adjusted close.
- **Execution proxy:** Massive U.S. Stocks SIP quote data only if account
  entitlement and executable-side/timestamp semantics are accepted. Quote
  timestamp capability is documented; opening-auction executable semantics,
  account entitlement, rate limits, and licensing remain
  `UNVERIFIED_CAPABILITY`. Missing capability means
  `NOT_OBSERVABLE_IN_PAPER_MODE`, never a fabricated proxy.

No vendor was selected using a historical strategy result. The exact public
documentation references are recorded in the data-source spec and decision
CSV. Account-specific plan/licensing acceptance remains an external pre-freeze
item.

## 3. Calendar and schedule audit

The proposed canonical calendar is the pinned NASDAQ schedule from
`pandas_market_calendars`, reconciled to published Nasdaq/NYSE holiday and
early-close calendars. QQQ and QLD are Nasdaq-listed ETFs. Session dates are New York civil dates; machine times
are UTC plus the `America/New_York` rendering. Regular core hours are 09:30 to
16:00 ET; an early close uses the calendar's published close. Holidays,
unscheduled closures, halts, and DST are explicit incidents or calendar
outcomes, never vendor-row inference.

Schedule functions are deterministic and preserve the closed historical
semantics: weekly first eligible Monday–Sunday session, monthly first eligible
calendar-month session, bimonthly first eligible odd-month session (Jan/Mar/
May/Jul/Sep/Nov), and quarterly first eligible Jan/Apr/Jul/Oct session. The
calendar spec lists normal weeks, Monday holidays, month/year/quarter
boundaries, early closes, unscheduled closures, next-session, and both DST
fixtures.

## 4. Timestamp, adjustment, and revision policy

The timestamp ontology covers `session_date`, exchange open/close, signal close,
availability/acquisition, decision-ready, order-created/recorded, intended
execution, proxy quote, fill-recorded, valuation, and ledger-written times.
All machine timestamps are timezone-aware ISO-8601 and retain UTC; naive
timestamps and Japan-local session inference are rejected.

The MA200 uses authoritative adjusted QQQ close. Raw opens/closes remain
unadjusted execution/reference values. Splits, dividends, QLD distributions,
source revision IDs, raw payload hashes, and old/new values are preserved.
`DATA_REVISION_INCIDENT` appends a correction; an original decision is never
silently rewritten. An informational future revision is harmless, a
reconstructable correction is a recoverable incident, and loss of original
decision reconstructability or silent overwrite is `PROTOCOL_INVALID`.

## 5. Fail-closed and disagreement audit

The source spec and incident taxonomy define deterministic `WAIT`, `SKIP`,
`INCIDENT_AND_CONTINUE`, `INCIDENT_AND_RECONSTRUCT`, and
`PROTOCOL_INVALID` actions for missing/stale closes, missing/delayed opens,
invalid prices, duplicates, source disagreement, partial/early sessions,
closures, outages, corporate-action/timestamp ambiguity, post-decision
revisions, and unavailable execution proxies. No forward-fill, interpolation,
midpoint, last-known value, averaging, or favorable synthetic price is
permitted. A reconciliation source can diagnose but cannot silently replace the
authoritative observation.

## 6. Append-only ledgers and hash chain

`docs/PAPER_TRADING_LEDGER_SCHEMA.md` and the eight JSON Schema files under
`schemas/paper_trading/` specify `paper_observations`, `paper_decisions`,
`paper_orders`, `paper_fills`, `paper_nav`, `paper_tax`, `paper_incidents`, and
`paper_data_revisions`. Each has an immutable primary key, protocol/schema
version, fixture status, provenance, creation timestamp, previous-record hash,
and current SHA-256 record hash. Foreign keys are immutable IDs. Corrections
append to the revision ledger; old records remain byte-identical.

Canonical JSON uses UTF-8, sorted keys, compact separators, fixed decimal
scales, and rejects NaN/Infinity. Canonical CSV uses UTF-8, LF, schema column
order, empty nulls, and fixed numeric scales. Raw vendor bytes are hashed before
parsing. The future archive layout is Git-ignored and remains empty until a
separate freeze/start.

## 7. Environment, secrets, and runbook

`PAPER_TRADING_ENVIRONMENT_SPEC.md` records the pinned repository dependency
contract, observed preparation environment, IANA timezone requirement, UTC
clock health, and rebuild tuple. No dependency upgrade was made. `.gitignore`
now excludes environment files, key/certificate patterns, secrets, and future
paper raw/ledger/manifest directories.

The operational decision registry also covers the external dependency table:
market-data vendors, NASDAQ/calendar, IANA timezone database, synchronized UTC
clock, local append-only storage/backup, secret management, and a calendar-driven
runtime scheduler design that remains inactive.

`PAPER_TRADING_OPERATIONAL_RUNBOOK.md` is person-executable and covers before
close, close acquisition, raw hashing, reconciliation, signal/decision/order,
next-open simulated fill/proxy, end-of-session NAV/tax/turnover, hash checks,
incident handling, and manual interventions. Favorable-price overrides,
backdating, threshold/MA/schedule changes, deleting losses, and start resets
are forbidden.

## 8. Incident taxonomy

`docs/paper_trading_incident_taxonomy.csv` provides fixed INFO, WARNING,
RECOVERABLE, MATERIAL, and PROTOCOL_INVALIDATING severity meanings with an
automatic action, evidence requirement, protocol effect, and restart flag.
Severity is determined by trigger, not selected after seeing performance.

## 9. Uncounted dry-run and implementation acceptance

`PAPER_TRADING_DRY_RUN_ACCEPTANCE.md` defines one
`UNCOUNTED_OPERATIONAL_DRY_RUN` after a future implementation and before final
freeze/start. It tests calendar transitions, close→next-open timing, source
acquisition/reconciliation, raw snapshots, hashes, ledgers, NAV/tax, incidents,
restart/recovery, duplicate/revision/clock behavior, and every golden fixture.
It contributes zero to the 36/48-month horizon, 500 sessions, state changes,
episodes, inference, or outcome. Return performance is explicitly not an
acceptance criterion. An economic-semantic defect requires a versioned fix,
implementation re-audit, and full dry-run restart.

`PAPER_TRADING_IMPLEMENTATION_ACCEPTANCE_SPEC.md` requires deterministic
equivalence for MA200, calendar/schedules, close boundary, next-open execution,
5-bps fill, quantity, NAV, tax, turnover, drawdown, benchmark, paired returns,
terminal outcome, and hash chain. `PAPER_TRADING_GOLDEN_FIXTURE_SPEC.md`
defines 27 synthetic edge cases, including off-by-one MA, holidays, DST,
corporate actions, stale/missing data, tax, turnover, and terminal
liquidation. No expected value is copied from historical strategy output.

## 10. Acceptance-manifest design

`PAPER_TRADING_ACCEPTANCE_MANIFEST_SPEC.md` designs but does not create
`paper_validation_v1_acceptance_manifest.json`. The future manifest will hash
the final protocol, statistical/rationale/outcome artifacts, threshold registry,
data-source/calendar/ledger/runbook/incident/environment/dry-run/
implementation/golden-fixture specs and schemas using canonical SHA-256 path
rules. It will be created only after external Operational Freeze Audit.

## 11. Dedicated governance tests

`tests/test_paper_trading_operational_prep.py` contains the dedicated
pre-start governance suite. It covers the requested 60 categories: source
roles/capability boundaries, calendar/schedules/holidays/early closes/DST,
timestamp and adjustment/revision policy, fail-closed disagreement actions,
all eight append-only schemas, canonical/hash/archive/secrets rules,
environment/runbook/manual operations, incident taxonomy, dry-run/semantic
restart, implementation/golden fixtures, acceptance-manifest design, registry
statuses, design references, closed-file byte identity, freeze hash/tag, and
no-start/no-engine/no-Phase9 boundaries.

Final test counts are recorded after execution below.

Dedicated operational-preparation suite: **36 passed**. The three prospective
governance suites together: **117 passed**. Complete repository suite:

```text
python3 -m pytest -q
501 passed in 26.32s
```

## 12. Remaining unresolved items

The following remain intentionally unresolved and `PROPOSED_NOT_FROZEN`:

- vendor account/plan entitlement, licensing, rate limits, and exact endpoint
  acceptance;
- daily source timestamp/revision guarantees and independent corporate-action
  reconciliation;
- quote entitlement and opening-auction executable semantics;
- pinned calendar/IANA versions and final exchange-page evidence hashes;
- implementation code review, dependency-lock exception resolution, and
  complete uncounted dry-run evidence;
- final acceptance manifest generation and external Operational Freeze Audit.

No item authorizes prospective start, official observation, engine activation,
scheduler start, historical backtest, Phase 9, or live capital.

## 13. Final status

All new operational decisions remain `PROPOSED_NOT_FROZEN`. This is operational
freeze preparation only and is not protocol freeze.

PAPER TRADING PROTOCOL V1 OPERATIONAL FREEZE PREPARATION COMPLETE — NO PROSPECTIVE START OR ENGINE ACTIVATED — AWAITING OPERATIONAL FREEZE AUDIT
