# Fixed-Rule Chronological OOS — MA200

## Experiment contract

The continuous OOS evaluation period is **2013-01-02 through 2026-08-31** (inclusive), covering 14 chronological calendar-year diagnostic folds. The fixed strategy universe is QQQ_MA200_QQQ, QQQ_MA200_QLD, and SPY_MA200_SSO at weekly, monthly, bimonthly, and quarterly frequencies: 3 × 4 × 2 tax modes = 24 stitched rows. The MA window is permanently fixed at 200; `parameter_results.csv` records `selected=False`, `searched_for_selection=False`, and `selection_performed=False` for this fixed baseline. No optimization or parameter-selection claim is made.

Signal is the adjusted close of the unleveraged underlying at close t. A completed close decision can first affect the next eligible trading-day open t+1. Annual folds are diagnostic slices only; the economic OOS ledger is continuous and never resets capital, holdings, average-cost basis, tax loss pools, or trades at a fold boundary.

## Warm-up and calendar alignment

Historical observations before the OOS start provide the legitimate 200-session MA warm-up. They create no pre-start equity, positions, trades, or tax entries. The first evaluation target uses only information available by the preceding close, and all signal/held calendars are aligned with zero missing targets.

| Signal asset | Window | Full rows | Pre-start rows | Lookback observations | Lookback start | First valid MA date | First evaluation date | Missing targets |
|---|---:|---:|---:|---:|---|---|---|---:|
| QQQ | 200 | 6919 | 3476 | 200 | 2012-03-16 | 1999-12-21 | 2013-01-02 | 0 |
| SPY | 200 | 8461 | 5018 | 200 | 2012-03-16 | 1993-11-11 | 2013-01-02 | 0 |

| Rule | Signal asset | Held asset | Signal rows | Held rows | Common rows | Missing aligned targets |
|---|---|---|---:|---:|---:|---:|
| QQQ_MA200_QQQ | QQQ | QQQ | 3436 | 3436 | 3436 | 0 |
| QQQ_MA200_QLD | QQQ | QLD | 3436 | 3436 | 3436 | 0 |
| SPY_MA200_SSO | SPY | SSO | 3436 | 3436 | 3436 | 0 |

## Metrics and tax semantics

Primary after-tax wealth is the live ledger after realized tax paid to date. Terminal liquidation is a non-mutating diagnostic using the 0.20315 tax rate and execution cost rate 0.00050000; it does not add a SELL, affect turnover or holding periods, or alter the tax ledger. Fold metrics never perform hypothetical liquidation.

Turnover is `sum(abs(trade_notional) / contemporaneous_open_pretrade_equity) / calendar_years`. The global initial deployment BUY and hypothetical terminal liquidation are excluded; every other genuine strategy trade is included. Fold turnover includes only execution dates inside that fold.

Holding periods are completed risky-position episodes measured in trading sessions. Episodes begin on CASH→risky and complete on risky→CASH. An open terminal episode is excluded, and fold boundaries do not terminate or restart an episode. For fold diagnostics, a completed episode is attributed to the fold containing its actual exit date, preserving a December-to-January episode in full.

| Rule | Frequency | Pre-tax CAGR | Pre-tax MaxDD | After-tax CAGR | Annual turnover | Mean hold | Median hold | Max hold | Terminal CAGR |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| QQQ_MA200_QLD | bimonthly | 32.4043% | -51.7154% | 27.7485% | 0.731928 | 528.200000 | 589.000000 | 756.000000 | 27.0501% |
| QQQ_MA200_QLD | monthly | 27.9382% | -51.7154% | 23.4136% | 1.171084 | 353.875000 | 358.000000 | 671.000000 | 23.2285% |
| QQQ_MA200_QLD | quarterly | 20.5655% | -51.7154% | 16.9881% | 0.878313 | 471.666667 | 471.000000 | 754.000000 | 16.9838% |
| QQQ_MA200_QLD | weekly | 28.8706% | -49.1544% | 24.3365% | 1.610241 | 254.636364 | 211.000000 | 662.000000 | 23.8634% |
| QQQ_MA200_QQQ | bimonthly | 18.5373% | -28.5594% | 15.6468% | 0.731928 | 528.200000 | 589.000000 | 756.000000 | 15.2275% |
| QQQ_MA200_QQQ | monthly | 16.3148% | -28.5594% | 13.4360% | 1.171084 | 353.875000 | 358.000000 | 671.000000 | 13.3190% |
| QQQ_MA200_QQQ | quarterly | 12.8844% | -28.5594% | 10.4962% | 0.878313 | 471.666667 | 471.000000 | 754.000000 | 10.4921% |
| QQQ_MA200_QQQ | weekly | 16.6039% | -26.5495% | 13.8079% | 1.610241 | 254.636364 | 211.000000 | 662.000000 | 13.5466% |
| SPY_MA200_SSO | bimonthly | 20.4070% | -35.2135% | 17.2738% | 1.024699 | 359.857143 | 333.000000 | 671.000000 | 16.7066% |
| SPY_MA200_SSO | monthly | 14.0366% | -46.7416% | 11.6722% | 1.756626 | 235.750000 | 178.500000 | 671.000000 | 11.5030% |
| SPY_MA200_SSO | quarterly | 12.2605% | -60.4699% | 10.1599% | 0.878313 | 471.833333 | 502.000000 | 693.000000 | 10.0826% |
| SPY_MA200_SSO | weekly | 17.0441% | -36.2138% | 14.2607% | 2.634940 | 156.277778 | 55.000000 | 663.000000 | 13.9064% |

## Diagnostic fold continuity

The fold table is a chronological diagnostic view of the single stitched ledger. Fold 2013 starts from the configured initial capital; each later fold starts from the prior session's live equity. No fold-end liquidation or state reconstruction is used. Cross-year episodes and tax loss-pool state therefore remain continuous.

`oos_fold_metrics.csv` contains 336 rows (24 stitched combinations × 14 folds).

## Scope statement

This is fixed-rule chronological OOS evidence for the already-frozen MA200 baseline. The expanding annual folds are reporting slices, not parameter-fitting intervals. No window is chosen from these results, and this artifact makes no Walk-Forward parameter-selection claim.
