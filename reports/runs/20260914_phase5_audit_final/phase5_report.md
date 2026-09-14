# Phase 5 — Relative Momentum

## Frozen specification and common sample

The full-sample evaluation period is **2006-06-21 through 2026-08-31** (inclusive). The exact frozen lookback grid is `(126, 189, 252)` trading sessions, with two mappings and four frequencies: 24 economic combinations per tax mode and 48 rows in `relative_momentum_results.csv`.

Signals are calculated only from SPY and QQQ adjusted closes. For lookback L, `mom_SPY(t,L) = SPY_adjclose_t / SPY_adjclose_(t-L) - 1` and `mom_QQQ(t,L) = QQQ_adjclose_t / QQQ_adjclose_(t-L) - 1`; L-day momentum requires L+1 observations. The larger positive momentum is selected, but both non-positive values select CASH.

The 1X mapping is SPY selection → SPY and QQQ selection → QQQ. The 2X mapping is SPY selection → SSO and QQQ selection → QLD. Leveraged ETF prices are never used for selection. CASH earns exactly 0%.

Signals are observed at close *t*. A completed decision first becomes executable at the next available held-asset open (*t+1*); no same-day-close execution is used. Commission is 0 bps and slippage is 5 bps.

Phase 5 is a descriptive full-sample study only. No lookback or frequency is selected. It makes no OOS or Walk-Forward claim; Walk-Forward parameter selection remains deferred to the frozen later phase.

## Decision table and positive-tie audit

The implementation uses `choose_spy = ready & ~both_off & (spy_momentum >= qqq_momentum)`, so an exact positive tie would be assigned to SPY by this implementation convention. The frozen Phase 5 specification does not define a tie-break, so this is not described as a frozen strategy rule. The complete historical signal scan below found zero exact positive ties at every lookback/frequency rebalance decision; consequently the convention has zero historical economic impact.

| Case | Condition | Selected state |
|---|---|---|
| A | SPY > QQQ and SPY > 0 | SPY |
| B | QQQ > SPY and QQQ > 0 | QQQ |
| C | SPY > 0 and QQQ <= 0 | SPY |
| D | QQQ > 0 and SPY <= 0 | QQQ |
| E | SPY <= 0 and QQQ <= 0 | CASH |
| F | SPY = 0 and QQQ < 0 | CASH |
| G | QQQ = 0 and SPY < 0 | CASH |
| H | SPY = QQQ = 0 | CASH |

| L | Frequency | Rebalance decisions | Exact positive ties in full signal history | Ties used at rebalance | Tie close dates | Tie execution dates |
|---:|---|---:|---:|---:|---|---|
| 126 | weekly | 1436 | 0 | 0 | none | none |
| 126 | monthly | 331 | 0 | 0 | none | none |
| 126 | bimonthly | 166 | 0 | 0 | none | none |
| 126 | quarterly | 111 | 0 | 0 | none | none |
| 189 | weekly | 1436 | 0 | 0 | none | none |
| 189 | monthly | 331 | 0 | 0 | none | none |
| 189 | bimonthly | 166 | 0 | 0 | none | none |
| 189 | quarterly | 111 | 0 | 0 | none | none |
| 252 | weekly | 1436 | 0 | 0 | none | none |
| 252 | monthly | 331 | 0 | 0 | none | none |
| 252 | bimonthly | 166 | 0 | 0 | none | none |
| 252 | quarterly | 111 | 0 | 0 | none | none |

## Warm-up and common-calendar audit

Pre-evaluation history is used only for legitimate signal warm-up. The relative comparison is formed on the common SPY/QQQ signal calendar. The final evaluation index is deliberately based on the SSO calendar because it is the canonical first held-asset execution calendar; all SPY, QQQ, SSO, and QLD evaluation calendars were checked and have zero missing sessions. Warm-up creates no pre-evaluation equity, positions, trades, or taxes.

| Signal | L | Full rows | Pre-start rows | Required observations | Lookback start | First valid momentum date | Common signal rows | Evaluation rows | Missing targets |
|---|---:|---:|---:|---:|---|---|---:|---:|---:|
| SPY | 126 | 8461 | 3374 | 127 | 2005-12-19 | 1999-09-08 | 5080 | 5080 | 0 |
| QQQ | 126 | 6919 | 1832 | 127 | 2005-12-19 | 1999-09-08 | 5080 | 5080 | 0 |
| SPY | 189 | 8461 | 3374 | 190 | 2005-09-20 | 1999-12-07 | 5080 | 5080 | 0 |
| QQQ | 189 | 6919 | 1832 | 190 | 2005-09-20 | 1999-12-07 | 5080 | 5080 | 0 |
| SPY | 252 | 8461 | 3374 | 253 | 2005-06-21 | 2000-03-08 | 5080 | 5080 | 0 |
| QQQ | 252 | 6919 | 1832 | 253 | 2005-06-21 | 2000-03-08 | 5080 | 5080 | 0 |

| Mapping | Evaluation basis | Common signal rows | Evaluation rows | Missing SPY | Missing QQQ | Missing held SPY leg | Missing held QQQ leg | Missing targets |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| RELATIVE_MOMENTUM_1X (SPY / QQQ) | SSO calendar | 5080 | 5080 | 0 | 0 | 0 | 0 | 0 |
| RELATIVE_MOMENTUM_2X (SSO / QLD) | SSO calendar | 5080 | 5080 | 0 | 0 | 0 | 0 | 0 |

## Rebalance convention

Weekly uses the first trading session of each Sunday-ending week. Monthly uses the first trading session of each calendar month. Bi-monthly uses the first trading session of odd frozen months Jan/Mar/May/Jul/Sep/Nov. Quarterly uses the first trading session of each calendar quarter. Ranking changes between scheduled sessions do not change the target until the next eligible rebalance.

## Stability ranges (descriptive only)

`CAGR spread = max(CAGR) − min(CAGR)` and `MaxDD spread = max(abs(MaxDD)) − min(abs(MaxDD))`. The lookback labels are descriptive extrema only and are never called optimal, best, selected, recommended, or a winner.

| Mapping | Frequency | Pre-tax CAGR min–max | CAGR spread | Abs MaxDD min–max | MaxDD spread | Calmar min–max | After-tax CAGR min–max | Terminal CAGR min–max | Turnover min–max | Trades min–max | Mean hold min–max | Descriptive min-CAGR L | Descriptive max-CAGR L |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| RELATIVE_MOMENTUM_1X | weekly | 10.8905%–12.4877% | 1.5972% | 28.5594%–29.6278% | 1.0685% | 0.380688–0.421485 | 8.8398%–10.1958% | 8.7397%–10.0279% | 6.533549–8.315753 | 133–169 | 49.142857–64.893939 | 126 | 252 |
| RELATIVE_MOMENTUM_1X | monthly | 10.8111%–15.1154% | 4.3042% | 28.5594%–32.0289% | 3.4696% | 0.337542–0.529261 | 8.7175%–12.5964% | 8.6788%–12.2734% | 2.276846–4.454803 | 47–91 | 91.422222–179.869565 | 126 | 252 |
| RELATIVE_MOMENTUM_1X | bimonthly | 10.2354%–14.5767% | 4.3414% | 28.5594%–52.2243% | 23.6650% | 0.195988–0.510401 | 8.3190%–12.1674% | 8.2434%–11.8310% | 1.880894–2.771810 | 39–57 | 148.500000–214.421053 | 126 | 252 |
| RELATIVE_MOMENTUM_1X | quarterly | 10.5112%–12.9901% | 2.4790% | 28.5594%–30.3242% | 1.7648% | 0.346627–0.454847 | 8.4774%–10.7947% | 8.4747%–10.5228% | 1.583881–2.276846 | 33–47 | 183.391304–259.875000 | 126 | 252 |
| RELATIVE_MOMENTUM_2X | weekly | 17.3845%–19.7620% | 2.3775% | 50.3891%–54.8009% | 4.4118% | 0.345004–0.369707 | 14.0962%–16.1048% | 14.0357%–15.9200% | 6.533549–8.315753 | 133–169 | 49.142857–64.893939 | 126 | 252 |
| RELATIVE_MOMENTUM_2X | monthly | 16.4199%–25.0237% | 8.6038% | 51.7154%–57.3824% | 5.6670% | 0.286149–0.483873 | 13.2995%–20.9934% | 13.2768%–20.5129% | 2.276846–4.454803 | 47–91 | 91.422222–179.869565 | 126 | 252 |
| RELATIVE_MOMENTUM_2X | bimonthly | 14.5420%–23.6181% | 9.0761% | 51.7154%–79.6724% | 27.9570% | 0.182523–0.456693 | 11.9229%–19.8851% | 11.8094%–19.3665% | 1.880894–2.771810 | 39–57 | 148.500000–214.421053 | 126 | 252 |
| RELATIVE_MOMENTUM_2X | quarterly | 15.5814%–20.2158% | 4.6344% | 51.7154%–57.2588% | 5.5434% | 0.272122–0.377751 | 12.6469%–16.9719% | 12.6441%–16.5390% | 1.583881–2.276846 | 33–47 | 183.391304–259.875000 | 126 | 252 |

## Complete metric surface

All 48 tax-mode metric rows are retained. Holding periods are completed continuous risky-asset episodes measured in trading sessions; a SPY→QQQ or SSO→QLD switch ends one episode and starts another, and an open terminal position is not fabricated into a completed episode. After-tax wealth and CAGR mean wealth after realized tax paid to date. Terminal-liquidation fields are hypothetical diagnostics only: they do not add a SELL, change turnover or holding statistics, or mutate the tax ledger.

| Mapping | Frequency | L | Tax mode | CAGR | MaxDD | Calmar | Annual turnover | Mean hold | Median hold | Max hold | Trades | Costs | Realized tax | Terminal CAGR |
|---|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| RELATIVE_MOMENTUM_1X | bimonthly | 126 | after_tax | 8.3190% | -52.3270% | 0.158981 | 2.658697 | 149.296296 | 125.000000 | 586.000000 | 55 | $6,343.15 | $93,952.53 | 8.2434% |
| RELATIVE_MOMENTUM_1X | bimonthly | 126 | pre_tax | 10.2354% | -52.2243% | 0.195988 | 2.672921 | 149.296296 | 125.000000 | 586.000000 | 55 | $7,999.95 | $0.00 | N/A |
| RELATIVE_MOMENTUM_1X | bimonthly | 189 | after_tax | 10.2915% | -28.5594% | 0.360355 | 2.754850 | 148.500000 | 82.500000 | 463.000000 | 57 | $9,222.30 | $146,473.98 | 10.2145% |
| RELATIVE_MOMENTUM_1X | bimonthly | 189 | pre_tax | 12.6296% | -28.5594% | 0.442221 | 2.771810 | 148.500000 | 82.500000 | 463.000000 | 57 | $12,361.53 | $0.00 | N/A |
| RELATIVE_MOMENTUM_1X | bimonthly | 252 | after_tax | 12.1674% | -28.5594% | 0.426039 | 1.863914 | 214.421053 | 128.000000 | 755.000000 | 39 | $5,531.42 | $159,043.40 | 11.8310% |
| RELATIVE_MOMENTUM_1X | bimonthly | 252 | pre_tax | 14.5767% | -28.5594% | 0.510401 | 1.880894 | 214.421053 | 128.000000 | 755.000000 | 39 | $7,250.49 | $0.00 | N/A |
| RELATIVE_MOMENTUM_1X | monthly | 126 | after_tax | 8.7175% | -32.0289% | 0.272176 | 4.437188 | 91.422222 | 42.000000 | 316.000000 | 91 | $11,281.64 | $107,795.84 | 8.6788% |
| RELATIVE_MOMENTUM_1X | monthly | 126 | pre_tax | 10.8111% | -32.0289% | 0.337542 | 4.454803 | 91.422222 | 42.000000 | 316.000000 | 91 | $14,650.49 | $0.00 | N/A |
| RELATIVE_MOMENTUM_1X | monthly | 189 | after_tax | 9.5068% | -29.8791% | 0.318175 | 3.348469 | 125.352941 | 43.500000 | 483.000000 | 69 | $9,784.61 | $130,482.11 | 9.4798% |
| RELATIVE_MOMENTUM_1X | monthly | 189 | pre_tax | 11.7472% | -28.5594% | 0.411324 | 3.365837 | 125.352941 | 43.500000 | 483.000000 | 69 | $12,850.49 | $0.00 | N/A |
| RELATIVE_MOMENTUM_1X | monthly | 252 | after_tax | 12.5964% | -28.5594% | 0.441059 | 2.259395 | 179.869565 | 64.000000 | 777.000000 | 47 | $8,707.57 | $177,274.13 | 12.2734% |
| RELATIVE_MOMENTUM_1X | monthly | 252 | pre_tax | 15.1154% | -28.5594% | 0.529261 | 2.276846 | 179.869565 | 64.000000 | 777.000000 | 47 | $12,097.82 | $0.00 | N/A |
| RELATIVE_MOMENTUM_1X | quarterly | 126 | after_tax | 8.4774% | -34.6609% | 0.244580 | 2.165810 | 186.045455 | 127.500000 | 565.000000 | 45 | $5,777.56 | $108,713.42 | 8.4747% |
| RELATIVE_MOMENTUM_1X | quarterly | 126 | pre_tax | 10.5112% | -30.3242% | 0.346627 | 2.177932 | 186.045455 | 127.500000 | 565.000000 | 45 | $7,400.21 | $0.00 | N/A |
| RELATIVE_MOMENTUM_1X | quarterly | 189 | after_tax | 9.0815% | -29.4130% | 0.308757 | 2.261480 | 183.391304 | 188.000000 | 504.000000 | 47 | $6,831.71 | $124,640.87 | 9.0788% |
| RELATIVE_MOMENTUM_1X | quarterly | 189 | pre_tax | 11.2454% | -28.5594% | 0.393756 | 2.276846 | 183.391304 | 188.000000 | 504.000000 | 47 | $8,986.77 | $0.00 | N/A |
| RELATIVE_MOMENTUM_1X | quarterly | 252 | after_tax | 10.7947% | -30.6389% | 0.352321 | 1.566124 | 259.875000 | 190.000000 | 878.000000 | 33 | $4,868.98 | $128,811.34 | 10.5228% |
| RELATIVE_MOMENTUM_1X | quarterly | 252 | pre_tax | 12.9901% | -28.5594% | 0.454847 | 1.583881 | 259.875000 | 190.000000 | 878.000000 | 33 | $6,314.94 | $0.00 | N/A |
| RELATIVE_MOMENTUM_1X | weekly | 126 | after_tax | 8.8398% | -28.9316% | 0.305541 | 8.298320 | 49.142857 | 14.500000 | 334.000000 | 169 | $21,561.54 | $103,050.81 | 8.7397% |
| RELATIVE_MOMENTUM_1X | weekly | 126 | pre_tax | 10.8905% | -28.6075% | 0.380688 | 8.315753 | 49.142857 | 14.500000 | 334.000000 | 169 | $28,212.52 | $0.00 | N/A |
| RELATIVE_MOMENTUM_1X | weekly | 189 | after_tax | 9.5789% | -29.1634% | 0.328455 | 8.003526 | 53.037037 | 10.000000 | 489.000000 | 163 | $26,929.07 | $137,553.64 | 9.5762% |
| RELATIVE_MOMENTUM_1X | weekly | 189 | pre_tax | 11.8894% | -28.5594% | 0.416306 | 8.018566 | 53.037037 | 10.000000 | 489.000000 | 163 | $36,417.36 | $0.00 | N/A |
| RELATIVE_MOMENTUM_1X | weekly | 252 | after_tax | 10.1958% | -31.5983% | 0.322670 | 6.514988 | 64.893939 | 15.000000 | 573.000000 | 133 | $23,267.39 | $128,929.15 | 10.0279% |
| RELATIVE_MOMENTUM_1X | weekly | 252 | pre_tax | 12.4877% | -29.6278% | 0.421485 | 6.533549 | 64.893939 | 15.000000 | 573.000000 | 133 | $32,295.79 | $0.00 | N/A |
| RELATIVE_MOMENTUM_2X | bimonthly | 126 | after_tax | 11.9229% | -79.6724% | 0.149649 | 2.654321 | 149.296296 | 125.000000 | 586.000000 | 55 | $9,274.42 | $198,164.75 | 11.8094% |
| RELATIVE_MOMENTUM_2X | bimonthly | 126 | pre_tax | 14.5420% | -79.6724% | 0.182523 | 2.672921 | 149.296296 | 125.000000 | 586.000000 | 55 | $13,123.52 | $0.00 | N/A |
| RELATIVE_MOMENTUM_2X | bimonthly | 189 | after_tax | 16.3906% | -52.1863% | 0.314079 | 2.747498 | 148.500000 | 82.500000 | 463.000000 | 57 | $19,893.16 | $467,531.41 | 16.2725% |
| RELATIVE_MOMENTUM_2X | bimonthly | 189 | pre_tax | 19.9514% | -51.7154% | 0.385792 | 2.771810 | 148.500000 | 82.500000 | 463.000000 | 57 | $31,646.52 | $0.00 | N/A |
| RELATIVE_MOMENTUM_2X | bimonthly | 252 | after_tax | 19.8851% | -51.7154% | 0.384510 | 1.856603 | 214.421053 | 128.000000 | 755.000000 | 39 | $11,916.87 | $559,832.37 | 19.3665% |
| RELATIVE_MOMENTUM_2X | bimonthly | 252 | pre_tax | 23.6181% | -51.7154% | 0.456693 | 1.880894 | 214.421053 | 128.000000 | 755.000000 | 39 | $18,875.11 | $0.00 | N/A |
| RELATIVE_MOMENTUM_2X | monthly | 126 | after_tax | 13.2995% | -57.3824% | 0.231770 | 4.430144 | 91.422222 | 42.000000 | 316.000000 | 91 | $20,480.57 | $286,150.69 | 13.2768% |
| RELATIVE_MOMENTUM_2X | monthly | 126 | pre_tax | 16.4199% | -57.3824% | 0.286149 | 4.454803 | 91.422222 | 42.000000 | 316.000000 | 91 | $31,519.23 | $0.00 | N/A |
| RELATIVE_MOMENTUM_2X | monthly | 189 | after_tax | 14.8867% | -56.0693% | 0.265506 | 3.341583 | 125.352941 | 43.500000 | 483.000000 | 69 | $18,932.21 | $377,959.73 | 14.8380% |
| RELATIVE_MOMENTUM_2X | monthly | 189 | pre_tax | 18.2735% | -52.7129% | 0.346660 | 3.365837 | 125.352941 | 43.500000 | 483.000000 | 69 | $29,315.49 | $0.00 | N/A |
| RELATIVE_MOMENTUM_2X | monthly | 252 | after_tax | 20.9934% | -51.7154% | 0.405942 | 2.251229 | 179.869565 | 64.000000 | 777.000000 | 47 | $23,506.07 | $718,256.18 | 20.5129% |
| RELATIVE_MOMENTUM_2X | monthly | 252 | pre_tax | 25.0237% | -51.7154% | 0.483873 | 2.276846 | 179.869565 | 64.000000 | 777.000000 | 47 | $40,725.58 | $0.00 | N/A |
| RELATIVE_MOMENTUM_2X | quarterly | 126 | after_tax | 12.6469% | -61.1983% | 0.206655 | 2.160847 | 186.045455 | 127.500000 | 565.000000 | 45 | $10,231.51 | $280,445.86 | 12.6441% |
| RELATIVE_MOMENTUM_2X | quarterly | 126 | pre_tax | 15.5814% | -57.2588% | 0.272122 | 2.177932 | 186.045455 | 127.500000 | 565.000000 | 45 | $15,104.71 | $0.00 | N/A |
| RELATIVE_MOMENTUM_2X | quarterly | 189 | after_tax | 13.7232% | -52.1530% | 0.263134 | 2.255972 | 183.391304 | 188.000000 | 504.000000 | 47 | $12,834.46 | $334,672.27 | 13.7204% |
| RELATIVE_MOMENTUM_2X | quarterly | 189 | pre_tax | 16.8261% | -51.7154% | 0.325359 | 2.276846 | 183.391304 | 188.000000 | 504.000000 | 47 | $19,499.12 | $0.00 | N/A |
| RELATIVE_MOMENTUM_2X | quarterly | 252 | after_tax | 16.9719% | -56.9892% | 0.297810 | 1.559186 | 259.875000 | 190.000000 | 878.000000 | 33 | $9,654.00 | $365,415.03 | 16.5390% |
| RELATIVE_MOMENTUM_2X | quarterly | 252 | pre_tax | 20.2158% | -53.5162% | 0.377751 | 1.583881 | 259.875000 | 190.000000 | 878.000000 | 33 | $14,541.50 | $0.00 | N/A |
| RELATIVE_MOMENTUM_2X | weekly | 126 | after_tax | 14.0962% | -50.3891% | 0.279747 | 8.288697 | 49.142857 | 14.500000 | 334.000000 | 169 | $42,745.20 | $321,619.61 | 14.0357% |
| RELATIVE_MOMENTUM_2X | weekly | 126 | pre_tax | 17.3845% | -50.3891% | 0.345004 | 8.315753 | 49.142857 | 14.500000 | 334.000000 | 169 | $67,831.79 | $0.00 | N/A |
| RELATIVE_MOMENTUM_2X | weekly | 189 | after_tax | 15.5180% | -52.0837% | 0.297944 | 7.997272 | 53.037037 | 10.000000 | 489.000000 | 163 | $60,099.88 | $453,533.11 | 15.5152% |
| RELATIVE_MOMENTUM_2X | weekly | 189 | pre_tax | 19.1196% | -51.7154% | 0.369707 | 8.018566 | 53.037037 | 10.000000 | 489.000000 | 163 | $97,399.27 | $0.00 | N/A |
| RELATIVE_MOMENTUM_2X | weekly | 252 | after_tax | 16.1048% | -58.8829% | 0.273506 | 6.505700 | 64.893939 | 15.000000 | 573.000000 | 133 | $51,280.99 | $414,548.57 | 15.9200% |
| RELATIVE_MOMENTUM_2X | weekly | 252 | pre_tax | 19.7620% | -54.8009% | 0.360614 | 6.533549 | 64.893939 | 15.000000 | 573.000000 | 133 | $86,867.79 | $0.00 | N/A |

## Turnover audit

Annual turnover uses `sum(abs(trade_notional) / contemporaneous_pretrade_equity) / calendar_years`, using the audited Phase 2 helper after reconstructing rotation open-before-trade equity from cash and each asset's prior-session shares valued at the current open. Initial deployment and hypothetical terminal liquidation are excluded. Both SELL and BUY legs of a rotation are included. The execution cost rate is 0.00050000 (0 commission bps + 5 slippage bps).

| Mapping | Frequency | L | Included normalized turnover | Calendar years | Annual turnover | Included trade dates | Gross notional | Trades |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| RELATIVE_MOMENTUM_1X | weekly | 126 | 167.931534233 | 20.194387406 | 8.315752831 | 115 | $56,425,045.02 | 169 |
| RELATIVE_MOMENTUM_1X | weekly | 189 | 161.930034983 | 20.194387406 | 8.018566334 | 103 | $72,834,728.74 | 163 |
| RELATIVE_MOMENTUM_1X | weekly | 252 | 131.941029485 | 20.194387406 | 6.533549487 | 80 | $64,591,570.09 | 133 |
| RELATIVE_MOMENTUM_1X | monthly | 126 | 89.962018991 | 20.194387406 | 4.454803069 | 59 | $29,300,984.79 | 91 |
| RELATIVE_MOMENTUM_1X | monthly | 189 | 67.971014493 | 20.194387406 | 3.365836909 | 44 | $25,700,988.22 | 69 |
| RELATIVE_MOMENTUM_1X | monthly | 252 | 45.979510245 | 20.194387406 | 2.276846003 | 28 | $24,195,635.08 | 47 |
| RELATIVE_MOMENTUM_1X | bimonthly | 126 | 53.978010995 | 20.194387406 | 2.672921437 | 37 | $15,999,904.80 | 55 |
| RELATIVE_MOMENTUM_1X | bimonthly | 189 | 55.975012494 | 20.194387406 | 2.771810373 | 34 | $24,723,056.25 | 57 |
| RELATIVE_MOMENTUM_1X | bimonthly | 252 | 37.983508246 | 20.194387406 | 1.880894304 | 24 | $14,500,972.19 | 39 |
| RELATIVE_MOMENTUM_1X | quarterly | 126 | 43.982008996 | 20.194387406 | 2.177932319 | 30 | $14,800,413.47 | 45 |
| RELATIVE_MOMENTUM_1X | quarterly | 189 | 45.979510245 | 20.194387406 | 2.276846003 | 28 | $17,973,544.90 | 47 |
| RELATIVE_MOMENTUM_1X | quarterly | 252 | 31.985507246 | 20.194387406 | 1.583881036 | 19 | $12,629,876.36 | 33 |
| RELATIVE_MOMENTUM_2X | weekly | 126 | 167.931534233 | 20.194387406 | 8.315752831 | 115 | $135,663,584.42 | 169 |
| RELATIVE_MOMENTUM_2X | weekly | 189 | 161.930034983 | 20.194387406 | 8.018566334 | 103 | $194,798,544.61 | 163 |
| RELATIVE_MOMENTUM_2X | weekly | 252 | 131.941029485 | 20.194387406 | 6.533549487 | 80 | $173,735,587.39 | 133 |
| RELATIVE_MOMENTUM_2X | monthly | 126 | 89.962018991 | 20.194387406 | 4.454803069 | 59 | $63,038,458.89 | 91 |
| RELATIVE_MOMENTUM_2X | monthly | 189 | 67.971014493 | 20.194387406 | 3.365836909 | 44 | $58,630,979.57 | 69 |
| RELATIVE_MOMENTUM_2X | monthly | 252 | 45.979510245 | 20.194387406 | 2.276846003 | 28 | $81,451,158.71 | 47 |
| RELATIVE_MOMENTUM_2X | bimonthly | 126 | 53.978010995 | 20.194387406 | 2.672921437 | 37 | $26,247,043.15 | 55 |
| RELATIVE_MOMENTUM_2X | bimonthly | 189 | 55.975012494 | 20.194387406 | 2.771810373 | 34 | $63,293,046.24 | 57 |
| RELATIVE_MOMENTUM_2X | bimonthly | 252 | 37.983508246 | 20.194387406 | 1.880894304 | 24 | $37,750,211.74 | 39 |
| RELATIVE_MOMENTUM_2X | quarterly | 126 | 43.982008996 | 20.194387406 | 2.177932319 | 30 | $30,209,428.06 | 45 |
| RELATIVE_MOMENTUM_2X | quarterly | 189 | 45.979510245 | 20.194387406 | 2.276846003 | 28 | $38,998,244.52 | 47 |
| RELATIVE_MOMENTUM_2X | quarterly | 252 | 31.985507246 | 20.194387406 | 1.583881036 | 19 | $29,082,991.70 | 33 |

## Common-sample benchmarks

SPY, QQQ, SSO, and QLD buy-and-hold endpoints use the same SSO-based evaluation sample and audited benchmark conventions. They are descriptive benchmarks, not predictive evidence.

| Benchmark | Start | End | CAGR | MaxDD | Calmar | Annual turnover |
|---|---|---|---:|---:|---:|---:|
| SPY | 2006-06-21 | 2026-08-31 | 11.4506% | -55.1894% | 0.207478 | 0.000000 |
| QQQ | 2006-06-21 | 2026-08-31 | 16.5315% | -53.4040% | 0.309556 | 0.000000 |
| SSO | 2006-06-21 | 2026-08-31 | 15.8320% | -84.6673% | 0.186991 | 0.000000 |
| QLD | 2006-06-21 | 2026-08-31 | 25.0201% | -83.1289% | 0.300979 | 0.000000 |

Tax convention: Simplified Japan taxable mode uses average cost, immediate payment, and loss-pool treatment at realized sales. Unrealized appreciation is not taxed merely for increasing in value. Cumulative realized tax paid is retained in `cumulative_realized_tax_paid`; terminal liquidation is non-mutating and diagnostic only.

`relative_momentum_results.csv` is the complete 48-row metric surface including tax mode. `parameter_results.csv` is the 24-row unique frozen economic grid with `searched_for_selection=False` and `selection_performed=False`; it is enumeration, not parameter selection.

No lookback or frequency is selected from Phase 5 results. Phase 5 is not OOS evidence, and Walk-Forward parameter selection remains deferred to the frozen later phase.
