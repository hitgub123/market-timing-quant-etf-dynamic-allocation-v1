# Phase 1 External Audit Diff

Compared against `reports/runs/20260913_phase1_static_final`.

## A. Tests

The final complete suite result is **68 passed** (`68 passed in 11.70s`), with no failures, errors, skips, or xfails.

## B. Candidate-count verification

| Scope | Pair rows | Triple rows | Total rows |
|---|---:|---:|---:|
| One frequency | 168 | 330 | 498 |
| Two frequencies, one tax mode | 336 | 660 | 996 |
| Two frequencies, two tax modes | 672 | 1,320 | 1,992 |

The eight mandated pair definitions each produce 21 weights (`0.00, 0.05, ..., 1.00`). Each of the five mandated triple definitions produces 66 nonnegative 10% allocations summing to 100%. All 498 candidates are finite, nonnegative, and sum to one within `1e-12`; required rows were not deduplicated.

## C. Old → new metric diff

The old CSVs predate the metrics audit. The selected rows below use the monthly pair name for 100% endpoints and the explicitly named SPY/QLD and QQQ/CASH allocations. Primary metrics are pre-tax unless marked after-tax.

| Strategy | Ending value old → new | CAGR old → new | MaxDD old → new | Calmar old → new | Annual turnover old → new | Holding fields old → new |
|---|---:|---:|---:|---:|---:|---|
| 100% SPY (monthly) | $892,891.79 → $892,891.79 | 11.450579% → 11.450579% | -55.189444% → -55.189444% | 0.207478 → 0.207478 | 0.049494 → 0.000000 | full 7,376 days → mean/median/max null |
| 100% QQQ (monthly) | $2,196,760.87 → $2,196,760.87 | 16.531504% → 16.531504% | -53.403989% → -53.403989% | 0.309556 → 0.309556 | 0.049494 → 0.000000 | full 7,376 days → mean/median/max null |
| 100% SSO (monthly) | $1,945,274.48 → $1,945,274.48 | 15.832031% → 15.832031% | -84.667301% → -84.667301% | 0.186991 → 0.186991 | 0.049494 → 0.000000 | full 7,376 days → mean/median/max null |
| 100% QLD (monthly) | $9,087,552.15 → $9,087,552.15 | 25.020077% → 25.020077% | -83.128864% → -83.128864% | 0.300979 → 0.300979 | 0.049494 → 0.000000 | full 7,376 days → mean/median/max null |
| 50/50 SPY/QLD (monthly) | $3,354,782.46 → $3,354,782.46 | 19.000539% → 19.000539% | -71.381681% → -71.381681% | 0.266182 → 0.266182 | 2.679312 → 0.349327 | full 7,376 days → completed-episode fields null |
| 50/50 SPY/QLD (quarterly) | $3,434,380.21 → $3,434,380.21 | 19.138802% → 19.138802% | -71.394778% → -71.394778% | 0.268070 → 0.268070 | 1.752428 → 0.211084 | full 7,376 days → completed-episode fields null |
| 50/50 QQQ/CASH (monthly) | $516,091.95 → $516,091.95 | 8.465925% → 8.465925% | -30.300446% → -30.300446% | 0.279399 → 0.279399 | 0.331776 → 0.134269 | full 7,376 days → completed-episode fields null |

For the after-tax versions of the same seven rows, ending value, CAGR, MaxDD, Calmar, and realized `tax_paid` are unchanged numerically. The 50/50 realized tax totals are `$252,030.05` monthly, `$217,358.06` quarterly, and `$45,508.84` for QQQ/CASH monthly; the 100% endpoints have zero realized tax.

The old after-tax table had no terminal-liquidation fields. New diagnostic values are:

| Strategy | Wealth after realized tax paid to date | Terminal wealth | Terminal CAGR | Terminal tax | Terminal cost | Unrealized gain after cost |
|---|---:|---:|---:|---:|---:|---:|
| 100% SPY | $892,891.79 | $731,460.07 | 10.3554% | $160,985.27 | $446.45 | $792,445.34 |
| 100% QQQ | $2,196,760.87 | $1,769,928.66 | 15.2915% | $425,733.84 | $1,098.38 | $2,095,662.49 |
| 100% SSO | $1,945,274.48 | $1,569,631.92 | 14.6078% | $374,669.92 | $972.64 | $1,844,301.84 |
| 100% QLD | $9,087,552.15 | $7,258,110.22 | 23.6362% | $1,824,898.15 | $4,543.78 | $8,983,008.37 |
| 50/50 SPY/QLD monthly | $2,516,607.81 | $2,225,501.40 | 16.6065% | $289,848.11 | $1,258.30 | $1,426,768.92 |
| 50/50 SPY/QLD quarterly | $2,756,133.74 | $2,388,643.82 | 17.0157% | $366,111.85 | $1,378.07 | $1,802,174.98 |
| 50/50 QQQ/CASH monthly | $430,927.76 | $399,875.92 | 7.1042% | $30,941.93 | $109.91 | $152,310.73 |

The canonical field is `after_tax_wealth_tax_paid_to_date`; cumulative realized tax is `cumulative_realized_tax_paid` (also retained as `tax_paid` for compatibility). Terminal-liquidation after-tax metrics are diagnostic and do not mutate the strategy ledger.

## D. Economic-integrity check

The metrics audit did not change strategy economics:

| Check across 996 matching strategy rows per mode | Maximum absolute delta |
|---|---:|
| Ending value | `0.0` |
| CAGR | `0.0` |
| MaxDD | `0.0` |
| Calmar | `0.0` |

The complete old/new `equity_curve.csv` byte hash is identical:

`46c70bf5897bbb1bdb7d8190d9018210aee9d37f1d1dbeecadec2ef5c483d5f9`

Normalized strategy-row hashes are also identical for trades (`420bca204d4eed89d50efdaa75e16953931e328ed5cb776ecdedf51d5f945259`), positions (`044ca44dd7d9db1e21553b69500365873768bf3f80bb6a7d4680870a7330a176`), and the tax ledger (`5ce8ff42c5a6a9e2d2990be1a1a7a2beb44593c012751679a5f1a4c1526193a1`). Drawdown numeric values are identical; the CSV header was normalized from the stale `index` label to `date`.

Thus daily equity curves, ending values, CAGR, MaxDD, and Calmar are unchanged. Turnover and holding-period fields changed only because stale artifacts were regenerated under the current audited definitions. New terminal fields are non-mutating diagnostics.

## E. Pareto audit

| Frontier | Nondominated strategy rows | Unique exact risk/return coordinates | Unique allocation IDs |
|---|---:|---:|---:|
| Pre-tax | 131 | 57 | 43 |
| After realized tax paid to date | 114 | 45 | 42 |
| Terminal-liquidation after tax | 114 | 44 | 42 |

`economic_allocation_id` is a stable normalized full-universe weight identifier. `mark_pareto()` now uses strict dominance: no-worse absolute MaxDD and no-worse CAGR, with at least one difference larger than `1e-12`. Identical risk/CAGR rows do not dominate one another; all such rows retain `pareto=True`. Required duplicate experiment rows remain in the CSV. Plotting may show overlapping points, but the CSV flags are strategy-level and mathematically consistent.

## F. Static accounting audit

The deterministic 50/50 synthetic case uses a 5 bps rate, initial capital `$1,000`, and two assets at `$100` initially. Initial total notional is `$999.500249875`, initial cost `$0.499750125`, and each asset receives `$499.750124938` / `4.997501249` shares. When asset A opens at `$120` and B at `$100`, pre-rebalance equity is `$1,099.450274863`; the engine sells `$50.000000000` of A and buys `$49.950024988` of B, charges `$0.049975012`, leaves cash `$0`, and ends at `$1,099.400299850`. These values match the independent hand calculation in `tests/test_static_frontier.py`.

The QQQ/CASH 50/50 case buys `$499.875031242` of QQQ, charges `$0.249937516`, leaves `$499.875031242` cash, and has a post-rebalance risky weight of exactly 50% within tolerance. The 100% single-asset test matches Phase 0 equity, ending value, CAGR, MaxDD, and Calmar within numerical tolerance.

Turnover audit rows generated from the actual ledger:

| Strategy | Included normalized turnover | Years | Annual turnover | Nonzero-trade rebalances | Gross notional |
|---|---:|---:|---:|---:|---:|
| 100% QLD monthly | 0.000000000 | 20.194387406 | 0.000000000 | 0 | $99,950.02 |
| 100% QLD quarterly | 0.000000000 | 20.194387406 | 0.000000000 | 0 | $99,950.02 |
| 50/50 SPY/QLD monthly | 7.054438860 | 20.194387406 | 0.349326707 | 242 | $5,410,706.81 |
| 50/50 SPY/QLD quarterly | 4.262720437 | 20.194387406 | 0.211084414 | 81 | $3,538,921.14 |
| 50/50 QQQ/CASH monthly | 2.711474867 | 20.194387406 | 0.134268736 | 242 | $670,001.28 |

Each annualized value is independently recomputed as `sum(abs(trade_notional) / contemporaneous_pretrade_equity)`, excluding initial deployment, divided by calendar backtest years.

## G. Data integrity

Raw snapshot SHA-256 values remain unchanged and match `data/raw/manifest.yaml`:

| Asset | SHA-256 |
|---|---|
| SPY | `6a73a96bf408a041bc7e77df51117ae5a0965769c407c6699f52b0fd489b28d8` |
| QQQ | `fe5aa0db7c8a717e00cd7726d04ba1d2faff627e9f6e48c0952a5e2f235052c6` |
| SSO | `b0636de318b2d72d4cf774d6af2e11b2bc47904150891a06a39d29355e6e2b5d` |
| QLD | `2499976b07ea6711b33befad63bd8e177ab85f0c820662330f9a4ad257532a9f` |
| TQQQ | `4b0b5c7500d7510bb2e61607e86130d635a3d05339cf7cde10ab7174551ccf76` |

## H. Final conclusion

`PHASE 1 AUDIT PASS`

No unresolved Phase 1 issue remains within this audit scope. Phase 2–7 strategy logic and artifacts were not modified.
