# Phase 2 — MA200 Simple Trend

## Frozen specification and common sample

The common evaluation sample is **2006-06-21 through 2026-08-31** (inclusive), the intersection of each signal/held ETF calendar. The three frozen rules are QQQ MA200 → QQQ/CASH, QQQ MA200 → QLD/CASH, and SPY MA200 → SSO/CASH. The MA window is exactly 200 trading sessions and was not selected through a parameter search; no neighboring windows were evaluated. Phase 2 makes no OOS or Walk-Forward claim.

Signal uses the adjusted close of the unleveraged underlying at close *t*. A completed decision can first affect the next available session's open (*t+1*); the held ETF's open is the execution price. No same-day-close execution is used.

Rebalance dates are the first available trading session of each period: weekly (first session of the Sunday-ending week), monthly (first session of the calendar month), bi-monthly (first session of odd months Jan/Mar/May/Jul/Sep/Nov), and quarterly (first session of Jan/Apr/Jul/Oct). A signal change on a non-rebalance day is held until the next scheduled decision/execution sequence.

## MA200 warm-up audit

Pre-start observations are used only to form the legitimate 200-session moving average. They create no pre-evaluation equity or trades. The first evaluation-day target is read from the already-available prior close and is executed, if scheduled, at the evaluation-day open.

| Signal asset | Full signal rows | Pre-start warm-up rows | 200-observation lookback at evaluation start | Lookback start | First valid MA200 date | First evaluation date |
|---|---:|---:|---:|---|---|---|
| QQQ | 6919 | 1832 | 200 | 2005-09-06 | 1999-12-21 | 2006-06-21 |
| SPY | 8461 | 3374 | 200 | 2005-09-06 | 1993-11-11 | 2006-06-21 |

## Signal/held-calendar alignment

The full signal is computed on the signal asset, then reindexed to the held ETF calendar. No unexplained forward-fill is used for missing dates; every final reindex below has zero missing targets.

| Rule | Signal calendar rows | Held-asset calendar rows | Common evaluation rows | Missing targets after reindex |
|---|---:|---:|---:|---:|
| QQQ_MA200_QQQ (QQQ → QQQ) | 5080 | 5080 | 5080 | 0 |
| QQQ_MA200_QLD (QQQ → QLD) | 5080 | 5080 | 5080 | 0 |
| SPY_MA200_SSO (SPY → SSO) | 5080 | 5080 | 5080 | 0 |

## First execution dates

The first execution date below is the first actual BUY or SELL in the pre-tax strategy ledger; there is no trade or equity before the common evaluation start.

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

## Strategy results

Primary after-tax wealth and CAGR mean wealth after realized tax paid to date. `terminal_liquidation_*` values are non-mutating diagnostics that hypothetically sell the remaining terminal position, deduct the same transaction-cost rate, apply the frozen tax/loss-pool rules, and do not add a trade, change turnover, or change holding-period statistics.

| Rule | Frequency | Tax mode | Ending value | CAGR | MaxDD | Calmar | Annual turnover | Mean hold (sessions) | Median hold (sessions) | Max hold (sessions) | Trades | Costs | Realized tax | Terminal wealth | Terminal CAGR |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| QQQ_MA200_QQQ | weekly | pre_tax | $1,146,534.21 | 12.8391% | -28.7670% | 0.446312 | 2.673342 | 146.814815 | 29.000000 | 662.000000 | 55 | $6,813.53 | $0.00 | N/A | N/A |
| QQQ_MA200_QQQ | weekly | after_tax | $767,667.88 | 10.6197% | -30.5029% | 0.348155 | 2.673342 | 146.814815 | 29.000000 | 662.000000 | 55 | $5,593.64 | $140,823.92 | 743,940.832648 | 10.4479% |
| QQQ_MA200_QQQ | monthly | pre_tax | $1,194,574.82 | 13.0687% | -28.5594% | 0.457596 | 1.386177 | 286.214286 | 253.000000 | 901.000000 | 29 | $4,861.83 | $0.00 | N/A | N/A |
| QQQ_MA200_QQQ | monthly | after_tax | $787,260.28 | 10.7579% | -32.3668% | 0.332374 | 1.386177 | 286.214286 | 253.000000 | 901.000000 | 29 | $3,813.83 | $161,770.11 | 776,236.204533 | 10.6806% |
| QQQ_MA200_QQQ | bimonthly | pre_tax | $1,474,567.90 | 14.2538% | -28.5594% | 0.499095 | 0.990127 | 373.900000 | 313.500000 | 881.000000 | 21 | $3,227.60 | $0.00 | N/A | N/A |
| QQQ_MA200_QQQ | bimonthly | after_tax | $983,855.05 | 11.9873% | -30.2245% | 0.396608 | 0.990127 | 373.900000 | 313.500000 | 881.000000 | 21 | $2,606.39 | $166,053.79 | 936,227.868325 | 11.7124% |
| QQQ_MA200_QQQ | quarterly | pre_tax | $730,757.58 | 10.3502% | -28.5594% | 0.362408 | 0.990127 | 390.600000 | 314.000000 | 880.000000 | 21 | $3,306.61 | $0.00 | N/A | N/A |
| QQQ_MA200_QQQ | quarterly | after_tax | $511,496.15 | 8.4179% | -28.5594% | 0.294751 | 0.990127 | 390.600000 | 314.000000 | 880.000000 | 21 | $2,652.51 | $107,235.12 | 511,240.399636 | 8.4152% |
| QQQ_MA200_QLD | weekly | pre_tax | $4,946,095.42 | 21.3103% | -49.9992% | 0.426213 | 2.673342 | 146.814815 | 29.000000 | 662.000000 | 55 | $14,985.59 | $0.00 | N/A | N/A |
| QQQ_MA200_QLD | weekly | after_tax | $2,753,153.37 | 17.8416% | -52.0843% | 0.342552 | 2.673342 | 146.814815 | 29.000000 | 662.000000 | 55 | $10,363.97 | $502,469.47 | 2,613,461.137599 | 17.5381% |
| QQQ_MA200_QLD | monthly | pre_tax | $4,958,359.99 | 21.3252% | -51.7154% | 0.412356 | 1.386177 | 286.214286 | 253.000000 | 901.000000 | 29 | $13,177.21 | $0.00 | N/A | N/A |
| QQQ_MA200_QLD | monthly | after_tax | $2,781,882.08 | 17.9022% | -53.5520% | 0.334295 | 1.386177 | 286.214286 | 253.000000 | 901.000000 | 29 | $8,740.36 | $614,296.02 | 2,725,451.149388 | 17.7826% |
| QQQ_MA200_QLD | bimonthly | pre_tax | $6,987,774.31 | 23.4040% | -51.7154% | 0.452554 | 0.990127 | 373.900000 | 313.500000 | 881.000000 | 21 | $8,498.46 | $0.00 | N/A | N/A |
| QQQ_MA200_QLD | bimonthly | after_tax | $3,990,150.41 | 20.0270% | -51.7154% | 0.387254 | 0.990127 | 373.900000 | 313.500000 | 881.000000 | 21 | $5,844.78 | $632,462.10 | 3,702,254.005244 | 19.5827% |
| QQQ_MA200_QLD | quarterly | pre_tax | $1,829,407.48 | 15.4803% | -51.7154% | 0.299337 | 0.990127 | 390.600000 | 314.000000 | 880.000000 | 21 | $6,677.49 | $0.00 | N/A | N/A |
| QQQ_MA200_QLD | quarterly | after_tax | $1,132,531.48 | 12.7704% | -54.0984% | 0.236059 | 0.990127 | 390.600000 | 314.000000 | 880.000000 | 21 | $4,757.89 | $278,392.80 | 1,131,965.212338 | 12.7676% |
| SPY_MA200_SSO | weekly | pre_tax | $1,109,089.20 | 12.6537% | -41.4097% | 0.305573 | 3.168405 | 122.187500 | 17.000000 | 663.000000 | 65 | $8,576.06 | $0.00 | N/A | N/A |
| SPY_MA200_SSO | weekly | after_tax | $759,082.73 | 10.5582% | -42.9556% | 0.245792 | 3.168405 | 122.187500 | 17.000000 | 663.000000 | 65 | $6,960.31 | $128,843.88 | 727,556.880596 | 10.3262% |
| SPY_MA200_SSO | monthly | pre_tax | $1,505,936.15 | 14.3730% | -46.7416% | 0.307499 | 1.485190 | 263.200000 | 209.000000 | 921.000000 | 31 | $9,939.81 | $0.00 | N/A | N/A |
| SPY_MA200_SSO | monthly | after_tax | $974,585.53 | 11.9348% | -50.2185% | 0.237657 | 1.485190 | 263.200000 | 209.000000 | 921.000000 | 31 | $7,097.50 | $198,391.42 | 954,613.379224 | 11.8201% |
| SPY_MA200_SSO | bimonthly | pre_tax | $2,744,303.97 | 17.8228% | -37.3594% | 0.477063 | 0.990127 | 361.700000 | 292.500000 | 921.000000 | 21 | $7,314.79 | $0.00 | N/A | N/A |
| SPY_MA200_SSO | bimonthly | after_tax | $1,691,809.29 | 15.0340% | -39.7948% | 0.377789 | 0.990127 | 361.700000 | 292.500000 | 921.000000 | 21 | $5,197.15 | $270,620.85 | 1,583,403.397253 | 14.6574% |
| SPY_MA200_SSO | quarterly | pre_tax | $957,364.28 | 11.8360% | -60.4699% | 0.195734 | 0.891114 | 441.222222 | 385.000000 | 942.000000 | 19 | $3,978.54 | $0.00 | N/A | N/A |
| SPY_MA200_SSO | quarterly | after_tax | $662,416.48 | 9.8149% | -62.9437% | 0.155932 | 0.891114 | 441.222222 | 385.000000 | 942.000000 | 19 | $3,091.42 | $135,775.53 | 656,090.382324 | 9.7628% |

## Turnover audit

The execution-cost rate is 0.00050000 (0 commission bps + 5 slippage bps). Annual turnover is the sum of `abs(trade_notional) / contemporaneous pretrade_equity` for included trades, excluding initial portfolio deployment and any hypothetical terminal liquidation, divided by calendar backtest years. Nonzero trade dates are the included rebalance dates; gross notional and trade counts are reported from the actual trade ledger.

| Strategy | Frequency | Included normalized turnover | Calendar years | Annual turnover | Included trade dates/rebalances | Gross traded notional | Number of trades |
|---|---|---:|---:|---:|---:|---:|---:|
| QQQ_MA200_QQQ | weekly | 53.986506747 | 20.194387406 | 2.673342135 | 54 | $13,627,055.54 | 55 |
| QQQ_MA200_QQQ | monthly | 27.993003498 | 20.194387406 | 1.386177403 | 28 | $9,723,665.69 | 29 |
| QQQ_MA200_QLD | weekly | 53.986506747 | 20.194387406 | 2.673342135 | 54 | $29,971,174.70 | 55 |
| SPY_MA200_SSO | monthly | 29.992503748 | 20.194387406 | 1.485190075 | 30 | $19,879,622.53 | 31 |

## Common-sample benchmarks

The buy-and-hold SPY, QQQ, SSO, and QLD endpoints use the same common evaluation sample and frozen 5 bps execution cost for their initial deployment. They are descriptive benchmarks, not predictive evidence.

| Benchmark | Start | End | CAGR | MaxDD | Calmar |
|---|---|---|---:|---:|---:|
| SPY | 2006-06-21 | 2026-08-31 | 11.4506% | -55.1894% | 0.207478 |
| QQQ | 2006-06-21 | 2026-08-31 | 16.5315% | -53.4040% | 0.309556 |
| SSO | 2006-06-21 | 2026-08-31 | 15.8320% | -84.6673% | 0.186991 |
| QLD | 2006-06-21 | 2026-08-31 | 25.0201% | -83.1289% | 0.300979 |

Tax semantics: `tax_paid` and `cumulative_realized_tax_paid` are realized taxes paid immediately under frozen average-cost/loss-pool accounting; unrealized appreciation is not taxed until a sale or the separate terminal diagnostic. CASH earns exactly 0%.

MA=200 remains frozen, no parameter alternatives were searched, and this Phase 2 report makes no out-of-sample or Walk-Forward claim.
