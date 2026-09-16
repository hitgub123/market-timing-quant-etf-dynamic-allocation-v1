# Prospective Paper-Trading Validation Protocol v1.0

**Status: DRAFT FOR AUDIT — NOT FROZEN**  
**Protocol version:** `paper-validation-v1.0-draft`  
**Historical reference:** Research v1.0, tag `research-v1.0-final`  
**Implementation status:** not implemented  
**Observation status:** no prospective observations collected

This document defines a proposed independent prospective validation stage. It
does not authorize paper trading, live trading, a live frequency, or a change to
the frozen historical research. Every new operational choice and threshold in
this document is explicitly `PROPOSED_NOT_FROZEN` and requires external audit
and a final protocol freeze before the prospective start timestamp.

## 1. Purpose

The purpose is to test whether the frozen Research v1.0 findings survive
genuinely unseen future market observations. The exercise is prospective
validation, not strategy development.

Paper trading is not intended to improve the strategy, find new parameters,
select whichever historical frequency had the highest return, optimize
execution, discover indicators, or rescue a failed historical objective. Any
such activity invalidates this protocol version and belongs in a separately
audited research version.

## 2. Model-family boundary

### Primary prospective model

`FIXED_MA200_QQQ_TO_QLD` is the **PRIMARY PROSPECTIVE MODEL**. It is the frozen
QQQ adjusted-close MA200 rule that maps to QLD or CASH. Phase 8D classified its
historical evidence as `MODERATE`.

### Non-decision comparator

`PHASE7A_FIXED_FOUR_STATE` may be retained only as a **NON-DECISION SHADOW
COMPARATOR**, if operationally useful. Phase 8D classified its incremental
complexity versus Fixed MA200 as `NOT_JUSTIFIED`; a higher historical CAGR in a
subset of scenarios is not a reason to promote it. It cannot replace the
primary model or determine a live frequency.

Phase7B Model A and Model B are not prospective candidates. Their
`NO_ELIGIBLE_PARAMETER` and `CASH_FALLBACK` behavior remains historical context
only.

## 3. Frequency problem and alternatives

Research v1.0 intentionally did not select weekly, monthly, bimonthly, or quarterly.
This draft keeps the issue visible rather than solving it silently.

| Alternative | Statistical implications | Operational implications | Selection-bias implications | Proposed duration | Eventual decision rule |
|---|---|---|---|---|---|
| **A. Shadow-run all four** | Four paired return streams require a prospectively frozen multiplicity treatment; a single primary hypothesis must remain identifiable. | Four schedules, fills, tax ledgers, and reports; higher logging burden but no hidden choice. | Avoids selecting from historical CAGR; any later choice must be made by a separate frozen rule using prospective evidence. | At least the audited duration/event design in Section 10, marked `PROPOSED_NOT_FROZEN`. | Continue all shadows until a separately audited frequency-decision protocol is approved; no live-frequency choice in this draft. |
| **B. Pre-freeze one frequency independently of historical return** | One primary stream reduces multiplicity, but inference applies only to the preselected schedule. | Lowest operating burden. | A rule based on calendar/operations can be independent of performance, but must be documented before start. | The same proposed time/event adequacy gate; `PROPOSED_NOT_FROZEN`. | Use only the pre-frozen rule; do not revisit it after results are visible. |
| **C. Treat frequency as a prospective design dimension** | Frequency is part of the hypothesis family; family-level inference and adequacy must be frozen before observing outcomes. | Four shadows and a longer evidence-collection burden. | Explicitly acknowledges design multiplicity instead of hiding it. | Longer if the decision rule requires adequate observations for every shadow; `PROPOSED_NOT_FROZEN`. | A later, separately audited protocol may decide whether and how a frequency can be selected. |

### Recommendation for audit

**PROPOSED_NOT_FROZEN:** use Alternative A operationally and Alternative C
statistically: shadow-run all four frequencies, designate Fixed MA200 as the
model family, predeclare one primary comparison, and defer any frequency choice
until a separate prospective decision protocol has been audited. This is a
recommendation for protocol design, not a final frequency selection.

## 4. Prospective start boundary

The prospective start timestamp must be recorded only after all four gates have
passed:

1. external audit of this draft and its decision table;
2. final protocol freeze under a new commit/tag;
3. implementation audit against the frozen semantics; and
4. a dry-run that proves logging, valuation, tax, and fill records without
   counting dry-run observations.

The timestamp must be an exact ISO-8601 instant with an explicit offset and a
corresponding U.S. trading-session date. `America/New_York` is the proposed
session timezone because the instruments trade on U.S. exchanges;
`PROPOSED_NOT_FROZEN`. The session date is the exchange calendar date, not the
local calendar date of an operator in another timezone. Historical observations
before the frozen prospective start timestamp, including data already present
in Research v1.0, do not count toward prospective evidence.

No prospective start timestamp is activated by this draft.

## 5. Signal-generation protocol

The implementation must reproduce the following Research v1.0 semantics:

- **Source price:** complete, positive adjusted close for QQQ. Raw and adjusted
  values are retained separately in the observation record.
- **Lookback:** simple moving average with exactly 200 observations.
- **Decision timestamp:** close of session `t`; the close is the information
  boundary for that decision.
- **Rebalance calendar:** weekly, monthly, bimonthly, and quarterly schedules
  remain visible as four shadows. The schedule definition is the frozen
  Research v1 convention; it must not be inferred from the best historical
  return.
- **Eligibility:** a target is eligible only when the required 200 complete
  adjusted closes and the scheduled close are available. No future value may
  enter the decision.
- **Execution boundary:** a close-`t` decision may first affect the next
  eligible U.S. trading-session open, never the open of `t`.
- **State mapping:** QQQ close above its MA maps to 100% QLD; otherwise it maps
  to 100% CASH. The model does not add QQQ, TQQQ, VIX, momentum, volatility, or
  other states.
- **Missing data:** do not interpolate, forward-fill, or silently revise a
  missing required price. Do not create a synthetic signal or fill. The order
  is skipped or held at the previously recorded target, with an incident and
  reason recorded; the exact fail-closed handling is `PROPOSED_NOT_FROZEN` and
  must be audited before start.
- **Market holidays:** use one frozen official U.S. exchange-session calendar.
  The next eligible open is the next session on that calendar.
- **Partial sessions:** no special favorable fill is permitted. A partial or
  unavailable session is logged and handled by the pre-frozen skip rule;
  `PROPOSED_NOT_FROZEN`.
- **Stale data:** record acquisition time and data age. A stale-data threshold,
  and whether the order is held or skipped, are `PROPOSED_NOT_FROZEN`; no stale
  value may silently pass as a current close.
- **Corporate actions/data revisions:** retain the originally acquired value,
  adjusted value, revision status, and hash. A vendor revision creates a
  correction-ledger entry; it never silently rewrites an earlier prospective
  observation or changes a completed report.

## 6. Paper-order and fill protocol

Each scheduled decision creates a theoretical order record before any simulated
fill. At minimum record:

| Field | Requirement |
|---|---|
| Signal timestamp | Close timestamp and exchange-session date for `t`. |
| Decision | Binary QQQ-MA decision and state (`QLD` or `CASH`). |
| Target weight | Target asset and weight, including zero/cash weight. |
| Order-generation timestamp | Software timestamp when the order record was created. |
| Intended execution session | First eligible session after `t`. |
| Intended price convention | Next eligible open, with the frozen baseline identifiable. |
| Observable market price | Raw/adjusted observable price used for the diagnostic. |
| Simulated fill price | Deterministic paper fill derived from the predeclared convention. |
| Assumed slippage | Baseline 5 bps, unless a separately frozen protocol says otherwise. |
| Quantity | Theoretical quantity and rounding rule. |
| Pre-trade NAV | Open-before-trade NAV used for accounting and turnover. |
| Post-trade NAV | NAV after fill and transaction cost. |
| Transaction cost | Commission plus slippage cost, separately identifiable. |
| Unfilled/skipped reason | Required for missing data, holiday, stale data, or operational failure. |

Research v1 uses 0 commission bps and 5 bps slippage with execution at the next
eligible open. A paper fill must retain that baseline as a comparison field and
must not silently substitute a close, midpoint, same-day, or otherwise more
favorable fill rule. Any live-observable fill diagnostic is additional evidence,
not a rewrite of the historical baseline.

## 7. Prospective data provenance

Use an append-only architecture with separate roots:

```
research_v1/                 # read-only references to the frozen historical set
prospective_validation_v1/  # paper orders, fills, observations, incidents
```

Every prospective observation must include acquisition timestamp, source,
original value, adjusted value when applicable, revision status, observation
hash, software version, Git commit, strategy-version identifier, exchange
session date, and timezone/offset. A correction ledger records the prior hash,
new hash, vendor explanation, detection time, affected reports, and auditor
disposition. Past prospective observations are never silently overwritten when
a vendor revises history.

The paper engine and storage layout are not implemented by this task.

## 8. Benchmark

QQQ buy-and-hold remains the primary benchmark. For every prospective shadow,
use the identical validation start, $100,000 capital base (unless a separately
audited protocol changes that assumption), U.S. session calendar, valuation
dates, and data provenance. Do not retrospectively change the benchmark or its
start boundary.

## 9. Metrics to collect

Collect the following without treating a short sample as reliable merely
because a formula returns a number.

**Performance:** cumulative return, CAGR where information content is adequate,
realized volatility, Sharpe, Sortino, MaxDD, Calmar, and Ulcer Index.

**Implementation:** realized/simulated slippage, signal-to-order latency,
order-to-fill latency, tracking difference, turnover, transaction costs,
skipped/failed orders, and stale/missing-data incidents.

**Tax/accounting:** realized gains/losses, average cost, the simplified 20.315%
tax ledger, tax-paid-to-date NAV, and a terminal-liquidation diagnostic where
meaningful. Terminal liquidation must remain non-mutating and diagnostic only.

**Benchmark-relative:** return difference versus QQQ, drawdown difference,
Sharpe difference, and Calmar difference over identical prospective dates.

## 10. Validation duration and information adequacy

A MA200 strategy can have few regime changes, so a short paper period may show
almost no informative trades. The final duration gate must be frozen before the
start. Candidate designs for audit are:

- a minimum calendar duration, such as **36 months** (`PROPOSED_NOT_FROZEN`);
- at least **24 scheduled rebalance observations for each shadow**
  (`PROPOSED_NOT_FROZEN`), which intentionally makes quarterly evidence take
  longer;
- at least **8 completed actual position-change episodes**
  (`PROPOSED_NOT_FROZEN`); and
- at least one predeclared adverse/regime-transition episode, identified by an
  ex-ante event definition rather than selected after inspecting returns
  (`PROPOSED_NOT_FROZEN`).

The recommended audit design is the intersection of those four gates,
`PROPOSED_NOT_FROZEN`. A time-only design, an event-only design, and a combined
time/event design should be compared during audit. None may be relaxed because
historical results make it inconvenient or tightened because a result looks
unfavorable.

## 11. Success, failure, and inconclusive criteria

The outcome must be one of `PROSPECTIVE_VALIDATION_PASS`,
`PROSPECTIVE_VALIDATION_FAIL`, or `PROSPECTIVE_VALIDATION_INCONCLUSIVE`. There
is no composite score. Each dimension is a separate gate:

### Strategy fidelity

**Hard failure:** any unapproved change to MA200, adjusted-close input,
close-`t` information boundary, next-open execution, QLD/CASH mapping, tax
semantics, benchmark, or frequency-shadow definitions; an unlogged order or
observation; or silent rewriting of a prior observation. A fidelity failure
invalidates the current protocol version and requires a new audit.

### Operational reliability

**Hard failure:** inability to reconstruct the signal, order, fill, NAV, tax,
or incident history; an unapproved reset/restart; or unresolved data/operational
incidents beyond a predeclared tolerance. The tolerance is
`PROPOSED_NOT_FROZEN`.

### Execution and slippage

Compare simulated and observable fills, latencies, and tracking difference. A
pass requires behavior within a pre-frozen slippage/latency/tracking guardrail;
the guardrail is `PROPOSED_NOT_FROZEN`. Changing the assumption to improve the
result is prohibited.

### Benchmark-relative economics

After the information-adequacy gates, evaluate cumulative return and paired
daily excess returns versus QQQ. A proposed economic pass requires a positive
predeclared return-difference direction and no material unexplained tracking
failure; any numerical guardrail is `PROPOSED_NOT_FROZEN`. Short-horizon CAGR or
Sharpe alone cannot produce a pass.

### Drawdown behavior

The historical project did not establish QQQ drawdown dominance. Therefore a
prospective pass cannot be declared solely because cumulative return exceeds
QQQ while MaxDD materially deteriorates. Compare strategy and QQQ MaxDD,
drawdown difference, underwater duration, and recovery duration. The allowable
drawdown guardrail is `PROPOSED_NOT_FROZEN` and must preserve the original risk
concern.

### Tax and turnover burden

Reconcile realized gains/losses, average cost, tax-paid-to-date NAV, turnover,
and costs. A proposed pass requires no unexplained tax/accounting break and
burdens within a pre-frozen guardrail; all numerical limits are
`PROPOSED_NOT_FROZEN`. Tax drag is not ignored merely because pre-tax return is
positive.

### Outcome rule

`PROSPECTIVE_VALIDATION_PASS` requires fidelity and operational hard gates to
pass, information adequacy to be met, and the separately reported execution,
benchmark-relative, drawdown, and tax/turnover conditions to satisfy their
pre-frozen rules. `PROSPECTIVE_VALIDATION_FAIL` occurs on a hard failure or a
pre-frozen economic failure. `PROSPECTIVE_VALIDATION_INCONCLUSIVE` applies when
fidelity is intact but the time/event information gate is incomplete or the
pre-frozen evidence conditions cannot yet distinguish the outcomes. These are
separate conditions, not a combined numerical score.

## 12. Drawdown issue

Research v1.0 did not demonstrate drawdown dominance over QQQ. Every monitoring
report must therefore show strategy MaxDD, QQQ MaxDD on identical dates,
drawdown difference, underwater duration, and recovery duration where
observable. Return outperformance with materially worse drawdown must remain a
risk exception, not a successful validation by itself.

## 13. Statistical plan

Do not automatically reuse the historical Phase8B p-value machinery. Before
observations begin, an external audit must freeze a prospective plan using
paired daily strategy/QQQ returns, an explicit serial-dependence treatment,
limited-sample caveats, and one primary hypothesis. If all four frequencies
are shadowed, the family and multiplicity treatment must be declared before the
first observation. A minimum sample-adequacy rule is
`PROPOSED_NOT_FROZEN`.

Prospective p-values are not calculated by this draft and historical p-values
are not reused as prospective evidence. Descriptive metrics may be displayed
with a clear small-sample warning.

## 14. Future DSR

Historical DSR is not retrofitted. If a future DSR is desired, the separately
audited prospective protocol must define one trial, comparable trial Sharpe
observations, the immutable trial universe, dependence/effective-trial
treatment, and an append-only trial registry before any results are observed.
Otherwise DSR remains outside the prospective validation protocol.

## 15. Anti-overfitting governance

During validation, prohibit MA200 modification; changing frequency after seeing
prospective results; changing QLD leverage; adding indicators, VIX, momentum,
or volatility states; changing slippage assumptions to improve results;
excluding bad periods; resetting the validation start; restarting after losses;
changing the benchmark; or redefining pass/fail thresholds. Any such change
invalidates the current prospective version and requires a new separately
labeled protocol, commit, tag, and audit.

## 16. Monitoring reports

The future implementation should produce, without being implemented here:

1. a daily operational log;
2. a per-rebalance report;
3. a monthly validation report;
4. a quarterly evidence report;
5. an incident report; and
6. a final validation report.

Monthly and quarterly reports must not make early pass/fail declarations unless
a predeclared hard failure condition has occurred. Reports must retain raw
inputs, corrected values, hashes, and the exact software commit.

## 17. Paper-to-live boundary

This draft authorizes no live capital and cannot automatically promote a model
to live trading. A future stage named `SMALL_CAPITAL_LIVE_VALIDATION` may be
considered only after prospective paper validation is externally/manual
audited and accepted. That future stage requires its own frozen protocol and
decision record.

## 18. Prospective Freeze Decisions

The companion `docs/paper_trading_protocol_decision_table.csv` records each
decision, its Research v1 status, proposed rule, rationale, selection-bias risk,
and status. Every unresolved decision is `PROPOSED_NOT_FROZEN`.

## 19. Implementation boundary and required audit actions

This task creates no daemon, scheduler, broker connector, order simulator,
observation writer, or prospective report generator. Before any implementation
or observation collection, audit the decision table, freeze a final protocol
version, audit the implementation, perform a dry-run, and record a new start
timestamp. No Phase 9 is created by this draft.
