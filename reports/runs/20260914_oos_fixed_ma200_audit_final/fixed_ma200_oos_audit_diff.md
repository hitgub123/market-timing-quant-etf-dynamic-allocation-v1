# Fixed-Rule Chronological OOS — MA200 audit diff

## Scope

This is the final reporting-only correction to the canonical Fixed-Rule Chronological OOS — MA200 audit.
No strategy, signal, execution, accounting, tax engine, turnover, holding-period, OOS-period, raw-data, or
Phase 0–7 logic changed. The complete 2013-01-02 through 2026-08-31 ledger remains one continuous OOS
ledger with 3 rules × 4 frequencies × 2 tax modes = 24 stitched rows and 336 diagnostic fold rows.

## Artifact and test result

The canonical run is `reports/runs/20260914_oos_fixed_ma200_audit_final`. It contains the fixed MA200
metrics, fold metrics, parameter declaration, path tables, tax ledger, plots, report, and this audit diff.
The dedicated module is `tests/test_walk_forward_fixed_ma200.py` with 23 tests. The final repository
verification command was `pytest -q`: **223 passed in 19.20s**, including all 23 dedicated tests.

## Artifact-completeness correction retained from the prior audit

The prior audit corrected stale turnover and holding-period reporting. It verified 12 pre-tax rows, 12
after-tax rows, 24 stitched rows, 336 fold rows, and the required path artifacts. `parameter_results.csv`
declares `ma_window=200`, `selected=False`, `searched_for_selection=False`, and
`selection_performed=False`; no parameter search or selection claim is made.

| Artifact | Rows |
|---|---:|
| `metrics_pre_tax.csv` | 12 |
| `metrics_after_tax.csv` | 12 |
| `oos_results.csv` | 24 |
| `oos_fold_metrics.csv` | 336 |
| `walk_forward_folds.csv` | 14 |
| `equity_curve.csv` | 82464 |
| `positions.csv` | 82464 |
| `trades.csv` | 436 |
| `tax_ledger.csv` | 103 |

## Final fold-tax reporting correction

Previously `_segment_metrics()` wrote `segment["tax_paid"].sum()` into
`cumulative_realized_tax_paid`. That value is tax paid inside the current diagnostic fold, not cumulative
tax paid since OOS inception.

The corrected fold schema now contains both fields:

- `fold_realized_tax_paid`: realized tax actually paid on execution dates inside that fold
  (`segment["tax_paid"].sum()`).
- `cumulative_realized_tax_paid`: realized tax paid from the first OOS session through that fold's end
  date (`ledger.loc[ledger.index <= fold_end, "tax_paid"].cumsum().iloc[-1]`).

Both values are derived from the existing continuous after-tax ledger. No tax events are reconstructed and
no tax state is reset. Pre-tax rows report 0 for both fields. The final after-tax cumulative value equals
the stitched `tax_paid` and stitched `cumulative_realized_tax_paid` for every strategy/frequency.

Dedicated tests verify, for all 12 after-tax strategy/frequency paths and all 14 folds, that:

1. `fold_realized_tax_paid` equals the tax ledger's actual in-fold tax;
2. `cumulative_realized_tax_paid` is monotonic non-decreasing;
3. the sum of fold tax equals stitched realized tax paid;
4. the final cumulative fold value equals stitched cumulative tax and stitched `tax_paid`;
5. all pre-tax values are zero.

This is a Class A reporting-semantic correction only.

## Fold-continuity, timing, and holding-period audit

Each strategy/frequency/tax mode uses one execution call for the complete OOS span. Annual folds are
diagnostic slices only. No fold resets capital, shares, average-cost basis, tax loss pools, positions, or
trades, and no fold performs terminal liquidation. Synthetic December/January tests cover a position and
its tax basis crossing a boundary without a synthetic boundary trade.

The MA200 decision uses the unleveraged underlying adjusted close at close *t* and shifts once to the next
eligible open. Synthetic Friday/Monday gap tests and future-data mutation tests pass. Historical pre-start
observations are used only for legitimate MA warm-up and create no pre-evaluation equity or trades.

Holding statistics are completed risky-position episodes measured in trading sessions. Open terminal
episodes are excluded. A cross-year episode is attributed to the fold containing its actual exit session,
so the fold boundary does not truncate or restart it.

## Turnover audit

Stitched turnover remains the audited definition:

`sum(abs(trade_notional) / contemporaneous_open_pretrade_equity) / calendar_years`

The true initial deployment BUY and hypothetical terminal liquidation are excluded. Fold turnover includes
only real execution dates inside that fold. Synthetic before/after-year-boundary trades verify that the
boundary itself contributes no turnover.

## Old → new stitched metric comparison

All 24 stitched rows were matched by `(strategy, tax_mode)`. The following economic fields have zero
old→new delta for all 24 rows: `ending_value`, `total_return`, `cagr`, `annualized_volatility`,
`max_drawdown`, `sharpe`, `sortino`, `calmar`, `ulcer_index`, `number_of_trades`, `transaction_costs`,
and `tax_paid` (realized tax). The earlier stale holding-period and turnover corrections remain Class A;
this fold-tax correction is also Class A. No Class B economic path change occurred.

## Economic-integrity audit

All stitched economic fields and the complete economic path remain unchanged versus
`20260913_oos_fixed_ma200_final`: ending value, total return, CAGR, annualized volatility, MaxDD, Sharpe,
Sortino, Calmar, Ulcer index, trade count, transaction costs, and realized tax. No economic result changed.

The complete path tables remain byte-identical:

| File | SHA-256 (old and new) | Result |
|---|---|---|
| `equity_curve.csv` | `8eb1176e05a1b5bd3da75fefebc4b6f99255d7468f442c781832857cef8fc404` | byte-identical |
| `positions.csv` | `14fe3cc83160d13be49a3fe3542e5ab310d8b3dd0c8d1efddd66a601f67adbf0` | byte-identical |
| `trades.csv` | `36fa8cf1d9837bcaf1f0b01c91bf2378866806ecaa3586439c65478ccf9905f1` | byte-identical |
| `tax_ledger.csv` | `6ba2d9b423022ef59a11c5c445f8323b4bd3fa6adfd484551086b3f4df80ff6c` | byte-identical |

The preceding Class A corrections remain in force: turnover uses contemporaneous open pretrade equity,
and holding periods use completed risky episodes measured in trading sessions. Terminal liquidation remains
non-mutating and diagnostic only; folds perform no hypothetical liquidation.

## Raw-data integrity

The immutable manifest hashes for SPY, QQQ, SSO, and QLD remain unchanged and match the external raw
snapshots. No raw snapshot was modified.

| Asset | Manifest SHA-256 |
|---|---|
| SPY | `6a73a96bf408a041bc7e77df51117ae5a0965769c407c6699f52b0fd489b28d8` |
| QQQ | `fe5aa0db7c8a717e00cd7726d04ba1d2faff627e9f6e48c0952a5e2f235052c6` |
| SSO | `b0636de318b2d72d4cf774d6af2e11b2bc47904150891a06a39d29355e6e2b5d` |
| QLD | `2499976b07ea6711b33befad63bd8e177ab85f0c820662330f9a4ad257532a9f` |

## Final verification

The final `pytest -q` run includes the complete repository suite and all 23 dedicated OOS tests. No
unresolved issues remain. No economic metric or path changed.

FIXED MA200 CHRONOLOGICAL OOS AUDIT PASS
