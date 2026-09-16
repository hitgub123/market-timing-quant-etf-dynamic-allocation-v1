# Prospective Paper-Trading Protocol v1 — Design Remediation Audit

**Status:** design remediation complete; protocol remains DRAFT and is **NOT
FROZEN**  
**Audit scope:** pre-observation governance only  
**Audit commit before this remediation:** `b0e10e9671cacf9c04e7d921772dd17f3f615fe1`  
**Accepted historical reference:** tag `research-v1.0-final` →
`2b2bf987f2e00540412d263a8ef39566af1d1e2a`  
**Freeze manifest SHA-256:**
`dcb8f9d79de93c61e0bd7d93b743b0356be9eb3b1467acf5db9a58563889d400`

This report records a prospective-design correction only. No paper-trading
engine, broker connector, scheduler, observation writer, historical backtest,
optimizer, selector, Phase 9, prospective start timestamp, or prospective
observation was created or run.

## 1. Required outputs

Updated:

- `docs/PAPER_TRADING_VALIDATION_PROTOCOL_V1_DRAFT.md`
- `docs/paper_trading_protocol_decision_table.csv`

Created:

- `docs/PAPER_TRADING_PROTOCOL_V1_DESIGN_RATIONALE.md`
- `docs/PAPER_TRADING_PROTOCOL_V1_STATISTICAL_DESIGN.md`
- `docs/paper_trading_threshold_registry.csv`
- this audit report
- `tests/test_paper_trading_design_remediation.py`

The decision table has 29 rows and exactly these columns:
`decision_id,issue,current_draft_rule,remediated_proposal,rationale,
threshold_derivation,selection_bias_control,statistical_role,status`. Every
row is `PROPOSED_NOT_FROZEN`. The threshold registry has 21 rows and all
prospective statuses are `PROPOSED_NOT_FROZEN`.

## 2. Proposed prospective design

### Model and frequency

The primary model remains exactly `FIXED_MA200_QQQ_TO_QLD`: QQQ adjusted
close, SMA 200 completed observations, close-`t` information boundary, next
eligible U.S. open, 100% QLD above the average and 100% CASH otherwise, zero
commission, 5 bps baseline slippage, zero cash return, and the simplified
20.315% average-cost immediate-tax ledger. There is no same-day execution,
leverage change, or additional indicator.

The proposed primary inferential schedule is:

`PRIMARY_PROSPECTIVE_SCHEDULE = WEEKLY`

Weekly is proposed solely because its prospective observation density,
operational feedback, state-change responsiveness, and statistical information
are highest among the four already-visible calendars while remaining tractable
to review. The rationale was written without historical CAGR, Sharpe, MaxDD,
Calmar, p-values, multiplicity results, or survival counts.

Monthly, bimonthly, and quarterly remain
`ROBUSTNESS_SHADOW_SCHEDULE`. They are descriptive only. They cannot trigger
PASS or promote a frequency. A later frequency or live-frequency decision
requires a separately audited and frozen protocol; there is no performance-
ranked frequency rule.

`PHASE7A_FIXED_FOUR_STATE` remains a NON-DECISION SHADOW COMPARATOR.
Phase7B Model A/B remain historical context only and cannot enter the
prospective candidate set.

### Horizon and information adequacy

The proposed core horizon is **36 calendar months** from one future frozen
start, with a mandatory evaluation at the end. Scheduled observations, actual
target-state changes, completed position episodes, and adverse/regime-
transition observations are reported as separate inventories. No arbitrary
crossing or episode quota forces a verdict.

At month 36, at least **500 valid paired daily sessions**, reconstructable
weekly records, and enough state/episode information to interpret the mechanism
are proposed as the adequacy diagnostic. Insufficient information is a valid
`PROSPECTIVE_VALIDATION_INCONCLUSIVE` outcome.

If and only if the core result is INCONCLUSIVE, one fixed **12-calendar-month
extension** may run under the unchanged original start, model, schedules,
thresholds, benchmark, and source architecture. The maximum is **48 months**
from the original start. There is no second extension, reset, parameter or
threshold change, frequency change, deletion of the first 36 months, or repeat
extension until PASS.

### Primary question and method

The primary question is whether the frozen strategy executes faithfully on
unseen observations and produces paired benchmark-relative return evidence in
the predicted direction without unacceptable implementation degradation or
materially unacceptable drawdown deterioration. A 36-month CAGR alone cannot
validate long-run timing.

For weekly Fixed MA200 versus QQQ on identical valid U.S. sessions,

`d_t = strategy_daily_return_t - qqq_daily_return_t`.

The primary statistic is mean `d_t`, with Newey–West HAC standard error,

`L = min(20, floor(4 * (n / 100)^(2/9)))`,

a two-sided 95% confidence interval, and one-sided alpha .05 only when the
adequacy gate is met. Monthly, bimonthly, and quarterly are descriptive
shadows and do not add confirmatory hypotheses. No prospective p-value is
calculated in this remediation.

### Outcome separation

- `PROTOCOL_INVALID`: unauthorized strategy/code change, silent observation
  rewrite, benchmark/start reset, unrecoverable provenance, or unapproved
  parameter/frequency change. This is invalid evidence, not economic failure.
- `PROSPECTIVE_VALIDATION_FAIL`: valid protocol, but a predeclared economic,
  risk, accounting, or implementation guardrail fails.
- `PROSPECTIVE_VALIDATION_INCONCLUSIVE`: valid protocol, but information is
  insufficient at 36 months or after the one permitted extension.
- `PROSPECTIVE_VALIDATION_PASS`: adequate, reconstructable, faithful evidence
  with no hard guardrail failure and positive paired evidence under the frozen
  criteria. No shadow can independently trigger PASS.

## 3. Quantitative guardrails and derivations

The registry is `docs/paper_trading_threshold_registry.csv`. Each numerical
value has exactly one derivation class and was set before observations. No
threshold was selected because a historical strategy path would pass it.

| Threshold | Proposed value | Derivation class | Role |
|---|---:|---|---|
| Core horizon | 36 months | `STATISTICAL_DESIGN` | Mandatory bounded evaluation |
| Single extension | 12 months; 48-month maximum | `STATISTICAL_DESIGN` / `GOVERNANCE_LIMIT` | One finite INCONCLUSIVE extension |
| Paired-session adequacy | 500 sessions | `STATISTICAL_DESIGN` | Information diagnostic |
| HAC lag cap | 20 sessions | `STATISTICAL_DESIGN` | Serial-dependence design |
| Confidence / alpha | 95% / .05 | `STATISTICAL_DESIGN` | Predeclared uncertainty |
| Material negative excess floor | −2 percentage points annualized | `STATISTICAL_DESIGN` | Economic evidence floor |
| p95 observed slippage | ≤25 bps | `IMPLEMENTATION_TOLERANCE` | Hard implementation guard |
| p95 tracking difference | ≤50 bps | `IMPLEMENTATION_TOLERANCE` | Hard implementation guard |
| Signal-to-order latency | ≤5 minutes | `IMPLEMENTATION_TOLERANCE` | Hard timing guard |
| Order-to-fill latency | ≤15 minutes | `IMPLEMENTATION_TOLERANCE` | Hard timing guard |
| Stale scheduled close | incident after 15 minutes | `IMPLEMENTATION_TOLERANCE` | Fail-closed data guard |
| Strategy MaxDD | below −60% | `GOVERNANCE_LIMIT` | Severe-risk hard failure |
| Drawdown difference | below −10 percentage points vs QQQ | `GOVERNANCE_LIMIT` | Material deterioration hard failure |
| Annual turnover | ≤6.0× | `GOVERNANCE_LIMIT` | Canonical-burden guard |
| NAV reconciliation | ≤$0.01 absolute | `ACCOUNTING_IDENTITY` | Cent-level identity check |
| Tax reconciliation | ≤$0.01 absolute | `ACCOUNTING_IDENTITY` | Cent-level ledger check |
| Tax rate | 20.315% | `ORIGINAL_FROZEN_OBJECTIVE` | Unchanged model assumption |
| Commission | 0 bps | `ORIGINAL_FROZEN_OBJECTIVE` | Unchanged model assumption |
| Baseline slippage | 5 bps | `ORIGINAL_FROZEN_OBJECTIVE` | Unchanged model assumption |

The original frozen risk objectives remain visible and unchanged: Goal A is
`strategy MaxDD >= QQQ MaxDD`; Goal B is `MaxDD >= -45%`; Goal C is
`MaxDD >= -50%`. The new −60% and −10-point limits are governance guardrails,
not a claim that the strategy dominates QQQ.

The 5-bps value is a `MODEL_ASSUMPTION`. Official next-open reference,
observed slippage, tracking difference, and latency are
`OBSERVED_IMPLEMENTATION_DIAGNOSTIC`; an observed breach does not retune the
model.

## 4. Data, accounting, and operations

The proposed source architecture has one authoritative timestamped feed and an
independent backup/reconciliation feed. Both must expose raw and adjusted
fields, corporate actions, official U.S. session timestamps, revisions, and
stable hashes. Vendor identity remains `PROPOSED_NOT_FROZEN` pending operational
acceptance.

Missing/stale closes, missing next opens, delayed updates, partial sessions,
exchange halts, and source disagreements fail closed, create append-only
incidents, and never generate an interpolated, forward-filled, or favorable
synthetic fill. A scheduled close acquired more than 15 minutes after the
official close is an incident. No back-dated fill is permitted.

The ledger preserves 20.315% immediate tax, average-cost basis, realized
gains/losses, tax paid to date, canonical contemporaneous pretrade-equity
turnover, initial-deployment exclusion, and terminal liquidation as a
non-mutating diagnostic. Terminal liquidation creates no SELL and does not
alter turnover, holding periods, or the tax ledger.

## 5. Monitoring, multiplicity, and deployment boundary

Monthly and quarterly monitoring may detect protocol invalidation, operational
incidents, or a predeclared severe-risk breach. It may not change MA200,
frequency, thresholds, slippage, benchmark, or start date, exclude bad periods,
restart after losses, or declare success. There is **NO EARLY-SUCCESS RULE**.

There is one primary confirmatory hypothesis. The three shadows and optional
Phase7A comparator are descriptive and cannot independently trigger PASS. No
prospective p-value or new historical test is calculated here.

Paper PASS does not authorize normal live deployment. The named
`SMALL_CAPITAL_LIVE_VALIDATION` stage remains a separate future protocol after
external/manual audit, with its own frozen capital, broker, fill, risk, and
decision controls. This remediation authorizes no live capital.

## 6. Immutable Research v1 verification

The verification was run before and after the documentation/test changes:

- `research-v1.0-final` remains an annotated tag resolving to
  `2b2bf987f2e00540412d263a8ef39566af1d1e2a`;
- `reports/research_v1_freeze_manifest.json` SHA-256 remains
  `dcb8f9d79de93c61e0bd7d93b743b0356be9eb3b1467acf5db9a58563889d400`;
- the manifest companion SHA file still matches;
- the 52 accepted Phase7B/8A/8B1/8B2/8C plus raw snapshot hashes pass
  `phase8d.verify_source_hashes()` byte-for-byte;
- the seven Phase8D output hashes remain byte-for-byte accepted:

| Phase8D artifact | SHA-256 |
|---|---|
| `complexity_incremental_evidence.csv` | `b622514a52fbe60c25a63856684a03004a5a3041a06e1a9d7ca457dc8f8f180f` |
| `final_claim_evidence_ledger.csv` | `92a9c23854dd13302d4ee3f92aa8f37f44988389caa2c0b73bbb5faffe3ec8a5` |
| `final_evidence_matrix.csv` | `ef35796946bfd587f14311003dfc4575f98657c70f5b9d79992ee70cafc78605` |
| `original_goal_scorecard.csv` | `ad3998d4291cb9a6f77c4a32d09aa6c07f3e82efe4ffdc1d2f087868169ae462` |
| `phase8d_configuration.json` | `3bee1f2da9872c7338e0b39afadf7def0c13be327c678d835863e7780381362a` |
| `phase8d_final_research_verdict.md` | `4470e42756cb5f02e6cd551224250cd15dc8632463eec273c07b77c9db80b284` |
| `phase8d_audit_diff.md` | `fb9bc23354eb089157ea651c97991673e24e57e805a415295f67332f008e64a7` |

No Phase 0–8D code, raw data, canonical reports, plots, freeze manifest, or
freeze policy was modified.

## 7. Dedicated governance tests

`tests/test_paper_trading_design_remediation.py` contains **49 dedicated
tests** covering the requested tag/manifest/source-hash gates, draft/no-start/
no-observation/no-engine boundary, model and Phase7A/7B roles, four shadows,
one primary schedule, rationale independence, finite horizon and extension,
INCONCLUSIVE and PROTOCOL_INVALID separation, no early success, derivation
classes and no outcome tuning, Goals A/B/C, benchmark, MA200, next-open and
5-bps semantics, tax, one hypothesis, shadow non-confirmatory role, no
prospective p-value/backtest/optimizer/Phase9/live capital, schema/statuses,
source and stale policy, HAC method, design-only power table, monitoring, and
post-edit frozen-hash integrity.

Dedicated command/result:

`python3 -m pytest -q tests/test_paper_trading_design_remediation.py`

**49 passed**.

The existing 13-test freeze governance file also passed alongside the dedicated
tests (**62 passed**).

## 8. Complete pytest result

Command:

`python3 -m pytest -q`

Result: **433 passed, 0 failed**. The freeze manifest's recorded 384-test
freeze-package result was not edited; 49 new remediation tests are reported
here as a later design-package result.

## 9. Unresolved decisions awaiting final protocol audit

The following are intentionally unresolved and remain
`PROPOSED_NOT_FROZEN`:

1. final vendor identities and contractual access for the authoritative and
   backup feeds;
2. final official calendar implementation and operational stale/hold-versus-
   skip runbook;
3. implementation audit of append-only observation, order, fill, NAV, tax,
   incident, correction, and hash ledgers;
4. external approval of every threshold and the one-extension rule;
5. final protocol freeze commit/tag and a future exact start timestamp; and
6. any separate `SMALL_CAPITAL_LIVE_VALIDATION` design.

No unresolved item is solved by looking at historical performance. No paper
observations may be collected until these items are externally audited and a
new final protocol is frozen.

## 10. Final remediation conclusion

The prospective design degrees of freedom requested for remediation are now
explicit: one weekly primary inference, three descriptive shadows, a finite
36-month core with at most one 12-month extension, an explicit INCONCLUSIVE
outcome, separate protocol invalidation, predeclared statistical and economic
guardrails, fail-closed data handling, preserved accounting semantics, and a
paper-to-live boundary. The Research v1.0 historical freeze remains intact.

PAPER TRADING PROTOCOL V1 DESIGN REMEDIATION COMPLETE — ALL NEW DECISIONS REMAIN PROPOSED_NOT_FROZEN — AWAITING FINAL PROTOCOL AUDIT
