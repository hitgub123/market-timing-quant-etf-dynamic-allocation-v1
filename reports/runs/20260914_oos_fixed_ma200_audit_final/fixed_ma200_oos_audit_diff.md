# Fixed-Rule Chronological OOS — MA200 audit diff

## Scope and guardrails

This is an audit/remediation of the existing Fixed-Rule Chronological OOS — MA200 run. The frozen strategy
rules, asset mappings, frequencies, close-*t* to next eligible open execution, 0 bps commission, 5 bps
slippage, 20.315% tax rate, 2013 through latest 2026 YTD sample, raw data, and Phase 0–6/Phase 7 code
were not changed. No Phase 7 work was started.

## A. Test result

The dedicated module is `tests/test_walk_forward_fixed_ma200.py` (22 tests collected). The complete final
verification command was `pytest -q`: **222 passed in 19.51s** (including all 22 dedicated tests).

## B. Artifact and row counts

The old run was `reports/runs/20260913_oos_fixed_ma200_final`. The new canonical run is
`reports/runs/20260914_oos_fixed_ma200_audit_final`.

| Artifact | Old rows | New rows |
|---|---:|---:|
| `metrics_pre_tax.csv` | 12 | 12 |
| `metrics_after_tax.csv` | 12 | 12 |
| `oos_results.csv` | 24 | 24 |
| `oos_fold_metrics.csv` | 336 | 336 |
| `walk_forward_folds.csv` | 14 | 14 |
| `parameter_results.csv` | 1 | 1 |
| `equity_curve.csv` | 82464 | 82464 |
| `positions.csv` | 82464 | 82464 |
| `trades.csv` | 436 | 436 |
| `tax_ledger.csv` | 103 | 103 |

The 24 stitched rows are exactly 3 rules × 4 frequencies × 2 tax modes. `parameter_results.csv` is one
fixed-baseline record with `ma_window=200`, `selected=False`, `searched_for_selection=False`, and
`selection_performed=False`; it is a fixed-run declaration, not a parameter search.

## C. Reporting-definition correction

The old run used the stale equity denominator for OOS turnover and reported the full stitched/fold span as
`average_holding_period_days` (4989). The new run attaches the Phase 2 reporting-only
`pretrade_equity` reconstruction and uses the contemporaneous open-before-trade denominator. Initial
deployment and hypothetical terminal liquidation are excluded; genuine strategy trades are included.

Holding statistics now use completed risky-position episodes measured in trading sessions. Open terminal
positions are excluded. Fold episodes are attributed to the fold containing their actual exit session, so a
December-to-January episode remains whole and is not restarted or truncated.

After-tax rows now include realized-tax-paid-to-date wealth plus non-mutating terminal liquidation wealth,
CAGR, tax, cost, and unrealized-gain diagnostics. Fold rows do not request terminal liquidation.

## D. Fold-continuity audit

One `single_asset_timed_backtest` call covers the entire 2013-01-02 through 2026-08-31 sample for every
strategy/frequency/tax mode. Annual rows are slices of that returned ledger. No fold resets capital, shares,
average-cost basis, tax loss pool, positions, or trades. Synthetic December/January tests confirm that a
position and its average-cost/tax state cross the boundary and that an unchanged target creates no synthetic
boundary trade.

## E. No-lookahead and timing audit

The MA200 decision uses the unleveraged underlying adjusted close at close *t*. `trend_target_next_open`
shifts the decision once to the next eligible scheduled open. Dedicated synthetic tests verify that a Friday
close cannot trade at that Friday open, that the Monday trade uses the Monday open (including an artificial
gap), and that mutating future closes does not change prior targets or trades.

## F. Holding-period audit

The completed-episode helper identifies CASH/no-risk → risky → CASH/no-risk transitions. The new stitched
mean/median/max values are finite where an episode completed and are null where none completed; no value is
the 4989-day full sample. A cross-year synthetic episode has its full trading-session duration attributed to
the exit fold. Open episodes remain excluded from all fold statistics.

## G. Turnover audit

The stitched turnover helper is the audited Phase 2 helper:

`sum(abs(trade_notional) / contemporaneous_open_pretrade_equity) / calendar_years`

The new pre-tax annual turnover values are 1.610241 (QQQ/weekly), 1.171084 (QQQ/monthly), 0.731928
(QQQ/bimonthly), 0.878313 (QQQ/quarterly), 1.610241 (QLD/weekly), 1.171084 (QLD/monthly), 0.731928
(QLD/bimonthly), 0.878313 (QLD/quarterly), 2.634940 (SSO/weekly), 1.756626 (SSO/monthly), 1.024699
(SSO/bimonthly), and 0.878313 (SSO/quarterly). After-tax turnover is identical because the trade path is
identical for each tax mode's denominator convention. Fold turnover includes only real execution dates
inside that fold; a fold boundary itself contributes nothing.

## H. Tax and terminal-liquidation audit

The primary after-tax result is live wealth after realized tax paid to date. `cumulative_realized_tax_paid`
equals `tax_paid` in every after-tax stitched row. Terminal diagnostics are computed by
`performance_metrics` without mutating the ledger, positions, trades, or tax ledger. No annual fold performs
hypothetical liquidation.

## I. Old → new stitched metric comparison

Every one of the 24 `(strategy, tax_mode)` rows was matched by key. The automated comparison requires exact
or serialization-safe equality for `ending_value`, `total_return`, `cagr`, `annualized_volatility`,
`max_drawdown`, `sharpe`, `sortino`, `calmar`, `ulcer_index`, `number_of_trades`, `transaction_costs`, and
`tax_paid`. All 24 rows pass with zero economic delta. The following reporting-only fields changed as
expected:

| Strategy family | Frequencies | Old hold field | New mean / median / max trading sessions | Turnover change |
|---|---|---:|---:|---|
| QQQ → QQQ | weekly | 4989 | 254.636 / 211 / 662 | stale denominator → open pretrade |
| QQQ → QQQ | monthly | 4989 | 353.875 / 358 / 671 | stale denominator → open pretrade |
| QQQ → QQQ | bimonthly | 4989 | 528.200 / 589 / 756 | stale denominator → open pretrade |
| QQQ → QQQ | quarterly | 4989 | 471.667 / 471 / 754 | stale denominator → open pretrade |
| QQQ → QLD | weekly | 4989 | 254.636 / 211 / 662 | stale denominator → open pretrade |
| QQQ → QLD | monthly | 4989 | 353.875 / 358 / 671 | stale denominator → open pretrade |
| QQQ → QLD | bimonthly | 4989 | 528.200 / 589 / 756 | stale denominator → open pretrade |
| QQQ → QLD | quarterly | 4989 | 471.667 / 471 / 754 | stale denominator → open pretrade |
| SPY → SSO | weekly | 4989 | 156.278 / 55 / 663 | stale denominator → open pretrade |
| SPY → SSO | monthly | 4989 | 235.750 / 178.5 / 671 | stale denominator → open pretrade |
| SPY → SSO | bimonthly | 4989 | 359.857 / 333 / 671 | stale denominator → open pretrade |
| SPY → SSO | quarterly | 4989 | 471.833 / 502 / 693 | stale denominator → open pretrade |

All changes are Class A reporting/metric-definition corrections. No Class B economic strategy change was
found.

## J. Economic path SHA-256 comparison

The complete economic path tables are byte-identical old versus new:

| File | Old SHA-256 | New SHA-256 | Result |
|---|---|---|---|
| `equity_curve.csv` | `8eb1176e05a1b5bd3da75fefebc4b6f99255d7468f442c781832857cef8fc404` | `8eb1176e05a1b5bd3da75fefebc4b6f99255d7468f442c781832857cef8fc404` | byte-identical |
| `positions.csv` | `14fe3cc83160d13be49a3fe3542e5ab310d8b3dd0c8d1efddd66a601f67adbf0` | `14fe3cc83160d13be49a3fe3542e5ab310d8b3dd0c8d1efddd66a601f67adbf0` | byte-identical |
| `trades.csv` | `36fa8cf1d9837bcaf1f0b01c91bf2378866806ecaa3586439c65478ccf9905f1` | `36fa8cf1d9837bcaf1f0b01c91bf2378866806ecaa3586439c65478ccf9905f1` | byte-identical |
| `tax_ledger.csv` | `6ba2d9b423022ef59a11c5c445f8323b4bd3fa6adfd484551086b3f4df80ff6c` | `6ba2d9b423022ef59a11c5c445f8323b4bd3fa6adfd484551086b3f4df80ff6c` | byte-identical |

## K. Raw snapshot SHA verification

The immutable manifest entries for all relevant assets match the external raw snapshots:

| Asset | Manifest SHA-256 |
|---|---|
| SPY | `6a73a96bf408a041bc7e77df51117ae5a0965769c407c6699f52b0fd489b28d8` |
| QQQ | `fe5aa0db7c8a717e00cd7726d04ba1d2faff627e9f6e48c0952a5e2f235052c6` |
| SSO | `b0636de318b2d72d4cf774d6af2e11b2bc47904150891a06a39d29355e6e2b5d` |
| QLD | `2499976b07ea6711b33befad63bd8e177ab85f0c820662330f9a4ad257532a9f` |

No raw snapshot changed.

## L. Unresolved issues

None. The stale holding-duration reporting and turnover denominator were corrected without changing any
economic path or frozen strategy definition.

## Final verification

The final verification run was `pytest -q`: **222 passed in 19.51s**. The 22 dedicated OOS tests passed,
the complete prior Phase 0–6 and Phase 7 test suite passed, all requested artifacts are present, and all
economic path hashes are byte-identical.

FIXED MA200 CHRONOLOGICAL OOS AUDIT PASS
