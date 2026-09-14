# Phase 8A — OOS Evidence Consolidation

This is a descriptive consolidation of already-audited strategies on one common chronological OOS calendar. No new strategy, parameter optimization, parameter selection, or statistical inference was performed. Phase 8B is not started.

## Scope and source runs

Common OOS period: **2013-01-02 through 2026-08-31**. Initial capital is **$100,000**. The canonical source run IDs are `phase7a=20260913_phase7a_metrics_tax_audited_final`, `phase7b=20260914_phase7b_turnover_audit_final`, and `fixed_ma200=20260914_oos_fixed_ma200_audit_final`. Exact artifact hashes are in `canonical_source_manifest.csv`.

The two buy-and-hold benchmark rows use `frequency=none`. Fixed MA200, Phase 7A, and both Phase 7B models retain all four frozen frequencies. No frequency or strategy was removed, ranked as a winner, or designated for production.

## Accounting and metric conventions

The table copies canonical metric rows and preserves close decision → next eligible open execution, 5 bps slippage, zero commission, zero CASH return, continuous ledgers, simplified Japanese capital-gains tax at 20.315%, contemporaneous-open pretrade-equity turnover, initial deployment exclusion, report-only terminal liquidation, and completed risky-position holding episodes. No metric definition is changed here.

`realized_tax_paid` preserves each source row's tax-mode-specific `tax_paid` value (zero on pre-tax and tax-neutral benchmark rows). `after_tax_CAGR_tax_paid_to_date`, terminal wealth, and terminal CAGR are copied from the source after-tax diagnostic row and repeated on the matching pre-tax row for apples-to-apples display.

## Consolidated OOS rows

`oos_champion_table.csv` contains **34 rows**: 2 benchmark rows plus 4 frequencies × 2 tax modes for each of Fixed MA200, Phase 7A, Phase 7B Model A, and Phase 7B Model B. Each row is dated 2013-01-02–2026-08-31.

| strategy_id              | frequency   | tax_mode   |      cagr |   max_drawdown |      calmar |   annual_turnover |   number_of_trades | qqq_dominance   |
|:-------------------------|:------------|:-----------|----------:|---------------:|------------:|------------------:|-------------------:|:----------------|
| QQQ_BUY_HOLD             | none        | benchmark  | 0.199559  |      -0.351187 |   0.56824   |          0        |                  1 | False           |
| QLD_BUY_HOLD             | none        | benchmark  | 0.334038  |      -0.636845 |   0.524519  |          0        |                  1 | False           |
| FIXED_MA200_QQQ_TO_QLD   | weekly      | pre_tax    | 0.288706  |      -0.491544 |   0.587344  |          1.61024  |                 23 | False           |
| FIXED_MA200_QQQ_TO_QLD   | weekly      | after_tax  | 0.243365  |      -0.491544 |   0.495104  |          1.61024  |                 23 | False           |
| FIXED_MA200_QQQ_TO_QLD   | monthly     | pre_tax    | 0.279382  |      -0.517154 |   0.54023   |          1.17108  |                 17 | False           |
| FIXED_MA200_QQQ_TO_QLD   | monthly     | after_tax  | 0.234136  |      -0.527778 |   0.443625  |          1.17108  |                 17 | False           |
| FIXED_MA200_QQQ_TO_QLD   | bimonthly   | pre_tax    | 0.324043  |      -0.517154 |   0.626588  |          0.731928 |                 11 | False           |
| FIXED_MA200_QQQ_TO_QLD   | bimonthly   | after_tax  | 0.277485  |      -0.517154 |   0.536562  |          0.731928 |                 11 | False           |
| FIXED_MA200_QQQ_TO_QLD   | quarterly   | pre_tax    | 0.205655  |      -0.517154 |   0.397667  |          0.878313 |                 13 | False           |
| FIXED_MA200_QQQ_TO_QLD   | quarterly   | after_tax  | 0.169881  |      -0.540984 |   0.314022  |          0.878313 |                 13 | False           |
| PHASE7A_FIXED_FOUR_STATE | weekly      | pre_tax    | 0.293715  |      -0.491544 |   0.597535  |          4.23283  |                715 | False           |
| PHASE7A_FIXED_FOUR_STATE | weekly      | after_tax  | 0.246349  |      -0.491544 |   0.501174  |          4.23815  |                715 | False           |
| PHASE7A_FIXED_FOUR_STATE | monthly     | pre_tax    | 0.2806    |      -0.517154 |   0.542584  |          2.68821  |                211 | False           |
| PHASE7A_FIXED_FOUR_STATE | monthly     | after_tax  | 0.232808  |      -0.517154 |   0.450171  |          2.68828  |                211 | False           |
| PHASE7A_FIXED_FOUR_STATE | bimonthly   | pre_tax    | 0.327739  |      -0.530668 |   0.617598  |          1.65922  |                107 | False           |
| PHASE7A_FIXED_FOUR_STATE | bimonthly   | after_tax  | 0.276381  |      -0.532756 |   0.518776  |          1.65912  |                107 | False           |
| PHASE7A_FIXED_FOUR_STATE | quarterly   | pre_tax    | 0.199425  |      -0.556324 |   0.358469  |          1.57528  |                 87 | False           |
| PHASE7A_FIXED_FOUR_STATE | quarterly   | after_tax  | 0.164937  |      -0.556324 |   0.296476  |          1.57168  |                 87 | False           |
| PHASE7B_MODEL_A_SELECTED | weekly      | pre_tax    | 0.0424376 |      -0.491544 |   0.0863352 |          1.09791  |                 16 | False           |
| PHASE7B_MODEL_A_SELECTED | weekly      | after_tax  | 0.0354313 |      -0.491544 |   0.0720815 |          1.09791  |                 16 | False           |
| PHASE7B_MODEL_A_SELECTED | monthly     | pre_tax    | 0         |       0        | nan         |          0        |                  0 | False           |
| PHASE7B_MODEL_A_SELECTED | monthly     | after_tax  | 0         |       0        | nan         |          0        |                  0 | False           |
| PHASE7B_MODEL_A_SELECTED | bimonthly   | pre_tax    | 0         |       0        | nan         |          0        |                  0 | False           |
| PHASE7B_MODEL_A_SELECTED | bimonthly   | after_tax  | 0         |       0        | nan         |          0        |                  0 | False           |
| PHASE7B_MODEL_A_SELECTED | quarterly   | pre_tax    | 0         |       0        | nan         |          0        |                  0 | False           |
| PHASE7B_MODEL_A_SELECTED | quarterly   | after_tax  | 0         |       0        | nan         |          0        |                  0 | False           |
| PHASE7B_MODEL_B_SELECTED | weekly      | pre_tax    | 0.0665677 |      -0.491544 |   0.135426  |          3.6428   |                294 | False           |
| PHASE7B_MODEL_B_SELECTED | weekly      | after_tax  | 0.0552639 |      -0.491544 |   0.112429  |          3.64381  |                294 | False           |
| PHASE7B_MODEL_B_SELECTED | monthly     | pre_tax    | 0.054205  |      -0.517154 |   0.104814  |          1.37036  |                 84 | False           |
| PHASE7B_MODEL_B_SELECTED | monthly     | after_tax  | 0.0443467 |      -0.517154 |   0.0857514 |          1.36957  |                 84 | False           |
| PHASE7B_MODEL_B_SELECTED | bimonthly   | pre_tax    | 0.100262  |      -0.530668 |   0.188935  |          0.779949 |                 45 | False           |
| PHASE7B_MODEL_B_SELECTED | bimonthly   | after_tax  | 0.0841732 |      -0.530668 |   0.158617  |          0.780069 |                 45 | False           |
| PHASE7B_MODEL_B_SELECTED | quarterly   | pre_tax    | 0         |       0        | nan         |          0        |                  0 | False           |
| PHASE7B_MODEL_B_SELECTED | quarterly   | after_tax  | 0         |       0        | nan         |          0        |                  0 | False           |

## Benchmark-relative evidence

Every relative column uses the one QQQ buy-and-hold row on the exact same OOS calendar. `qqq_dominance` is the frozen boolean: strategy CAGR > QQQ CAGR AND strategy MaxDD >= QQQ MaxDD AND strategy Calmar > QQQ Calmar. This is evidence only and is not a production-selection rule.

## Complexity comparisons

`complexity_comparison.csv` preserves Phase 7B Model B minus Model A and Phase 7A fixed four-state minus Fixed MA200, by frequency. These are descriptive differences across the frozen experimental dimensions; no significance test or single-metric ranking is performed.

| comparison                                 | right_strategy_id        | left_strategy_id         | frequency   |   pre_tax_cagr_difference |   pre_tax_max_drawdown_difference |   pre_tax_calmar_difference |   pre_tax_sharpe_difference |   pre_tax_sortino_difference |   pre_tax_turnover_difference |   after_tax_cagr_difference |   after_tax_terminal_cagr_difference |   after_tax_realized_tax_difference | descriptive_only   |
|:-------------------------------------------|:-------------------------|:-------------------------|:------------|--------------------------:|----------------------------------:|----------------------------:|----------------------------:|-----------------------------:|------------------------------:|----------------------------:|-------------------------------------:|------------------------------------:|:-------------------|
| PHASE7B_MODEL_B_MINUS_MODEL_A              | PHASE7B_MODEL_B_SELECTED | PHASE7B_MODEL_A_SELECTED | weekly      |                0.0241302  |                       0           |                  0.0490906  |                 0.0858446   |                   0.100932   |                      2.54489  |                  0.0198326  |                          0.0198326   |                            12134.7  | True               |
| PHASE7B_MODEL_B_MINUS_MODEL_A              | PHASE7B_MODEL_B_SELECTED | PHASE7B_MODEL_A_SELECTED | monthly     |                0.054205   |                      -0.517154    |                nan          |               nan           |                 nan          |                      1.37036  |                  0.0443467  |                          0.0443467   |                            20620.9  | True               |
| PHASE7B_MODEL_B_MINUS_MODEL_A              | PHASE7B_MODEL_B_SELECTED | PHASE7B_MODEL_A_SELECTED | bimonthly   |                0.100262   |                      -0.530668    |                nan          |               nan           |                 nan          |                      0.779949 |                  0.0841732  |                          0.0841732   |                            51393.7  | True               |
| PHASE7B_MODEL_B_MINUS_MODEL_A              | PHASE7B_MODEL_B_SELECTED | PHASE7B_MODEL_A_SELECTED | quarterly   |                0          |                       0           |                nan          |               nan           |                 nan          |                      0        |                  0          |                          0           |                                0    | True               |
| PHASE7A_FIXED_FOUR_STATE_MINUS_FIXED_MA200 | PHASE7A_FIXED_FOUR_STATE | FIXED_MA200_QQQ_TO_QLD   | weekly      |                0.00500939 |                       1.11022e-16 |                  0.0101911  |                -0.000448258 |                  -0.00172781 |                      2.62258  |                  0.00298376 |                          0.00297241  |                            12505.7  | True               |
| PHASE7A_FIXED_FOUR_STATE_MINUS_FIXED_MA200 | PHASE7A_FIXED_FOUR_STATE | FIXED_MA200_QQQ_TO_QLD   | monthly     |                0.0012172  |                       0           |                  0.00235365 |                -0.0106248   |                  -0.0141827  |                      1.51713  |                 -0.00132784 |                         -0.00132585  |                            -5941.38 | True               |
| PHASE7A_FIXED_FOUR_STATE_MINUS_FIXED_MA200 | PHASE7A_FIXED_FOUR_STATE | FIXED_MA200_QQQ_TO_QLD   | bimonthly   |                0.00369667 |                      -0.0135138   |                 -0.00899034 |                -0.00732708  |                  -0.00917422 |                      0.927291 |                 -0.00110462 |                          0.000298424 |                            43909.1  | True               |
| PHASE7A_FIXED_FOUR_STATE_MINUS_FIXED_MA200 | PHASE7A_FIXED_FOUR_STATE | FIXED_MA200_QQQ_TO_QLD   | quarterly   |               -0.00623021 |                      -0.0391698   |                 -0.0391979  |                -0.0305986   |                  -0.0431593  |                      0.696964 |                 -0.00494382 |                         -0.00494364  |                           -12858.2  | True               |

## Daily alignment for the next phase

`aligned_daily_equity.csv` and `aligned_daily_returns.csv` contain 116824 rows each with identity keys and the exact 3436 common OOS sessions. Strategy curves are copied from accepted Phase 7A, Phase 7B, and Fixed-MA200 OOS artifacts. The two benchmark curves are the daily expansion of the accepted Phase 7B benchmark method on the immutable processed price snapshot; the consolidated benchmark metrics remain copied from the accepted Phase 7B metric artifact.

No prior-phase source or canonical artifact was written by Phase 8A. No strategy winner, production recommendation, or Phase 8B statistical claim is made.

PHASE 8A EVIDENCE CONSOLIDATION COMPLETE — NO NEW STRATEGY OR PARAMETER SELECTION PERFORMED
