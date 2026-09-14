# Phase 2 External Audit Diff

Compared against `reports/runs/20260913_phase2_ma200_final`, the stale Phase 2 run whose holding-period field was `7376` for every strategy.

## A. Complete pytest result

The complete suite result after adding the dedicated Phase 2 module is **81 passed** (`81 passed in 12.16s`), with no failures, errors, skips, xfails, or warnings. The dedicated Phase 2 module itself is **12 passed**.

The dedicated tests cover the exact 200-session MA window and strict comparison, future-data mutation, actual close-*t* to next-open execution, a large open/close gap, all four first-available-session schedules, non-rebalance-day waiting, QQQ-signal/QLD-held separation, zero-return CASH, exact 5 bps costs, average-cost immediate tax and loss-pool treatment, warm-up/calendar alignment, non-mutating terminal diagnostics, and final artifact completeness.

## B. Strategy-count verification

The frozen grid is exactly three rules × four frequencies:

| Tax mode | Rows | Expected |
|---|---:|---:|
| `metrics_pre_tax.csv` | 12 | 12 |
| `metrics_after_tax.csv` | 12 | 12 |
| `ma200_results.csv` | 24 | 24 |
| `parameter_results.csv` | 12 | 12 |

`parameter_results.csv` contains only the twelve frozen rule/frequency combinations, every row has `ma_window=200`, and every row has `searched=False`. No neighboring MA window or parameter alternative was evaluated.

## C. No-lookahead and execution-gap audit

The deterministic MA200 test has 199 insufficient prior observations, uses the close through session *t* for the MA at *t*, and switches under the frozen strict `close > MA` rule. Mutating all prices strictly after a cutoff leaves every signal through that cutoff identical.

The actual `single_asset_timed_backtest` ledger test changes the MA state at a Friday close. The Friday position remains CASH and has no trade; the BUY occurs Monday (the next eligible weekly session) at Monday's open. The synthetic Monday open is 150 while Friday's close is 101, and the recorded trade price is exactly 150 with `transaction_cost = notional × 5 / 10000`. This is an actual trade-ledger assertion, not only a helper-output assertion.

## D. Rebalance schedule audit

All four schedule tests passed. They use intentionally missing first calendar days:

* weekly: first available session of the Sunday-ending week;
* monthly: first available session of the calendar month;
* bi-monthly: first available session of odd months Jan/Mar/May/Jul/Sep/Nov;
* quarterly: first available session of Jan/Apr/Jul/Oct.

The tests explicitly reject period-end scheduling. A daily signal change between scheduled sessions remains in the current state until the next scheduled decision/execution sequence.

## E. Warm-up and calendar-alignment audit

The common evaluation sample is `2006-06-21` through `2026-08-31`, inclusive. Pre-start history is used only as MA warm-up; no pre-evaluation equity or trade is created.

| Signal asset | Full rows | Rows before evaluation start | 200-observation lookback at start | Lookback start | First valid MA200 date | First evaluation date |
|---|---:|---:|---:|---|---|---|
| QQQ | 6,919 | 1,832 | 200 | 2005-09-06 | 1999-12-21 | 2006-06-21 |
| SPY | 8,461 | 3,374 | 200 | 2005-09-06 | 1993-11-11 | 2006-06-21 |

The first evaluation-day target is derived only from information available by the prior close; execution, when scheduled, is at the evaluation-day open. The final reindex is explicit and has no missing targets:

| Mapping | Signal rows in evaluation sample | Held rows in evaluation sample | Common rows | Missing targets |
|---|---:|---:|---:|---:|
| QQQ → QQQ | 5,080 | 5,080 | 5,080 | 0 |
| QQQ → QLD | 5,080 | 5,080 | 5,080 | 0 |
| SPY → SSO | 5,080 | 5,080 | 5,080 | 0 |

First actual strategy execution dates (from the pre-tax trade ledger) are:

| Rule | Frequency | First evaluation date | First strategy execution date |
|---|---|---|---|
| QQQ_MA200_QQQ | weekly | 2006-06-21 | 2006-09-18 |
| QQQ_MA200_QQQ | monthly | 2006-06-21 | 2006-10-02 |
| QQQ_MA200_QQQ | bimonthly | 2006-06-21 | 2006-06-21 |
| QQQ_MA200_QQQ | quarterly | 2006-06-21 | 2006-06-21 |
| QQQ_MA200_QLD | weekly | 2006-06-21 | 2006-09-18 |
| QQQ_MA200_QLD | monthly | 2006-06-21 | 2006-10-02 |
| QQQ_MA200_QLD | bimonthly | 2006-06-21 | 2006-06-21 |
| QQQ_MA200_QLD | quarterly | 2006-06-21 | 2006-06-21 |
| SPY_MA200_SSO | weekly | 2006-06-21 | 2006-07-03 |
| SPY_MA200_SSO | monthly | 2006-06-21 | 2006-06-21 |
| SPY_MA200_SSO | bimonthly | 2006-06-21 | 2006-06-21 |
| SPY_MA200_SSO | quarterly | 2006-06-21 | 2006-06-21 |

## F. Complete old → new metric diff

The old run had only `average_holding_period_days`; its value was the full calendar duration `7376`. It did not have the audited mean/median/max fields. The new primary holding fields are completed position episodes measured in trading sessions; an open terminal position is excluded. Every economic result and trade count is unchanged; turnover and holding fields are reporting-definition corrections (classification A), not strategy-economic changes (classification B).

| Rule / frequency | Tax mode | Ending value old → new | CAGR old → new | MaxDD old → new | Calmar old → new | Annual turnover old → new | Mean hold old → new | Median hold old → new | Max hold old → new | Trades old → new | Costs old → new | Realized tax old → new |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| QQQ_MA200_QQQ / weekly | pre_tax | $1,146,534.21 → $1,146,534.21 | 12.839065% → 12.839065% | -28.766996% → -28.766996% | 0.446312 → 0.446312 | 6.747942 → 2.673342 | 7376.000000 → 146.814815 | N/A → 29.000000 | N/A → 662 | 55 → 55 | $6,813.53 → $6,813.53 | $0.00 → $0.00 |
| QQQ_MA200_QQQ / weekly | after_tax | $767,667.88 → $767,667.88 | 10.619742% → 10.619742% | -30.502918% → -30.502918% | 0.348155 → 0.348155 | 5.539796 → 2.673342 | 7376.000000 → 146.814815 | N/A → 29.000000 | N/A → 662 | 55 → 55 | $5,593.64 → $5,593.64 | $140,823.92 → $140,823.92 |
| QQQ_MA200_QQQ / monthly | pre_tax | $1,194,574.82 → $1,194,574.82 | 13.068652% → 13.068652% | -28.559366% → -28.559366% | 0.457596 → 0.457596 | 4.815034 → 1.386177 | 7376.000000 → 286.214286 | N/A → 253.000000 | N/A → 901 | 29 → 29 | $4,861.83 → $4,861.83 | $0.00 → $0.00 |
| QQQ_MA200_QQQ / monthly | after_tax | $787,260.28 → $787,260.28 | 10.757877% → 10.757877% | -32.366804% → -32.366804% | 0.332374 → 0.332374 | 3.777115 → 1.386177 | 7376.000000 → 286.214286 | N/A → 253.000000 | N/A → 901 | 29 → 29 | $3,813.83 → $3,813.83 | $161,770.11 → $161,770.11 |
| QQQ_MA200_QQQ / bimonthly | pre_tax | $1,474,567.90 → $1,474,567.90 | 14.253831% → 14.253831% | -28.559366% → -28.559366% | 0.499095 → 0.499095 | 3.196532 → 0.990127 | 7376.000000 → 373.900000 | N/A → 313.500000 | N/A → 881 | 21 → 21 | $3,227.60 → $3,227.60 | $0.00 → $0.00 |
| QQQ_MA200_QQQ / bimonthly | after_tax | $983,855.05 → $983,855.05 | 11.987273% → 11.987273% | -30.224513% → -30.224513% | 0.396608 → 0.396608 | 2.581306 → 0.990127 | 7376.000000 → 373.900000 | N/A → 313.500000 | N/A → 881 | 21 → 21 | $2,606.39 → $2,606.39 | $166,053.79 → $166,053.79 |
| QQQ_MA200_QQQ / quarterly | pre_tax | $730,757.58 → $730,757.58 | 10.350153% → 10.350153% | -28.559366% → -28.559366% | 0.362408 → 0.362408 | 3.274785 → 0.990127 | 7376.000000 → 390.600000 | N/A → 314.000000 | N/A → 880 | 21 → 21 | $3,306.61 → $3,306.61 | $0.00 → $0.00 |
| QQQ_MA200_QQQ / quarterly | after_tax | $511,496.15 → $511,496.15 | 8.417892% → 8.417892% | -28.559366% → -28.559366% | 0.294751 → 0.294751 | 2.626978 → 0.990127 | 7376.000000 → 390.600000 | N/A → 314.000000 | N/A → 880 | 21 → 21 | $2,652.51 → $2,652.51 | $107,235.12 → $107,235.12 |
| QQQ_MA200_QLD / weekly | pre_tax | $4,946,095.42 → $4,946,095.42 | 21.310304% → 21.310304% | -49.999165% → -49.999165% | 0.426213 → 0.426213 | 14.841339 → 2.673342 | 7376.000000 → 146.814815 | N/A → 29.000000 | N/A → 662 | 55 → 55 | $14,985.59 → $14,985.59 | $0.00 → $0.00 |
| QQQ_MA200_QLD / weekly | after_tax | $2,753,153.37 → $2,753,153.37 | 17.841576% → 17.841576% | -52.084319% → -52.084319% | 0.342552 → 0.342552 | 10.264208 → 2.673342 | 7376.000000 → 146.814815 | N/A → 29.000000 | N/A → 662 | 55 → 55 | $10,363.97 → $10,363.97 | $502,469.47 → $502,469.47 |
| QQQ_MA200_QLD / monthly | pre_tax | $4,958,359.99 → $4,958,359.99 | 21.325182% → 21.325182% | -51.715422% → -51.715422% | 0.412356 → 0.412356 | 13.050364 → 1.386177 | 7376.000000 → 286.214286 | N/A → 253.000000 | N/A → 901 | 29 → 29 | $13,177.21 → $13,177.21 | $0.00 → $0.00 |
| QQQ_MA200_QLD / monthly | after_tax | $2,781,882.08 → $2,781,882.08 | 17.902167% → 17.902167% | -53.552037% → -53.552037% | 0.334295 → 0.334295 | 8.656230 → 1.386177 | 7376.000000 → 286.214286 | N/A → 253.000000 | N/A → 901 | 29 → 29 | $8,740.36 → $8,740.36 | $614,296.02 → $614,296.02 |
| QQQ_MA200_QLD / bimonthly | pre_tax | $6,987,774.31 → $6,987,774.31 | 23.404012% → 23.404012% | -51.715422% → -51.715422% | 0.452554 → 0.452554 | 8.416651 → 0.990127 | 7376.000000 → 373.900000 | N/A → 313.500000 | N/A → 881 | 21 → 21 | $8,498.46 → $8,498.46 | $0.00 → $0.00 |
| QQQ_MA200_QLD / bimonthly | after_tax | $3,990,150.41 → $3,990,150.41 | 20.026992% → 20.026992% | -51.715422% → -51.715422% | 0.387254 → 0.387254 | 5.788523 → 0.990127 | 7376.000000 → 373.900000 | N/A → 313.500000 | N/A → 881 | 21 → 21 | $5,844.78 → $5,844.78 | $632,462.10 → $632,462.10 |
| QQQ_MA200_QLD / quarterly | pre_tax | $1,829,407.48 → $1,829,407.48 | 15.480322% → 15.480322% | -51.715422% → -51.715422% | 0.299337 → 0.299337 | 6.613213 → 0.990127 | 7376.000000 → 390.600000 | N/A → 314.000000 | N/A → 880 | 21 → 21 | $6,677.49 → $6,677.49 | $0.00 → $0.00 |
| QQQ_MA200_QLD / quarterly | after_tax | $1,132,531.48 → $1,132,531.48 | 12.770423% → 12.770423% | -54.098403% → -54.098403% | 0.236059 → 0.236059 | 4.712093 → 0.990127 | 7376.000000 → 390.600000 | N/A → 314.000000 | N/A → 880 | 21 → 21 | $4,757.89 → $4,757.89 | $278,392.80 → $278,392.80 |
| SPY_MA200_SSO / weekly | pre_tax | $1,109,089.20 → $1,109,089.20 | 12.653682% → 12.653682% | -41.409735% → -41.409735% | 0.305573 → 0.305573 | 8.493512 → 3.168405 | 7376.000000 → 122.187500 | N/A → 17.000000 | N/A → 663 | 65 → 65 | $8,576.06 → $8,576.06 | $0.00 → $0.00 |
| SPY_MA200_SSO / weekly | after_tax | $759,082.73 → $759,082.73 | 10.558155% → 10.558155% | -42.955630% → -42.955630% | 0.245792 → 0.245792 | 6.893309 → 3.168405 | 7376.000000 → 122.187500 | N/A → 17.000000 | N/A → 663 | 65 → 65 | $6,960.31 → $6,960.31 | $128,843.88 → $128,843.88 |
| SPY_MA200_SSO / monthly | pre_tax | $1,505,936.15 → $1,505,936.15 | 14.372986% → 14.372986% | -46.741580% → -46.741580% | 0.307499 → 0.307499 | 9.844132 → 1.485190 | 7376.000000 → 263.200000 | N/A → 209.000000 | N/A → 921 | 31 → 31 | $9,939.81 → $9,939.81 | $0.00 → $0.00 |
| SPY_MA200_SSO / monthly | after_tax | $974,585.53 → $974,585.53 | 11.934790% → 11.934790% | -50.218467% → -50.218467% | 0.237657 → 0.237657 | 7.029181 → 1.485190 | 7376.000000 → 263.200000 | N/A → 209.000000 | N/A → 921 | 31 → 31 | $7,097.50 → $7,097.50 | $198,391.42 → $198,391.42 |
| SPY_MA200_SSO / bimonthly | pre_tax | $2,744,303.97 → $2,744,303.97 | 17.822791% → 17.822791% | -37.359406% → -37.359406% | 0.477063 → 0.477063 | 7.244383 → 0.990127 | 7376.000000 → 361.700000 | N/A → 292.500000 | N/A → 921 | 21 → 21 | $7,314.79 → $7,314.79 | $0.00 → $0.00 |
| SPY_MA200_SSO / bimonthly | after_tax | $1,691,809.29 → $1,691,809.29 | 15.034041% → 15.034041% | -39.794833% → -39.794833% | 0.377789 → 0.377789 | 5.147122 → 0.990127 | 7376.000000 → 361.700000 | N/A → 292.500000 | N/A → 921 | 21 → 21 | $5,197.15 → $5,197.15 | $270,620.85 → $270,620.85 |
| SPY_MA200_SSO / quarterly | pre_tax | $957,364.28 → $957,364.28 | 11.836013% → 11.836013% | -60.469851% → -60.469851% | 0.195734 → 0.195734 | 3.940239 → 0.891114 | 7376.000000 → 441.222222 | N/A → 385.000000 | N/A → 942 | 19 → 19 | $3,978.54 → $3,978.54 | $0.00 → $0.00 |
| SPY_MA200_SSO / quarterly | after_tax | $662,416.48 → $662,416.48 | 9.814921% → 9.814921% | -62.943690% → -62.943690% | 0.155932 → 0.155932 | 3.061666 → 0.891114 | 7376.000000 → 441.222222 | N/A → 385.000000 | N/A → 942 | 19 → 19 | $3,091.42 → $3,091.42 | $135,775.53 → $135,775.53 |

The only changed primary fields are the audited annual turnover and completed-episode holding-period fields (classification A). Ending value, CAGR, MaxDD, Calmar, number of trades, transaction costs, and realized tax are byte/numerically unchanged. No classification B strategy-economic change occurred.

## G. Turnover audit

The four required rows were recomputed from actual Phase 2 ledgers. Initial deployment is excluded; terminal liquidation is hypothetical and excluded; each included notional is divided by the contemporaneous open-before-trade equity; annualization uses calendar years.

| Strategy | Frequency | Included normalized turnover | Calendar years | Annual turnover | Included trade dates/rebalances | Gross traded notional | Number of trades |
|---|---|---:|---:|---:|---:|---:|---:|
| QQQ_MA200_QQQ | weekly | 53.986506747 | 20.194387406 | 2.673342135 | 54 | $13,627,055.54 | 55 |
| QQQ_MA200_QQQ | monthly | 27.993003498 | 20.194387406 | 1.386177403 | 28 | $9,723,665.69 | 29 |
| QQQ_MA200_QLD | weekly | 53.986506747 | 20.194387406 | 2.673342135 | 54 | $29,971,174.70 | 55 |
| SPY_MA200_SSO | monthly | 29.992503748 | 20.194387406 | 1.485190075 | 30 | $19,879,622.53 | 31 |

## H. Tax and terminal-liquidation audit

All 12 after-tax rows include `after_tax_wealth_tax_paid_to_date`, `after_tax_cagr_tax_paid_to_date`, `cumulative_realized_tax_paid`, `terminal_liquidation_wealth`, `terminal_liquidation_cagr`, `terminal_liquidation_tax`, `terminal_liquidation_cost`, and `terminal_unrealized_gain_after_cost`. `cumulative_realized_tax_paid` equals the actual tax ledger total exactly for every row. Primary after-tax wealth/CAGR remain wealth after realized tax paid to date.

| Strategy / frequency | After-tax wealth after realized tax | Terminal wealth | Terminal CAGR | Terminal tax | Terminal cost | Terminal unrealized gain after cost |
|---|---:|---:|---:|---:|---:|---:|
| QQQ_MA200_QQQ / weekly | $767,667.88 | $743,940.83 | 10.4479% | $23,343.22 | $383.83 | $114,906.30 |
| QQQ_MA200_QQQ / monthly | $787,260.28 | $776,236.20 | 10.6806% | $10,630.45 | $393.63 | $52,328.07 |
| QQQ_MA200_QQQ / bimonthly | $983,855.05 | $936,227.87 | 11.7124% | $47,135.25 | $491.93 | $232,021.89 |
| QQQ_MA200_QQQ / quarterly | $511,496.15 | $511,240.40 | 8.4152% | $0.00 | $255.75 | -$9,386.25 |
| QQQ_MA200_QLD / weekly | $2,753,153.37 | $2,613,461.14 | 17.5381% | $138,315.66 | $1,376.58 | $680,854.80 |
| QQQ_MA200_QLD / monthly | $2,781,882.08 | $2,725,451.15 | 17.7826% | $55,039.99 | $1,390.94 | $270,932.80 |
| QQQ_MA200_QLD / bimonthly | $3,990,150.41 | $3,702,254.01 | 19.5827% | $285,901.33 | $1,995.08 | $1,407,341.05 |
| QQQ_MA200_QLD / quarterly | $1,132,531.48 | $1,131,965.21 | 12.7676% | $0.00 | $566.27 | -$60,022.51 |
| SPY_MA200_SSO / weekly | $759,082.73 | $727,556.88 | 10.3262% | $31,146.31 | $379.54 | $153,316.80 |
| SPY_MA200_SSO / monthly | $974,585.53 | $954,613.38 | 11.8201% | $19,484.85 | $487.29 | $95,913.63 |
| SPY_MA200_SSO / bimonthly | $1,691,809.29 | $1,583,403.40 | 14.6574% | $107,559.99 | $845.90 | $529,460.90 |
| SPY_MA200_SSO / quarterly | $662,416.48 | $656,090.38 | 9.7628% | $5,994.89 | $331.21 | $29,509.66 |

Terminal liquidation is diagnostic only: it does not append a SELL to `trades.csv`, does not change the 776 actual trade rows, does not change turnover or holding episodes, and does not mutate `tax_ledger.csv`. Dedicated synthetic tests also verify immediate average-cost tax, loss-pool offsets, and zero tax on unrealized appreciation.

## I. Raw snapshot SHA verification

The immutable raw snapshots are unchanged and match `data/raw/manifest.yaml`:

| Asset | SHA-256 |
|---|---|
| SPY | `6a73a96bf408a041bc7e77df51117ae5a0965769c407c6699f52b0fd489b28d8` |
| QQQ | `fe5aa0db7c8a717e00cd7726d04ba1d2faff627e9f6e48c0952a5e2f235052c6` |
| SSO | `b0636de318b2d72d4cf774d6af2e11b2bc47904150891a06a39d29355e6e2b5d` |
| QLD | `2499976b07ea6711b33befad63bd8e177ab85f0c820662330f9a4ad257532a9f` |
| TQQQ | `4b0b5c7500d7510bb2e61607e86130d635a3d05339cf7cde10ab7174551ccf76` |

The regenerated run's config snapshot SHA is identical to the stale run, and no data files were modified.

## J. Strategy equity-curve integrity

The complete `equity_curve.csv` SHA-256 is identical old → new:

`3a5985659b244ef2eda8fb634b317bdc7e8421baf0b8db865c7e8aeaff6f55f0`

The `drawdown.csv`, `positions.csv`, `trades.csv`, and `tax_ledger.csv` hashes are also identical old → new. Thus the strategy signals, executions, economic ledgers, ending values, CAGR, MaxDD, Calmar, costs, realized taxes, and equity curves did not change. Only stale metric reporting fields and the new non-mutating terminal diagnostics were added.

No Phase 3–7 code was started or modified.

PHASE 2 AUDIT PASS
