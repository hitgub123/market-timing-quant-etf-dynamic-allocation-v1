# Paper-Trading Outcome Decision Specification

**Status:** `PROPOSED_NOT_FROZEN`  
**Scope:** deterministic prospective outcome logic; no engine and no
observations

This specification is the mechanical contract for a future paper-validation
run. It does not calculate a historical or prospective statistic now. It uses
only values produced by the future append-only observation, order, valuation,
incident, and accounting ledgers.

## 1. Outputs and priority

The function returns exactly one `PAPER_PROTOCOL_RESULT` from:

- `PROTOCOL_INVALID`;
- `PROSPECTIVE_VALIDATION_FAIL`;
- `PROSPECTIVE_VALIDATION_INCONCLUSIVE`; or
- `PROSPECTIVE_VALIDATION_PASS`.

It also returns the separate `ORIGINAL_RESEARCH_GOAL_STATUS` object containing
Goal A, Goal B, and Goal C statuses under their unchanged definitions. A paper
PASS does not imply any original goal passed:

`PAPER_PROTOCOL_PASS_DOES_NOT_IMPLY_ORIGINAL_GOAL_PASS`

Priority is strict and ordered:

1. `protocol_valid == FALSE` → `PROTOCOL_INVALID`;
2. any hard gate is `FAIL` → `PROSPECTIVE_VALIDATION_FAIL`;
3. `information_adequate == FALSE` → `PROSPECTIVE_VALIDATION_INCONCLUSIVE`;
4. `mechanism_information_limited == TRUE` →
   `PROSPECTIVE_VALIDATION_INCONCLUSIVE`;
5. confidently harmful return evidence → `PROSPECTIVE_VALIDATION_FAIL`;
6. the strict primary positive gate → `PROSPECTIVE_VALIDATION_PASS`;
7. every remaining valid case → `PROSPECTIVE_VALIDATION_INCONCLUSIVE`.

The same function is used at the 36-month core and at the maximum 48-month
horizon. At the core, an INCONCLUSIVE result with
`extension_available == TRUE` opens the one predeclared 12-month extension;
the returned outcome remains INCONCLUSIVE and the rationale records the next
mechanical action. There is no fifth outcome and no operator choice. At 48
months `extension_available == FALSE`, so INCONCLUSIVE is terminal.

## 2. Exact input variables

The future report supplies these values:

| Variable | Definition |
|---|---|
| `n_valid` | Count of identical U.S. session dates with reconstructable strategy and QQQ daily returns. |
| `mean_excess_ann` | `252 * mean(d_t)`, where `d_t = strategy_daily_return_t - qqq_daily_return_t`. Annualized decimal units. |
| `hac_se` | Annualized Newey–West/HAC standard error of the mean excess return using the predeclared lag. |
| `ci95_two_sided_lower` | `mean_excess_ann - 1.959963984540054 * hac_se`. |
| `ci95_two_sided_upper` | `mean_excess_ann + 1.959963984540054 * hac_se`. |
| `ci95_one_sided_lower` | `mean_excess_ann - 1.6448536269514722 * hac_se`. |
| `cumulative_excess` | `product(1 + strategy_daily_return_t) / product(1 + qqq_daily_return_t) - 1` on the same valid dates. |
| `n_primary_scheduled` | Count of recorded weekly primary scheduled observations. |
| `n_state_changes` | Count of actual weekly target-state changes, not scheduled observations. |
| `n_completed_episodes` | Count of completed weekly position episodes. |
| `n_adverse_observations` | Count of ex-ante adverse/regime-transition observations; reported diagnostically and not used as a subjective quota. |
| `protocol_valid` | Boolean structural/provenance result. False includes unauthorized code/parameter/frequency changes, silent rewrite, start/benchmark reset, or unrecoverable provenance. |
| `hard_implementation_gate` | Boolean result for applicable paper-system diagnostics. |
| `hard_risk_gate` | Boolean result for the severe-risk limits. |
| `hard_accounting_gate` | Boolean result for NAV/tax reconciliation. |
| `hard_turnover_gate` | Boolean result for the canonical annual-turnover limit. |
| `paper_slippage_proxy_status` | `PASS`, `FAIL`, or `NOT_OBSERVABLE_IN_PAPER_MODE`; the last value is not a fabricated pass/fail observation. |
| `tracking_proxy_status` | `PASS`, `FAIL`, or `NOT_OBSERVABLE_IN_PAPER_MODE`. |
| `extension_available` | True only at the 36-month core when the result is INCONCLUSIVE and no extension has been used. False at 48 months. |
| `extension_used` | Boolean append-only extension flag. A second extension is invalid. |

All numeric return inputs must be finite for information adequacy. A missing or
non-finite return input makes `information_adequate == FALSE`; it never becomes
zero.

## 3. Derived booleans and gates

### Information adequacy

`information_adequate` is exactly:

```text
information_adequate = (
    n_valid >= 500
    and n_primary_scheduled >= 1
    and mean_excess_ann is finite
    and hac_se is finite
    and ci95_two_sided_lower is finite
    and ci95_two_sided_upper is finite
    and ci95_one_sided_lower is finite
    and cumulative_excess is finite
)
```

There is no discretionary “enough information” judgment.

### Mechanism-information limitation

The exact mechanical rule is:

```text
mechanism_information_limited = (
    n_state_changes == 0
    or n_completed_episodes == 0
)
```

This deliberately uses zero-event conditions rather than an arbitrary crossing
quota. `n_adverse_observations` is always reported; its absence is a warning
in the evidence report, not an operator-selected reason to extend or fail.
There is no arbitrary crossing quota.
When `mechanism_information_limited` is true and all higher-priority gates are
valid, the outcome is INCONCLUSIVE.

### Hard gates

The severe-risk gate uses equality as a pass boundary:

```text
hard_risk_gate = (
    strategy_max_drawdown >= -0.60
    and max_drawdown_difference_vs_qqq >= -0.10
)
```

Thus exactly −60% and exactly −10 percentage points pass the severe-risk
limits; values strictly below them fail. The accounting gate is:

```text
hard_accounting_gate = (
    abs(nav_reconciliation_error_usd) <= 0.01
    and abs(tax_reconciliation_error_usd) <= 0.01
)
```

The turnover gate is `annual_turnover <= 6.0`. The implementation gate uses
the paper-system latency and observable proxy rules in the protocol. A
slippage or tracking proxy marked `NOT_OBSERVABLE_IN_PAPER_MODE` is not
silently treated as a measured zero and does not create a live-execution
claim; its applicable paper gate is `PASS` with a diagnostic status of
NOT_OBSERVABLE. If a reliable proxy exists, p95 values at or below their
predeclared limits pass and values above them fail.

```text
hard_gate_status = PASS iff all of:
    hard_implementation_gate == TRUE
    hard_risk_gate == TRUE
    hard_accounting_gate == TRUE
    hard_turnover_gate == TRUE
otherwise hard_gate_status = FAIL
```

## 4. Return-evidence regions

The region classifier is evaluated only after all required return inputs are
finite. The tests use strict inequalities exactly as written:

```text
MATERIAL_HARM_FLOOR = -0.02

if ci95_two_sided_upper < MATERIAL_HARM_FLOOR:
    region = HARMFUL_BELOW_FLOOR
elif ci95_two_sided_upper < 0:
    region = STATISTICALLY_NEGATIVE_ECONOMICALLY_SMALL
elif ci95_one_sided_lower > 0 and cumulative_excess > 0:
    region = STRONG_POSITIVE
elif mean_excess_ann > 0 and ci95_two_sided_lower <= 0 <= ci95_two_sided_upper:
    region = POSITIVE_ESTIMATE_CI_CROSSES_ZERO
elif mean_excess_ann == 0:
    region = ESTIMATE_NEAR_ZERO
elif mean_excess_ann < 0 and ci95_two_sided_lower <= 0 <= ci95_two_sided_upper:
    region = NEGATIVE_ESTIMATE_CI_INCLUDES_ZERO
else:
    region = OTHER_UNCERTAIN
```

The `elif` order makes regions mutually exclusive. In particular:

- positive point estimate alone is not PASS;
- a two-sided interval whose upper bound equals −2% is not below the harm
  floor, so it is economically small/uncertain rather than FAIL;
- a two-sided interval whose upper bound equals zero is not statistically
  negative;
- a one-sided lower bound equal to zero is not a positive PASS bound;
- cumulative excess equal to zero is not positive PASS evidence.

## 5. Exact decision pseudocode

```text
def paper_protocol_result(inputs):
    # Structural validity has absolute priority.
    if inputs.protocol_valid is FALSE:
        return PROTOCOL_INVALID

    # A missing hard-gate record is an unreconstructable protocol record.
    if any_gate_is_missing(inputs):
        return PROTOCOL_INVALID

    hard_gate_status = derive_hard_gate_status(inputs)
    if hard_gate_status == FAIL:
        return PROSPECTIVE_VALIDATION_FAIL

    information_adequate = derive_information_adequacy(inputs)
    if information_adequate is FALSE:
        return PROSPECTIVE_VALIDATION_INCONCLUSIVE

    mechanism_information_limited = (
        inputs.n_state_changes == 0
        or inputs.n_completed_episodes == 0
    )
    if mechanism_information_limited is TRUE:
        return PROSPECTIVE_VALIDATION_INCONCLUSIVE

    region = classify_return_region(inputs)
    if region == HARMFUL_BELOW_FLOOR:
        return PROSPECTIVE_VALIDATION_FAIL

    if (
        region == STRONG_POSITIVE
        and inputs.ci95_one_sided_lower > 0
        and inputs.cumulative_excess > 0
    ):
        return PROSPECTIVE_VALIDATION_PASS

    # A positive point estimate alone cannot PASS. This includes positive estimates with a zero-crossing interval, a
    # statistically negative but economically small result, negative estimates
    # whose interval includes zero, near-zero estimates, and every other finite
    # uncertain region. No operator may select another label.
    return PROSPECTIVE_VALIDATION_INCONCLUSIVE
```

The confirmatory return PASS condition is therefore exactly:

```text
PRIMARY_RETURN_PASS = (
    ci95_one_sided_lower > 0
    and cumulative_excess > 0
)
```

The one-sided lower bound is the mechanically consistent 5%-alpha directional
criterion. The two-sided harm floor has one precise role: a valid, adequate,
mechanism-informative path with `ci95_two_sided_upper < -0.02` is FAIL. A
statistically negative result with upper bound in `[−0.02, 0)` is economically
small under the proposed governance limit and is INCONCLUSIVE, not a hidden
FAIL. Inadequate or mechanism-limited information is INCONCLUSIVE even when a
point estimate happens to be positive or negative.
No arbitrary count of crossings is used.

## 6. Original research goals are separate outputs

The separate `ORIGINAL_RESEARCH_GOAL_STATUS` object always reports:

```text
Goal_A = strategy_max_drawdown >= qqq_max_drawdown
Goal_B = strategy_max_drawdown >= -0.45
Goal_C = strategy_max_drawdown >= -0.50
```

These definitions are not gates that are silently substituted for the paper
protocol result. The future report shows strategy MaxDD, QQQ MaxDD, the
difference, Goal A status, Goal B status, and Goal C status beside the two
paper severe-risk governance limits.

## 7. Extension and audit boundary

At the core, an INCONCLUSIVE result with `extension_available == TRUE` records
the same one outcome and the deterministic next action `OPEN_SINGLE_EXTENSION`.
The extension cannot change any input definition, threshold, start date,
frequency, or model. At the 48-month terminal evaluation, the same function
returns the final result with `extension_available == FALSE`. No engine,
historical backtest, optimization, vendor selection, live authorization, or
prospective observation is created by this specification.
