# Phase 4 — Absolute Momentum

## Frozen specification and common sample

The full-sample evaluation period is **2006-06-21 through 2026-08-31** (inclusive). The exact frozen momentum grid is `(126, 189, 252)` trading sessions across two rules and four frequencies: 24 economic combinations per tax mode and 48 rows in `absolute_momentum_results.csv`.

SPY adjusted-close absolute momentum signals map only to SSO/CASH. QQQ adjusted-close absolute momentum signals map only to QLD/CASH. The mathematical definition is `momentum_t = adjusted_close_t / adjusted_close_(t-L) - 1`; Risk-On is strictly `momentum_t > 0`, while exact zero and negative momentum are Risk-Off.

The signal is observed at close *t*. Execution is at the held ETF open no earlier than the next available session (*t+1*); no same-day-close execution is used. Weekly, monthly, bi-monthly, and quarterly schedules use the first available trading session of the period (odd months Jan/Mar/May/Jul/Sep/Nov for bi-monthly). CASH earns exactly 0%.

The three frozen lookbacks were evaluated as a descriptive full-sample grid, but no lookback was selected for deployment. Extrema below are in-sample descriptive observations, not selection evidence. Phase 4 makes no OOS or Walk-Forward claim; Walk-Forward parameter selection remains deferred to the frozen later phase.

## Warm-up and calendar audit

Pre-evaluation history is used only as legitimate warm-up. For momentum window L, the first valid calculation is the date at position L because it requires the current close and the close L sessions earlier. Warm-up creates no pre-evaluation equity, positions, or trades. Missing targets after final signal-to-held calendar alignment are zero.

| Signal | Window | Full rows | Pre-start rows | Required L | Observations at evaluation start | Lookback start | First valid momentum date | Missing targets |
|---|---:|---:|---:|---:|---:|---|---|---:|
| SPY | 126 | 8461 | 3374 | 126 | 127 | 2005-12-19 | 1993-07-30 | 0 |
| QQQ | 126 | 6919 | 1832 | 126 | 127 | 2005-12-19 | 1999-09-08 | 0 |
| SPY | 189 | 8461 | 3374 | 189 | 190 | 2005-09-20 | 1993-10-28 | 0 |
| QQQ | 189 | 6919 | 1832 | 189 | 190 | 2005-09-20 | 1999-12-07 | 0 |
| SPY | 252 | 8461 | 3374 | 252 | 253 | 2005-06-21 | 1994-01-27 | 0 |
| QQQ | 252 | 6919 | 1832 | 252 | 253 | 2005-06-21 | 2000-03-08 | 0 |

| Rule | Signal | Held | Signal rows | Held rows | Common rows | Missing targets |
|---|---|---|---:|---:|---:|---:|
| SPY_ABS_MOM_SSO | SPY | SSO | 5080 | 5080 | 5080 | 0 |
| QQQ_ABS_MOM_QLD | QQQ | QLD | 5080 | 5080 | 5080 | 0 |

| Rule | Frequency | Window | First actual execution date |
|---|---|---:|---|
| SPY_ABS_MOM_SSO | weekly | 126 | 2006-07-03 |
| SPY_ABS_MOM_SSO | weekly | 189 | 2006-06-21 |
| SPY_ABS_MOM_SSO | weekly | 252 | 2006-06-21 |
| SPY_ABS_MOM_SSO | monthly | 126 | 2006-06-21 |
| SPY_ABS_MOM_SSO | monthly | 189 | 2006-06-21 |
| SPY_ABS_MOM_SSO | monthly | 252 | 2006-06-21 |
| SPY_ABS_MOM_SSO | bimonthly | 126 | 2006-06-21 |
| SPY_ABS_MOM_SSO | bimonthly | 189 | 2006-06-21 |
| SPY_ABS_MOM_SSO | bimonthly | 252 | 2006-06-21 |
| SPY_ABS_MOM_SSO | quarterly | 126 | 2006-06-21 |
| SPY_ABS_MOM_SSO | quarterly | 189 | 2006-06-21 |
| SPY_ABS_MOM_SSO | quarterly | 252 | 2006-06-21 |
| QQQ_ABS_MOM_QLD | weekly | 126 | 2006-10-16 |
| QQQ_ABS_MOM_QLD | weekly | 189 | 2006-10-02 |
| QQQ_ABS_MOM_QLD | weekly | 252 | 2006-06-21 |
| QQQ_ABS_MOM_QLD | monthly | 126 | 2006-11-01 |
| QQQ_ABS_MOM_QLD | monthly | 189 | 2006-06-21 |
| QQQ_ABS_MOM_QLD | monthly | 252 | 2006-06-21 |
| QQQ_ABS_MOM_QLD | bimonthly | 126 | 2006-06-21 |
| QQQ_ABS_MOM_QLD | bimonthly | 189 | 2006-06-21 |
| QQQ_ABS_MOM_QLD | bimonthly | 252 | 2006-06-21 |
| QQQ_ABS_MOM_QLD | quarterly | 126 | 2006-06-21 |
| QQQ_ABS_MOM_QLD | quarterly | 189 | 2006-06-21 |
| QQQ_ABS_MOM_QLD | quarterly | 252 | 2006-06-21 |

## Stability ranges (descriptive only)

`CAGR spread = max(CAGR) − min(CAGR)` and `MaxDD spread = max(abs(MaxDD)) − min(abs(MaxDD))`. Lookback labels in the final two columns identify descriptive extrema only; none is optimal, selected, recommended, or a winner.

| Rule | Frequency | Pre-tax CAGR min–max | CAGR spread | Abs MaxDD min–max | MaxDD spread | Calmar min–max | After-tax CAGR min–max | Terminal CAGR min–max | Turnover min–max | Descriptive min-CAGR L | Descriptive max-CAGR L |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| SPY_ABS_MOM_SSO | weekly | 9.2723%–12.6559% | 3.3836% | 54.8982%–61.6461% | 6.7479% | 0.150413–0.228908 | 7.8204%–10.9516% | 7.5942%–10.4133% | 1.881241–2.772355 | 126 | 252 |
| SPY_ABS_MOM_SSO | monthly | 10.9663%–15.9286% | 4.9623% | 59.3411%–64.5284% | 5.1873% | 0.169946–0.268425 | 9.5196%–14.3024% | 9.1668%–13.5107% | 0.594076–1.386177 | 189 | 252 |
| SPY_ABS_MOM_SSO | bimonthly | 14.3590%–16.7979% | 2.4389% | 59.3411%–62.9796% | 3.6385% | 0.228239–0.283073 | 12.1620%–15.0529% | 11.7948%–14.2560% | 0.396051–0.891114 | 189 | 252 |
| SPY_ABS_MOM_SSO | quarterly | 9.7795%–12.8266% | 3.0471% | 60.4699%–63.4667% | 2.9969% | 0.154089–0.212116 | 8.0457%–11.5768% | 7.9944%–10.8701% | 0.495063–0.891114 | 126 | 252 |
| QQQ_ABS_MOM_QLD | weekly | 17.6603%–23.0206% | 5.3603% | 51.7154%–53.9978% | 2.2824% | 0.341157–0.445140 | 14.7887%–19.8138% | 14.4931%–19.1573% | 1.584203–3.069393 | 126 | 189 |
| QQQ_ABS_MOM_QLD | monthly | 16.6779%–24.1688% | 7.4910% | 51.7154%–57.3824% | 5.6670% | 0.290644–0.467343 | 13.9737%–21.7590% | 13.8581%–20.7956% | 0.693089–1.485190 | 126 | 252 |
| QQQ_ABS_MOM_QLD | bimonthly | 13.2595%–24.6885% | 11.4291% | 51.7154%–79.6724% | 27.9570% | 0.166425–0.477392 | 11.4566%–22.1739% | 11.0441%–21.2073% | 0.495063–1.188152 | 126 | 252 |
| QQQ_ABS_MOM_QLD | quarterly | 12.7321%–22.1907% | 9.4586% | 58.2856%–62.7380% | 4.4524% | 0.218443–0.353704 | 10.4488%–20.2923% | 10.4461%–19.4553% | 0.297038–1.089139 | 126 | 252 |

## Complete metric surface

All 48 metric rows are retained. Holding periods are completed position episodes measured in trading sessions; an open terminal position is not fabricated into an episode. After-tax wealth and CAGR are wealth after realized tax paid to date. Terminal liquidation fields are hypothetical diagnostics only and do not add a SELL, change turnover/holding statistics, or mutate the tax ledger.

| Rule | Frequency | L | Tax mode | CAGR | MaxDD | Calmar | Annual turnover | Mean hold | Median hold | Max hold | Trades | Costs | Realized tax | Terminal CAGR |
|---|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| QQQ_ABS_MOM_QLD | bimonthly | 126 | after_tax | 11.4566% | -79.6724% | 0.143797 | 1.188152 | 297.583333 | 252.500000 | 714.000000 | 25 | $1,887.88 | $121,900.62 | 11.0441% |
| QQQ_ABS_MOM_QLD | bimonthly | 126 | pre_tax | 13.2595% | -79.6724% | 0.166425 | 1.188152 | 297.583333 | 252.500000 | 714.000000 | 25 | $2,160.68 | $0.00 | N/A |
| QQQ_ABS_MOM_QLD | bimonthly | 189 | after_tax | 19.3645% | -51.7154% | 0.374443 | 0.792101 | 410.000000 | 461.000000 | 799.000000 | 17 | $2,657.50 | $222,284.27 | 18.4200% |
| QQQ_ABS_MOM_QLD | bimonthly | 189 | pre_tax | 21.8346% | -51.7154% | 0.422206 | 0.792101 | 410.000000 | 461.000000 | 799.000000 | 17 | $3,358.52 | $0.00 | N/A |
| QQQ_ABS_MOM_QLD | bimonthly | 252 | after_tax | 22.1739% | -51.7154% | 0.428768 | 0.495063 | 697.400000 | 629.000000 | 1,591.000000 | 11 | $3,123.47 | $370,872.69 | 21.2073% |
| QQQ_ABS_MOM_QLD | bimonthly | 252 | pre_tax | 24.6885% | -51.7154% | 0.477392 | 0.495063 | 697.400000 | 629.000000 | 1,591.000000 | 11 | $4,048.71 | $0.00 | N/A |
| QQQ_ABS_MOM_QLD | monthly | 126 | after_tax | 13.9737% | -57.4647% | 0.243170 | 1.485190 | 255.800000 | 209.000000 | 695.000000 | 31 | $5,725.70 | $297,230.79 | 13.8581% |
| QQQ_ABS_MOM_QLD | monthly | 126 | pre_tax | 16.6779% | -57.3824% | 0.290644 | 1.485190 | 255.800000 | 209.000000 | 695.000000 | 31 | $7,881.72 | $0.00 | N/A |
| QQQ_ABS_MOM_QLD | monthly | 189 | after_tax | 17.1607% | -54.3020% | 0.316023 | 1.287165 | 295.615385 | 230.000000 | 715.000000 | 27 | $4,432.01 | $290,495.05 | 16.5463% |
| QQQ_ABS_MOM_QLD | monthly | 189 | pre_tax | 20.0205% | -51.7154% | 0.387128 | 1.287165 | 295.615385 | 230.000000 | 715.000000 | 27 | $5,882.54 | $0.00 | N/A |
| QQQ_ABS_MOM_QLD | monthly | 252 | after_tax | 21.7590% | -51.8412% | 0.419725 | 0.693089 | 510.000000 | 375.000000 | 1,613.000000 | 15 | $3,353.89 | $344,556.36 | 20.7956% |
| QQQ_ABS_MOM_QLD | monthly | 252 | pre_tax | 24.1688% | -51.7154% | 0.467343 | 0.693089 | 510.000000 | 375.000000 | 1,613.000000 | 15 | $4,219.87 | $0.00 | N/A |
| QQQ_ABS_MOM_QLD | quarterly | 126 | after_tax | 10.4488% | -61.6088% | 0.169600 | 1.089139 | 343.363636 | 253.000000 | 757.000000 | 23 | $3,416.57 | $174,158.55 | 10.4461% |
| QQQ_ABS_MOM_QLD | quarterly | 126 | pre_tax | 12.7321% | -58.2856% | 0.218443 | 1.089139 | 343.363636 | 253.000000 | 757.000000 | 23 | $4,431.47 | $0.00 | N/A |
| QQQ_ABS_MOM_QLD | quarterly | 189 | after_tax | 14.9409% | -62.0235% | 0.240891 | 0.792101 | 472.750000 | 502.500000 | 820.000000 | 17 | $3,032.79 | $248,950.65 | 14.5155% |
| QQQ_ABS_MOM_QLD | quarterly | 189 | pre_tax | 17.5836% | -58.2856% | 0.301679 | 0.792101 | 472.750000 | 502.500000 | 820.000000 | 17 | $4,016.00 | $0.00 | N/A |
| QQQ_ABS_MOM_QLD | quarterly | 252 | after_tax | 20.2923% | -66.0770% | 0.307100 | 0.297038 | 1,219.333333 | 820.000000 | 2,328.000000 | 7 | $2,722.39 | $351,717.32 | 19.4553% |
| QQQ_ABS_MOM_QLD | quarterly | 252 | pre_tax | 22.1907% | -62.7380% | 0.353704 | 0.297038 | 1,219.333333 | 820.000000 | 2,328.000000 | 7 | $3,325.09 | $0.00 | N/A |
| QQQ_ABS_MOM_QLD | weekly | 126 | after_tax | 14.7887% | -52.6734% | 0.280763 | 3.069393 | 125.838710 | 24.000000 | 596.000000 | 63 | $10,199.16 | $285,250.29 | 14.4931% |
| QQQ_ABS_MOM_QLD | weekly | 126 | pre_tax | 17.6603% | -51.7659% | 0.341157 | 3.069393 | 125.838710 | 24.000000 | 596.000000 | 63 | $14,204.35 | $0.00 | N/A |
| QQQ_ABS_MOM_QLD | weekly | 189 | after_tax | 19.8138% | -52.3253% | 0.378666 | 2.376304 | 159.500000 | 24.500000 | 667.000000 | 49 | $11,371.90 | $450,495.85 | 19.1573% |
| QQQ_ABS_MOM_QLD | weekly | 189 | pre_tax | 23.0206% | -51.7154% | 0.445140 | 2.376304 | 159.500000 | 24.500000 | 667.000000 | 49 | $15,935.10 | $0.00 | N/A |
| QQQ_ABS_MOM_QLD | weekly | 252 | after_tax | 18.2965% | -54.2631% | 0.337181 | 1.584203 | 249.937500 | 25.500000 | 1,606.000000 | 33 | $6,818.76 | $331,326.95 | 17.6289% |
| QQQ_ABS_MOM_QLD | weekly | 252 | pre_tax | 20.8353% | -53.9978% | 0.385854 | 1.584203 | 249.937500 | 25.500000 | 1,606.000000 | 33 | $8,982.72 | $0.00 | N/A |
| SPY_ABS_MOM_SSO | bimonthly | 126 | after_tax | 12.1620% | -65.0259% | 0.187034 | 0.891114 | 382.444444 | 376.000000 | 838.000000 | 19 | $3,126.36 | $152,217.55 | 11.7948% |
| SPY_ABS_MOM_SSO | bimonthly | 126 | pre_tax | 14.3744% | -62.9796% | 0.228239 | 0.891114 | 382.444444 | 376.000000 | 838.000000 | 19 | $4,026.30 | $0.00 | N/A |
| SPY_ABS_MOM_SSO | bimonthly | 189 | after_tax | 12.8027% | -59.3411% | 0.215747 | 0.792101 | 399.500000 | 360.500000 | 881.000000 | 17 | $1,713.96 | $78,275.97 | 12.0213% |
| SPY_ABS_MOM_SSO | bimonthly | 189 | pre_tax | 14.3590% | -59.3411% | 0.241974 | 0.792101 | 399.500000 | 360.500000 | 881.000000 | 17 | $1,974.84 | $0.00 | N/A |
| SPY_ABS_MOM_SSO | bimonthly | 252 | after_tax | 15.0529% | -61.5067% | 0.244736 | 0.396051 | 882.500000 | 756.500000 | 1,591.000000 | 9 | $1,558.01 | $129,139.87 | 14.2560% |
| SPY_ABS_MOM_SSO | bimonthly | 252 | pre_tax | 16.7979% | -59.3411% | 0.283073 | 0.396051 | 882.500000 | 756.500000 | 1,591.000000 | 9 | $1,874.00 | $0.00 | N/A |
| SPY_ABS_MOM_SSO | monthly | 126 | after_tax | 9.5196% | -64.1322% | 0.148437 | 1.386177 | 268.500000 | 211.000000 | 858.000000 | 29 | $4,405.95 | $118,624.09 | 9.4074% |
| SPY_ABS_MOM_SSO | monthly | 126 | pre_tax | 11.4298% | -62.9796% | 0.181484 | 1.386177 | 268.500000 | 211.000000 | 858.000000 | 29 | $5,621.56 | $0.00 | N/A |
| SPY_ABS_MOM_SSO | monthly | 189 | after_tax | 9.8964% | -66.8704% | 0.147994 | 1.188152 | 271.750000 | 210.000000 | 881.000000 | 25 | $2,029.94 | $40,061.84 | 9.1668% |
| SPY_ABS_MOM_SSO | monthly | 189 | pre_tax | 10.9663% | -64.5284% | 0.169946 | 1.188152 | 271.750000 | 210.000000 | 881.000000 | 25 | $2,314.17 | $0.00 | N/A |
| SPY_ABS_MOM_SSO | monthly | 252 | after_tax | 14.3024% | -60.6534% | 0.235805 | 0.594076 | 574.500000 | 465.500000 | 1,488.000000 | 13 | $2,023.23 | $109,995.96 | 13.5107% |
| SPY_ABS_MOM_SSO | monthly | 252 | pre_tax | 15.9286% | -59.3411% | 0.268425 | 0.594076 | 574.500000 | 465.500000 | 1,488.000000 | 13 | $2,430.13 | $0.00 | N/A |
| SPY_ABS_MOM_SSO | quarterly | 126 | after_tax | 8.0457% | -65.7530% | 0.122363 | 0.891114 | 412.888889 | 385.000000 | 816.000000 | 19 | $2,364.25 | $90,679.18 | 7.9944% |
| SPY_ABS_MOM_SSO | quarterly | 126 | pre_tax | 9.7795% | -63.4667% | 0.154089 | 0.891114 | 412.888889 | 385.000000 | 816.000000 | 19 | $2,931.06 | $0.00 | N/A |
| SPY_ABS_MOM_SSO | quarterly | 189 | after_tax | 9.7724% | -63.1411% | 0.154770 | 0.693089 | 468.285714 | 446.000000 | 880.000000 | 15 | $1,151.00 | $33,638.00 | 9.0064% |
| SPY_ABS_MOM_SSO | quarterly | 189 | pre_tax | 10.7055% | -60.4699% | 0.177038 | 0.693089 | 468.285714 | 446.000000 | 880.000000 | 15 | $1,270.74 | $0.00 | N/A |
| SPY_ABS_MOM_SSO | quarterly | 252 | after_tax | 11.5768% | -63.1411% | 0.183349 | 0.495063 | 680.600000 | 504.000000 | 1,446.000000 | 11 | $1,458.04 | $69,797.66 | 10.8701% |
| SPY_ABS_MOM_SSO | quarterly | 252 | pre_tax | 12.8266% | -60.4699% | 0.212116 | 0.495063 | 680.600000 | 504.000000 | 1,446.000000 | 11 | $1,721.66 | $0.00 | N/A |
| SPY_ABS_MOM_SSO | weekly | 126 | after_tax | 7.8204% | -64.1923% | 0.121828 | 2.772355 | 135.000000 | 24.000000 | 897.000000 | 57 | $5,707.90 | $67,522.94 | 7.5942% |
| SPY_ABS_MOM_SSO | weekly | 126 | pre_tax | 9.2723% | -61.6461% | 0.150413 | 2.772355 | 135.000000 | 24.000000 | 897.000000 | 57 | $6,895.31 | $0.00 | N/A |
| SPY_ABS_MOM_SSO | weekly | 189 | after_tax | 10.4344% | -54.8982% | 0.190069 | 2.475317 | 151.320000 | 15.000000 | 892.000000 | 51 | $5,605.30 | $79,264.58 | 9.9135% |
| SPY_ABS_MOM_SSO | weekly | 189 | pre_tax | 12.1113% | -54.8982% | 0.220614 | 2.475317 | 151.320000 | 15.000000 | 892.000000 | 51 | $6,842.90 | $0.00 | N/A |
| SPY_ABS_MOM_SSO | weekly | 252 | after_tax | 10.9516% | -55.2882% | 0.198082 | 1.881241 | 203.684211 | 20.000000 | 815.000000 | 39 | $4,263.66 | $87,081.27 | 10.4133% |
| SPY_ABS_MOM_SSO | weekly | 252 | pre_tax | 12.6559% | -55.2882% | 0.228908 | 1.881241 | 203.684211 | 20.000000 | 815.000000 | 39 | $5,113.69 | $0.00 | N/A |

## Turnover audit

Annual turnover uses `sum(abs(trade_notional) / contemporaneous_pretrade_equity) / calendar_years`, with initial deployment and hypothetical terminal liquidation excluded. The execution cost rate is 0.00050000 (0 commission bps + 5 slippage bps). The same audited Phase 2/3 helpers are used for every Phase 4 row.

| Rule | Frequency | L | Included normalized turnover | Calendar years | Annual turnover | Included trade dates | Gross notional | Trades |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| SPY_ABS_MOM_SSO | weekly | 126 | 55.986006997 | 20.194387406 | 2.772354807 | 56 | $13,790,617.85 | 57 |
| SPY_ABS_MOM_SSO | weekly | 189 | 49.987506247 | 20.194387406 | 2.475316792 | 50 | $13,685,799.78 | 51 |
| SPY_ABS_MOM_SSO | weekly | 252 | 37.990504748 | 20.194387406 | 1.881240762 | 38 | $10,227,388.80 | 39 |
| SPY_ABS_MOM_SSO | monthly | 126 | 27.993003498 | 20.194387406 | 1.386177403 | 28 | $11,243,120.48 | 29 |
| SPY_ABS_MOM_SSO | monthly | 189 | 23.994002999 | 20.194387406 | 1.188152060 | 24 | $4,628,345.88 | 25 |
| SPY_ABS_MOM_SSO | monthly | 252 | 11.997001499 | 20.194387406 | 0.594076030 | 12 | $4,860,268.60 | 13 |
| SPY_ABS_MOM_SSO | bimonthly | 126 | 17.995502249 | 20.194387406 | 0.891114045 | 18 | $8,052,602.26 | 19 |
| SPY_ABS_MOM_SSO | bimonthly | 189 | 15.996001999 | 20.194387406 | 0.792101373 | 16 | $3,949,681.17 | 17 |
| SPY_ABS_MOM_SSO | bimonthly | 252 | 7.998001000 | 20.194387406 | 0.396050687 | 8 | $3,748,005.68 | 9 |
| SPY_ABS_MOM_SSO | quarterly | 126 | 17.995502249 | 20.194387406 | 0.891114045 | 18 | $5,862,111.29 | 19 |
| SPY_ABS_MOM_SSO | quarterly | 189 | 13.996501749 | 20.194387406 | 0.693088702 | 14 | $2,541,477.39 | 15 |
| SPY_ABS_MOM_SSO | quarterly | 252 | 9.997501249 | 20.194387406 | 0.495063358 | 10 | $3,443,324.87 | 11 |
| QQQ_ABS_MOM_QLD | weekly | 126 | 61.984507746 | 20.194387406 | 3.069392822 | 62 | $28,408,700.40 | 63 |
| QQQ_ABS_MOM_QLD | weekly | 189 | 47.988005997 | 20.194387406 | 2.376304120 | 48 | $31,870,192.10 | 49 |
| QQQ_ABS_MOM_QLD | weekly | 252 | 31.992003998 | 20.194387406 | 1.584202747 | 32 | $17,965,449.67 | 33 |
| QQQ_ABS_MOM_QLD | monthly | 126 | 29.992503748 | 20.194387406 | 1.485190075 | 30 | $15,763,437.74 | 31 |
| QQQ_ABS_MOM_QLD | monthly | 189 | 25.993503248 | 20.194387406 | 1.287164732 | 26 | $11,765,078.01 | 27 |
| QQQ_ABS_MOM_QLD | monthly | 252 | 13.996501749 | 20.194387406 | 0.693088702 | 14 | $8,439,732.41 | 15 |
| QQQ_ABS_MOM_QLD | bimonthly | 126 | 23.994002999 | 20.194387406 | 1.188152060 | 24 | $4,321,358.01 | 25 |
| QQQ_ABS_MOM_QLD | bimonthly | 189 | 15.996001999 | 20.194387406 | 0.792101373 | 16 | $6,717,038.97 | 17 |
| QQQ_ABS_MOM_QLD | bimonthly | 252 | 9.997501249 | 20.194387406 | 0.495063358 | 10 | $8,097,429.37 | 11 |
| QQQ_ABS_MOM_QLD | quarterly | 126 | 21.994502749 | 20.194387406 | 1.089139388 | 22 | $8,862,930.89 | 23 |
| QQQ_ABS_MOM_QLD | quarterly | 189 | 15.996001999 | 20.194387406 | 0.792101373 | 16 | $8,031,998.86 | 17 |
| QQQ_ABS_MOM_QLD | quarterly | 252 | 5.998500750 | 20.194387406 | 0.297038015 | 6 | $6,650,188.50 | 7 |

## Common-sample benchmarks

SPY, QQQ, SSO, and QLD buy-and-hold endpoints use the same common evaluation sample and audited benchmark turnover convention; they are descriptive benchmarks, not predictive evidence.

| Benchmark | Start | End | CAGR | MaxDD | Calmar | Annual turnover |
|---|---|---|---:|---:|---:|---:|
| SPY | 2006-06-21 | 2026-08-31 | 11.4506% | -55.1894% | 0.207478 | 0.000000 |
| QQQ | 2006-06-21 | 2026-08-31 | 16.5315% | -53.4040% | 0.309556 | 0.000000 |
| SSO | 2006-06-21 | 2026-08-31 | 15.8320% | -84.6673% | 0.186991 | 0.000000 |
| QLD | 2006-06-21 | 2026-08-31 | 25.0201% | -83.1289% | 0.300979 | 0.000000 |

Tax convention: Simplified Japan taxable mode uses average cost, immediate payment, and loss-pool treatment at realized sales. Unrealized appreciation is not taxed merely for increasing in value. Cumulative realized tax paid is retained in `cumulative_realized_tax_paid`; terminal liquidation is non-mutating and diagnostic only.

`absolute_momentum_results.csv` is the complete 48-row tax-mode metric surface. `parameter_results.csv` is the 24-row unique economic grid with `searched_for_selection=False` and `selection_performed=False`; the frozen windows were evaluated for stability, not selected for deployment.

Phase 4 is a full-sample parameter study only. It makes no OOS or Walk-Forward claim. Walk-Forward parameter selection remains deferred to the frozen later phase.
