# Phase 4 audit diff

Canonical regenerated run: reports/runs/20260914_phase4_audit_final.
The preceding stale run is reports/runs/20260913_phase4_absolute_momentum_final.
No signals.py, data, or Phase 5-7 code was changed.

## A. Complete pytest result

pytest -q -> **115 passed in 14.10s**.
Dedicated Phase 4 file: tests/test_phase4_absolute_momentum.py -> **19 passed**.

## B. Dedicated Phase 4 test count

19 dedicated tests cover the frozen grid, formula/zero boundary, next-open timing, schedule semantics, signal/held separation, CASH, warm-up/calendar, terminal-tax non-mutation, stability enumeration, old-to-new economic invariance, artifact completeness, and report semantics.

## C. Exact grid/count audit

parameter_grid() == (126, 189, 252); two frozen rules x four frequencies x three lookbacks = **24 economic combinations**. The canonical files contain **24 pre-tax rows**, **24 after-tax rows**, **48 combined metric rows**, and **24 unique parameter_results.csv rows**. Every (rule, frequency, momentum_window, tax_mode) key occurs exactly once. No other momentum window is evaluated.

## D. Exact absolute-momentum formula audit

The tested frozen definition is momentum_t = adjusted_close_t / adjusted_close_(t-L) - 1. The first computable observation is index L (current observation plus the prior Lth observation), so the first L decisions are Risk-Off/invalid-history zeros. Risk-On is exactly momentum > 0; negative and exact-zero momentum are Risk-Off. The Phase 4 call path invokes absolute_momentum_target_next_open directly and does not use leveraged ETF prices for the signal.

## E. Zero-momentum boundary test

Dedicated deterministic tests cover positive, negative, and exact-zero momentum for all three frozen lookbacks. Exact zero returns 0.0, confirming the strict-positive boundary.

## F. No-lookahead / t+1-open integration audit

Dedicated deterministic integration cases for 126D and 252D mutate post-cutoff closes and preserve all targets through the cutoff. A positive Friday close decision first changes the following scheduled Monday target; no Friday-open trade is possible. The actual BUY price is the held asset's Monday open and the cost equals notional x 0.0005 (0 bps commission + 5 bps slippage).

## G. Rebalance-schedule audit

Dedicated tests cover weekly (first trading session of the week), monthly (first trading session of the month), bi-monthly (first trading session of odd frozen months Jan/Mar/May/Jul/Sep/Nov), and quarterly (first trading session of the calendar quarter), including missing calendar first days. Between scheduled sessions, a changed momentum decision leaves the prior target unchanged.

## H. Signal-asset vs held-asset audit

SPY adjusted closes drive only SPY->SSO; QQQ adjusted closes drive only QQQ->QLD. Synthetic tests make the held ETF open materially different and show execution price changes when held prices change while the signal target is unchanged. Leveraged ETF prices are never input to the momentum calculation.

## I. CASH zero-return audit

Risk-Off targets execute no risky shares. The dedicated CASH case has no trades, zero shares, constant USD cash, and constant equity despite changing hypothetical prices; CASH return is exactly 0%.

## J. Warm-up/calendar alignment audit

Pre-evaluation history is used only for legitimate lookback warm-up; the evaluated ledger starts at 2006-06-21 and creates no earlier equity, position, or trade. The runner reports all six signal/window pairs:

| Signal | L | Full rows | Pre-start rows | Lookback observations at start | Lookback start | First valid momentum date | Missing targets |
|---|---:|---:|---:|---:|---|---|---:|
| SPY | 126 | 8461 | 3374 | 127 | 2005-12-19 | 1993-07-30 | 0 |
| QQQ | 126 | 6919 | 1832 | 127 | 2005-12-19 | 1999-09-08 | 0 |
| SPY | 189 | 8461 | 3374 | 190 | 2005-09-20 | 1993-10-28 | 0 |
| QQQ | 189 | 6919 | 1832 | 190 | 2005-09-20 | 1999-12-07 | 0 |
| SPY | 252 | 8461 | 3374 | 253 | 2005-06-21 | 1994-01-27 | 0 |
| QQQ | 252 | 6919 | 1832 | 253 | 2005-06-21 | 2000-03-08 | 0 |

| Rule | Signal rows | Held rows | Common rows | Missing targets |
|---|---:|---:|---:|---:|
| SPY_ABS_MOM_SSO | 5080 | 5080 | 5080 | 0 |
| QQQ_ABS_MOM_QLD | 5080 | 5080 | 5080 | 0 |

## K. Old-to-new 48-row metrics diff

All 48 stale rows were matched by (rule, frequency, momentum_window, tax_mode). Numeric serialization differences are treated equal at absolute tolerance 1e-8. Every economic row is classified **A - reporting/metric-definition correction**: equity-derived economics, trades, costs, and realized tax are unchanged; only turnover and holding-period reporting changed, plus newly surfaced terminal diagnostics. The old 33-column table had average_holding_period_days = 7376 for every row and no completed-episode mean/median/max fields.

| Key | Ending value old -> new | Total return old -> new | CAGR old -> new | MaxDD old -> new | Sharpe old -> new | Sortino old -> new | Calmar old -> new | Ulcer old -> new | Trades old -> new | Costs old -> new | Tax old -> new | Turnover old -> new | Holding avg -> mean/median/max | Class |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| QQQ_ABS_MOM_QLD / bimonthly / 126 / after_tax | 893869.818 -> 893869.818 | 7.93869818 -> 7.93869818 | 0.114566214 -> 0.114566214 | -0.796723743 -> -0.796723743 | 0.480307321 -> 0.480307321 | 0.51721811 -> 0.51721811 | 0.143796661 -> 0.143796661 | 0.36952647 -> 0.36952647 | 25 -> 25 | 1887.87566 -> 1887.87566 | 121900.616 -> 121900.616 | 1.86970332 -> 1.18815206 | 7376 -> 297.583333/252.5/714 | A |
| QQQ_ABS_MOM_QLD / bimonthly / 126 / pre_tax | 1235952.54 -> 1235952.54 | 11.3595254 -> 11.3595254 | 0.132594686 -> 0.132594686 | -0.796723743 -> -0.796723743 | 0.524664263 -> 0.524664263 | 0.569843552 -> 0.569843552 | 0.16642492 -> 0.16642492 | 0.357082469 -> 0.357082469 | 25 -> 25 | 2160.67901 -> 2160.67901 | 0 -> 0 | 2.13988071 -> 1.18815206 | 7376 -> 297.583333/252.5/714 | A |
| QQQ_ABS_MOM_QLD / bimonthly / 189 / after_tax | 3568167.12 -> 3568167.12 | 34.6816712 -> 34.6816712 | 0.193644722 -> 0.193644722 | -0.517154219 -> -0.517154219 | 0.672095757 -> 0.672095757 | 0.760202233 -> 0.760202233 | 0.374442893 -> 0.374442893 | 0.242161674 -> 0.242161674 | 17 -> 17 | 2657.49995 -> 2657.49995 | 222284.268 -> 222284.268 | 2.63191935 -> 0.792101373 | 7376 -> 410/461/799 | A |
| QQQ_ABS_MOM_QLD / bimonthly / 189 / pre_tax | 5396152.52 -> 5396152.52 | 52.9615252 -> 52.9615252 | 0.218345812 -> 0.218345812 | -0.517154219 -> -0.517154219 | 0.731760873 -> 0.731760873 | 0.841544558 -> 0.841544558 | 0.422206383 -> 0.422206383 | 0.216378984 -> 0.216378984 | 17 -> 17 | 3358.51949 -> 3358.51949 | 0 -> 0 | 3.326191 -> 0.792101373 | 7376 -> 410/461/799 | A |
| QQQ_ABS_MOM_QLD / bimonthly / 252 / after_tax | 5707935.28 -> 5707935.28 | 56.0793528 -> 56.0793528 | 0.221739387 -> 0.221739387 | -0.517154219 -> -0.517154219 | 0.730079874 -> 0.730079874 | 0.849538148 -> 0.849538148 | 0.4287684 -> 0.4287684 | 0.245613564 -> 0.245613564 | 11 -> 11 | 3123.46722 -> 3123.46722 | 370872.692 -> 370872.692 | 3.09340131 -> 0.495063358 | 7376 -> 697.4/629/1591 | A |
| QQQ_ABS_MOM_QLD / bimonthly / 252 / pre_tax | 8613082.55 -> 8613082.55 | 85.1308255 -> 85.1308255 | 0.246885449 -> 0.246885449 | -0.517154219 -> -0.517154219 | 0.789227077 -> 0.789227077 | 0.933997433 -> 0.933997433 | 0.477392313 -> 0.477392313 | 0.223514757 -> 0.223514757 | 11 -> 11 | 4048.71469 -> 4048.71469 | 0 -> 0 | 4.00974251 -> 0.495063358 | 7376 -> 697.4/629/1591 | A |
| QQQ_ABS_MOM_QLD / monthly / 126 / after_tax | 1403245.56 -> 1403245.56 | 13.0324556 -> 13.0324556 | 0.139736821 -> 0.139736821 | -0.574646708 -> -0.574646708 | 0.55439981 -> 0.55439981 | 0.599987908 -> 0.599987908 | 0.243169967 -> 0.243169967 | 0.257172858 -> 0.257172858 | 31 -> 31 | 5725.70427 -> 5725.70427 | 297230.793 -> 297230.793 | 5.67058971 -> 1.48519008 | 7376 -> 255.8/209/695 | A |
| QQQ_ABS_MOM_QLD / monthly / 126 / pre_tax | 2253156.87 -> 2253156.87 | 21.5315687 -> 21.5315687 | 0.166778682 -> 0.166778682 | -0.57382442 -> -0.57382442 | 0.624527165 -> 0.624527165 | 0.683994731 -> 0.683994731 | 0.2906441 -> 0.2906441 | 0.22819316 -> 0.22819316 | 31 -> 31 | 7881.71887 -> 7881.71887 | 0 -> 0 | 7.80585091 -> 1.48519008 | 7376 -> 255.8/209/695 | A |
| QQQ_ABS_MOM_QLD / monthly / 189 / after_tax | 2449102.73 -> 2449102.73 | 23.4910273 -> 23.4910273 | 0.171606666 -> 0.171606666 | -0.54301992 -> -0.54301992 | 0.626142479 -> 0.626142479 | 0.708590326 -> 0.708590326 | 0.316022783 -> 0.316022783 | 0.261001993 -> 0.261001993 | 27 -> 27 | 4432.01158 -> 4432.01158 | 290495.045 -> 290495.045 | 4.38934987 -> 1.28716473 | 7376 -> 295.615385/230/715 | A |
| QQQ_ABS_MOM_QLD / monthly / 189 / pre_tax | 3985785.42 -> 3985785.42 | 38.8578542 -> 38.8578542 | 0.200204866 -> 0.200204866 | -0.517154219 -> -0.517154219 | 0.697358487 -> 0.697358487 | 0.803281444 -> 0.803281444 | 0.387127976 -> 0.387127976 | 0.233450088 -> 0.233450088 | 27 -> 27 | 5882.539 -> 5882.539 | 0 -> 0 | 5.82591478 -> 1.28716473 | 7376 -> 295.615385/230/715 | A |
| QQQ_ABS_MOM_QLD / monthly / 252 / after_tax | 5328963.34 -> 5328963.34 | 52.2896334 -> 52.2896334 | 0.217590132 -> 0.217590132 | -0.518411594 -> -0.518411594 | 0.718171113 -> 0.718171113 | 0.844347956 -> 0.844347956 | 0.419724663 -> 0.419724663 | 0.233026177 -> 0.233026177 | 15 -> 15 | 3353.88587 -> 3353.88587 | 344556.363 -> 344556.363 | 3.32160199 -> 0.693088702 | 7376 -> 510/375/1613 | A |
| QQQ_ABS_MOM_QLD / monthly / 252 / pre_tax | 7916384.74 -> 7916384.74 | 78.1638474 -> 78.1638474 | 0.241688336 -> 0.241688336 | -0.517154219 -> -0.517154219 | 0.774465039 -> 0.774465039 | 0.925380206 -> 0.925380206 | 0.467342867 -> 0.467342867 | 0.209834866 -> 0.209834866 | 15 -> 15 | 4219.86621 -> 4219.86621 | 0 -> 0 | 4.17924656 -> 0.693088702 | 7376 -> 510/375/1613 | A |
| QQQ_ABS_MOM_QLD / quarterly / 126 / after_tax | 744069.314 -> 744069.314 | 6.44069314 -> 6.44069314 | 0.104488429 -> 0.104488429 | -0.61608812 -> -0.61608812 | 0.460803818 -> 0.460803818 | 0.502681449 -> 0.502681449 | 0.169599811 -> 0.169599811 | 0.276489393 -> 0.276489393 | 23 -> 23 | 3416.57245 -> 3416.57245 | 174158.546 -> 174158.546 | 3.38368516 -> 1.08913939 | 7376 -> 343.363636/253/757 | A |
| QQQ_ABS_MOM_QLD / quarterly / 126 / pre_tax | 1124784.62 -> 1124784.62 | 10.2478462 -> 10.2478462 | 0.127321003 -> 0.127321003 | -0.582855705 -> -0.582855705 | 0.520277515 -> 0.520277515 | 0.572605752 -> 0.572605752 | 0.218443437 -> 0.218443437 | 0.25032295 -> 0.25032295 | 23 -> 23 | 4431.46544 -> 4431.46544 | 0 -> 0 | 4.38880899 -> 1.08913939 | 7376 -> 343.363636/253/757 | A |
| QQQ_ABS_MOM_QLD / quarterly / 189 / after_tax | 1664359.86 -> 1664359.86 | 15.6435986 -> 15.6435986 | 0.149408983 -> 0.149408983 | -0.62023548 -> -0.62023548 | 0.569146432 -> 0.569146432 | 0.638638221 -> 0.638638221 | 0.240890738 -> 0.240890738 | 0.27548909 -> 0.27548909 | 17 -> 17 | 3032.78668 -> 3032.78668 | 248950.645 -> 248950.645 | 3.00359364 -> 0.792101373 | 7376 -> 472.75/502.5/820 | A |
| QQQ_ABS_MOM_QLD / quarterly / 189 / pre_tax | 2633942.2 -> 2633942.2 | 25.339422 -> 25.339422 | 0.175835553 -> 0.175835553 | -0.582855705 -> -0.582855705 | 0.634713367 -> 0.634713367 | 0.721945834 -> 0.721945834 | 0.301679389 -> 0.301679389 | 0.248392867 -> 0.248392867 | 17 -> 17 | 4015.99943 -> 4015.99943 | 0 -> 0 | 3.97734217 -> 0.792101373 | 7376 -> 472.75/502.5/820 | A |
| QQQ_ABS_MOM_QLD / quarterly / 252 / after_tax | 4172056.62 -> 4172056.62 | 40.7205662 -> 40.7205662 | 0.202922506 -> 0.202922506 | -0.660769577 -> -0.660769577 | 0.678373402 -> 0.678373402 | 0.79884904 -> 0.79884904 | 0.307100255 -> 0.307100255 | 0.277763373 -> 0.277763373 | 7 -> 7 | 2722.39307 -> 2722.39307 | 351717.324 -> 351717.324 | 2.69618783 -> 0.297038015 | 7376 -> 1219.33333/820/2328 | A |
| QQQ_ABS_MOM_QLD / quarterly / 252 / pre_tax | 5723760.06 -> 5723760.06 | 56.2376006 -> 56.2376006 | 0.221906895 -> 0.221906895 | -0.627379525 -> -0.627379525 | 0.722414319 -> 0.722414319 | 0.867409959 -> 0.867409959 | 0.353704394 -> 0.353704394 | 0.25081836 -> 0.25081836 | 7 -> 7 | 3325.09425 -> 3325.09425 | 0 -> 0 | 3.29308751 -> 0.297038015 | 7376 -> 1219.33333/820/2328 | A |
| QQQ_ABS_MOM_QLD / weekly / 126 / after_tax | 1620428.1 -> 1620428.1 | 15.204281 -> 15.204281 | 0.147887442 -> 0.147887442 | -0.526733631 -> -0.526733631 | 0.58747981 -> 0.58747981 | 0.636505942 -> 0.636505942 | 0.280763243 -> 0.280763243 | 0.249384322 -> 0.249384322 | 63 -> 63 | 10199.1564 -> 10199.1564 | 285250.293 -> 285250.293 | 10.1009813 -> 3.06939282 | 7376 -> 125.83871/24/596 | A |
| QQQ_ABS_MOM_QLD / weekly / 126 / pre_tax | 2668866.19 -> 2668866.19 | 25.6886619 -> 25.6886619 | 0.176602758 -> 0.176602758 | -0.517658535 -> -0.517658535 | 0.667401224 -> 0.667401224 | 0.742268816 -> 0.742268816 | 0.341156856 -> 0.341156856 | 0.2205495 -> 0.2205495 | 63 -> 63 | 14204.3502 -> 14204.3502 | 0 -> 0 | 14.0676218 -> 3.06939282 | 7376 -> 125.83871/24/596 | A |
| QQQ_ABS_MOM_QLD / weekly / 189 / after_tax | 3849438.83 -> 3849438.83 | 37.4943883 -> 37.4943883 | 0.198137977 -> 0.198137977 | -0.523253037 -> -0.523253037 | 0.704682994 -> 0.704682994 | 0.79173454 -> 0.79173454 | 0.378665699 -> 0.378665699 | 0.23674434 -> 0.23674434 | 49 -> 49 | 11371.898 -> 11371.898 | 450495.848 -> 450495.848 | 11.2624342 -> 2.37630412 | 7376 -> 159.5/24.5/667 | A |
| QQQ_ABS_MOM_QLD / weekly / 189 / pre_tax | 6562192.43 -> 6562192.43 | 64.6219243 -> 64.6219243 | 0.230206222 -> 0.230206222 | -0.517154219 -> -0.517154219 | 0.784853514 -> 0.784853514 | 0.887732573 -> 0.887732573 | 0.445140374 -> 0.445140374 | 0.207637129 -> 0.207637129 | 49 -> 49 | 15935.0961 -> 15935.0961 | 0 -> 0 | 15.7817078 -> 2.37630412 | 7376 -> 159.5/24.5/667 | A |
| QQQ_ABS_MOM_QLD / weekly / 252 / after_tax | 2975934.33 -> 2975934.33 | 28.7593433 -> 28.7593433 | 0.182965083 -> 0.182965083 | -0.54263129 -> -0.54263129 | 0.649630363 -> 0.649630363 | 0.742084695 -> 0.742084695 | 0.337181225 -> 0.337181225 | 0.230202627 -> 0.230202627 | 33 -> 33 | 6818.7627 -> 6818.7627 | 331326.954 -> 331326.954 | 6.75312657 -> 1.58420275 | 7376 -> 249.9375/25.5/1606 | A |
| QQQ_ABS_MOM_QLD / weekly / 252 / pre_tax | 4569330.25 -> 4569330.25 | 44.6933025 -> 44.6933025 | 0.208352809 -> 0.208352809 | -0.539978245 -> -0.539978245 | 0.712682388 -> 0.712682388 | 0.832654029 -> 0.832654029 | 0.385854079 -> 0.385854079 | 0.205130136 -> 0.205130136 | 33 -> 33 | 8982.72483 -> 8982.72483 | 0 -> 0 | 8.8962588 -> 1.58420275 | 7376 -> 249.9375/25.5/1606 | A |
| SPY_ABS_MOM_SSO / bimonthly / 126 / after_tax | 1015329.49 -> 1015329.49 | 9.1532949 -> 9.1532949 | 0.121620348 -> 0.121620348 | -0.650258736 -> -0.650258736 | 0.553214039 -> 0.553214039 | 0.564735614 -> 0.564735614 | 0.187033778 -> 0.187033778 | 0.204098917 -> 0.204098917 | 19 -> 19 | 3126.35789 -> 3126.35789 | 152217.549 -> 152217.549 | 3.09626415 -> 0.891114045 | 7376 -> 382.444444/376/838 | A |
| SPY_ABS_MOM_SSO / bimonthly / 126 / pre_tax | 1506308.16 -> 1506308.16 | 14.0630816 -> 14.0630816 | 0.143743852 -> 0.143743852 | -0.629796083 -> -0.629796083 | 0.626024972 -> 0.626024972 | 0.643788629 -> 0.643788629 | 0.22823872 -> 0.22823872 | 0.179273042 -> 0.179273042 | 19 -> 19 | 4026.30113 -> 4026.30113 | 0 -> 0 | 3.98754471 -> 0.891114045 | 7376 -> 382.444444/376/838 | A |
| SPY_ABS_MOM_SSO / bimonthly / 189 / after_tax | 1139085.36 -> 1139085.36 | 10.3908536 -> 10.3908536 | 0.128026501 -> 0.128026501 | -0.593410603 -> -0.593410603 | 0.559938955 -> 0.559938955 | 0.594898009 -> 0.594898009 | 0.215746905 -> 0.215746905 | 0.198256003 -> 0.198256003 | 17 -> 17 | 1713.95902 -> 1713.95902 | 78275.9717 -> 78275.9717 | 1.69746077 -> 0.792101373 | 7376 -> 399.5/360.5/881 | A |
| SPY_ABS_MOM_SSO / bimonthly / 189 / pre_tax | 1502213.41 -> 1502213.41 | 14.0221341 -> 14.0221341 | 0.143589691 -> 0.143589691 | -0.593410603 -> -0.593410603 | 0.609341498 -> 0.609341498 | 0.655393688 -> 0.655393688 | 0.241973585 -> 0.241973585 | 0.177512068 -> 0.177512068 | 17 -> 17 | 1974.84059 -> 1974.84059 | 0 -> 0 | 1.95583114 -> 0.792101373 | 7376 -> 399.5/360.5/881 | A |
| SPY_ABS_MOM_SSO / bimonthly / 252 / after_tax | 1697418.83 -> 1697418.83 | 15.9741883 -> 15.9741883 | 0.150528987 -> 0.150528987 | -0.615066946 -> -0.615066946 | 0.607502895 -> 0.607502895 | 0.674822369 -> 0.674822369 | 0.244735939 -> 0.244735939 | 0.198507669 -> 0.198507669 | 9 -> 9 | 1558.01402 -> 1558.01402 | 129139.871 -> 129139.871 | 1.54301686 -> 0.396050687 | 7376 -> 882.5/756.5/1591 | A |
| SPY_ABS_MOM_SSO / bimonthly / 252 / pre_tax | 2300417.17 -> 2300417.17 | 22.0041717 -> 22.0041717 | 0.167978653 -> 0.167978653 | -0.593410603 -> -0.593410603 | 0.658334105 -> 0.658334105 | 0.739339526 -> 0.739339526 | 0.283073224 -> 0.283073224 | 0.178553203 -> 0.178553203 | 9 -> 9 | 1874.00284 -> 1874.00284 | 0 -> 0 | 1.85596404 -> 0.396050687 | 7376 -> 882.5/756.5/1591 | A |
| SPY_ABS_MOM_SSO / monthly / 126 / after_tax | 627354.151 -> 627354.151 | 5.27354151 -> 5.27354151 | 0.095195885 -> 0.095195885 | -0.641321888 -> -0.641321888 | 0.472148404 -> 0.472148404 | 0.481741453 -> 0.481741453 | 0.148436981 -> 0.148436981 | 0.231092141 -> 0.231092141 | 29 -> 29 | 4405.95427 -> 4405.95427 | 118624.085 -> 118624.085 | 4.36354338 -> 1.3861774 | 7376 -> 268.5/211/858 | A |
| SPY_ABS_MOM_SSO / monthly / 126 / pre_tax | 889533.658 -> 889533.658 | 7.89533658 -> 7.89533658 | 0.11429786 -> 0.11429786 | -0.629796083 -> -0.629796083 | 0.537747169 -> 0.537747169 | 0.553332661 -> 0.553332661 | 0.181483916 -> 0.181483916 | 0.204302918 -> 0.204302918 | 29 -> 29 | 5621.56024 -> 5621.56024 | 0 -> 0 | 5.56744815 -> 1.3861774 | 7376 -> 268.5/211/858 | A |
| SPY_ABS_MOM_SSO / monthly / 189 / after_tax | 672413.841 -> 672413.841 | 5.72413841 -> 5.72413841 | 0.0989640821 -> 0.0989640821 | -0.668703537 -> -0.668703537 | 0.471796365 -> 0.471796365 | 0.500993314 -> 0.500993314 | 0.147993956 -> 0.147993956 | 0.237019897 -> 0.237019897 | 25 -> 25 | 2029.94269 -> 2029.94269 | 40061.844 -> 40061.844 | 2.01040284 -> 1.18815206 | 7376 -> 271.75/210/881 | A |
| SPY_ABS_MOM_SSO / monthly / 189 / pre_tax | 817731.132 -> 817731.132 | 7.17731132 -> 7.17731132 | 0.109663486 -> 0.109663486 | -0.645283564 -> -0.645283564 | 0.506148477 -> 0.506148477 | 0.541311165 -> 0.541311165 | 0.169946195 -> 0.169946195 | 0.217661432 -> 0.217661432 | 25 -> 25 | 2314.17294 -> 2314.17294 | 0 -> 0 | 2.29189714 -> 1.18815206 | 7376 -> 271.75/210/881 | A |
| SPY_ABS_MOM_SSO / monthly / 252 / after_tax | 1487275.96 -> 1487275.96 | 13.8727596 -> 13.8727596 | 0.143023914 -> 0.143023914 | -0.606533706 -> -0.606533706 | 0.594578979 -> 0.594578979 | 0.649166471 -> 0.649166471 | 0.235805385 -> 0.235805385 | 0.193906167 -> 0.193906167 | 13 -> 13 | 2023.2274 -> 2023.2274 | 109995.961 -> 109995.961 | 2.00375219 -> 0.59407603 | 7376 -> 574.5/465.5/1488 | A |
| SPY_ABS_MOM_SSO / monthly / 252 / pre_tax | 1978292.46 -> 1978292.46 | 18.7829246 -> 18.7829246 | 0.15928611 -> 0.15928611 | -0.593410603 -> -0.593410603 | 0.643493314 -> 0.643493314 | 0.709333997 -> 0.709333997 | 0.268424778 -> 0.268424778 | 0.167836017 -> 0.167836017 | 13 -> 13 | 2430.1343 -> 2430.1343 | 0 -> 0 | 2.40674228 -> 0.59407603 | 7376 -> 574.5/465.5/1488 | A |
| SPY_ABS_MOM_SSO / quarterly / 126 / after_tax | 477182.855 -> 477182.855 | 3.77182855 -> 3.77182855 | 0.080457272 -> 0.080457272 | -0.657530211 -> -0.657530211 | 0.420313026 -> 0.420313026 | 0.42659349 -> 0.42659349 | 0.122362852 -> 0.122362852 | 0.271434316 -> 0.271434316 | 19 -> 19 | 2364.25222 -> 2364.25222 | 90679.1847 -> 90679.1847 | 2.34149437 -> 0.891114045 | 7376 -> 412.888889/385/816 | A |
| SPY_ABS_MOM_SSO / quarterly / 126 / pre_tax | 658118.803 -> 658118.803 | 5.58118803 -> 5.58118803 | 0.0977953143 -> 0.0977953143 | -0.634667294 -> -0.634667294 | 0.479224376 -> 0.479224376 | 0.489215713 -> 0.489215713 | 0.154089103 -> 0.154089103 | 0.24637344 -> 0.24637344 | 19 -> 19 | 2931.05564 -> 2931.05564 | 0 -> 0 | 2.90284185 -> 0.891114045 | 7376 -> 412.888889/385/816 | A |
| SPY_ABS_MOM_SSO / quarterly / 189 / after_tax | 657252.963 -> 657252.963 | 5.57252963 -> 5.57252963 | 0.09772375 -> 0.09772375 | -0.631411051 -> -0.631411051 | 0.464834856 -> 0.464834856 | 0.499036472 -> 0.499036472 | 0.154770414 -> 0.154770414 | 0.237148331 -> 0.237148331 | 15 -> 15 | 1150.99935 -> 1150.99935 | 33638.0006 -> 33638.0006 | 1.13992005 -> 0.693088702 | 7376 -> 468.285714/446/880 | A |
| SPY_ABS_MOM_SSO / quarterly / 189 / pre_tax | 779772.932 -> 779772.932 | 6.79772932 -> 6.79772932 | 0.107054781 -> 0.107054781 | -0.604698508 -> -0.604698508 | 0.494197842 -> 0.494197842 | 0.533543989 -> 0.533543989 | 0.177038275 -> 0.177038275 | 0.223747042 -> 0.223747042 | 15 -> 15 | 1270.7387 -> 1270.7387 | 0 -> 0 | 1.2585068 -> 0.693088702 | 7376 -> 468.285714/446/880 | A |
| SPY_ABS_MOM_SSO / quarterly / 252 / after_tax | 913540.88 -> 913540.88 | 8.1354088 -> 8.1354088 | 0.115768278 -> 0.115768278 | -0.631411051 -> -0.631411051 | 0.515105473 -> 0.515105473 | 0.558014839 -> 0.558014839 | 0.183348514 -> 0.183348514 | 0.22744744 -> 0.22744744 | 11 -> 11 | 1458.04442 -> 1458.04442 | 69797.6621 -> 69797.6621 | 1.44400956 -> 0.495063358 | 7376 -> 680.6/504/1446 | A |
| SPY_ABS_MOM_SSO / quarterly / 252 / pre_tax | 1143987.51 -> 1143987.51 | 10.4398751 -> 10.4398751 | 0.128266403 -> 0.128266403 | -0.604698508 -> -0.604698508 | 0.553457238 -> 0.553457238 | 0.605804695 -> 0.605804695 | 0.212116287 -> 0.212116287 | 0.211785181 -> 0.211785181 | 11 -> 11 | 1721.66243 -> 1721.66243 | 0 -> 0 | 1.70509003 -> 0.495063358 | 7376 -> 680.6/504/1446 | A |
| SPY_ABS_MOM_SSO / weekly / 126 / after_tax | 457487.12 -> 457487.12 | 3.5748712 -> 3.5748712 | 0.0782044238 -> 0.0782044238 | -0.641923049 -> -0.641923049 | 0.425355035 -> 0.425355035 | 0.425928248 -> 0.425928248 | 0.121828347 -> 0.121828347 | 0.253119417 -> 0.253119417 | 57 -> 57 | 5707.9003 -> 5707.9003 | 67522.9384 -> 67522.9384 | 5.65295712 -> 2.77235481 | 7376 -> 135/24/897 | A |
| SPY_ABS_MOM_SSO / weekly / 126 / pre_tax | 599364.694 -> 599364.694 | 4.99364694 -> 4.99364694 | 0.0927234479 -> 0.0927234479 | -0.616460864 -> -0.616460864 | 0.480195632 -> 0.480195632 | 0.489870721 -> 0.489870721 | 0.150412546 -> 0.150412546 | 0.224243195 -> 0.224243195 | 57 -> 57 | 6895.30893 -> 6895.30893 | 0 -> 0 | 6.82893597 -> 2.77235481 | 7376 -> 135/24/897 | A |
| SPY_ABS_MOM_SSO / weekly / 189 / after_tax | 742108.647 -> 742108.647 | 6.42108647 -> 6.42108647 | 0.104344129 -> 0.104344129 | -0.548981529 -> -0.548981529 | 0.506715605 -> 0.506715605 | 0.524312363 -> 0.524312363 | 0.190068561 -> 0.190068561 | 0.217976426 -> 0.217976426 | 51 -> 51 | 5605.29954 -> 5605.29954 | 79264.5804 -> 79264.5804 | 5.55134398 -> 2.47531679 | 7376 -> 151.32/15/892 | A |
| SPY_ABS_MOM_SSO / weekly / 189 / pre_tax | 1006093.4 -> 1006093.4 | 9.06093402 -> 9.06093402 | 0.121112912 -> 0.121112912 | -0.548981529 -> -0.548981529 | 0.56601021 -> 0.56601021 | 0.595298176 -> 0.595298176 | 0.22061382 -> 0.22061382 | 0.197736163 -> 0.197736163 | 51 -> 51 | 6842.89989 -> 6842.89989 | 0 -> 0 | 6.77703141 -> 2.47531679 | 7376 -> 151.32/15/892 | A |
| SPY_ABS_MOM_SSO / weekly / 252 / after_tax | 815540.631 -> 815540.631 | 7.15540631 -> 7.15540631 | 0.109516103 -> 0.109516103 | -0.552882255 -> -0.552882255 | 0.509812025 -> 0.509812025 | 0.540826635 -> 0.540826635 | 0.198082146 -> 0.198082146 | 0.212890656 -> 0.212890656 | 39 -> 39 | 4263.66448 -> 4263.66448 | 87081.2749 -> 87081.2749 | 4.22262324 -> 1.88124076 | 7376 -> 203.684211/20/815 | A |
| SPY_ABS_MOM_SSO / weekly / 252 / pre_tax | 1109537.62 -> 1109537.62 | 10.0953762 -> 10.0953762 | 0.126559371 -> 0.126559371 | -0.552882255 -> -0.552882255 | 0.564794975 -> 0.564794975 | 0.604395057 -> 0.604395057 | 0.228908362 -> 0.228908362 | 0.197726877 -> 0.197726877 | 39 -> 39 | 5113.6944 -> 5113.6944 | 0 -> 0 | 5.06447093 -> 1.88124076 | 7376 -> 203.684211/20/815 | A |

## L. Turnover audit

The regenerated runner reuses the audited Phase 2 _turnover_audit helper and performance_metrics with pretrade_equity: sum(abs(trade_notional) / contemporaneous_pretrade_equity) / calendar_years. Initial deployment and hypothetical terminal liquidation are excluded. Turnover changed in all rows because the stale denominator was corrected; no trade path changed.

Pre-tax annual turnover range across 24 rows: **0.297038015 - 3.069392822**. After-tax reporting uses the same contemporaneous pre-trade denominator and has range **0.297038015 - 3.069392822**.

## M. Holding-period audit

Completed zero-to-positive-to-zero episodes only are measured in trading sessions. Open terminal positions are excluded. All 48 stale 7376 values were replaced by completed-episode mean/median/max fields; no equity, trade, or tax-ledger rows changed.
* mean_holding_period_days regenerated range: **125.838710 - 1219.333333 trading sessions**.
* median_holding_period_days regenerated range: **15.000000 - 820.000000 trading sessions**.
* max_holding_period_days regenerated range: **596.000000 - 2328.000000 trading sessions**.

## N. Realized-tax and terminal-liquidation audit

After-tax primary wealth remains wealth after realized tax paid to date. cumulative_realized_tax_paid equals tax_paid for all 24 after-tax rows. The canonical terminal diagnostics are present and non-null for every after-tax row: after_tax_wealth_tax_paid_to_date, after_tax_cagr_tax_paid_to_date, terminal_liquidation_wealth, terminal_liquidation_cagr, terminal_liquidation_tax, terminal_liquidation_cost, and terminal_unrealized_gain_after_cost. Terminal liquidation is hypothetical and non-mutating: it creates no SELL, does not change turnover/holding statistics, and does not mutate the tax ledger.

| Rule | Frequency | L | Tax-paid-to-date wealth | Terminal wealth | Terminal CAGR | Terminal tax | Terminal cost | Unrealized gain after cost |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| QQQ_ABS_MOM_QLD | bimonthly | 126 | 893869.818 | 829375.53 | 11.044071% | 64047.3529 | 446.934909 | 315271.243 |
| QQQ_ABS_MOM_QLD | bimonthly | 189 | 3568167.12 | 3039314.54 | 18.420022% | 527068.496 | 1784.08356 | 2594479.43 |
| QQQ_ABS_MOM_QLD | bimonthly | 252 | 5707935.28 | 4861938.95 | 21.207259% | 843142.363 | 2853.96764 | 4150343.9 |
| QQQ_ABS_MOM_QLD | monthly | 126 | 1403245.56 | 1374780.49 | 13.858078% | 27763.4436 | 701.62278 | 136664.748 |
| QQQ_ABS_MOM_QLD | monthly | 189 | 2449102.73 | 2202387.7 | 16.546267% | 245490.475 | 1224.55137 | 1208419.77 |
| QQQ_ABS_MOM_QLD | monthly | 252 | 5328963.34 | 4539135.98 | 20.795616% | 787162.876 | 2664.48167 | 3874786.49 |
| QQQ_ABS_MOM_QLD | quarterly | 126 | 744069.314 | 743697.279 | 10.446108% | 0 | 372.034657 | -39434.5815 |
| QQQ_ABS_MOM_QLD | quarterly | 189 | 1664359.86 | 1544273.36 | 14.515451% | 119254.327 | 832.179931 | 587025.975 |
| QQQ_ABS_MOM_QLD | quarterly | 252 | 4172056.62 | 3623422.02 | 19.455337% | 546548.577 | 2086.02831 | 2690369.56 |
| QQQ_ABS_MOM_QLD | weekly | 126 | 1620428.1 | 1538209.21 | 14.493141% | 81408.6782 | 810.214052 | 400731.864 |
| QQQ_ABS_MOM_QLD | weekly | 189 | 3849438.83 | 3445184.23 | 19.157334% | 402329.874 | 1924.71941 | 1980457.17 |
| QQQ_ABS_MOM_QLD | weekly | 252 | 2975934.33 | 2654520.47 | 17.628878% | 319925.895 | 1487.96716 | 1574825.97 |
| SPY_ABS_MOM_SSO | bimonthly | 126 | 1015329.49 | 950270.325 | 11.794833% | 64551.4998 | 507.664745 | 317752.891 |
| SPY_ABS_MOM_SSO | bimonthly | 189 | 1139085.36 | 989915.538 | 12.021333% | 148600.28 | 569.542681 | 731480.583 |
| SPY_ABS_MOM_SSO | bimonthly | 252 | 1697418.83 | 1475132.01 | 14.255995% | 221438.114 | 848.709415 | 1090022.71 |
| SPY_ABS_MOM_SSO | monthly | 126 | 627354.151 | 614497.804 | 9.407353% | 12542.6698 | 313.677075 | 61740.9296 |
| SPY_ABS_MOM_SSO | monthly | 189 | 672413.841 | 587783.343 | 9.166817% | 84294.291 | 336.206921 | 437927.933 |
| SPY_ABS_MOM_SSO | monthly | 252 | 1487275.96 | 1292508.56 | 13.510686% | 194023.76 | 743.637981 | 955076.349 |
| SPY_ABS_MOM_SSO | quarterly | 126 | 477182.855 | 472625.745 | 7.994398% | 4318.51874 | 238.591427 | 21257.7836 |
| SPY_ABS_MOM_SSO | quarterly | 189 | 657252.963 | 570589.598 | 9.006446% | 86334.7382 | 328.626481 | 428053.996 |
| SPY_ABS_MOM_SSO | quarterly | 252 | 913540.88 | 803524.339 | 10.870086% | 109559.77 | 456.77044 | 544258.155 |
| SPY_ABS_MOM_SSO | weekly | 126 | 457487.12 | 438486.991 | 7.594202% | 18771.3857 | 228.74356 | 92401.6031 |
| SPY_ABS_MOM_SSO | weekly | 189 | 742108.647 | 674530.582 | 9.913514% | 67207.011 | 371.054323 | 330824.568 |
| SPY_ABS_MOM_SSO | weekly | 252 | 815540.631 | 739244.334 | 10.413267% | 75888.5268 | 407.770316 | 373559.079 |

## O. Full economic-path hash comparison

The regenerated equity_curve.csv, positions.csv, trades.csv, and tax_ledger.csv are byte-identical to the stale run after the reporting-only regeneration (the strategy identifiers are unchanged). This is stronger than normalized-label equality for all 24 economic combinations.

| File | Old rows | New rows | Old SHA-256 | New SHA-256 | Equal |
|---|---:|---:|---|---|---|
| equity_curve.csv | 243840 | 243840 | 687dc6a8b9fcc56a2875ab2772f8147489672c317eff9852d9872101000d9892 | 687dc6a8b9fcc56a2875ab2772f8147489672c317eff9852d9872101000d9892 | **True** |
| positions.csv | 243840 | 243840 | 30685853b3ce37053e65939e8cb6ea637a0ff2592cf49bf654d2f4bc6929b894 | 30685853b3ce37053e65939e8cb6ea637a0ff2592cf49bf654d2f4bc6929b894 | **True** |
| trades.csv | 1244 | 1244 | 2da44f819f51772bcd872482afe09b030d44ebef8cfa22f2b8ae7fee303c2406 | 2da44f819f51772bcd872482afe09b030d44ebef8cfa22f2b8ae7fee303c2406 | **True** |
| tax_ledger.csv | 299 | 299 | 7d38cd301cf954d89f5fe372fa10fca82abae60c7ece87ee2249b46c7ed8d943 | 7d38cd301cf954d89f5fe372fa10fca82abae60c7ece87ee2249b46c7ed8d943 | **True** |

Key regenerated artifact hashes:
* metrics_pre_tax.csv: 487c73bc7efe7008765ab1b30f2b5113a58b7ce0e7351ba8d9388947de7fb139
* metrics_after_tax.csv: c3c7d7b001a3e68d919fe9d0e97a76ea7f7310f42731d82b8392a5c70ecb99de
* absolute_momentum_results.csv: 6e4315f821ca5c4fb55815f00909e7517bf20ae4782ffef88ae02fa2a84daf85
* parameter_results.csv: afb92b9a5db858a12e6c3b359552d9997da326edf0281b6f887800cc99e87dd0

## P. Raw SHA verification

Immutable raw snapshots match data/raw/manifest.yaml; no raw file was modified.

| Asset | Manifest SHA-256 | Current SHA-256 | Equal |
|---|---|---|---|
| SPY | 6a73a96bf408a041bc7e77df51117ae5a0965769c407c6699f52b0fd489b28d8 | 6a73a96bf408a041bc7e77df51117ae5a0965769c407c6699f52b0fd489b28d8 | **True** |
| QQQ | fe5aa0db7c8a717e00cd7726d04ba1d2faff627e9f6e48c0952a5e2f235052c6 | fe5aa0db7c8a717e00cd7726d04ba1d2faff627e9f6e48c0952a5e2f235052c6 | **True** |
| SSO | b0636de318b2d72d4cf774d6af2e11b2bc47904150891a06a39d29355e6e2b5d | b0636de318b2d72d4cf774d6af2e11b2bc47904150891a06a39d29355e6e2b5d | **True** |
| QLD | 2499976b07ea6711b33befad63bd8e177ab85f0c820662330f9a4ad257532a9f | 2499976b07ea6711b33befad63bd8e177ab85f0c820662330f9a4ad257532a9f | **True** |
| TQQQ | 4b0b5c7500d7510bb2e61607e86130d635a3d05339cf7cde10ab7174551ccf76 | 4b0b5c7500d7510bb2e61607e86130d635a3d05339cf7cde10ab7174551ccf76 | **True** |

## Q. Unresolved issues

None. Phase 4 is a descriptive full-sample stability study only. No lookback was selected, no OOS or Walk-Forward claim is made, and Phase 5-7 were not started or modified.

PHASE 4 AUDIT PASS
