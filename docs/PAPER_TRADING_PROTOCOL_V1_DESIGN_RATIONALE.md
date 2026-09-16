# Paper-Trading Protocol v1 — Prospective Design Rationale

**Status: PROPOSED_NOT_FROZEN**  
**Scope:** design remediation only; no engine, start timestamp, or prospective
observations  
**Historical reference:** immutable Research v1.0,
`research-v1.0-final` → `2b2bf987f2e00540412d263a8ef39566af1d1e2a`

This note explains the choices proposed before any prospective observation
exists. It is intentionally separate from the frozen historical research. It
does not rerun a backtest, inspect historical performance to tune a rule, or
authorize paper or live capital.

## Why the primary frequency is weekly

The primary frequency is proposed for information density, operational feedback,
responsiveness, and prospective statistical efficiency. The choice is not a
historical-performance ranking and remains `PROPOSED_NOT_FROZEN`.

## Primary model and frequency roles

The primary model is exactly `FIXED_MA200_QQQ_TO_QLD`: QQQ adjusted close,
SMA 200 complete observations, close-`t` information, earliest next eligible
U.S. open, 100% QLD above the average and 100% CASH otherwise, 0 bps
commission, 5 bps baseline slippage, zero cash return, and the accepted
20.315% simplified average-cost immediate-tax ledger. No indicator, leverage,
parameter, or state is added.

The proposed primary schedule is:

`PRIMARY_PROSPECTIVE_SCHEDULE = WEEKLY`

This choice is based only on considerations available before collection:

- weekly has the highest scheduled observation density among the four existing
  calendars;
- more scheduled observations make timestamp, holiday, stale-data, and fill
  defects easier to discover promptly;
- a weekly review is operationally tractable while being more responsive to a
  real MA200 state change than slower schedules;
- the daily paired-return stream supplies more prospective information for one
  predeclared comparison; and
- the rule is independent of any realized return, drawdown, Sharpe, p-value,
  multiplicity result, or survival count.

Monthly, bimonthly, and quarterly remain
`ROBUSTNESS_SHADOW_SCHEDULE`. They use the same source, capital, benchmark,
calendar, tax, and execution rules. They are descriptive robustness evidence,
not contestants. A shadow cannot trigger PASS, and no future shadow return can
change the primary schedule. A later frequency or live decision needs a new
externally audited and frozen protocol.

`PRIMARY_INFERENCE` therefore means one weekly Fixed MA200 versus QQQ paired
comparison. `ROBUSTNESS_SHADOW_EVIDENCE` means the three slower schedules and
the optional Phase7A non-decision comparator. This separation prevents a
four-frequency winner exercise and keeps multiplicity to one confirmatory
hypothesis.

## Why a finite horizon is proposed

The core horizon is 36 calendar months from one future frozen start. It gives a
bounded mandatory evaluation and does not claim to validate long-run CAGR. A
clock that waits for an arbitrary number of profitable crossings can become an
unbounded optional-stopping exercise, especially for a slow MA200 rule and
quarterly shadow. The core horizon is therefore a governance boundary, not a
promise of statistical power.

At month 36, the information inventory is reported without substituting one
event type for another:

1. scheduled rebalance observations are operational opportunities;
2. actual target-state changes are mechanism/economic events;
3. completed position episodes are the only observations used for holding
   periods; and
4. adverse/regime-transition observations are risk-coverage diagnostics.

No arbitrary crossing or episode count is required merely to force PASS or
FAIL. At least 500 valid paired daily sessions, reconstructable weekly records,
and enough state/episode information to interpret the mechanism are proposed
as the adequacy diagnostic. If the state barely changes or the adverse regime
never appears, the valid result can be
`PROSPECTIVE_VALIDATION_INCONCLUSIVE`.

There is one and only one finite extension: if the month-36 result is
INCONCLUSIVE, a 12-calendar-month extension may run under the unchanged
original start, model, frequency roles, thresholds, benchmark, and source
architecture. The maximum is 48 months from the original start. There is no
second extension, threshold/parameter/frequency change, reset, deletion of
the first 36 months, or repeated extension until PASS. All of these decisions
remain `PROPOSED_NOT_FROZEN`.

## Primary question and outcome separation

The primary question is:

> Does the frozen Fixed MA200 strategy execute faithfully on genuinely unseen
> observations and produce paired benchmark-relative return evidence in the
> direction predicted by Research v1.0, without unacceptable implementation
> degradation or materially unacceptable drawdown deterioration?

This question does not reduce validation to a three-year CAGR. It requires
faithful data/order/fill records, a paired relative-return direction, and
predeclared risk and implementation limits.

The four labels are not interchangeable:

- `PROTOCOL_INVALID` means the evidence boundary was broken (unauthorized code,
  silent observation rewrite, benchmark/start reset, unrecoverable provenance,
  or unapproved parameter/frequency change). It is not an economic loss.
- `PROSPECTIVE_VALIDATION_FAIL` means the protocol remained valid but a
  predeclared economic, risk, accounting, or implementation limit failed.
- `PROSPECTIVE_VALIDATION_INCONCLUSIVE` means the protocol remained valid but
  information cannot distinguish PASS from FAIL at the core horizon or after
  the one permitted extension.
- `PROSPECTIVE_VALIDATION_PASS` requires intact fidelity, reconstructability,
  adequate information, no failed hard limit, and the paired-return/risk/
  implementation/accounting evidence specified before observations.

Separating these states prevents an implementation defect from being called a
strategy failure and prevents an information shortfall from being called a
success.

## Numerical guardrail derivation

The registry at `docs/paper_trading_threshold_registry.csv` is authoritative
for proposed numbers. Each number is assigned exactly one derivation class:
`ORIGINAL_FROZEN_OBJECTIVE`, `IMPLEMENTATION_TOLERANCE`,
`STATISTICAL_DESIGN`, `ACCOUNTING_IDENTITY`, or `GOVERNANCE_LIMIT`. No value is
justified by finding a historical level that would have passed.

| Guardrail | Proposal | Class | Why it is fixed before observations |
|---|---:|---|---|
| Core horizon | 36 calendar months | STATISTICAL_DESIGN | Bounded information collection with a mandatory review. |
| Single extension | 12 calendar months, maximum 48 total | STATISTICAL_DESIGN / GOVERNANCE_LIMIT | One fixed addition handles INCONCLUSIVE without optional stopping. |
| Paired-session adequacy | 500 valid daily sessions | STATISTICAL_DESIGN | A minimum for an interpretable HAC estimate, not a trade or crossing quota. |
| HAC lag cap | 20 sessions | STATISTICAL_DESIGN | Limits long-lag instability while the lag formula scales with `n`. |
| Confidence level / alpha | 95% two-sided / 0.05 one-sided | STATISTICAL_DESIGN | Conventional uncertainty and directional error rates declared in advance. |
| Negative excess floor | −2 percentage points annualized | STATISTICAL_DESIGN | Distinguishes material harmful degradation from uncertainty near zero. |
| Observed slippage | p95 absolute ≤25 bps | IMPLEMENTATION_TOLERANCE | Conservative deviation flag relative to the immutable 5-bps model assumption. |
| Tracking difference | p95 absolute ≤50 bps | IMPLEMENTATION_TOLERANCE | Detects material implementation drift without changing the model path. |
| Signal-to-order latency | ≤5 minutes | IMPLEMENTATION_TOLERANCE | Detects delayed decision capture while allowing ordinary order logging. |
| Order-to-fill latency | ≤15 minutes | IMPLEMENTATION_TOLERANCE | Detects delayed next-open recording; it is not a return target. |
| Stale close | Incident after 15 minutes | IMPLEMENTATION_TOLERANCE | Deterministic freshness boundary and fail-closed handling. |
| Strategy MaxDD | below −60% is hard failure | GOVERNANCE_LIMIT | Severe-loss governance limit, not a claim of QQQ dominance. |
| Drawdown difference | below −10 percentage points is hard failure | GOVERNANCE_LIMIT | Predeclared material deterioration versus the identical-date benchmark. |
| Annual turnover | ≤6.0× | GOVERNANCE_LIMIT | Controls operational burden using the canonical contemporaneous denominator. |
| NAV/tax reconciliation | absolute difference ≤$0.01 | ACCOUNTING_IDENTITY | Cent-level serialization/rounding tolerance, not an economic allowance. |
| Tax rate | 20.315% | ORIGINAL_FROZEN_OBJECTIVE | Carried unchanged from the accepted simplified ledger. |
| Commission/slippage model | 0 bps / 5 bps | ORIGINAL_FROZEN_OBJECTIVE | Preserves the accepted economic path; observed fills are diagnostics only. |

The original historical objectives remain visible and unchanged: Goal A is
`strategy MaxDD >= QQQ MaxDD`; Goal B is `MaxDD >= -45%`; Goal C is
`MaxDD >= -50%`. They are evidence fields, not a redefined dominance claim.

## Execution and stale-data governance

The 5-bps slippage and zero commission are `MODEL_ASSUMPTION`. Official
next-open observations, actual slippage, tracking difference, and latencies are
`OBSERVED_IMPLEMENTATION_DIAGNOSTIC`. An observation outside tolerance does not
permit retuning the model. Missing/stale closes, missing next opens, delayed
vendors, partial sessions, halts, and source disagreements fail closed, create
an append-only incident, and never create a synthetic favorable price.

The proposed source architecture has one authoritative timestamped feed and an
independent backup/reconciliation feed. Both must expose raw and adjusted
fields, corporate actions, official session timestamps, revisions, and stable
hashes. Vendor identity remains `PROPOSED_NOT_FROZEN` until operations complete
that acceptance check; the architecture itself cannot be changed silently.

## Tax and turnover preservation

The future ledger keeps the 20.315% simplified rate, average-cost basis,
realized gains/losses, immediate payment, and wealth after tax paid to date.
Turnover uses contemporaneous open-before-trade equity, excludes initial
deployment and hypothetical terminal liquidation, and is annualized by
calendar years. Holding periods use completed trading-session episodes only.
Terminal liquidation is a non-mutating diagnostic: no SELL, turnover, holding
period, or tax-ledger mutation. A cent-level NAV and tax reconciliation is a
hard accounting check; a broken or unreconstructable ledger is
`PROTOCOL_INVALID`.

## Why no historical threshold tuning occurred

The remediation does not read a historical metric to choose weekly, does not
search for a drawdown or slippage level that the old path would pass, and does
not reuse a historical p-value. The original objectives are carried as
`ORIGINAL_FROZEN_OBJECTIVE`; operational limits come from conservative
implementation feasibility; information limits come from the predeclared
statistical design; and reconciliation limits come from accounting identity.
This separation is the selection-bias control.

## Paper-to-live boundary

Paper PASS is evidence for an external/manual audit only. It does not authorize
normal deployment. `SMALL_CAPITAL_LIVE_VALIDATION` remains a separate future
protocol requiring its own frozen capital, broker, fill, risk, and decision
controls. No live-capital permission is created here.

All decisions in the companion table and threshold registry remain
`PROPOSED_NOT_FROZEN` pending final protocol audit.
