# Phase 5 Audit Diff

## A. Full pytest result

pytest -q → **156 passed in 16.41s**.

pytest -q tests/test_phase5_relative_momentum.py → **40 passed in 2.97s**.

## B. Dedicated Phase 5 test count

The dedicated suite tests/test_phase5_relative_momentum.py contains **40 collected tests** including parametrized cases, covering the frozen grid, exact formula, decision boundaries, tie audit, t+1-open integration, mappings, rotation execution, turnover, CASH, holding episodes, warm-up/calendar alignment, tax diagnostics, stability, stale-to-regenerated integrity, and artifact/report semantics.

## C. Exact grid/count audit

- `parameter_grid()` == (126, 189, 252); no other lookback was evaluated.
- 2 mappings × 4 frequencies × 3 lookbacks = 24 economic combinations.
- `metrics_pre_tax.csv` = 24; `metrics_after_tax.csv` = 24; `relative_momentum_results.csv` = 48; `parameter_results.csv` = 24 unique economic combinations.
- Every (rule, frequency, momentum_window, tax_mode) occurs exactly once; `searched_for_selection=False` and `selection_performed=False` everywhere.

## D. Exact relative-momentum formula audit

The implementation computes `SPY_adjclose_t / SPY_adjclose_(t-L) - 1` and `QQQ_adjclose_t / QQQ_adjclose_(t-L) - 1` on the identical common signal index. The first L rows are not ready, so L+1 observations are required. `relative_momentum_target_next_open` applies the close decision through the scheduled next-open shift.

## E. Complete decision-table boundary audit

Deterministic tests cover cases A–H: stronger positive SPY/QQQ, one positive versus one non-positive, both non-positive, exact-zero boundaries, and both zero → CASH. Exact zero is never positive risk-on.

| Case | Condition | Expected |
|---|---|---|
| A | SPY > QQQ and SPY > 0 | SPY |
| B | QQQ > SPY and QQQ > 0 | QQQ |
| C | SPY > 0 and QQQ <= 0 | SPY |
| D | QQQ > 0 and SPY <= 0 | QQQ |
| E | SPY <= 0 and QQQ <= 0 | CASH |
| F | SPY = 0 and QQQ < 0 | CASH |
| G | QQQ = 0 and SPY < 0 | CASH |
| H | SPY = QQQ = 0 | CASH |

## F. Positive-tie occurrence audit

The current implementation uses `spy_momentum >= qqq_momentum`, which would assign an exact positive tie to SPY. The frozen specification does not define a tie-break; this remains an implementation convention, not a frozen rule. The complete common SPY/QQQ history was scanned with exact equality. No historically exercised positive tie was found, so no tie behavior was changed and economic impact is zero.

| Lookback | Frequency | Rebalance decisions | Exact positive ties (full history) | Ties used at rebalance | Tie close dates | Tie execution dates |
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

## G. No-lookahead / t+1-open audit

Four deterministic integration cases (126D and 252D × SPY→QQQ and QQQ→SPY) passed. Close-t ranking changes first execute at the next scheduled held-asset open, use the incoming asset open, charge 5 bps slippage, and are unchanged by post-cutoff future-price mutation.

## H. Rebalance-schedule audit

Weekly, monthly, bi-monthly (odd months Jan/Mar/May/Jul/Sep/Nov), and quarterly schedules passed deterministic first-available-session and holiday cases; between scheduled sessions ranking changes do not alter targets.

## I. Underlying-signal / held-asset mapping audit

Signals use only SPY and QQQ adjusted closes. 1X maps SPY→SPY and QQQ→QQQ; 2X maps SPY→SSO and QQQ→QLD. Held ETF prices affect execution only; leveraged ETF prices never enter selection.

## J. Rotation execution/accounting audit

Outgoing SELL then incoming BUY execute at the same next-open; both legs carry 5 bps traded-notional costs, realized gain comes from the outgoing asset, incoming basis is initialized correctly, after-tax cash includes immediate tax before the BUY, and risky gross exposure never exceeds 100%.

## K. CASH audit

Both non-positive signals produce all-zero risky targets and USD CASH. Risky shares are absent and prolonged CASH equity/cash is unchanged (0% CASH return). Asset→CASH and CASH→asset are tested.

## L. Warm-up/common-calendar audit

Pre-evaluation history is signal warm-up only. The SSO calendar is the held-asset execution basis; SPY, QQQ, SSO, and QLD have zero missing sessions over the evaluation index, and no pre-evaluation equity, positions, trades, or taxes are emitted.

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

## M. Old→new 48-row metric diff

The old surface had stale `average_holding_period_days=7376`; the regenerated surface adds completed-episode and terminal diagnostics. Rows are matched by (rule, frequency, momentum_window, tax_mode). Class A is reporting/metric-definition correction; no class B economic strategy change occurred.

| Rule | Frequency | L | Tax | Ending old→new | CAGR old→new | MaxDD old→new | Calmar old→new | Trades old→new | Turnover old→new | Holding old avg→new mean/median/max | Costs old→new | Tax old→new | Class |
|---|---|---:|---|---|---|---|---|---|---|---|---|---|---|
| RELATIVE_MOMENTUM_1X | bimonthly | 126 | after_tax | 502,154.68 → 502,154.68 | 0.08318982 → 0.08318982 | -0.52326954 → -0.52326954 | 0.15898082 → 0.15898082 | 55 → 55 | 6.28209126 → 2.65869723 | 7376.00 → 149.30/125.00/586.00 | 6,343.15 → 6,343.15 | 93,952.53 → 93,952.53 | A |
| RELATIVE_MOMENTUM_1X | bimonthly | 126 | pre_tax | 715,557.55 → 715,557.55 | 0.10235353 → 0.10235353 | -0.52224322 → -0.52224322 | 0.19598824 → 0.19598824 | 55 → 55 | 7.92294635 → 2.67292144 | 7376.00 → 149.30/125.00/586.00 | 7,999.95 → 7,999.95 | 0.00 → 0.00 | A |
| RELATIVE_MOMENTUM_1X | bimonthly | 189 | after_tax | 722,955.22 → 722,955.22 | 0.10291511 → 0.10291511 | -0.28559366 → -0.28559366 | 0.36035503 → 0.36035503 | 57 → 57 | 9.13352821 → 2.75485030 | 7376.00 → 148.50/82.50/463.00 | 9,222.30 → 9,222.30 | 146,473.98 → 146,473.98 | A |
| RELATIVE_MOMENTUM_1X | bimonthly | 189 | pre_tax | 1,104,301.94 → 1,104,301.94 | 0.12629554 → 0.12629554 | -0.28559366 → -0.28559366 | 0.44222108 → 0.44222108 | 57 → 57 | 12.24253836 → 2.77181037 | 7376.00 → 148.50/82.50/463.00 | 12,361.53 → 12,361.53 | 0.00 → 0.00 | A |
| RELATIVE_MOMENTUM_1X | bimonthly | 252 | after_tax | 1,016,312.77 → 1,016,312.77 | 0.12167411 → 0.12167411 | -0.28559366 → -0.28559366 | 0.42603926 → 0.42603926 | 39 → 39 | 5.47817942 → 1.86391365 | 7376.00 → 214.42/128.00/755.00 | 5,531.42 → 5,531.42 | 159,043.40 → 159,043.40 | A |
| RELATIVE_MOMENTUM_1X | bimonthly | 252 | pre_tax | 1,561,050.98 → 1,561,050.98 | 0.14576743 → 0.14576743 | -0.28559366 → -0.28559366 | 0.51040150 → 0.51040150 | 39 → 39 | 7.18069427 → 1.88089430 | 7376.00 → 214.42/128.00/755.00 | 7,250.49 → 7,250.49 | 0.00 → 0.00 | A |
| RELATIVE_MOMENTUM_1X | monthly | 126 | after_tax | 540,809.90 → 540,809.90 | 0.08717492 → 0.08717492 | -0.32028921 → -0.32028921 | 0.27217563 → 0.27217563 | 91 → 91 | 11.17304900 → 4.43718840 | 7376.00 → 91.42/42.00/316.00 | 11,281.64 → 11,281.64 | 107,795.84 → 107,795.84 | A |
| RELATIVE_MOMENTUM_1X | monthly | 126 | pre_tax | 794,936.01 → 794,936.01 | 0.10811105 → 0.10811105 | -0.32028921 → -0.32028921 | 0.33754198 → 0.33754198 | 91 → 91 | 14.50946949 → 4.45480307 | 7376.00 → 91.42/42.00/316.00 | 14,650.49 → 14,650.49 | 0.00 → 0.00 | A |
| RELATIVE_MOMENTUM_1X | monthly | 189 | after_tax | 625,875.44 → 625,875.44 | 0.09506791 → 0.09506791 | -0.29879141 → -0.29879141 | 0.31817485 → 0.31817485 | 69 → 69 | 9.69042468 → 3.34846860 | 7376.00 → 125.35/43.50/483.00 | 9,784.61 → 9,784.61 | 130,482.11 → 130,482.11 | A |
| RELATIVE_MOMENTUM_1X | monthly | 189 | pre_tax | 942,120.46 → 942,120.46 | 0.11747160 → 0.11747160 | -0.28559366 → -0.28559366 | 0.41132425 → 0.41132425 | 69 → 69 | 12.72679765 → 3.36583691 | 7376.00 → 125.35/43.50/483.00 | 12,850.49 → 12,850.49 | 0.00 → 0.00 | A |
| RELATIVE_MOMENTUM_1X | monthly | 252 | after_tax | 1,097,749.69 → 1,097,749.69 | 0.12596368 → 0.12596368 | -0.28559366 → -0.28559366 | 0.44105909 → 0.44105909 | 47 → 47 | 8.62375398 → 2.25939492 | 7376.00 → 179.87/64.00/777.00 | 8,707.57 → 8,707.57 | 177,274.13 → 177,274.13 | A |
| RELATIVE_MOMENTUM_1X | monthly | 252 | pre_tax | 1,716,123.55 → 1,716,123.55 | 0.15115353 → 0.15115353 | -0.28559366 → -0.28559366 | 0.52926081 → 0.52926081 | 47 → 47 | 11.98136621 → 2.27684600 | 7376.00 → 179.87/64.00/777.00 | 12,097.82 → 12,097.82 | 0.00 → 0.00 | A |
| RELATIVE_MOMENTUM_1X | quarterly | 126 | after_tax | 517,193.05 → 517,193.05 | 0.08477373 → 0.08477373 | -0.34660909 → -0.34660909 | 0.24458023 → 0.24458023 | 45 → 45 | 5.72194798 → 2.16581017 | 7376.00 → 186.05/127.50/565.00 | 5,777.56 → 5,777.56 | 108,713.42 → 108,713.42 | A |
| RELATIVE_MOMENTUM_1X | quarterly | 126 | pre_tax | 752,597.66 → 752,597.66 | 0.10511192 → 0.10511192 | -0.30324182 → -0.30324182 | 0.34662737 → 0.34662737 | 45 → 45 | 7.32897373 → 2.17793232 | 7376.00 → 186.05/127.50/565.00 | 7,400.21 → 7,400.21 | 0.00 → 0.00 | A |
| RELATIVE_MOMENTUM_1X | quarterly | 189 | after_tax | 578,572.36 → 578,572.36 | 0.09081467 → 0.09081467 | -0.29413011 → -0.29413011 | 0.30875678 → 0.30875678 | 47 → 47 | 6.76595208 → 2.26147991 | 7376.00 → 183.39/188.00/504.00 | 6,831.71 → 6,831.71 | 124,640.87 → 124,640.87 | A |
| RELATIVE_MOMENTUM_1X | quarterly | 189 | pre_tax | 860,281.76 → 860,281.76 | 0.11245436 → 0.11245436 | -0.28559366 → -0.28559366 | 0.39375649 → 0.39375649 | 47 → 47 | 8.90026746 → 2.27684600 | 7376.00 → 183.39/188.00/504.00 | 8,986.77 → 8,986.77 | 0.00 → 0.00 | A |
| RELATIVE_MOMENTUM_1X | quarterly | 252 | after_tax | 792,565.17 → 792,565.17 | 0.10794717 → 0.10794717 | -0.30638907 → -0.30638907 | 0.35232056 → 0.35232056 | 33 → 33 | 4.82211545 → 1.56612403 | 7376.00 → 259.88/190.00/878.00 | 4,868.98 → 4,868.98 | 128,811.34 → 128,811.34 | A |
| RELATIVE_MOMENTUM_1X | quarterly | 252 | pre_tax | 1,177,937.00 → 1,177,937.00 | 0.12990149 → 0.12990149 | -0.28559366 → -0.28559366 | 0.45484725 → 0.45484725 | 33 → 33 | 6.25415176 → 1.58388104 | 7376.00 → 259.88/190.00/878.00 | 6,314.94 → 6,314.94 | 0.00 → 0.00 | A |
| RELATIVE_MOMENTUM_1X | weekly | 126 | after_tax | 553,227.47 → 553,227.47 | 0.08839775 → 0.08839775 | -0.28931590 → -0.28931590 | 0.30554057 → 0.30554057 | 169 → 169 | 21.35399316 → 8.29832039 | 7376.00 → 49.14/14.50/334.00 | 21,561.54 → 21,561.54 | 103,050.81 → 103,050.81 | A |
| RELATIVE_MOMENTUM_1X | weekly | 126 | pre_tax | 806,521.61 → 806,521.61 | 0.10890529 → 0.10890529 | -0.28607468 → -0.28607468 | 0.38068831 → 0.38068831 | 169 → 169 | 27.94095403 → 8.31575283 | 7376.00 → 49.14/14.50/334.00 | 28,212.52 → 28,212.52 | 0.00 → 0.00 | A |
| RELATIVE_MOMENTUM_1X | weekly | 189 | after_tax | 634,248.67 → 634,248.67 | 0.09578880 → 0.09578880 | -0.29163410 → -0.29163410 | 0.32845542 → 0.32845542 | 163 → 163 | 26.66985437 → 8.00352553 | 7376.00 → 53.04/10.00/489.00 | 26,929.07 → 26,929.07 | 137,553.64 → 137,553.64 | A |
| RELATIVE_MOMENTUM_1X | weekly | 189 | pre_tax | 966,643.39 → 966,643.39 | 0.11889444 → 0.11889444 | -0.28559366 → -0.28559366 | 0.41630629 → 0.41630629 | 163 → 163 | 36.06681761 → 8.01856633 | 7376.00 → 53.04/10.00/489.00 | 36,417.36 → 36,417.36 | 0.00 → 0.00 | A |
| RELATIVE_MOMENTUM_1X | weekly | 252 | after_tax | 710,391.59 → 710,391.59 | 0.10195808 → 0.10195808 | -0.31598290 → -0.31598290 | 0.32266960 → 0.32266960 | 133 → 133 | 23.04342583 → 6.51498843 | 7376.00 → 64.89/15.00/573.00 | 23,267.39 → 23,267.39 | 128,929.15 → 128,929.15 | A |
| RELATIVE_MOMENTUM_1X | weekly | 252 | pre_tax | 1,076,550.76 → 1,076,550.76 | 0.12487695 → 0.12487695 | -0.29627830 → -0.29627830 | 0.42148530 → 0.42148530 | 133 → 133 | 31.98491184 → 6.53354949 | 7376.00 → 64.89/15.00/573.00 | 32,295.79 → 32,295.79 | 0.00 → 0.00 | A |
| RELATIVE_MOMENTUM_2X | bimonthly | 126 | after_tax | 972,494.85 → 972,494.85 | 0.11922887 → 0.11922887 | -0.79672374 → -0.79672374 | 0.14964895 → 0.14964895 | 55 → 55 | 9.18514703 → 2.65432078 | 7376.00 → 149.30/125.00/586.00 | 9,274.42 → 9,274.42 | 198,164.75 → 198,164.75 | A |
| RELATIVE_MOMENTUM_2X | bimonthly | 126 | pre_tax | 1,551,520.89 → 1,551,520.89 | 0.14542005 → 0.14542005 | -0.79672374 → -0.79672374 | 0.18252255 → 0.18252255 | 55 → 55 | 12.99719700 → 2.67292144 | 7376.00 → 149.30/125.00/586.00 | 13,123.52 → 13,123.52 | 0.00 → 0.00 | A |
| RELATIVE_MOMENTUM_2X | bimonthly | 189 | after_tax | 2,143,732.48 → 2,143,732.48 | 0.16390585 → 0.16390585 | -0.52186261 → -0.52186261 | 0.31407854 → 0.31407854 | 57 → 57 | 19.70167311 → 2.74749754 | 7376.00 → 148.50/82.50/463.00 | 19,893.16 → 19,893.16 | 467,531.41 → 467,531.41 | A |
| RELATIVE_MOMENTUM_2X | bimonthly | 189 | pre_tax | 3,939,714.65 → 3,939,714.65 | 0.19951410 → 0.19951410 | -0.51715422 → -0.51715422 | 0.38579226 → 0.38579226 | 57 → 57 | 31.34189959 → 2.77181037 | 7376.00 → 148.50/82.50/463.00 | 31,646.52 → 31,646.52 | 0.00 → 0.00 | A |
| RELATIVE_MOMENTUM_2X | bimonthly | 252 | after_tax | 3,895,976.22 → 3,895,976.22 | 0.19885116 → 0.19885116 | -0.51715422 → -0.51715422 | 0.38451036 → 0.38451036 | 39 → 39 | 11.80215669 → 1.85660316 | 7376.00 → 214.42/128.00/755.00 | 11,916.87 → 11,916.87 | 559,832.37 → 559,832.37 | A |
| RELATIVE_MOMENTUM_2X | bimonthly | 252 | pre_tax | 7,236,671.57 → 7,236,671.57 | 0.23618072 → 0.23618072 | -0.51715422 → -0.51715422 | 0.45669301 → 0.45669301 | 39 → 39 | 18.69341762 → 1.88089430 | 7376.00 → 214.42/128.00/755.00 | 18,875.11 → 18,875.11 | 0.00 → 0.00 | A |
| RELATIVE_MOMENTUM_2X | monthly | 126 | after_tax | 1,244,814.83 → 1,244,814.83 | 0.13299547 → 0.13299547 | -0.57382442 → -0.57382442 | 0.23177032 → 0.23177032 | 91 → 91 | 20.28342532 → 4.43014404 | 7376.00 → 91.42/42.00/316.00 | 20,480.57 → 20,480.57 | 286,150.69 → 286,150.69 | A |
| RELATIVE_MOMENTUM_2X | monthly | 126 | pre_tax | 2,154,667.31 → 2,154,667.31 | 0.16419912 → 0.16419912 | -0.57382442 → -0.57382442 | 0.28614872 → 0.28614872 | 91 → 91 | 31.21583122 → 4.45480307 | 7376.00 → 91.42/42.00/316.00 | 31,519.23 → 31,519.23 | 0.00 → 0.00 | A |
| RELATIVE_MOMENTUM_2X | monthly | 189 | after_tax | 1,648,589.43 → 1,648,589.43 | 0.14886723 → 0.14886723 | -0.56069260 → -0.56069260 | 0.26550596 → 0.26550596 | 69 → 69 | 18.74997544 → 3.34158344 | 7376.00 → 125.35/43.50/483.00 | 18,932.21 → 18,932.21 | 377,959.73 → 377,959.73 | A |
| RELATIVE_MOMENTUM_2X | monthly | 189 | pre_tax | 2,964,245.89 → 2,964,245.89 | 0.18273457 → 0.18273457 | -0.52712880 → -0.52712880 | 0.34666020 → 0.34666020 | 69 → 69 | 29.03330435 → 3.36583691 | 7376.00 → 125.35/43.50/483.00 | 29,315.49 → 29,315.49 | 0.00 → 0.00 | A |
| RELATIVE_MOMENTUM_2X | monthly | 252 | after_tax | 4,691,635.84 → 4,691,635.84 | 0.20993439 → 0.20993439 | -0.51715422 → -0.51715422 | 0.40594157 → 0.40594157 | 47 → 47 | 23.27980579 → 2.25122919 | 7376.00 → 179.87/64.00/777.00 | 23,506.07 → 23,506.07 | 718,256.18 → 718,256.18 | A |
| RELATIVE_MOMENTUM_2X | monthly | 252 | pre_tax | 9,092,845.76 → 9,092,845.76 | 0.25023683 → 0.25023683 | -0.51715422 → -0.51715422 | 0.48387274 → 0.48387274 | 47 → 47 | 40.33356252 → 2.27684600 | 7376.00 → 179.87/64.00/777.00 | 40,725.58 → 40,725.58 | 0.00 → 0.00 | A |
| RELATIVE_MOMENTUM_2X | quarterly | 126 | after_tax | 1,107,748.64 → 1,107,748.64 | 0.12646935 → 0.12646935 | -0.61198314 → -0.61198314 | 0.20665496 → 0.20665496 | 45 → 45 | 10.13301960 → 2.16084744 | 7376.00 → 186.05/127.50/565.00 | 10,231.51 → 10,231.51 | 280,445.86 → 280,445.86 | A |
| RELATIVE_MOMENTUM_2X | quarterly | 126 | pre_tax | 1,862,016.55 → 1,862,016.55 | 0.15581399 → 0.15581399 | -0.57258815 → -0.57258815 | 0.27212227 → 0.27212227 | 45 → 45 | 14.95931887 → 2.17793232 | 7376.00 → 186.05/127.50/565.00 | 15,104.71 → 15,104.71 | 0.00 → 0.00 | A |
| RELATIVE_MOMENTUM_2X | quarterly | 189 | after_tax | 1,342,274.85 → 1,342,274.85 | 0.13723248 → 0.13723248 | -0.52152984 → -0.52152984 | 0.26313446 → 0.26313446 | 47 → 47 | 12.71092184 → 2.25597233 | 7376.00 → 183.39/188.00/504.00 | 12,834.46 → 12,834.46 | 334,672.27 → 334,672.27 | A |
| RELATIVE_MOMENTUM_2X | quarterly | 189 | pre_tax | 2,311,672.36 → 2,311,672.36 | 0.16826097 → 0.16826097 | -0.51715422 → -0.51715422 | 0.32535937 → 0.32535937 | 47 → 47 | 19.31142735 → 2.27684600 | 7376.00 → 183.39/188.00/504.00 | 19,499.12 → 19,499.12 | 0.00 → 0.00 | A |
| RELATIVE_MOMENTUM_2X | quarterly | 252 | after_tax | 2,370,653.64 → 2,370,653.64 | 0.16971940 → 0.16971940 | -0.56989201 → -0.56989201 | 0.29780976 → 0.29780976 | 33 → 33 | 9.56107008 → 1.55918597 | 7376.00 → 259.88/190.00/878.00 | 9,654.00 → 9,654.00 | 365,415.03 → 365,415.03 | A |
| RELATIVE_MOMENTUM_2X | quarterly | 252 | pre_tax | 4,118,844.91 → 4,118,844.91 | 0.20215812 → 0.20215812 | -0.53516172 → -0.53516172 | 0.37775146 → 0.37775146 | 33 → 33 | 14.40152212 → 1.58388104 | 7376.00 → 259.88/190.00/878.00 | 14,541.50 → 14,541.50 | 0.00 → 0.00 | A |
| RELATIVE_MOMENTUM_2X | weekly | 126 | after_tax | 1,434,031.71 → 1,434,031.71 | 0.14096231 → 0.14096231 | -0.50389137 → -0.50389137 | 0.27974741 → 0.27974741 | 169 → 169 | 42.33374333 → 8.28869692 | 7376.00 → 49.14/14.50/334.00 | 42,745.20 → 42,745.20 | 321,619.61 → 321,619.61 | A |
| RELATIVE_MOMENTUM_2X | weekly | 126 | pre_tax | 2,545,332.65 → 2,545,332.65 | 0.17384473 → 0.17384473 | -0.50389137 → -0.50389137 | 0.34500439 → 0.34500439 | 169 → 169 | 67.17885603 → 8.31575283 | 7376.00 → 49.14/14.50/334.00 | 67,831.79 → 67,831.79 | 0.00 → 0.00 | A |
| RELATIVE_MOMENTUM_2X | weekly | 189 | after_tax | 1,841,503.44 → 1,841,503.44 | 0.15518013 → 0.15518013 | -0.52083657 → -0.52083657 | 0.29794400 → 0.29794400 | 163 → 163 | 59.52137426 → 7.99727175 | 7376.00 → 53.04/10.00/489.00 | 60,099.88 → 60,099.88 | 453,533.11 → 453,533.11 | A |
| RELATIVE_MOMENTUM_2X | weekly | 189 | pre_tax | 3,423,199.39 → 3,423,199.39 | 0.19119566 → 0.19119566 | -0.51715422 → -0.51715422 | 0.36970724 → 0.36970724 | 163 → 163 | 96.46172508 → 8.01856633 | 7376.00 → 53.04/10.00/489.00 | 97,399.27 → 97,399.27 | 0.00 → 0.00 | A |
| RELATIVE_MOMENTUM_2X | weekly | 252 | after_tax | 2,039,904.22 → 2,039,904.22 | 0.16104803 → 0.16104803 | -0.58882920 → -0.58882920 | 0.27350551 → 0.27350551 | 133 → 133 | 50.78736423 → 6.50570016 | 7376.00 → 64.89/15.00/573.00 | 51,280.99 → 51,280.99 | 414,548.57 → 414,548.57 | A |
| RELATIVE_MOMENTUM_2X | weekly | 252 | pre_tax | 3,815,960.72 → 3,815,960.72 | 0.19761984 → 0.19761984 | -0.54800917 → -0.54800917 | 0.36061412 → 0.36061412 | 133 → 133 | 86.03162052 → 6.53354949 | 7376.00 → 64.89/15.00/573.00 | 86,867.79 → 86,867.79 | 0.00 → 0.00 | A |

Summary: ending value, total return, CAGR, MaxDD, Sharpe, Sortino, Calmar, Ulcer index, trade count, transaction costs, realized tax, and complete equity/trade/tax paths are unchanged. Only turnover reporting, completed holding episodes, and terminal diagnostics changed.

## N. Turnover audit

Annual turnover is `sum(abs(trade_notional) / contemporaneous_pretrade_equity) / calendar_years`. Initial deployment BUY and hypothetical terminal liquidation are excluded; both SELL and BUY rotation legs are included.

| Mapping | Frequency | L | Included normalized turnover | Calendar years | Annual turnover | Included dates | Gross notional | Trades |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| RELATIVE_MOMENTUM_1X | weekly | 126 | 167.931534233 | 20.194387406 | 8.315752831 | 115 | $56,425,045.02 | 169 |
| RELATIVE_MOMENTUM_2X | weekly | 126 | 167.931534233 | 20.194387406 | 8.315752831 | 115 | $135,663,584.42 | 169 |

Dedicated synthetic turnover tests cover initial deployment exclusion, CASH→asset, asset→CASH, SPY→QQQ, QQQ→SPY, SSO→QLD, and QLD→SSO.

## O. Completed holding-episode audit

Holding periods are completed continuous risky-asset episodes measured in trading sessions. A rotation ends the outgoing episode and starts the incoming episode; an open terminal position is excluded. The stale value 7376 is absent from regenerated primary fields.

## P. Tax / terminal-liquidation audit

After-tax wealth is wealth after realized tax paid to date. The after-tax table contains cumulative realized tax and terminal liquidation wealth/CAGR/tax/cost/unrealized gain. Terminal liquidation is hypothetical and non-mutating: no SELL, ledger, tax-ledger, turnover, or holding-period change.

## Q. Full economic-path hash comparison

| File | Old rows | New rows | Old SHA-256 | New SHA-256 | Byte-identical |
|---|---:|---:|---|---|---|
| equity_curve.csv | 243840 | 243840 | a9b32e1063e40512ab9cb640266cd59c678f9e65badd98c1d64ebfc8ef4a51e5 | a9b32e1063e40512ab9cb640266cd59c678f9e65badd98c1d64ebfc8ef4a51e5 | True |
| positions.csv | 487680 | 487680 | 01a83e2f6807ef48b2d4b2d2ce2b936abd477d4d732043384a6d00bd3ba39a41 | 01a83e2f6807ef48b2d4b2d2ce2b936abd477d4d732043384a6d00bd3ba39a41 | True |
| trades.csv | 3792 | 3792 | fc16a62d297afd80457d93d6c17ee84a2d939b96e393a33c9b218371267811c6 | fc16a62d297afd80457d93d6c17ee84a2d939b96e393a33c9b218371267811c6 | True |
| tax_ledger.csv | 936 | 936 | a8479f5c2fee89b7fabcac7dfd456f13e99c7be037ab7f5bcd8bb67b1e7d397f | a8479f5c2fee89b7fabcac7dfd456f13e99c7be037ab7f5bcd8bb67b1e7d397f | True |

All four economic-path files are byte-identical, proving unchanged execution, positions, trades, and tax ledgers.

## R. Raw SHA verification

Immutable raw snapshots match data/raw/manifest.yaml; no raw data file was modified.

| Asset | Manifest SHA-256 | Current SHA-256 | Match |
|---|---|---|---|
| SPY | 6a73a96bf408a041bc7e77df51117ae5a0965769c407c6699f52b0fd489b28d8 | 6a73a96bf408a041bc7e77df51117ae5a0965769c407c6699f52b0fd489b28d8 | True |
| QQQ | fe5aa0db7c8a717e00cd7726d04ba1d2faff627e9f6e48c0952a5e2f235052c6 | fe5aa0db7c8a717e00cd7726d04ba1d2faff627e9f6e48c0952a5e2f235052c6 | True |
| SSO | b0636de318b2d72d4cf774d6af2e11b2bc47904150891a06a39d29355e6e2b5d | b0636de318b2d72d4cf774d6af2e11b2bc47904150891a06a39d29355e6e2b5d | True |
| QLD | 2499976b07ea6711b33befad63bd8e177ab85f0c820662330f9a4ad257532a9f | 2499976b07ea6711b33befad63bd8e177ab85f0c820662330f9a4ad257532a9f | True |
| TQQQ | 4b0b5c7500d7510bb2e61607e86130d635a3d05339cf7cde10ab7174551ccf76 | 4b0b5c7500d7510bb2e61607e86130d635a3d05339cf7cde10ab7174551ccf76 | True |

## S. Unresolved issues

None. Historical exact positive ties are zero for every lookback/frequency cell, so UNRESOLVED_FROZEN_SPEC_TIE_BREAK is not triggered. signals.py, Phase 0–4 code, and Phase 6–7 code were not modified. Phase 5 remains descriptive full-sample evidence only; no parameter is selected and no OOS/Walk-Forward claim is made.

PHASE 5 AUDIT PASS
