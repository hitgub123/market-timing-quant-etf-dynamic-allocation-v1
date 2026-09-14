# Development Log

This log records what was implemented, why it was needed, and the validation performed. Frozen strategy definitions live in the specification documents; this file does not redefine them.

## 2026-09-13 — Project isolation

- Created a separate `market-timing-quant-etf-dynamic-allocation-v1` repository because the original repository contained a different v3.3 protocol and unrelated uncommitted work.
- Copied the frozen v1 specification and immutable SPY/QQQ/SSO/QLD/TQQQ raw snapshots so the two research protocols cannot silently mix.

## 2026-09-13 — Data gate and Phase 0

- Added raw-data audits for chronology, duplicates, OHLC consistency, exchange-session gaps, required fields, and adjusted-return outliers.
- Retained two TQQQ return outliers after cross-snapshot review rather than deleting observations automatically.
- Implemented SPY/QQQ/SSO/QLD/TQQQ/CASH Buy & Hold baselines to establish the frozen reference results before testing timing rules.

## 2026-09-13 — Phase 1

- Implemented the exact two-asset 5% and three-asset 10% static-allocation grids with monthly and quarterly rebalancing.
- Added average-cost realized-gain taxation and immediate tax payment so static rebalancing can be compared pre-tax and after-tax.

## 2026-09-13 — Phases 2–3

- Implemented fixed MA200 timing using underlying QQQ/SPY adjusted closes and next-open execution.
- Scanned only the frozen MA windows 150/175/200/225/250 to measure neighborhood stability without promoting an isolated optimum.

## 2026-09-13 — Phases 4–6

- Implemented frozen absolute-momentum, relative-momentum, and volatility-target grids one factor at a time.
- Kept TQQQ locked and avoided combining factors before the dynamic-state phase.

## 2026-09-13 — Fixed-Rule Chronological OOS

- Added expanding calendar-year folds from the frozen 2006–2012 initial train through 2013–2026 YTD tests.
- Evaluated fixed MA200 without calling it parameter-selection Walk-Forward because no parameter was fitted in each train fold.

## 2026-09-13 — Phase 7 supplement and Phase 7A

- Stored the user-supplied Phase 7 supplemental frozen specification.
- Implemented the exact four-state QQQ-only state machine, strictly prior-only expanding RV20 quantile, TQQQ pre-listing fallback, four rebalance frequencies, and continuous tax/cost ledgers.
- Phase 7A did not satisfy the frozen QQQ dominance condition because its OOS drawdown was deeper than QQQ.

## 2026-09-13 — Phase 7A metrics/tax audit

- Confirmed the original `average_holding_period_days` incorrectly used total backtest duration.
- Replaced it with completed position-episode statistics. Primary holding-period fields use trading sessions; separate calendar-day diagnostics remain available.
- Changed primary annual turnover to exclude initial deployment and hypothetical terminal liquidation; retained gross traded notional separately.
- Preserved realized tax-paid-to-date accounting and added a non-mutating terminal-liquidation after-tax endpoint using the existing loss pool and frozen 20.315% rate.
- Added direct same-frequency comparison against fixed QLD/MA200 before allowing Phase 7B to begin.
- Added four regression tests covering completed position episodes, zero ongoing buy-and-hold turnover, terminal unrealized-gain tax, and terminal use of an existing loss pool. The complete suite passed: 43 tests.
- Regenerated Phase 7A and its same-period benchmarks in `20260913_phase7a_metrics_tax_audited_final`.
- Verified SHA-256 identity of both `state_decisions.csv` and `execution_targets.csv` against the prior Phase 7A run. This confirms the audit changed reporting only, not state or execution logic.
- Compared Phase 7A directly with QLD/MA200 on the same OOS dates. None of the four frequencies met the conservative material-improvement condition, principally because turnover increased at every frequency and some frequencies also worsened tax-adjusted return or drawdown/Calmar.
- Kept Phase 7B unstarted until the audit tests and regenerated-artifact checks passed.

## 2026-09-13 — Phase 7B eligibility gate

- Added a shared frozen candidate selector for Model A and Model B: CAGR >= 15%, absolute MaxDD <= 45%, maximize Calmar, then apply the relative 5% Calmar band and the frozen tie-break order.
- Added Model A's exact MA grid and Model B's exact 45-point grid for all four existing rebalance frequencies. Training metrics use training data only and pre-tax performance; no test result enters selection.
- Added a continuous-ledger OOS path that would execute one stitched target series without resetting holdings, cash, cost basis, tax ledger, or loss pool.
- Added three selector regression tests. The complete suite passed: 46 tests.
- Ran all candidate training evaluations. The frozen gate returned `NO_ELIGIBLE_PARAMETER` for both models in the initial 2006-06-21 through 2012-12-31 training window at every frequency.
- Stopped before OOS execution in the initial implementation attempt. The then-current specification simultaneously required `NO_ELIGIBLE_PARAMETER` without relaxed constraints and a complete stitched OOS comparison, but defined no allocation when a fold had no eligible parameter. Assigning cash, retaining a prior parameter, or selecting the least-bad candidate would have added an unfrozen rule; none was assumed.
- Preserved the candidate-level results, fold eligibility counts, configuration snapshot, and fold table in `reports/runs/20260913_phase7b_walk_forward_v1` for audit.

## 2026-09-13 — Phase 7B-v1 Strict Eligibility Gate resumed

- Added the user-frozen `NO_ELIGIBLE_PARAMETER -> {CASH: 1.00}` fallback. It is applied as a normal first test-session rebalance/open target, so any preceding invested position is liquidated with ordinary costs, realized tax, and loss-pool accounting; consecutive CASH folds do not create trades.
- Kept the complete expanding fold sequence and ran each Model A/Model B frequency through one continuous OOS ledger. Later eligible folds restart the selected strategy from the current continuous cash/portfolio state.
- Added the required fold audit fields, including train/test dates, candidate and eligible counts, null selected parameters for fallback folds, test-year return/MaxDD/turnover/tax, and allocation mode.
- Added six regression tests for fallback execution, normal liquidation, consecutive failed folds, later resumption, test-data exclusion, and full session stitching. The complete suite passed: 50 tests.
- Regenerated the complete `Phase 7B-v1 — Strict Eligibility Gate` report in `reports/runs/20260913_phase7b_strict_gate_v1_final`.
- The stitched OOS contains 3,436 sessions from 2013-01-02 through 2026-08-31 for every strategy/frequency ledger. Model A has 10/14/14/14 failed folds (weekly/monthly/bi-monthly/quarterly); Model B has 8/9/9/14. The strict gate leaves substantial CASH exposure, which is reported as an empirical outcome.
- Model B does not meet the predefined material-outperformance test against Model A at any frequency; the report therefore prefers the simpler Model A complexity control.
- Audited a reported tax discrepancy: the stitched table was displaying `tax_paid` from its pre-tax performance row (structurally zero), while the complexity table used the corresponding after-tax ledgers. The underlying ledgers were consistent; the report mapping was corrected to label and display `Realized tax paid (after-tax ledger)`. Added regression tests for strategy and benchmark tax-field mapping without rerunning parameter selection.
- Re-executed the complete suite after the tax-mapping tests were added: 52 tests passed. Synchronized the final Phase 7B audit text from the observed pytest result; no strategy or parameter result was rerun.

## 2026-09-14 — External Phase 0 metrics/reporting audit

- Regenerated Phase 0 using the already-audited primary turnover and completed-position holding-period definitions. Untouched Buy & Hold now reports zero annual turnover and null completed holding-period statistics.
- Split the report into a 2006-06-21 Live Main Period for SPY/QQQ/SSO/QLD and a 2010-02-11 Common TQQQ Period for all five ETFs. Removed the unequal-start `main_TQQQ` row; no synthetic TQQQ history was created.
- Made realized-tax-paid-to-date wealth distinct from diagnostic terminal-liquidation wealth. Added `after_tax_wealth_tax_paid_to_date`; retained `after_tax_tax_paid_to_date` only as a deprecated Phase 7 compatibility alias and documented that it contains wealth, not tax paid.
- Fixed MaxDD peak, trough, and recovery metadata to use the same equity path augmented by initial capital as the MaxDD series itself.
- Replaced the unsupported outlier-review claim in `audit_asset()` and connected the generated TQQQ audit rows to the immutable manifest's actual cross-snapshot evidence.
- Expanded deterministic regression coverage. The complete suite passed: 61 tests.
- Regenerated the canonical Phase 0 artifacts in `reports/runs/20260914_phase0_audit_final`. Normalized old/new hashes for all retained equity, trade, and position rows match exactly; ending value, CAGR, MaxDD, and Calmar have zero numerical delta.
