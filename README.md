# MarketTimingQuant ETF Dynamic Allocation v1

This repository implements only the frozen protocol in
`docs/MarketTimingQuant_ETF_Dynamic_Allocation_v1_FROZEN.md`.

Current completed scope: data audit gate, Phase 0 Buy & Hold baseline, and
Phase 1 Static Allocation Efficient Frontier, and Phase 2 MA200 Simple Trend.
Phase 3 MA Parameter Stability, Phase 4 Absolute Momentum, Phase 5 Relative
Momentum, and Phase 6 Volatility Targeting are also complete.
The fixed-MA200 Fixed-Rule Chronological OOS prerequisite is complete. The
supplemental frozen specification supplies the Phase 7 constraints; Phase 7A
Fixed Four-State Machine and its metrics/tax audit are complete. Phase 7B-v1
Strict Eligibility Gate is complete, including its frozen CASH fallback for
`NO_ELIGIBLE_PARAMETER` folds.

Canonical audited Phase 7A run:
`reports/runs/20260913_phase7a_metrics_tax_audited_final`.

Canonical audited Phase 0 run:
`reports/runs/20260914_phase0_audit_final`.

Canonical audited Phase 1 run:
`reports/runs/20260914_phase1_audit_final_v2`.

Canonical audited Phase 2 run:
`reports/runs/20260914_phase2_audit_final`.

Canonical audited Phase 3 run:
`reports/runs/20260914_phase3_audit_final_v3`.

Canonical audited Phase 4 run:
`reports/runs/20260914_phase4_audit_final`.

Canonical audited Phase 5 run:
`reports/runs/20260914_phase5_audit_final`.

Canonical audited Phase 6 run:
`reports/runs/20260914_phase6_audit_final`.

```bash
python3 experiments/phase0_buy_hold.py
python3 experiments/phase1_static_frontier.py
python3 experiments/phase2_ma200.py
python3 experiments/phase3_ma_stability.py
python3 experiments/phase4_absolute_momentum.py
python3 experiments/phase5_relative_momentum.py
python3 experiments/phase6_vol_target.py
python3 experiments/walk_forward_fixed_ma200.py
python3 experiments/phase7a_fixed_state_machine.py
python3 experiments/phase7b_parameter_walk_forward.py
pytest -q
```

Raw market snapshots are immutable. Processed adjusted OHLC files and audit
outputs are reproducible from the Phase 0 command.
