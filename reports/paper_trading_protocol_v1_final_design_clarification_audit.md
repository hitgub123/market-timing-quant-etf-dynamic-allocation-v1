# Paper-Trading Protocol v1 Final Design Clarification Audit

**Scope:** prospective-design clarification only  
**Status:** DRAFT FOR AUDIT — NOT FROZEN  
**Historical research:** unchanged and immutable

## A. Accepted architecture preserved

The clarification preserves the externally accepted architecture: Fixed MA200
as the primary model, WEEKLY as the sole proposed primary inferential schedule,
monthly/bimonthly/quarterly as descriptive shadows, a 36-calendar-month core,
one fixed 12-calendar-month extension only after INCONCLUSIVE (48 months
maximum), and the existing HAC paired-return framework. No strategy, signal,
accounting, tax, benchmark, horizon, historical result, or Phase 0–8D artifact
was redesigned.

No protocol freeze, paper engine, observation collection, prospective start,
historical backtest, historical-performance inspection, vendor selection,
live-capital authorization, or Phase 9 activity was performed.

## B. Deterministic terminal decision function

`docs/PAPER_TRADING_OUTCOME_DECISION_SPEC.md` is the normative pseudocode and
`docs/paper_trading_outcome_decision_table.csv` is its machine-readable table.
The function evaluates the exact finite inputs `n_valid`, `mean_excess_ann`,
`hac_se`, `ci95_two_sided_lower`, `ci95_two_sided_upper`,
`ci95_one_sided_lower`, `cumulative_excess`, `information_adequate`,
`protocol_valid`, `hard_implementation_gate`, `hard_risk_gate`,
`hard_accounting_gate`, and `hard_turnover_gate`.

Priority is exhaustive and non-overlapping:

1. `protocol_valid == FALSE` → `PROTOCOL_INVALID`;
2. any failed hard gate → `PROSPECTIVE_VALIDATION_FAIL`;
3. inadequate information → `PROSPECTIVE_VALIDATION_INCONCLUSIVE`;
4. `n_state_changes == 0 or n_completed_episodes == 0` → INCONCLUSIVE;
5. `ci95_two_sided_upper < -0.02` → FAIL;
6. `ci95_one_sided_lower > 0 and cumulative_excess > 0` → PASS;
7. every remaining finite valid case → INCONCLUSIVE.

The primary return condition is therefore exactly:

`PRIMARY_RETURN_PASS = (ci95_one_sided_lower > 0 and cumulative_excess > 0)`.

The harm floor has one role: a two-sided upper bound strictly below −2pp is
FAIL. An upper bound in [−2pp, 0) is statistically negative but economically
small under the proposed governance boundary and is INCONCLUSIVE. Equality at
−2pp is not FAIL; a one-sided lower bound or cumulative excess equal to zero
is not PASS. Regions A–G (strong positive, positive zero-crossing, near zero,
negative with uncertainty, statistically negative/economically small,
confidently below −2pp, and inadequate information) are each assigned exactly
one result in the CSV.

## C. Separate output families and risk interpretation

The future report emits `PAPER_PROTOCOL_RESULT` separately from
`ORIGINAL_RESEARCH_GOAL_STATUS`. The latter retains Goal A
(`strategy MaxDD >= QQQ MaxDD`), Goal B (`MaxDD >= -45%`), and Goal C
(`MaxDD >= -50%`). The literal invariant is:

`PAPER_PROTOCOL_PASS_DOES_NOT_IMPLY_ORIGINAL_GOAL_PASS`

The −60% strategy MaxDD and −10pp deterioration limits remain unchanged and
are labeled `PAPER_SEVERE_RISK_GOVERNANCE_LIMIT`, not
`ORIGINAL_RESEARCH_OBJECTIVE`. Future output shows strategy MaxDD, QQQ MaxDD,
their difference, and all Goal A/B/C risk statuses beside those governance
limits.

Mechanism information is deterministic:

`MECHANISM_INFORMATION_LIMITED = (n_state_changes == 0 or n_completed_episodes == 0)`.

That condition forces INCONCLUSIVE after protocol and hard-gate checks.
`n_adverse_observations` is diagnostic only; no crossing quota or subjective
operator judgment is introduced.

## D. Paper execution diagnostics

There is no broker execution. The canonical path retains
`MODEL_SLIPPAGE_BPS = 5` as a model assumption. When valid market-data evidence
exists, each eligible order records `P_ref_o` (official next-open reference),
`P_proxy_o` (same-timestamp ask for buys, bid for sells, or documented opening
auction executable price), timestamps/source/quote-or-auction flag, and
`side_o` (+1 buy, −1 sell). The signed proxy is

`slippage_proxy_bps_o = 10000 * side_o * (P_proxy_o / P_ref_o - 1)`;

the reported order-level quantity is its absolute value. Nearest-rank p95 uses
rank `ceil(0.95*m)` (one-indexed) and requires at least 20 valid positive
proxies. Missing, stale, invalid, or non-positive prices create no proxy and
no synthetic price; fewer than 20 valid observations are
`NOT_OBSERVABLE_IN_PAPER_MODE`. Real executable slippage is deferred to
`SMALL_CAPITAL_LIVE_VALIDATION`.

`CANONICAL_FILL_TRACKING_DIFFERENCE_BPS` is a distinct order-level comparison:

`tracking_difference_bps_o = 10000 * side_o * (P_canonical_o / P_proxy_o - 1)`.

`NAV_RECONCILIATION_ERROR_USD = paper_nav - independently_reconstructed_nav`
remains a separate dollar accounting identity and is never combined with price
proxies. The four latency fields are explicit timestamp differences and are
classified `PAPER_SYSTEM_OPERATIONAL_DIAGNOSTIC`, not live execution evidence.

## E. Statistical and horizon boundaries

The 1.5% annualized-volatility and AR(1) `phi = 0.25` power illustration is
planning-only: it is not used in PASS/FAIL, is not a future-volatility estimate,
and does not justify the 36-month horizon. Actual prospective HAC uncertainty
controls inference. The finite 36/48-month rule and single weekly confirmatory
hypothesis remain unchanged.

## F. Dedicated tests

`tests/test_paper_trading_outcome_clarification.py` adds **32** dedicated
clarification tests covering the 30 requested governance categories, including
all return regions/equalities, gate priority, proxy and tracking definitions,
latency semantics, goal separation, risk labels, mechanism rule, power boundary,
freeze integrity, and no-engine/no-observation boundaries.

Together with the existing prospective-design remediation suite, the dedicated
tests pass **81/81**:

```text
python3 -m pytest -q tests/test_paper_trading_design_remediation.py tests/test_paper_trading_outcome_clarification.py
81 passed
```

The complete repository suite also passes **465/465**:

```text
python3 -m pytest -q
465 passed in 26.46s
```

## G. Freeze and provenance checks

The Research v1.0 freeze manifest remains byte-identical with SHA-256
`dcb8f9d79de93c61e0bd7d93b743b0356be9eb3b1467acf5db9a58563889d400`.
The accepted `research-v1.0-final` tag still resolves to commit
`2b2bf987f2e00540412d263a8ef39566af1d1e2a`. No raw data or historical output
was modified.

## H. Modified artifacts

Only prospective draft/design artifacts were changed or created:

- `docs/PAPER_TRADING_VALIDATION_PROTOCOL_V1_DRAFT.md`;
- `docs/PAPER_TRADING_PROTOCOL_V1_DESIGN_RATIONALE.md`;
- `docs/PAPER_TRADING_PROTOCOL_V1_STATISTICAL_DESIGN.md`;
- `docs/paper_trading_protocol_decision_table.csv`;
- `docs/paper_trading_threshold_registry.csv`;
- `docs/PAPER_TRADING_OUTCOME_DECISION_SPEC.md`;
- `docs/paper_trading_outcome_decision_table.csv`;
- `tests/test_paper_trading_outcome_clarification.py`;
- this audit report.

All prospective decision and threshold statuses remain
`PROPOSED_NOT_FROZEN`.

## I. Remaining unresolved operational items

Before any future freeze or start, an external/manual audit must still approve
the concrete data vendors and revisions, session calendar/runbook, append-only
observation/order/NAV/tax/incident schemas, implementation audit, acceptance
hashes, and the live-boundary decision. This clarification does not authorize
any of those actions.

## J. Commit

The clarification is committed separately as:

`clarify prospective validation terminal decision rules` (the final hash is
reported in the handoff below).

PAPER TRADING PROTOCOL V1 FINAL DESIGN CLARIFICATION COMPLETE — AWAITING FREEZE AUDIT
