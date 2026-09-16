# Uncounted Operational Dry-Run Acceptance

**Status:** `PROPOSED_NOT_FROZEN`  
**Run type:** `UNCOUNTED_OPERATIONAL_DRY_RUN`

## 1. Boundary

The dry run occurs only after a future implementation exists and passes code
review, but before protocol freeze and before a prospective start. Every input
is `SYNTHETIC_TEST_FIXTURE` or `PRE_START_OPERATIONAL_TEST_DATA`. It contributes
zero to the 36-month horizon, 500 paired sessions, state changes, completed
episodes, return inference, and PASS/FAIL. It must not populate
`paper/observations/` or create official NAV #1.
It must not create official observation #1.

## 2. Required coverage matrix

The dry run must execute all golden fixture categories in
`PAPER_TRADING_GOLDEN_FIXTURE_SPEC.md` and at least one end-to-end sequence
covering:

- normal sessions, Monday holiday, month/quarter/year boundaries, bimonthly
  odd-month selection, early close, unscheduled closure, and both DST changes;
- close-to-next-open timing, 200-observation warm-up, target transitions, and
  no same-day execution;
- authoritative/reconciliation acquisition, raw snapshot/hash, disagreement,
  revision, duplicate, stale/missing data, and proxy-unavailable paths;
- observation → decision → order → fill → NAV → tax → incident chains;
- restart/recovery, duplicate protection, clock uncertainty, and manual
  intervention logging;
- canonical 5-bps fill, zero commission, average-cost tax, turnover, drawdown,
  paired returns, and non-mutating terminal diagnostics.

## 3. Mechanical acceptance

The dry run PASS requires all of the following:

1. every fixture expected value matches the pre-written expected value exactly
   (or the documented cent/decimal serialization tolerance);
2. every schema validates and every required timestamp is timezone-aware;
3. every record and batch hash chain verifies from the first synthetic record;
4. duplicate, missing, stale, invalid, disagreement, revision, and clock cases
   follow the fixed incident taxonomy and fail-closed action;
5. no output is written to an official prospective directory;
6. the dry-run report contains zero official observation count and no inference
   statistic or outcome result;
7. rerunning the same immutable fixture produces identical canonical bytes and
   hashes;
8. a second operator can execute the runbook without undocumented choices.

Return performance, CAGR, drawdown, Sharpe, or any alpha-like quantity is not a
dry-run acceptance criterion. It is not a dry-run acceptance criterion for the
acceptance decision. A dry-run result cannot produce paper PASS.

## 4. Defect classification and restart rule

An **economic-semantic defect** is any defect that can change signal timing,
target, session, price, fill, quantity, NAV, tax, turnover, drawdown, paired
return, terminal diagnostic, or outcome inputs. It requires a versioned fix,
implementation re-audit, and a complete restart of the uncounted dry run from
fresh synthetic fixtures. Examples include an off-by-one MA, holiday/DST
error, same-day trade, corporate-action error, tax-cost-basis error,
turnover-denominator error, or terminal-liquidation mutation.

A **non-economic documentation/logging defect** cannot change any record,
decision, hash, or acceptance result. It may be remediated with an incident,
reviewer sign-off, and rerun of the affected documentation/schema check; it
still cannot be silently edited in an official run.

## 5. Required dry-run evidence

The future handoff contains the fixture manifest, expected-value version,
environment manifest, source stubs, record/batch hashes, schema results,
incident log, restart/recovery evidence, operator checklist, and a statement
that no official prospective record was created. All evidence remains
`PROPOSED_NOT_FROZEN` until external Operational Freeze Audit.
