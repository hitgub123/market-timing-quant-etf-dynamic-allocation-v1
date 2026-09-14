# MarketTimingQuant v1 — Phase 7 Supplemental Frozen Specification

**Status: FROZEN**

## Phase 7A — Fixed Four-State Machine

All state signals use only underlying QQQ data. QLD and TQQQ signals are prohibited.

- `trend = QQQ adjusted_close > QQQ MA200`
- `momentum = QQQ 252-trading-day momentum`
- `rv20 = QQQ 20-day annualized realized volatility`
- `rv20_q33 = expanding historical 33rd percentile of QQQ RV20`

At date `t`, `rv20_q33` may use only RV20 values available before `t`. Full-sample quantiles are prohibited.

Priority: Trend → Momentum → Volatility.

```python
if qqq_close <= qqq_ma200:
    state = "RISK_OFF"
    weights = {"CASH": 1.00}
elif qqq_momentum_252 <= 0:
    state = "NORMAL"
    weights = {"QQQ": 1.00}
elif qqq_rv20 <= qqq_rv20_expanding_q33:
    state = "AGGRESSIVE"
    weights = {"QLD": 0.80, "TQQQ": 0.20}
else:
    state = "LEVERAGED"
    weights = {"QLD": 1.00}
```

TQQQ weight must be zero before its true listing date. AGGRESSIVE falls back to 100% QLD whenever TQQQ cannot be traded.

Phase 7A is fixed and performs no parameter selection or optimization. Test Weekly, Monthly, Bi-Monthly, and Quarterly rebalancing with close-t signals executed no earlier than the next trading-day open.

## Phase 7B — Parameterized Walk-Forward

Run only after Phase 7A completes.

```yaml
ma_days: [150, 175, 200, 225, 250]
momentum_days: [126, 189, 252]
low_vol_quantile: [0.25, 0.33, 0.40]
minimum_cagr: 0.15
maximum_abs_max_drawdown: 0.45
objective: maximize_calmar
```

Only training candidates with CAGR >= 15% and abs(MaxDD) <= 45% are eligible. Select highest Calmar. If none qualify, return `NO_ELIGIBLE_PARAMETER` without relaxing limits or inspecting test performance.

If eligible Calmar values differ by less than 5%, choose in order: lower MaxDD, lower turnover, longer MA, longer momentum lookback, then volatility quantile closest to 0.33.

## OOS

Use expanding yearly OOS: initial train 2006-06-21 through 2012-12-31 and test 2013, expanding one calendar year at a time through 2026 YTD.

The stitched OOS ledger must not reset holdings, cash, cost basis, tax ledger, or loss pool.

## Benchmarks and Dominance

Report same-OOS-period SPY, QQQ, SSO, QLD, and CASH benchmarks with CAGR, MaxDD, Calmar, Sortino, after-tax CAGR, turnover, and recovery time.

`QQQ_DOMINANCE = TRUE` only when all hold:

```text
CAGR_strategy > CAGR_QQQ
AND MaxDD_strategy >= MaxDD_QQQ
AND Calmar_strategy > Calmar_QQQ
```

MaxDD is negative. Otherwise `QQQ_DOMINANCE = FALSE`.

## Fixed MA200 Naming

The existing fixed MA200 experiment is named `Fixed-Rule Chronological OOS`, not parameter-selection Walk-Forward. Existing results remain preserved.

