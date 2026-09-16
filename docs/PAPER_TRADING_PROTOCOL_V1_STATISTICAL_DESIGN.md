# Paper-Trading Protocol v1 — Prospective Statistical Design

**Status: PROPOSED_NOT_FROZEN**  
**Observations:** none; no prospective statistic or p-value has been computed  
**Scope:** design-only inference plan, not a backtest

This document predeclares the inferential role of the future paper experiment.
It does not read or regenerate a historical strategy path, select a frequency
from historical results, or authorize a start timestamp.

## Primary schedule and hypothesis

The sole primary inferential schedule is
`PRIMARY_PROSPECTIVE_SCHEDULE = WEEKLY`. The primary comparison is

`FIXED_MA200_QQQ_TO_QLD_WEEKLY` versus `QQQ_BUY_AND_HOLD`.

For each valid common U.S. session `t`, define the paired excess return

`d_t = strategy_daily_return_t - qqq_daily_return_t`.

The primary statistic is the arithmetic mean of `d_t`, reported in daily units
and annualized by 252 sessions. The directional hypotheses are:

**Primary hypothesis:** the weekly paired mean excess return is positive while
the implementation and risk gates remain within their predeclared limits.

- H0: expected paired excess return ≤ 0;
- H1: expected paired excess return > 0.

The primary economic question also requires faithful reconstruction and no
unacceptable implementation or drawdown degradation. A positive mean is not by
itself a deployment recommendation, and a three-year CAGR is not treated as
long-run validation.

## Inference method and serial dependence

Use a Newey–West heteroskedasticity-and-autocorrelation-consistent (HAC)
standard error for the mean of `d_t`. The lag is frozen by the rule

`L = min(20, floor(4 * (n / 100)^(2/9)))`,

where `n` is the number of valid paired daily sessions. The cap and formula are
statistical-design guardrails, not values estimated from a historical path.

Report a two-sided 95% HAC confidence interval. If `n >= 500` and all fidelity
and risk/implementation gates are intact, a one-sided alpha of 0.05 may be used
for the predeclared directional decision. This plan does not require a
significance label when the sample is underpowered: an interval compatible with
both zero and harmful degradation is `PROSPECTIVE_VALIDATION_INCONCLUSIVE`, not
an automatic PASS or FAIL. No prospective p-value is calculated in this design
remediation because observations do not yet exist.

## Missing sessions and pairing

Pair only the same eligible U.S. session dates for which both the strategy and
QQQ valuation are reconstructable. Missing or stale inputs are not imputed,
forward-filled, or replaced with a favorable value. Each omission is recorded
in the incident ledger with the source, timestamp, reason, and affected order
or return. If valid paired sessions remain below 500 at the mandatory horizon,
the result is INCONCLUSIVE unless the fixed extension rule applies.

## Multiplicity and shadows

There is one confirmatory hypothesis: the weekly Fixed MA200 versus QQQ
comparison. Monthly, bimonthly, and quarterly are
`ROBUSTNESS_SHADOW_EVIDENCE`; they show schedule sensitivity descriptively and
cannot independently trigger PASS. The optional Phase7A comparator is also
non-decision context. No three additional confirmatory opportunities are
created, and no post-result multiplicity adjustment or frequency ranking is
introduced. A future secondary inferential family would require a separately
frozen protocol before observations.

## Economic evidence rule

At the 36-month core end (or the single permitted 48-month maximum after an
INCONCLUSIVE core result), report cumulative paired excess, mean daily excess,
the HAC interval, direction consistency, and an after-tax descriptive series.

- Directional evidence is positive when cumulative excess and the mean point
  estimate are positive.
- A HAC interval whose annualized upper and lower bounds remain below the
  proposed −2 percentage-point material-harm floor is an economic FAIL.
- A positive point estimate with uncertainty spanning zero or the harm floor
  is INCONCLUSIVE, provided no hard risk or implementation failure occurs.
- PASS requires adequate information, no hard guardrail failure, and positive
  directional evidence together with the fidelity, implementation, drawdown,
  turnover, and accounting gates in the protocol.

The floor is a prospective design/governance limit, not an observed estimate.
After-tax excess is a descriptive burden/evidence view and cannot replace the
primary pre-tax hypothesis.

## Horizon and information adequacy

The core horizon is 36 calendar months from one frozen start. At its end,
record scheduled observations, actual target-state changes, completed position
episodes, and adverse/regime-transition observations separately. The absence
of a crossing or adverse event can make a valid experiment INCONCLUSIVE; no
crossing quota is used to force PASS or FAIL.

Only an INCONCLUSIVE core result may open one fixed 12-calendar-month
extension. The original start, model, weekly primary, shadow roles, thresholds,
benchmark, and all first-period records remain unchanged. The maximum horizon
is 48 months. There is no repeated extension or reset.

## Design-only power and information analysis

The following calculation is illustrative planning information, not a
backtest. It assumes 252 sessions per year, hypothetical annualized excess
effects of 0%, 2%, 4%, and 6%, illustrative annualized paired-return standard
deviation of 1.5%, and AR(1) serial correlation `phi = 0.25`. Effective sample
size is approximated as

`n_eff = n * (1 - phi) / (1 + phi)`.

The interval half-width uses `1.96 * sigma_daily / sqrt(n_eff) * 252` and the
power column is the approximate one-sided alpha=.05 normal-theory power. The
1.5% volatility is a transparent low-noise illustration only; it is not a
historical estimate or a forecast. A higher-noise assumption would widen the
interval and lower power.

| Horizon | Nominal sessions | Effective sessions | 95% CI half-width (annualized pp) | Approx. power at 0% | at 2% | at 4% | at 6% |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 12 months | 252 | 151.2 | 3.80 | 0.050 | 0.270 | 0.663 | 0.927 |
| 24 months | 504 | 302.4 | 2.68 | 0.050 | 0.427 | 0.899 | 0.997 |
| 36 months | 756 | 453.6 | 2.19 | 0.050 | 0.557 | 0.973 | 1.000 |
| 48 months (maximum) | 1008 | 604.8 | 1.90 | 0.050 | 0.663 | 0.994 | 1.000 |

The table shows that even at 36 months, modest effects may remain uncertain.
It does not guarantee power, alter the 36-month horizon, or permit extending
until a preferred outcome. No realized historical excess return is used as an
effect-size input.

## Interpretation limits

HAC inference addresses dependence in paired daily returns; it does not prove
causality, future regime coverage, or long-run CAGR. Drawdown, tail loss,
implementation degradation, tax burden, skipped observations, and data
provenance remain separate gates. The three shadows are descriptive only.
`PROTOCOL_INVALID` is reserved for a broken evidence boundary, while FAIL and
INCONCLUSIVE apply to a valid protocol. Paper PASS remains subject to external
manual audit and does not authorize live capital.

All values and roles remain `PROPOSED_NOT_FROZEN` pending final protocol audit.
