# Phase 8B-2 — Multiple Testing and Data-Snooping Audit

This downstream audit consumes the accepted Phase 8B-1 remediated candidate and the immutable Phase 8A aligned daily-return snapshot. It changes no strategy, signal, execution, accounting, tax, OOS, bootstrap, pairwise, or prior-phase artifact.

## Frozen inputs and scope

The common OOS calendar is **2013-01-02 through 2026-08-31**, exactly **3,436** accepted sessions. Phase 8A source run: `20260914_phase8a_oos_evidence_consolidation_final`. Phase 8B-1 source run: `20260914_phase8b1_null_test_remediation_candidate`. All source hashes are recorded in `phase8b2_configuration.json` and were verified before this audit output was created.

Phase 8B-2 performs no model or frequency selection. It enumerates the frozen research history, adjusts the already-issued 20 primary Phase 8B-1 mean-return p-values, reports DSR paths without filtering, and applies a frozen White Reality Check candidate set.

## Research-trial inventory

Categories A–I explicitly enumerate static allocation, MA, momentum, relative-momentum, volatility-target, fixed-state, walk-forward Model A/Model B candidate, and rebalance-frequency dimensions. The inventory includes every listed grid unit and every Phase 7B candidate/frequency/fold; no poor result is removed. Tax-mode rows are reported separately as accounting views and are not counted as independent return hypotheses.

| inventory_id                          | phase     | category   | model_family                    |   economic_trial_count |   result_rows_including_tax_modes | results_used_for_selection   | strict_selection_included   | conservative_count_included   |
|:--------------------------------------|:----------|:-----------|:--------------------------------|-----------------------:|----------------------------------:|:-----------------------------|:----------------------------|:------------------------------|
| A1_PHASE1_PAIR_ALLOCATIONS            | Phase 1   | A          | static_pair_allocation          |                    336 |                               672 | False                        | False                       | True                          |
| A2_PHASE1_TRIPLE_ALLOCATIONS          | Phase 1   | A          | static_triple_allocation        |                    660 |                              1320 | False                        | False                       | True                          |
| B1_PHASE2_MA200_FIXED                 | Phase 2   | B          | fixed_ma200                     |                     12 |                                24 | False                        | False                       | True                          |
| B2_PHASE3_MA_STABILITY                | Phase 3   | B          | ma_parameter_stability          |                     60 |                               120 | False                        | False                       | True                          |
| C_PHASE4_ABSOLUTE_MOMENTUM            | Phase 4   | C          | absolute_momentum               |                     24 |                                48 | False                        | False                       | True                          |
| D_PHASE5_RELATIVE_MOMENTUM            | Phase 5   | D          | relative_momentum               |                     24 |                                48 | False                        | False                       | True                          |
| E_PHASE6_VOLATILITY_TARGETING         | Phase 6   | E          | volatility_targeting            |                    240 |                               480 | False                        | False                       | True                          |
| F_PHASE7A_FIXED_FOUR_STATE            | Phase 7A  | F          | fixed_four_state                |                      8 |                                16 | False                        | False                       | True                          |
| G_PHASE7B_MODEL_A_TRAINING_CANDIDATES | Phase 7B  | G          | model_a_walk_forward_candidates |                    280 |                               280 | True                         | True                        | True                          |
| H_PHASE7B_MODEL_B_TRAINING_CANDIDATES | Phase 7B  | H          | model_b_walk_forward_candidates |                   2520 |                              2520 | True                         | True                        | True                          |
| I_REBALANCE_FREQUENCY_DIMENSION       | Phase 1–7 | I          | rebalance_frequency_variants    |                      0 |                                 0 | True                         | False                       | False                         |

Strict selection trials = **2,800** (only candidates that could directly affect a selected Phase 7B OOS parameter). Conservative research trials = **4,164**. The corresponding source result rows including tax/accounting views total **5,528**.

## Multiple-testing adjustment

The confirmatory family is exactly **20** rows: the five frozen Phase 8B-1 comparisons at four frequencies, primary block length 20, metric `annualized_mean_return_difference`. Raw p-values are retained. Bonferroni, Holm step-down, and Benjamini–Hochberg q-values are computed across all 20 rows with no post-hoc filtering. A separate four-row-per-comparison-family sensitivity is labeled secondary and does not replace the confirmatory family.

| test_id                                   | comparison_id                  | strategy_frequency   |   raw_p_value |   bonferroni_p_value |   holm_p_value |   benjamini_hochberg_q_value |
|:------------------------------------------|:-------------------------------|:---------------------|--------------:|---------------------:|---------------:|-----------------------------:|
| A_FIXED_MA200_VS_QQQ__bimonthly           | A_FIXED_MA200_VS_QQQ           | bimonthly            |    0.0009999  |            0.019998  |      0.019998  |                    0.0129987 |
| A_FIXED_MA200_VS_QQQ__monthly             | A_FIXED_MA200_VS_QQQ           | monthly              |    0.0140986  |            0.281972  |      0.253775  |                    0.0439956 |
| A_FIXED_MA200_VS_QQQ__quarterly           | A_FIXED_MA200_VS_QQQ           | quarterly            |    0.194481   |            1         |      1         |                    0.316276  |
| A_FIXED_MA200_VS_QQQ__weekly              | A_FIXED_MA200_VS_QQQ           | weekly               |    0.0153985  |            0.307969  |      0.253775  |                    0.0439956 |
| B_PHASE7A_VS_QQQ__bimonthly               | B_PHASE7A_VS_QQQ               | bimonthly            |    0.00129987 |            0.0259974 |      0.0246975 |                    0.0129987 |
| B_PHASE7A_VS_QQQ__monthly                 | B_PHASE7A_VS_QQQ               | monthly              |    0.0146985  |            0.293971  |      0.253775  |                    0.0439956 |
| B_PHASE7A_VS_QQQ__quarterly               | B_PHASE7A_VS_QQQ               | quarterly            |    0.205579   |            1         |      1         |                    0.316276  |
| B_PHASE7A_VS_QQQ__weekly                  | B_PHASE7A_VS_QQQ               | weekly               |    0.0141986  |            0.283972  |      0.253775  |                    0.0439956 |
| C_PHASE7A_INCREMENTAL_VS_FIXED__bimonthly | C_PHASE7A_INCREMENTAL_VS_FIXED | bimonthly            |    0.189781   |            1         |      1         |                    0.316276  |
| C_PHASE7A_INCREMENTAL_VS_FIXED__monthly   | C_PHASE7A_INCREMENTAL_VS_FIXED | monthly              |    0.289971   |            1         |      1         |                    0.414244  |
| C_PHASE7A_INCREMENTAL_VS_FIXED__quarterly | C_PHASE7A_INCREMENTAL_VS_FIXED | quarterly            |    0.474553   |            1         |      1         |                    0.632737  |
| C_PHASE7A_INCREMENTAL_VS_FIXED__weekly    | C_PHASE7A_INCREMENTAL_VS_FIXED | weekly               |    0.153685   |            1         |      1         |                    0.307369  |
| D_PHASE7B_MODEL_A_VS_FIXED__bimonthly     | D_PHASE7B_MODEL_A_VS_FIXED     | bimonthly            |    1          |            1         |      1         |                    1         |
| D_PHASE7B_MODEL_A_VS_FIXED__monthly       | D_PHASE7B_MODEL_A_VS_FIXED     | monthly              |    1          |            1         |      1         |                    1         |
| D_PHASE7B_MODEL_A_VS_FIXED__quarterly     | D_PHASE7B_MODEL_A_VS_FIXED     | quarterly            |    0.9996     |            1         |      1         |                    1         |
| D_PHASE7B_MODEL_A_VS_FIXED__weekly        | D_PHASE7B_MODEL_A_VS_FIXED     | weekly               |    1          |            1         |      1         |                    1         |
| E_PHASE7B_MODEL_B_VS_MODEL_A__bimonthly   | E_PHASE7B_MODEL_B_VS_MODEL_A   | bimonthly            |    0.0152985  |            0.305969  |      0.253775  |                    0.0439956 |
| E_PHASE7B_MODEL_B_VS_MODEL_A__monthly     | E_PHASE7B_MODEL_B_VS_MODEL_A   | monthly              |    0.0584942  |            1         |      0.760424  |                    0.146235  |
| E_PHASE7B_MODEL_B_VS_MODEL_A__quarterly   | E_PHASE7B_MODEL_B_VS_MODEL_A   | quarterly            |    1          |            1         |      1         |                    1         |
| E_PHASE7B_MODEL_B_VS_MODEL_A__weekly      | E_PHASE7B_MODEL_B_VS_MODEL_A   | weekly               |    0.127087   |            1         |      1         |                    0.282416  |

## Deflated Sharpe Ratio

DSR is reported for the QQQ reference and every accepted pre-tax OOS strategy path: Fixed MA200, Phase 7A, Phase 7B Model A, and Phase 7B Model B at weekly, monthly, bimonthly, and quarterly frequencies. No path is selected because of its DSR. Daily skewness and excess kurtosis are calculated from the exact aligned OOS vectors; no benchmark, frequency, or path is omitted.

The published approximation uses sigma_SR = sqrt((1 − S·skew + ((excess kurtosis + 2)/4)·S²)/(T−1)), the Euler-constant expected maximum over N trials, and Phi((S − expected maximum)/sigma_SR). Primary N is each raw frozen inventory count. A participation-ratio estimate from the 17 visible path correlation eigenvalues is reported only as a transparent effective-trial sensitivity; it does not retroactively shrink the research ledger.

Estimated effective path count (sensitivity) = **2.520344**.

| path_id                             | trial_count_basis            |   observed_sharpe |   skewness |   excess_kurtosis |   trial_count_raw |   effective_trial_count_used |   expected_max_sharpe |   dsr_probability |   correlation_adjusted_dsr_probability |
|:------------------------------------|:-----------------------------|------------------:|-----------:|------------------:|------------------:|-----------------------------:|----------------------:|------------------:|---------------------------------------:|
| QQQ_BUY_HOLD__none                  | strict_selection_trials      |          0.97898  |  -0.204736 |           7.8376  |              2800 |                         2800 |             0.113835  |       1           |                               1        |
| QQQ_BUY_HOLD__none                  | conservative_research_trials |          0.97898  |  -0.204736 |           7.8376  |              4164 |                         4164 |             0.117168  |       1           |                               1        |
| FIXED_MA200_QQQ_TO_QLD__weekly      | strict_selection_trials      |          0.933452 |  -0.860124 |          10.3431  |              2800 |                         2800 |             0.12791   |       1           |                               1        |
| FIXED_MA200_QQQ_TO_QLD__weekly      | conservative_research_trials |          0.933452 |  -0.860124 |          10.3431  |              4164 |                         4164 |             0.131655  |       1           |                               1        |
| FIXED_MA200_QQQ_TO_QLD__monthly     | strict_selection_trials      |          0.890194 |  -0.658138 |          11.4086  |              2800 |                         2800 |             0.124309  |       1           |                               1        |
| FIXED_MA200_QQQ_TO_QLD__monthly     | conservative_research_trials |          0.890194 |  -0.658138 |          11.4086  |              4164 |                         4164 |             0.127949  |       1           |                               1        |
| FIXED_MA200_QQQ_TO_QLD__bimonthly   | strict_selection_trials      |          0.957154 |  -0.300611 |          13.055   |              2800 |                         2800 |             0.131342  |       1           |                               1        |
| FIXED_MA200_QQQ_TO_QLD__bimonthly   | conservative_research_trials |          0.957154 |  -0.300611 |          13.055   |              4164 |                         4164 |             0.135187  |       1           |                               1        |
| FIXED_MA200_QQQ_TO_QLD__quarterly   | strict_selection_trials      |          0.713082 |  -0.574415 |          11.1239  |              2800 |                         2800 |             0.105885  |       1           |                               1        |
| FIXED_MA200_QQQ_TO_QLD__quarterly   | conservative_research_trials |          0.713082 |  -0.574415 |          11.1239  |              4164 |                         4164 |             0.108985  |       1           |                               1        |
| PHASE7A_FIXED_FOUR_STATE__weekly    | strict_selection_trials      |          0.933004 |  -0.886392 |           9.77215 |              2800 |                         2800 |             0.126439  |       1           |                               1        |
| PHASE7A_FIXED_FOUR_STATE__weekly    | conservative_research_trials |          0.933004 |  -0.886392 |           9.77215 |              4164 |                         4164 |             0.130141  |       1           |                               1        |
| PHASE7A_FIXED_FOUR_STATE__monthly   | strict_selection_trials      |          0.879569 |  -0.681114 |          10.5408  |              2800 |                         2800 |             0.121078  |       1           |                               1        |
| PHASE7A_FIXED_FOUR_STATE__monthly   | conservative_research_trials |          0.879569 |  -0.681114 |          10.5408  |              4164 |                         4164 |             0.124623  |       1           |                               1        |
| PHASE7A_FIXED_FOUR_STATE__bimonthly | strict_selection_trials      |          0.949827 |  -0.338893 |          11.9911  |              2800 |                         2800 |             0.127709  |       1           |                               1        |
| PHASE7A_FIXED_FOUR_STATE__bimonthly | conservative_research_trials |          0.949827 |  -0.338893 |          11.9911  |              4164 |                         4164 |             0.131448  |       1           |                               1        |
| PHASE7A_FIXED_FOUR_STATE__quarterly | strict_selection_trials      |          0.682483 |  -0.628342 |          12.0243  |              2800 |                         2800 |             0.105608  |       1           |                               1        |
| PHASE7A_FIXED_FOUR_STATE__quarterly | conservative_research_trials |          0.682483 |  -0.628342 |          12.0243  |              4164 |                         4164 |             0.108701  |       1           |                               1        |
| PHASE7B_MODEL_A_SELECTED__weekly    | strict_selection_trials      |          0.298671 |  -1.98008  |          45.4174  |              2800 |                         2800 |             0.0982272 |       1           |                               1        |
| PHASE7B_MODEL_A_SELECTED__weekly    | conservative_research_trials |          0.298671 |  -1.98008  |          45.4174  |              4164 |                         4164 |             0.101103  |       1           |                               1        |
| PHASE7B_MODEL_A_SELECTED__monthly   | strict_selection_trials      |          0        |   0        |           0       |              2800 |                         2800 |             0.0603536 |       0.000202155 |                               0.236078 |
| PHASE7B_MODEL_A_SELECTED__monthly   | conservative_research_trials |          0        |   0        |           0       |              4164 |                         4164 |             0.0621207 |       0.000135882 |                               0.236078 |
| PHASE7B_MODEL_A_SELECTED__bimonthly | strict_selection_trials      |          0        |   0        |           0       |              2800 |                         2800 |             0.0603536 |       0.000202155 |                               0.236078 |
| PHASE7B_MODEL_A_SELECTED__bimonthly | conservative_research_trials |          0        |   0        |           0       |              4164 |                         4164 |             0.0621207 |       0.000135882 |                               0.236078 |
| PHASE7B_MODEL_A_SELECTED__quarterly | strict_selection_trials      |          0        |   0        |           0       |              2800 |                         2800 |             0.0603536 |       0.000202155 |                               0.236078 |
| PHASE7B_MODEL_A_SELECTED__quarterly | conservative_research_trials |          0        |   0        |           0       |              4164 |                         4164 |             0.0621207 |       0.000135882 |                               0.236078 |
| PHASE7B_MODEL_B_SELECTED__weekly    | strict_selection_trials      |          0.384515 |  -1.63427  |          31.9542  |              2800 |                         2800 |             0.102485  |       1           |                               1        |
| PHASE7B_MODEL_B_SELECTED__weekly    | conservative_research_trials |          0.384515 |  -1.63427  |          31.9542  |              4164 |                         4164 |             0.105486  |       1           |                               1        |
| PHASE7B_MODEL_B_SELECTED__monthly   | strict_selection_trials      |          0.337035 |  -1.22688  |          39.4118  |              2800 |                         2800 |             0.0971209 |       1           |                               1        |
| PHASE7B_MODEL_B_SELECTED__monthly   | conservative_research_trials |          0.337035 |  -1.22688  |          39.4118  |              4164 |                         4164 |             0.0999646 |       1           |                               1        |
| PHASE7B_MODEL_B_SELECTED__bimonthly | strict_selection_trials      |          0.494367 |  -0.921331 |          35.3541  |              2800 |                         2800 |             0.116684  |       1           |                               1        |
| PHASE7B_MODEL_B_SELECTED__bimonthly | conservative_research_trials |          0.494367 |  -0.921331 |          35.3541  |              4164 |                         4164 |             0.1201    |       1           |                               1        |
| PHASE7B_MODEL_B_SELECTED__quarterly | strict_selection_trials      |          0        |   0        |           0       |              2800 |                         2800 |             0.0603536 |       0.000202155 |                               0.236078 |
| PHASE7B_MODEL_B_SELECTED__quarterly | conservative_research_trials |          0        |   0        |           0       |              4164 |                         4164 |             0.0621207 |       0.000135882 |                               0.236078 |

## White Reality Check

The candidate set was frozen before reading any Phase 8B-2 result: the 16 accepted strategy/frequency pre-tax paths (Fixed MA200, Phase 7A, Model A, Model B; four frequencies each) versus the QQQ buy-and-hold benchmark on the identical 3,436-session index. The loss differential is candidate return minus benchmark return, and the statistic is the maximum annualized mean differential across all 16 candidates. Each differential is recentered by its observed mean under the null; common Politis–Romano stationary-bootstrap indices are applied to every candidate. The primary block is 20, replications are 10,000, sensitivity blocks are 5, 10, 40, and 60, and truncation is none. A finite-replication p-value uses (1 + exceedances)/(B + 1).

Only White Reality Check is implemented: it directly tests the frozen maximum-statistic family. A second Hansen SPA implementation was not added because it would duplicate an unplanned inferential layer without changing the frozen decision boundary.

|   expected_block_length | block_role   |   candidate_count |   observed_max_annualized_excess_mean |   p_value | bootstrap_index_sha256                                           |
|------------------------:|:-------------|------------------:|--------------------------------------:|----------:|:-----------------------------------------------------------------|
|                       5 | SENSITIVITY  |                16 |                              0.150101 | 0.0151985 | 3a684376251ecf139f500334c6c514081ef8796c2f67a8a8ca743a08ef37461a |
|                      10 | SENSITIVITY  |                16 |                              0.150101 | 0.0137986 | 4c6d72c8940ea37ac387680f516ff7206c91388578637bc0ba2257f23d0a1f2d |
|                      20 | PRIMARY      |                16 |                              0.150101 | 0.010299  | 0698377cc1696d1283e4d05298b72341d2d812c2b1c20bb2edabdcbfa014105c |
|                      40 | SENSITIVITY  |                16 |                              0.150101 | 0.0113989 | c016c551c60a1c48ec61d23bf4d46d2d8216116f12c7fa2b4fd2ab01d53ac3cf |
|                      60 | SENSITIVITY  |                16 |                              0.150101 | 0.010199  | c0eba28de9cdc1e31330854c6436666ff1386ebb99398510337ac83160deb483 |

## Interpretation boundary

Interpretation is hierarchical: (1) descriptive pairwise economic/path evidence, (2) the adjusted 20-test confirmatory mean-return family, (3) research-program snooping evidence from the complete inventory and White Reality Check, and (4) descriptive complexity evidence. MaxDD and Calmar remain descriptive path/risk diagnostics, not hidden multiple-testing outcomes. No winner, optimal parameter, recommended frequency, score, reoptimization, OOS claim beyond the frozen source, or Walk-Forward selection is made here. Walk-Forward parameter selection remains confined to the already accepted Phase 7B process.

The frozen configuration, source hashes, candidate fingerprint, bootstrap index hashes, formulas, and no-selection flags are machine-readable in `phase8b2_configuration.json`.

PHASE 8B-2 MULTIPLE-TESTING AUDIT COMPLETE — NO MODEL OR FREQUENCY SELECTION PERFORMED
