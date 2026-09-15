# Phase 8D — Final Research Verdict and Deployment-Evidence Classification

## Executive verdict

Overall classification: **PROMISING_BUT_INSUFFICIENT**. The common 2013-01-02 through 2026-08-31 OOS evidence contains a credible positive-return effect for Fixed MA200 and Phase7A against QQQ in several frequencies, including accepted family-level evidence. However, drawdowns are materially deeper than QQQ, frozen economic goals are not met broadly, Phase7A has not earned its additional complexity over Fixed MA200, and numerical DSR remains DSR_NOT_IDENTIFIABLE_FROM_FROZEN_ARTIFACTS. This is research evidence, not a live deployment recommendation.
Paper decision: **PROCEED_TO_PAPER_TRADING_VALIDATION** for prospective validation only. No historical frequency is selected, no production winner is selected, and `REQUIRES_PROSPECTIVE_FREEZE_BEFORE_PAPER_TRADING` applies before any paper protocol begins.

## What the research established

- Fixed MA200 and Phase7A produce positive OOS CAGR relative to QQQ in weekly, monthly, and bimonthly configurations; quarterly is weaker.
- The accepted White Reality Check rejects the global null for the exact 16 final OOS strategy-frequency paths at block length 20, but it is a global family statement and does not identify an individually superior path.
- The fixed 20-test multiplicity family has exactly the accepted Bonferroni/Holm/BH survivors shown below.
- Phase8C confirms that implementation, start-date, tax, and frequency sensitivities are material descriptive evidence; QQQ dominance survival is zero for the primary baseline rows.

## What the research did not establish

- No primary strategy demonstrates the frozen QQQ-dominance rule because the strategy drawdowns are deeper than QQQ's -35.12% drawdown.
- No credible incremental Phase7A value over Fixed MA200 survives the matched pairwise/multiplicity/after-tax complexity audit; the added state-machine turnover is substantially higher.
- Phase7B parameter-selection Walk-Forward did not improve the research result. `NO_ELIGIBLE_PARAMETER` folds remain `CASH_FALLBACK`, and Model A/B remain context only.
- DSR is not numerically available: `DSR_NOT_IDENTIFIABLE_FROM_FROZEN_ARTIFACTS`. No SR* or DSR statistic/probability is reported here.

## Original frozen Goal A/B/C scorecard

Goal A = `cagr > qqq_cagr AND max_drawdown >= qqq_max_drawdown`; Goal B = `cagr >= qqq_cagr + 0.03 AND max_drawdown >= -0.45`; Goal C = `cagr >= 0.25 AND max_drawdown >= -0.50`. The scorecard below is the complete 16-row primary set (Fixed MA200 and Phase7A), with pre-tax and after-tax rows separate; Phase7B remains context-only in the matrix.

| strategy_id              | frequency   | tax_mode   |     cagr |   max_drawdown | Goal_A   | Goal_B   | Goal_C   | qqq_dominance   |
|:-------------------------|:------------|:-----------|---------:|---------------:|:---------|:---------|:---------|:----------------|
| FIXED_MA200_QQQ_TO_QLD   | weekly      | pre_tax    | 0.288706 |      -0.491544 | False    | False    | True     | False           |
| FIXED_MA200_QQQ_TO_QLD   | weekly      | after_tax  | 0.243365 |      -0.491544 | False    | False    | False    | False           |
| FIXED_MA200_QQQ_TO_QLD   | monthly     | pre_tax    | 0.279382 |      -0.517154 | False    | False    | False    | False           |
| FIXED_MA200_QQQ_TO_QLD   | monthly     | after_tax  | 0.234136 |      -0.527778 | False    | False    | False    | False           |
| FIXED_MA200_QQQ_TO_QLD   | bimonthly   | pre_tax    | 0.324043 |      -0.517154 | False    | False    | False    | False           |
| FIXED_MA200_QQQ_TO_QLD   | bimonthly   | after_tax  | 0.277485 |      -0.517154 | False    | False    | False    | False           |
| FIXED_MA200_QQQ_TO_QLD   | quarterly   | pre_tax    | 0.205655 |      -0.517154 | False    | False    | False    | False           |
| FIXED_MA200_QQQ_TO_QLD   | quarterly   | after_tax  | 0.169881 |      -0.540984 | False    | False    | False    | False           |
| PHASE7A_FIXED_FOUR_STATE | weekly      | pre_tax    | 0.293715 |      -0.491544 | False    | False    | True     | False           |
| PHASE7A_FIXED_FOUR_STATE | weekly      | after_tax  | 0.246349 |      -0.491544 | False    | False    | False    | False           |
| PHASE7A_FIXED_FOUR_STATE | monthly     | pre_tax    | 0.2806   |      -0.517154 | False    | False    | False    | False           |
| PHASE7A_FIXED_FOUR_STATE | monthly     | after_tax  | 0.232808 |      -0.517154 | False    | False    | False    | False           |
| PHASE7A_FIXED_FOUR_STATE | bimonthly   | pre_tax    | 0.327739 |      -0.530668 | False    | False    | False    | False           |
| PHASE7A_FIXED_FOUR_STATE | bimonthly   | after_tax  | 0.276381 |      -0.532756 | False    | False    | False    | False           |
| PHASE7A_FIXED_FOUR_STATE | quarterly   | pre_tax    | 0.199425 |      -0.556324 | False    | False    | False    | False           |
| PHASE7A_FIXED_FOUR_STATE | quarterly   | after_tax  | 0.164937 |      -0.556324 | False    | False    | False    | False           |

The QQQ benchmark reference is CAGR 19.956%, MaxDD -35.119%, and Calmar 0.5682. The separate three-condition dominance rule is not merged into Goal A.

## Fixed MA200 evidence

Fixed MA200 is classified **MODERATE** by a frozen rule: positive common-OOS return evidence plus accepted multiplicity/global-family support, but failure of QQQ risk dominance, material frequency dispersion, and non-universal robustness. MODERATE does not mean risk-dominant; deeper drawdown remains explicit.

| frequency   |   pre_tax_cagr |   after_tax_cagr |   terminal_after_tax_cagr |   max_drawdown |   after_tax_max_drawdown |   sharpe |   after_tax_sharpe |   calmar |   after_tax_calmar |   turnover |   after_tax_turnover |   trades |   after_tax_trades | nominal_pairwise_evidence                                                         | holm_adjusted_evidence                    | slippage_survival                                                   | execution_survival                                                   | start_date_survival                                              |
|:------------|---------------:|-----------------:|--------------------------:|---------------:|-------------------------:|---------:|-------------------:|---------:|-------------------:|-----------:|---------------------:|---------:|-------------------:|:----------------------------------------------------------------------------------|:------------------------------------------|:--------------------------------------------------------------------|:---------------------------------------------------------------------|:-----------------------------------------------------------------|
| weekly      |       0.288706 |         0.243365 |                  0.238634 |      -0.491544 |                -0.491544 | 0.933452 |           0.814764 | 0.587344 |           0.495104 |   1.61024  |             1.61024  |       23 |                 23 | A_FIXED_MA200_VS_QQQ; nominal primary block-20 p=0.015398; P(difference>0)=0.9780 | Holm p=0.253775; survives alpha=.05=False | slippage CAGR>QQQ survival 4 / 4; QQQ dominance 0 / 14; descriptive | execution CAGR>QQQ survival 3 / 3; QQQ dominance 0 / 14; descriptive | start CAGR>QQQ survival 6 / 6; QQQ dominance 0 / 14; descriptive |
| monthly     |       0.279382 |         0.234136 |                  0.232285 |      -0.517154 |                -0.527778 | 0.890194 |           0.778534 | 0.54023  |           0.443625 |   1.17108  |             1.17108  |       17 |                 17 | A_FIXED_MA200_VS_QQQ; nominal primary block-20 p=0.014099; P(difference>0)=0.9833 | Holm p=0.253775; survives alpha=.05=False | slippage CAGR>QQQ survival 4 / 4; QQQ dominance 0 / 14; descriptive | execution CAGR>QQQ survival 3 / 3; QQQ dominance 0 / 14; descriptive | start CAGR>QQQ survival 6 / 6; QQQ dominance 0 / 14; descriptive |
| bimonthly   |       0.324043 |         0.277485 |                  0.270501 |      -0.517154 |                -0.517154 | 0.957154 |           0.851113 | 0.626588 |           0.536562 |   0.731928 |             0.731928 |       11 |                 11 | A_FIXED_MA200_VS_QQQ; nominal primary block-20 p=0.001000; P(difference>0)=0.9988 | Holm p=0.019998; survives alpha=.05=True  | slippage CAGR>QQQ survival 4 / 4; QQQ dominance 0 / 14; descriptive | execution CAGR>QQQ survival 3 / 3; QQQ dominance 0 / 14; descriptive | start CAGR>QQQ survival 6 / 6; QQQ dominance 0 / 14; descriptive |
| quarterly   |       0.205655 |         0.169881 |                  0.169838 |      -0.517154 |                -0.540984 | 0.713082 |           0.623448 | 0.397667 |           0.314022 |   0.878313 |             0.878313 |       13 |                 13 | A_FIXED_MA200_VS_QQQ; nominal primary block-20 p=0.194481; P(difference>0)=0.8024 | Holm p=1.000000; survives alpha=.05=False | slippage CAGR>QQQ survival 4 / 4; QQQ dominance 0 / 14; descriptive | execution CAGR>QQQ survival 2 / 3; QQQ dominance 0 / 14; descriptive | start CAGR>QQQ survival 1 / 6; QQQ dominance 0 / 14; descriptive |

## Phase7A incremental-complexity verdict

The relevant comparison is Phase7A versus Fixed MA200, not Phase7A versus QQQ. The evidence is classified **NOT_JUSTIFIED**: all four nominal incremental p-values are above .05, none survives Holm or BH in the confirmatory 20-test family, after-tax increments are mixed/small, and turnover/cost/tax burdens rise materially. Phase8C's accepted 14-scenario counts remain descriptive matched-comparison evidence only.

| frequency   |   baseline_pre_tax_cagr_difference |   baseline_after_tax_cagr_difference |   baseline_terminal_after_tax_cagr_difference |   baseline_max_drawdown_difference |   baseline_sharpe_difference |   baseline_calmar_difference |   baseline_turnover_difference |   baseline_transaction_cost_difference |   nominal_primary_p_value |   holm_p_value |   bh_q_value |   phase8c_positive_cagr_count |   phase8c_positive_sharpe_count |   phase8c_positive_calmar_count |   phase8c_positive_terminal_after_tax_cagr_count | complexity_classification   |
|:------------|-----------------------------------:|-------------------------------------:|----------------------------------------------:|-----------------------------------:|-----------------------------:|-----------------------------:|-------------------------------:|---------------------------------------:|--------------------------:|---------------:|-------------:|------------------------------:|--------------------------------:|--------------------------------:|-------------------------------------------------:|:----------------------------|
| weekly      |                         0.00500939 |                           0.00298376 |                                   0.00297241  |                        1.11022e-16 |                 -0.000448258 |                   0.0101911  |                       2.62258  |                               11474.8  |                  0.153685 |              1 |     0.307369 |                            13 |                               3 |                              13 |                                               10 | NOT_JUSTIFIED               |
| monthly     |                         0.0012172  |                          -0.00132784 |                                  -0.00132585  |                        0           |                 -0.0106248   |                   0.00235365 |                       1.51713  |                                6383.04 |                  0.289971 |              1 |     0.414244 |                             8 |                               0 |                               8 |                                                2 | NOT_JUSTIFIED               |
| bimonthly   |                         0.00369667 |                          -0.00110462 |                                   0.000298424 |                       -0.0135138   |                 -0.00732708  |                  -0.00899034 |                       0.927291 |                                5838.3  |                  0.189781 |              1 |     0.316276 |                            10 |                               0 |                               0 |                                                5 | NOT_JUSTIFIED               |
| quarterly   |                        -0.00623021 |                          -0.00494382 |                                  -0.00494364  |                       -0.0391698   |                 -0.0305986   |                  -0.0391979  |                       0.696964 |                                2322.56 |                  0.474553 |              1 |     0.632737 |                             0 |                               0 |                               0 |                                                0 | NOT_JUSTIFIED               |

## Phase7B verdict

Phase7B is classified **NO_DEMONSTRATED_VALUE**. The accepted report preserves `NO_ELIGIBLE_PARAMETER` folds and `CASH_FALLBACK`; there is no relaxation of constraints and no test-fold leakage into selection. Model A and Model B are shown in the matrix as context-only accepted stitched OOS paths. A conditional BH survivor does not overturn the full complexity evidence.

## Statistical evidence hierarchy

- Nominal pairwise evidence is taken only from Phase8B-1's primary block-20 annualized mean-return rows. Bonferroni survivors: `A_FIXED_MA200_VS_QQQ__bimonthly, B_PHASE7A_VS_QQQ__bimonthly`. Holm survivors: `A_FIXED_MA200_VS_QQQ__bimonthly, B_PHASE7A_VS_QQQ__bimonthly`. BH q<.05 survivors: `A_FIXED_MA200_VS_QQQ__bimonthly, A_FIXED_MA200_VS_QQQ__monthly, A_FIXED_MA200_VS_QQQ__weekly, B_PHASE7A_VS_QQQ__bimonthly, B_PHASE7A_VS_QQQ__monthly, B_PHASE7A_VS_QQQ__weekly, E_PHASE7B_MODEL_B_VS_MODEL_A__bimonthly`; BH controls FDR, not FWER.
- White Reality Check: `FINAL_OOS_PATH_FAMILY_WHITE_REALITY_CHECK`, candidate_count=16, exact final path family, primary block-20 p=0.010299. Candidate max-statistic path is `PHASE7A_FIXED_FOUR_STATE__bimonthly`; this is global and does not prove individual superiority or include all 4,164 historical trials.
- Deflated Sharpe boundary is exactly `DSR_NOT_IDENTIFIABLE_FROM_FROZEN_ARTIFACTS`. A future numerical DSR would require a prospectively designed comparable trial universe; Phase8D does not retrofit Phase1–7 historical trials.

## Robustness evidence

All four frequencies remain visible and no frequency is selected. The accepted Phase8C robustness summary below is descriptive and is not collapsed into a score.

| strategy_id              | frequency   | positive_cagr_vs_qqq_slippage   | positive_cagr_vs_qqq_execution   | positive_cagr_vs_qqq_start_date   | qqq_dominance_survival   | phase7a_positive_incremental_cagr   | phase7a_positive_terminal_after_tax_cagr   |
|:-------------------------|:------------|:--------------------------------|:---------------------------------|:----------------------------------|:-------------------------|:------------------------------------|:-------------------------------------------|
| FIXED_MA200_QQQ_TO_QLD   | weekly      | 4 / 4                           | 3 / 3                            | 6 / 6                             | 0 / 14                   | 13 / 14                             | 10 / 14                                    |
| FIXED_MA200_QQQ_TO_QLD   | monthly     | 4 / 4                           | 3 / 3                            | 6 / 6                             | 0 / 14                   | 8 / 14                              | 2 / 14                                     |
| FIXED_MA200_QQQ_TO_QLD   | bimonthly   | 4 / 4                           | 3 / 3                            | 6 / 6                             | 0 / 14                   | 10 / 14                             | 5 / 14                                     |
| FIXED_MA200_QQQ_TO_QLD   | quarterly   | 4 / 4                           | 2 / 3                            | 1 / 6                             | 0 / 14                   | 0 / 14                              | 0 / 14                                     |
| PHASE7A_FIXED_FOUR_STATE | weekly      | 4 / 4                           | 3 / 3                            | 6 / 6                             | 0 / 14                   | 13 / 14                             | 10 / 14                                    |
| PHASE7A_FIXED_FOUR_STATE | monthly     | 4 / 4                           | 3 / 3                            | 6 / 6                             | 0 / 14                   | 8 / 14                              | 2 / 14                                     |
| PHASE7A_FIXED_FOUR_STATE | bimonthly   | 4 / 4                           | 3 / 3                            | 6 / 6                             | 0 / 14                   | 10 / 14                             | 5 / 14                                     |
| PHASE7A_FIXED_FOUR_STATE | quarterly   | 1 / 4                           | 1 / 3                            | 0 / 6                             | 0 / 14                   | 0 / 14                              | 0 / 14                                     |

| strategy_id              | tax_mode   |   cagr_min |   cagr_max |   cagr_range |   max_drawdown_abs_range |   calmar_range |   sharpe_range |   turnover_range | frequency_selection_performed   | descriptive_only   |
|:-------------------------|:-----------|-----------:|-----------:|-------------:|-------------------------:|---------------:|---------------:|-----------------:|:--------------------------------|:-------------------|
| FIXED_MA200_QQQ_TO_QLD   | pre_tax    |   0.205655 |  0.324043  |    0.118387  |                0.02561   |      0.228921  |       0.244072 |         0.878313 | False                           | True               |
| FIXED_MA200_QQQ_TO_QLD   | after_tax  |   0.169881 |  0.277485  |    0.107605  |                0.0494398 |      0.22254   |       0.227665 |         0.878313 | False                           | True               |
| PHASE7A_FIXED_FOUR_STATE | pre_tax    |   0.199425 |  0.327739  |    0.128314  |                0.0647798 |      0.259128  |       0.267344 |         2.65755  | False                           | True               |
| PHASE7A_FIXED_FOUR_STATE | after_tax  |   0.164937 |  0.276381  |    0.111444  |                0.0647798 |      0.222299  |       0.239479 |         2.66646  | False                           | True               |
| PHASE7B_MODEL_A_SELECTED | pre_tax    |   0        |  0.0424376 |    0.0424376 |                0.491544  |      0         |       0        |         1.09791  | False                           | True               |
| PHASE7B_MODEL_A_SELECTED | after_tax  |   0        |  0.0354313 |    0.0354313 |                0.491544  |      0         |       0        |         1.09791  | False                           | True               |
| PHASE7B_MODEL_B_SELECTED | pre_tax    |   0        |  0.100262  |    0.100262  |                0.530668  |      0.0841213 |       0.157332 |         3.6428   | False                           | True               |
| PHASE7B_MODEL_B_SELECTED | after_tax  |   0        |  0.0841732 |    0.0841732 |                0.530668  |      0.072866  |       0.137785 |         3.64381  | False                           | True               |

## Tax and economic implementation implications

Primary after-tax wealth is wealth after realized tax paid to date. Terminal liquidation wealth/CAGR/tax/cost/unrealized-gain diagnostics are non-mutating and are not execution trades, turnover, or holding-period observations. Taxes materially drag CAGR and can change relative ordering; turnover is measured under the accepted contemporaneous open-before-trade denominator. Phase8D does not change any of these paths or definitions.

## Research limitations

The common OOS sample is finite, frequency dispersion is material, the White RC is global, BH is FDR rather than FWER, Phase7A complexity lacks incremental evidence, Phase7B has many cash-fallback folds, and DSR is non-identifiable. These limitations prevent a live-capital conclusion. No new p-value, p-value family, optimization, parameter selection, path, or model is introduced.

## Final evidence classification

**PROMISING_BUT_INSUFFICIENT** — credible OOS/statistical/robustness evidence exists, but the frozen drawdown objectives, QQQ dominance, complexity, and DSR limitations remain unresolved.

## Paper-trading decision

**PROCEED_TO_PAPER_TRADING_VALIDATION**. This means a future prospective, no-capital validation may be designed after an explicit freeze. It does not authorize real-money deployment and does not choose weekly, monthly, bimonthly, or quarterly.

## Conditions required before live deployment

Before any future live decision, prospectively freeze and monitor realized slippage; signal-to-fill timing; tracking difference; tax/accounting behavior; live turnover; operational failures; divergence from backtest; future drawdown; and future return differential versus QQQ. Do not invent historical thresholds. Any required numerical thresholds are `REQUIRES_PROSPECTIVE_FREEZE_BEFORE_PAPER_TRADING`.

## Governance boundary

The simplicity principle prefers the Fixed model family over Phase7A for future validation because added complexity did not earn credible incremental OOS/statistical/after-tax robustness. This is a model-family governance decision, not a live frequency selection. Research development stops here; no Phase9 is started.

PHASE 8D FINAL RESEARCH VERDICT COMPLETE — RESEARCH DEVELOPMENT FROZEN
