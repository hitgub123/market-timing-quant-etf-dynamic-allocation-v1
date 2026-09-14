# Phase 7B turnover / selection audit

## A. Test result

- Dedicated Phase 7B turnover audit: **13 passed** (`tests/test_phase7b_turnover_audit.py`).
- Complete repository pytest: **236 passed**.
- No Phase 7A source or canonical artifact was modified.

## B. Frozen grid and artifact counts

The frozen selector was rerun for the exact existing grid: Model A has 5 MA candidates per frequency and Model B has 45 candidates (5 MA × 3 momentum × 3 low-volatility quantiles) per frequency. There are 4 frequencies and 14 expanding folds (test years 2013–2026 YTD):

- `training_candidate_results.csv`: 2,800 rows (4 × 14 × (5 + 45)).
- `selected_parameters_by_fold.csv`: 112 rows (2 models × 4 frequencies × 14 folds).
- `selection_old_vs_new.csv`: 112 rows, one-to-one against the former canonical selection table.
- Stitched OOS sessions: 3,436 (2013-01-02 through 2026-08-31) per model/frequency/tax ledger.
- Strict gate remained CAGR ≥ 15% and absolute MaxDD ≤ 45%; no constraints or tie tolerances changed.

## C. Canonical turnover correction

Phase 7B now reconstructs the same contemporaneous open-before-trade `pretrade_equity` used by the audited Phase 2 and Fixed-MA200 implementations. Annual turnover is the sum of `abs(notional) / pretrade_equity` for real trades divided by calendar years. The true initial deployment BUY is excluded; terminal liquidation is report-only and cannot enter turnover. Model A training ledgers, final single-asset ledgers, and fold diagnostics all use this denominator. Model B's existing dynamic ledger was verified against the same reconstruction.

The regenerated `FIXED_QLD_MA200` rows match the accepted Fixed-MA200 OOS values (pre-tax and after-tax):

| Frequency | Annual turnover |
|---|---:|
| weekly | 1.610241 |
| monthly | 1.171084 |
| bimonthly | 0.731928 |
| quarterly | 0.878313 |

Synthetic open-gap, initial-deployment, terminal-diagnostic, and fold-boundary tests verify the denominator and exclusions directly. A later-fold trade is divided by continuous portfolio equity; a calendar boundary does not reset the denominator.

## D. MA200 cross-phase equality

All 24 `(rule/frequency/tax mode)` Fixed-MA200 comparisons against `reports/runs/20260914_oos_fixed_ma200_audit_final/oos_results.csv` matched within `1e-10` for start/end, ending value, total return, CAGR, MaxDD, Calmar, Sharpe, Sortino, Ulcer index, trade count, turnover, transaction costs, realized tax, and after-tax terminal-liquidation wealth/CAGR/tax/cost. The canonical QQQ→QLD turnover values above are the direct equality anchors.

The economic path hashes are unchanged from the prior Phase 7B run:

| Artifact | SHA-256 |
|---|---|
| `equity_curve.csv` | `c50093611649cfa379ba71498dcc58568a8ca4a6be780987a5287ad30f93cca0` |
| `positions.csv` | `f56dfa8f629fbac46b27725c799da8fdc733715bb92d9310e5c7f3e3225e8013` |
| `trades.csv` | `9a8e25ea5e79e291f06c7cf66b198bed1018d2bb231ddf7b83c2331a42d13b57` |
| `tax_ledger.csv` | `c6faf011c00d82608a1a0572edfc2c6eb3255d924e8052b7c7466e465a3f7b5a` |
| `stitched_execution_targets.csv` | `22b2286504c82eccdc0471ce51bf60167adf95dee6f38137b156276b37b6504d` |

## E. Old → new selection comparison

The former run `20260913_phase7b_strict_gate_v1_final` was compared fold by fold. Exactly zero of 112 selections changed: `selection_status`, selected MA, momentum, and low-volatility quantile are identical for every row. The corrected turnover inputs affected the selector inputs but did not alter any realized parameter choice; therefore stitched targets, equity curves, trades, positions, and tax ledgers remain byte-identical.

At the candidate level, all economic metrics (`cagr`, MaxDD, Calmar, Sharpe, Sortino) and eligibility flags are exactly unchanged. The 280 Model A candidate rows with real trades receive the corrected turnover (maximum absolute old→new delta `0.018569243`); all 2,520 Model B candidate turnover values are unchanged because their dynamic ledgers already carried the canonical field.

## F. Frozen selection / no-lookahead audit

The existing selector order remains unchanged: eligible candidates within the 5% Calmar band are ordered by lower absolute MaxDD, lower turnover, longer MA, longer momentum, then quantile distance from 0.33. No test-period observation is used by `_training_metric`; all candidate rows use the fold's training end. The direct integration tests retain the close-decision/next-open execution convention, and future-data mutation cannot change prior signal decisions. CASH fallback targets cover every test session and execute through the ordinary continuous ledger without fold resets.

## G. Tax, accounting, and raw-data integrity

No capital, holdings, average-cost basis, loss pool, transaction-cost history, or tax state is reset at a fold boundary. The turnover-only correction does not add trades or mutate taxes. Raw snapshot hashes still match `data/raw/manifest.yaml`:

| Asset | SHA-256 |
|---|---|
| SPY | `6a73a96bf408a041bc7e77df51117ae5a0965769c407c6699f52b0fd489b28d8` |
| QQQ | `fe5aa0db7c8a717e00cd7726d04ba1d2faff627e9f6e48c0952a5e2f235052c6` |
| SSO | `b0636de318b2d72d4cf774d6af2e11b2bc47904150891a06a39d29355e6e2b5d` |
| QLD | `2499976b07ea6711b33befad63bd8e177ab85f0c820662330f9a4ad257532a9f` |
| TQQQ | `4b0b5c7500d7510bb2e61607e86130d635a3d05339cf7cde10ab7174551ccf76` |

The accepted Phase 7A hashes remain unchanged (`state_decisions.csv` `228529085687af082df26d8a3a5e42826facacbd3fec4395d1339cfbf56be6d0`; `execution_targets.csv` `d48dc37826f711db427ad7c4e5338b9048037d506f4289cc729d6afb3609005e`).

## H. Regenerated artifact set

The canonical run contains `config_snapshot.yaml`, `phase7b_parameter_grid.yaml`, `training_candidate_results.csv`, `selected_parameters_by_fold.csv`, `selection_old_vs_new.csv`, `phase7b_stitched_oos_results.csv`, `metrics_pre_tax.csv`, `metrics_after_tax.csv`, `stitched_execution_targets.csv`, `walk_forward_folds.csv`, `equity_curve.csv`, `drawdown.csv`, `positions.csv`, `trades.csv`, `tax_ledger.csv`, `phase7b_report.md`, `phase7b_turnover_selection_audit.md`, and `model_b_minus_model_a.csv`.

## I. Unresolved issues

None. The correction is reporting-only; no economic result or path changed, and Phase 7A remains outside the change set.

PHASE 7B AUDIT PASS
