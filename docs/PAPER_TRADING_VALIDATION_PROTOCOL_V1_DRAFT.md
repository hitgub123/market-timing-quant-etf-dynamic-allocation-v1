# Prospective Paper-Trading Validation Protocol v1.0

**Status: DRAFT FOR AUDIT — NOT FROZEN**  
**Protocol version:** `paper-validation-v1.0-draft`  
**Historical reference:** Research v1.0, tag `research-v1.0-final`  
**Implementation status:** not implemented  
**Observation status:** no prospective observations collected

This is a design remediation, not an engine specification ready for use. It
does not authorize paper trading, a prospective start timestamp, live trading,
or a change to Research v1.0. Every choice introduced below is
`PROPOSED_NOT_FROZEN` and must be externally audited, frozen under a new
commit/tag, and implementation-audited before any observation is counted.

## 1. Scope and immutable boundary

The purpose is to test one already-frozen rule on genuinely unseen future
observations. This document does not develop a strategy, search parameters,
rank frequencies, optimize execution, add indicators, or rescue a historical
objective. It does not run a backtest, create a paper engine, collect an
observation, activate a timestamp, or start Phase 9.

The accepted historical reference remains immutable:

- tag: `research-v1.0-final`;
- accepted commit: `2b2bf987f2e00540412d263a8ef39566af1d1e2a`;
- freeze manifest SHA-256:
  `dcb8f9d79de93c61e0bd7d93b743b0356be9eb3b1467acf5db9a58563889d400`.

The freeze manifest, its companion SHA file, `docs/RESEARCH_V1_FROZEN.md`,
Phase 0–8D canonical code, reports, plots, raw snapshots, and accepted economic
paths are out of scope and must not be rewritten.

## 2. Accepted model boundary

### Primary prospective model

`FIXED_MA200_QQQ_TO_QLD` is the **PRIMARY PROSPECTIVE MODEL**. It is not a new
model: it is the frozen QQQ adjusted-close MA200 rule that maps to QLD or CASH.
No parameter is selected by this remediation.

Research v1.0 semantics are carried forward exactly:

1. signal input is complete, positive, split/dividend-adjusted QQQ close;
2. the moving average is a simple average of exactly 200 completed
   observations; it always uses exactly 200 observations;
3. the information boundary is QQQ close at session `t`;
4. the earliest execution is the next eligible U.S. trading-session open;
5. close above the average maps to 100% QLD, otherwise 100% CASH;
6. commission is 0 bps and the baseline slippage assumption is 5 bps;
7. the simplified taxable account uses 20.315% immediate tax and average-cost
   accounting, with realized gains/losses and zero cash return;
8. there is no same-day execution, leverage change, or additional indicator.
   There is no leverage change.
There is no additional indicator.

### Historical context only

`PHASE7A_FIXED_FOUR_STATE` may be retained only as a **NON-DECISION SHADOW
COMPARATOR**. It cannot change the primary model or determine a frequency.
Phase7B Model A and Model B are historical context only. Phase7B Model A and
Model B are not prospective candidates. The exact boundary is recorded as the
literal statement `Phase7B Model A and Model B are not prospective candidates`.
Their
`NO_ELIGIBLE_PARAMETER` and `CASH_FALLBACK` behavior is not a prospective
candidate. Phase7B cannot trigger a paper PASS.

## 3. Frequency design: one primary and three shadows

Research v1.0 intentionally did not select weekly, monthly, bimonthly, or quarterly.
This remediation resolves the inferential role prospectively while keeping all
four schedules observable. There is no live-frequency choice in this draft.

### Proposed roles (all `PROPOSED_NOT_FROZEN`)

`PRIMARY_PROSPECTIVE_SCHEDULE = WEEKLY`

Status: `PROPOSED_NOT_FROZEN`.

Weekly is defensible on design grounds that are knowable before observations:
it gives the densest scheduled feedback among the four frozen calendars,
provides more opportunities to detect a timestamp, calendar, or fill defect,
responds sooner to a genuine MA200 state change, and has a manageable review
burden. This rationale uses information density, operational observability,
responsiveness, and statistical information—not any realized outcome or
historical performance ranking.

`ROBUSTNESS_SHADOW_SCHEDULE = MONTHLY, BIMONTHLY, QUARTERLY`

The three shadows are run with identical data, capital, benchmark, tax, and
execution conventions. They are descriptive robustness evidence. Their future
returns cannot promote one of them to primary status, and they cannot create
three additional confirmatory opportunities. A future frequency change or
live-frequency decision requires a separately audited and frozen protocol.

The distinction is explicit:

- **PRIMARY_INFERENCE:** one predeclared weekly Fixed MA200 versus QQQ paired
  comparison, with the statistical method in the companion statistical design;
- **ROBUSTNESS_SHADOW_EVIDENCE:** monthly, bimonthly, and quarterly paths,
  plus any Phase7A shadow, reported descriptively and unable to trigger PASS.

No rule in this protocol ranks schedules or makes a performance-ranked
frequency choice after the experiment.

## 4. Prospective start boundary

No prospective start timestamp is activated, and no prospective observation is
present. A future start may be recorded only after all of the following gates:

1. external audit accepts this design remediation;
2. a final protocol is frozen under a new commit and tag;
3. the implementation is audited against the frozen semantics and this
   decision table;
4. an uncounted dry-run proves append-only observation, order, fill, valuation,
   tax, incident, and hash logging.

The future timestamp must be an exact ISO-8601 instant with an explicit offset,
the corresponding U.S. exchange-session date, and `America/New_York` session
timezone. The session date is not an operator's local calendar date. Historical
data already present in Research v1.0 cannot count as prospective evidence.

## 5. Signal, warm-up, and execution convention

The future implementation must use one official U.S. exchange-session calendar.
At a scheduled close, it may use only values available through that close.
There is no interpolation, forward fill, synthetic signal, or favorable fill.

The next eligible session open is the first permissible execution boundary.
Therefore a close-`t` decision cannot trade at open `t`; it can first affect open `t+1`
(or the next eligible session after a holiday). The formal boundary is close-t →
open-t+1. The theoretical order is
created before the fill and retains the signal timestamp, decision, target,
intended session, baseline fill convention, observable price, simulated fill,
quantity, pre-trade NAV, post-trade NAV, cost, and any skip reason.

MA warm-up is a diagnostic, not a reason to manufacture a trade. For QQQ and
the signal/reference series used by a shadow, record for every window used by
the frozen model: first valid MA date, number of pre-start observations,
lookback start at the evaluation start, evaluation start, and missing aligned
targets. No pre-evaluation equity or trade is created. The first evaluation-day
target uses only the previously available 200 complete observations.

## 6. Paper-mode execution diagnostics

Paper validation does not execute a broker transaction. Therefore no quantity
is called realized execution slippage. The canonical economic path always uses
the immutable model assumption:

`MODEL_SLIPPAGE_BPS = 5`

This five-basis-point value is a `MODEL_ASSUMPTION`, not an observed execution
result.

`OBSERVED_SLIPPAGE_PROXY_BPS` is defined only when a reliable market-data
quote or opening-auction record exists. For each eligible order `o`, record:

- `P_ref_o`: official next-open reference price for the instrument and session;
- `P_proxy_o`: same-timestamp executable-side quote, ask for a buy and bid for
  a sell, or a valid opening-auction executable price with a documented source;
- the exchange timestamp, acquisition timestamp, source, quote/auction flag,
  and valid positive prices;
- `side_o = +1` for a buy and `side_o = -1` for a sell.

The signed proxy is

`slippage_proxy_bps_o = 10000 * side_o * (P_proxy_o / P_ref_o - 1)`

and the reported guardrail quantity is

`OBSERVED_SLIPPAGE_PROXY_BPS_o = abs(slippage_proxy_bps_o)`.

It is one value per eligible order, not a rebalance aggregate. The p95 is the
nearest-rank empirical percentile: sort the `m` valid absolute values and take
rank `ceil(0.95 * m)` (one-indexed), after at least **20** valid proxy
observations. If a quote/auction is missing,
delayed beyond the session rule, non-positive, invalid, or otherwise not
reconstructable, that order has no proxy value and no synthetic price is
created. If fewer than 20 valid proxy observations exist, the metric is
`NOT_OBSERVABLE_IN_PAPER_MODE`. The paper report must show that status and may not claim realized slippage. Actual executable slippage is deferred to the
future `SMALL_CAPITAL_LIVE_VALIDATION` stage.

### Tracking difference is a separate metric

`CANONICAL_FILL_TRACKING_DIFFERENCE_BPS` is not NAV reconciliation error. When
the same order has valid `P_canonical_o` and `P_proxy_o`, define:

`tracking_difference_bps_o = 10000 * side_o * (P_canonical_o / P_proxy_o - 1)`

and report its absolute value for p95. This is canonical simulated fill versus
the market-data execution proxy. A separate
`NAV_RECONCILIATION_ERROR_USD = paper_nav - independently_reconstructed_nav`
is an accounting identity checked in dollars; the two metrics are never
combined. The tracking metric and NAV reconciliation are never combined.

### Latency fields are paper-system diagnostics

Record these timestamps and exact differences:

- `signal_to_order_latency_seconds = order_created_at - signal_close_at`;
- `order_generation_latency_seconds = order_recorded_at - decision_ready_at`;
- `market_data_acquisition_latency_seconds = data_acquired_at - exchange_event_at`;
- `simulated_fill_recording_latency_seconds = fill_recorded_at - intended_execution_at`.

The existing 5-minute and 15-minute limits apply to paper-system timestamps
only and are classified `PAPER_SYSTEM_OPERATIONAL_DIAGNOSTIC`. A simulated
order-to-fill interval is not proof of achievable live execution. The baseline
5-bps model assumption is never replaced by any of these diagnostics.

## 7. Data-source architecture and provenance

Before the final freeze, operations must approve a concrete two-source design.
Vendor identity is still `PROPOSED_NOT_FROZEN`; the acceptance requirements
are fixed here:

- **Authoritative signal/valuation source:** a timestamped U.S. market-data
  feed with adjusted and unadjusted OHLC fields, official exchange/session
  timestamps, corporate-action records, revision snapshots, and stable raw
  object hashes. It is the only source allowed to drive a signal or simulated
  fill after acceptance.
- **Backup/reconciliation source:** an independent timestamped feed with the
  same fields and calendar keys. It reconciles every scheduled close and next
  open. A disagreement creates an incident and cannot silently substitute a
  favorable value.

Every record stores source identity, acquisition timestamp, original and
adjusted values, adjustment/corporate-action identifier, revision status,
session date, timezone/offset, software version, Git commit, protocol/model
version, and an observation hash. An append-only correction ledger records
prior hash, replacement hash, vendor explanation, detection time, affected
reports, and auditor disposition. No historical observation is silently
rewritten.

## 8. Fail-closed stale, missing, and partial-session policy

The implementation must fail closed. A missing scheduled close, stale close,
missing next-session open, delayed vendor update, partial session, exchange
halt, or source disagreement creates an incident record with the reason and
timestamps. The order is not filled from an interpolation, last-known value,
midpoint, close, or synthetic favorable price. It is held or skipped according
to the final frozen incident procedure; that procedure cannot invent a price.
An exchange halt is always an incident and never a favorable fill.

For design purposes, a scheduled close acquired more than 15 minutes after the
official close is a proposed stale-data incident. A missing next open means no
fill for that session. A partial or halted session is ineligible until a future
fully eligible session, with no back-dated fill. These rules are
`PROPOSED_NOT_FROZEN` and require operational sign-off before use.

## 9. Benchmark and metrics

QQQ buy-and-hold is the primary benchmark on identical dates, capital base,
calendar, valuation convention, and provenance. Every shadow and the benchmark
start from the same future validation boundary.

Collect performance, implementation, benchmark-relative, and accounting
metrics, but label short-sample quantities as uncertain. Primary paired returns
are daily strategy and QQQ returns on the same valid U.S. sessions. Record
cumulative excess return, daily excess series, confidence interval, direction
consistency, and an after-tax descriptive counterpart.

The future report always shows strategy MaxDD, QQQ MaxDD on identical dates,
the MaxDD difference, underwater duration, recovery duration, and separate
`ORIGINAL_RESEARCH_GOAL_STATUS` fields for Goal A, Goal B, and Goal C. The
paper result is a separate `PAPER_PROTOCOL_RESULT` field.

Turnover preserves the audited definition: use contemporaneous open-before-trade
equity (`pretrade_equity`), sum `abs(trade_notional) / pretrade_equity`, divide
by calendar years, and exclude initial portfolio deployment and hypothetical
terminal liquidation. Holding periods count completed position episodes in
trading sessions only; open terminal positions are not completed episodes.

Tax preserves the audited simplified account: 20.315% immediate tax,
average-cost basis, realized gains/losses, and tax-paid-to-date wealth. A
terminal-liquidation wealth/tax/cost/unrealized-gain diagnostic is
non-mutating: it creates no SELL, does not enter turnover or holding-period
statistics, and does not mutate the ledger.

## 10. Finite horizon and information adequacy

### Core horizon

The proposed core evaluation horizon is **36 calendar months** from the one
frozen prospective start. A mandatory evaluation occurs at the core end date.
Status: `PROPOSED_NOT_FROZEN`.
The clock is finite and cannot be reset, shortened after an unfavorable result,
or silently extended because an event did not occur. This horizon is a design
proposal, not evidence that three years validates long-run CAGR.

### What is counted

The report keeps four non-interchangeable inventories:

1. **scheduled rebalance observations** — calendar opportunities (weekly is the
   primary operational count; the other three are shadows);
2. **actual target-state changes** — orders caused by a changed MA200 state;
3. **completed position episodes** — opened and closed episodes used for
   holding-period statistics;
4. **adverse/regime-transition observations** — ex-ante defined stress or
   transition diagnostics.

Scheduled observations are operational evidence. State changes and completed
episodes are economic/mechanism evidence. Adverse observations are risk and
information-adequacy diagnostics. None is substituted for another, and no
arbitrary count of crossings is imposed merely to force a verdict. The report
must show zero/low counts explicitly.

### Adequacy and finite extension

At 36 months, information adequacy is deterministic:

```text
information_adequate = (
    n_valid >= 500
    and n_primary_scheduled >= 1
    and is_finite(mean_excess_ann)
    and is_finite(hac_se)
    and is_finite(ci95_two_sided_lower)
    and is_finite(ci95_two_sided_upper)
    and is_finite(ci95_one_sided_lower)
    and is_finite(cumulative_excess)
)
```

Mechanism information is limited exactly when:

```text
MECHANISM_INFORMATION_LIMITED = (
    n_state_changes == 0 or n_completed_episodes == 0
)
```

`MECHANISM_INFORMATION_LIMITED = TRUE` deterministically produces INCONCLUSIVE
after protocol and hard-gate checks. `n_adverse_observations` is reported as a
risk diagnostic but is not a discretionary event quota. There is no operator
judgment about whether the mechanism is “enough” to interpret.

If and only if the 36-month result is `PROSPECTIVE_VALIDATION_INCONCLUSIVE`, one
fixed **12-calendar-month extension** may be opened under the same start date,
model, schedule, thresholds, benchmark, and data architecture. The extension
ends at 48 months from the original start. There is no second extension, no
parameter/threshold/frequency change, no reset, no deletion of the first 36
months, and no repeated extension until PASS. The extension rule is
`PROPOSED_NOT_FROZEN`; after 48 months the final result is PASS, FAIL, or
INCONCLUSIVE under the same criteria.
The permitted extension is exactly one fixed **12-calendar-month extension**.

## 11. Primary prospective question and outcome states

The primary question is:

> Does the frozen Fixed MA200 strategy execute faithfully on genuinely unseen
> observations and produce paired benchmark-relative return evidence in the
> direction predicted by Research v1.0, without unacceptable implementation
> degradation or materially unacceptable drawdown deterioration?

This is a question about faithful execution, paired relative evidence, and
predeclared risk/implementation limits. A 36-month CAGR estimate alone cannot
validate a long-run timing strategy.

The outcomes are distinct:

### `PROTOCOL_INVALID`

The evidence is invalid because strategy code or semantics changed without
authorization, an observation was silently rewritten, the benchmark or start
boundary changed, a material provenance gap is unrecoverable, or an
unapproved parameter/frequency/reset occurred. This is not an economic failure;
it requires a new labeled protocol, commit, tag, and audit.

### `PROSPECTIVE_VALIDATION_FAIL`

The protocol remains valid, but a predeclared economic, risk, accounting, or
implementation guardrail fails. It is not relabeled as a protocol defect.

### `PROSPECTIVE_VALIDATION_INCONCLUSIVE`

The protocol remains valid, but information is insufficient to distinguish PASS
from FAIL at the core evaluation or after the one permitted extension. This is
a valid reason for `PROSPECTIVE_VALIDATION_INCONCLUSIVE`, not an operator
choice.

### `PROSPECTIVE_VALIDATION_PASS`

PASS requires intact fidelity, reconstructable operations, adequate primary
information, no failed hard guardrail, and evidence satisfying the predeclared
paired-return, drawdown, implementation, turnover, and accounting rules. The
confirmatory return condition is strict:

`PRIMARY_RETURN_PASS = (ci95_one_sided_lower > 0 and cumulative_excess > 0)`.

A positive point estimate alone cannot PASS. A positive point estimate alone
never produces PASS. No shadow can independently
trigger PASS.

The machine-readable priority table and pseudocode are in
`docs/paper_trading_outcome_decision_table.csv` and
`docs/PAPER_TRADING_OUTCOME_DECISION_SPEC.md`. They define every equality
boundary and return exactly one `PAPER_PROTOCOL_RESULT`.

The original objectives are a separate output family. The protocol always
emits `ORIGINAL_RESEARCH_GOAL_STATUS` for Goal A, Goal B, and Goal C under
their original frozen definitions. `PAPER_PROTOCOL_PASS_DOES_NOT_IMPLY_ORIGINAL_GOAL_PASS`.

## 12. Proposed economic and risk guardrails

All numerical values below are proposals registered in
`docs/paper_trading_threshold_registry.csv`. Each has a derivation class and
rationale. None was tuned to a historical pass.

### Benchmark-relative evidence

Use the weekly paired daily excess series and the deterministic function in the
outcome specification. The exact return regions are:

- **strong positive:** `ci95_one_sided_lower > 0` and
  `cumulative_excess > 0` → PASS after information and hard gates;
- **positive estimate with a zero-crossing two-sided interval** → INCONCLUSIVE;
- **near-zero estimate** (`mean_excess_ann == 0`) → INCONCLUSIVE;
- **negative estimate with an interval including zero** → INCONCLUSIVE;
- **statistically negative but economically small**
  (`ci95_two_sided_upper < 0` and `>= -0.02`) → INCONCLUSIVE;
- **confidently below the material-harm floor**
  (`ci95_two_sided_upper < -0.02`) → FAIL;
- **inadequate information** → INCONCLUSIVE.

Equality is explicit: a one-sided lower bound of exactly zero is not PASS; a
two-sided upper bound of exactly `-0.02` is not below the harm floor and is not
FAIL; a cumulative excess of exactly zero is not positive. After-tax excess is
descriptive and cannot replace the primary pre-tax hypothesis.

### Drawdown

On identical dates record strategy MaxDD, QQQ MaxDD, drawdown difference,
underwater duration, and recovery duration. Keep the original frozen objectives
visible and unchanged:

- Goal A: `strategy MaxDD >= QQQ MaxDD` under the negative convention;
- Goal B: `MaxDD >= -45%`;
- Goal C: `MaxDD >= -50%`.

Those are historical objectives and evidence fields, not a claim of dominance.
The prospective limits are explicitly
`PAPER_SEVERE_RISK_GOVERNANCE_LIMIT`: strategy MaxDD below **-60%** is a hard
paper failure, and a strategy drawdown difference worse than **-10 percentage
points** versus QQQ is a hard paper failure. They are not
`ORIGINAL_RESEARCH_OBJECTIVE` values. These limits do not make Goals A, B, or
C easier and do not assert QQQ dominance.
The severe-risk labels are not `ORIGINAL_RESEARCH_OBJECTIVE` values.

The future report shows strategy MaxDD, QQQ MaxDD, MaxDD difference, Goal A risk
status, Goal B risk status, and Goal C risk status beside the paper governance
limits. `PAPER_PROTOCOL_PASS_DOES_NOT_IMPLY_ORIGINAL_GOAL_PASS`.

### Implementation, turnover, and accounting

- p95 observed absolute slippage ≤ **25 bps**;
- p95 absolute tracking difference ≤ **50 bps**;
- signal-to-order latency ≤ **5 minutes**;
- order-to-fill latency ≤ **15 minutes**;
- annual turnover ≤ **6.0x** under the canonical denominator;
- tax and NAV reconciliation absolute difference ≤ **$0.01**;
- tax-ledger reconciliation absolute difference ≤ **$0.01**.

Exceeding a hard implementation, turnover, or reconciliation limit is FAIL if
the protocol remains reconstructable; an unreconstructable or silently changed
record is PROTOCOL_INVALID. The 5-bps baseline remains a model assumption even
when an observed diagnostic is outside tolerance.

## 13. Prospective statistical design summary

Only the weekly Fixed MA200 versus QQQ comparison is confirmatory. Define

`d_t = strategy_daily_return_t - qqq_daily_return_t`

on identical valid U.S. sessions. The primary statistic is the mean of `d_t`,
reported in daily and annualized units with a two-sided 95% Newey–West/HAC
confidence interval. The predeclared lag is

`L = min(20, floor(4 * (n / 100)^(2/9)))`.

The directional hypothesis is H0: expected paired excess return ≤ 0 versus H1:
expected paired excess return > 0, with one-sided alpha 0.05 used only if the
sample-adequacy gate is met. The decision remains evidence-based: uncertainty
compatible with zero is INCONCLUSIVE rather than an automatic failure. Missing
sessions are excluded only when both series are unavailable and are logged;
there is no imputation or favorable carry. No prospective p-value is calculated
by this remediation because no observations exist.

Monthly, bimonthly, and quarterly shadows are descriptive. They cannot create
additional confirmatory hypotheses or independently trigger PASS. Any future
secondary inferential family requires a new frozen multiplicity decision.

The complete method, assumptions, and design-only power table are in
`docs/PAPER_TRADING_PROTOCOL_V1_STATISTICAL_DESIGN.md`.

The exact terminal decision function, including `n_valid`, `mean_excess_ann`,
`hac_se`, both two-sided bounds, the one-sided lower bound,
`cumulative_excess`, `information_adequate`, `protocol_valid`, every hard gate,
and equality boundaries is in
`docs/PAPER_TRADING_OUTCOME_DECISION_SPEC.md`. No operator may choose among
PASS, FAIL, or INCONCLUSIVE after seeing the result.

## 14. Design-only power and information analysis

The companion analysis uses hypothetical annualized excess effects of 0%, 2%,
4%, and 6%, 252 sessions per year, an illustrative annualized paired-return
standard deviation of 1.5%, and AR(1) serial correlation `phi = 0.25`. It uses
`n_eff = n * (1 - phi) / (1 + phi)` only to illustrate information loss. These
are transparent design assumptions, not realized strategy estimates, and are
not a backtest. The table covers 12, 24, and 36 months and the one permitted
48-month extension. It demonstrates what the horizon can and cannot establish;
it does not alter the 36-month proposal. The illustrative 1.5% volatility and
AR(1) phi=.25 are **not used in PASS/FAIL**, are **not estimates of future
strategy volatility**, and do **not justify the 36-month horizon by
themselves**. Actual prospective HAC uncertainty controls the return inference.

## 15. Monitoring and early stopping

Monthly and quarterly monitoring may detect protocol invalidation, data/ops
incidents, or a predeclared severe-risk breach. It may not change MA200,
frequency, threshold, slippage, benchmark, or change start date, exclude bad periods,
restart after losses, or declare success because interim performance is good.
There is **NO EARLY-SUCCESS RULE**. An early economic stop is permitted only for
the severe-risk hard limits already registered (for example MaxDD below -60%),
with incident evidence and no performance-based reset.

## 16. Anti-overfit and change control

Changing the strategy, MA200, close-to-next-open boundary, QLD/CASH mapping,
tax treatment, benchmark, data source without acceptance, schedule role,
threshold, or start boundary invalidates this protocol version. Such a change
requires a new protocol identifier, commit, tag, decision table, and external
audit. No optimizer, selector, historical backtest, Phase 9, or prospective
parameter search is introduced here.

## 17. Paper-to-live boundary

Paper PASS does not authorize normal live deployment. A separate future stage,
`SMALL_CAPITAL_LIVE_VALIDATION`, may be considered only after paper artifacts
and incidents are externally/manual audited and accepted. That stage needs its
own frozen protocol, capital limits, broker/fill controls, and decision record.
This remediation grants no live-capital authorization and does not design the
live engine. This draft authorizes no live capital.

## 18. Required prospective handoff package

After paper validation, an external/manual auditor must receive the immutable
protocol and commit, complete observation/order/fill/NAV/tax/incident ledgers,
source snapshots and revisions, raw and adjusted prices, calendar evidence,
primary weekly paired-return analysis, all three shadow reports, drawdown and
turnover reconciliations, threshold-breach evidence, and the final PASS/FAIL/
INCONCLUSIVE or PROTOCOL_INVALID decision. No live decision is implied.

## 19. Decision table and implementation boundary

`docs/paper_trading_protocol_decision_table.csv` is the companion contract. It
uses the columns `decision_id,issue,current_draft_rule,remediated_proposal,
rationale,threshold_derivation,selection_bias_control,statistical_role,status`.
Every row is `PROPOSED_NOT_FROZEN`; nothing is frozen by this remediation.

The terminal outcome contract is separately machine-readable in
`docs/paper_trading_outcome_decision_table.csv` and specified in
`docs/PAPER_TRADING_OUTCOME_DECISION_SPEC.md`. The future reporting
specification must emit both `PAPER_PROTOCOL_RESULT` and
`ORIGINAL_RESEARCH_GOAL_STATUS`, including the two paper severe-risk limits
and all Goal A/B/C fields.

This task creates no daemon, scheduler, broker connector, order simulator,
observation writer, or prospective report generator. It does not collect
official observations, activate a start timestamp, freeze the protocol, create
`paper-validation-v1.0-final`, or start Phase 9.
This design does not collect official observations and does not activate a
prospective start.

Design-status register (every item remains `PROPOSED_NOT_FROZEN`):

- model boundary: `PROPOSED_NOT_FROZEN`;
- primary schedule and shadows: `PROPOSED_NOT_FROZEN`;
- start/session boundary: `PROPOSED_NOT_FROZEN`;
- data source and revision policy: `PROPOSED_NOT_FROZEN`;
- execution and stale-data policy: `PROPOSED_NOT_FROZEN`;
- finite horizon and extension: `PROPOSED_NOT_FROZEN`;
- information-adequacy rule: `PROPOSED_NOT_FROZEN`;
- statistical method and multiplicity: `PROPOSED_NOT_FROZEN`;
- risk, implementation, turnover, and tax guardrails: `PROPOSED_NOT_FROZEN`;
- paper-to-live boundary: `PROPOSED_NOT_FROZEN`.

PAPER TRADING PROTOCOL V1 DESIGN REMEDIATION — DRAFT ONLY

## 20. Operational freeze-preparation references

The accepted statistical/economic design remains closed. Operational details
prepared for a future external Operational Freeze Audit are specified in:

- `docs/PAPER_TRADING_DATA_SOURCE_SPEC.md` and
  `docs/paper_trading_data_source_decision.csv`;
- `docs/PAPER_TRADING_CALENDAR_SPEC.md`;
- `docs/PAPER_TRADING_LEDGER_SCHEMA.md` and `schemas/paper_trading/`;
- `docs/PAPER_TRADING_ENVIRONMENT_SPEC.md`;
- `docs/PAPER_TRADING_OPERATIONAL_RUNBOOK.md`;
- `docs/paper_trading_incident_taxonomy.csv`;
- `docs/PAPER_TRADING_DRY_RUN_ACCEPTANCE.md`;
- `docs/PAPER_TRADING_IMPLEMENTATION_ACCEPTANCE_SPEC.md`;
- `docs/PAPER_TRADING_GOLDEN_FIXTURE_SPEC.md`;
- `docs/paper_trading_operational_decision_registry.csv`;
- `docs/PAPER_TRADING_ACCEPTANCE_MANIFEST_SPEC.md`.

These are all `PROPOSED_NOT_FROZEN`. This preparation does not create the
final acceptance manifest, select live credentials, implement a production
paper engine, start a scheduler, activate a prospective start, collect an
official observation, or alter any closed statistical/economic threshold.
This preparation does not create the final acceptance manifest.
