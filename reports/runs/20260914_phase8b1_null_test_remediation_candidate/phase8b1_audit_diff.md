# Phase 8B-1 null-test remediation audit diff

This candidate run is `20260914_phase8b1_null_test_remediation_candidate`. The prior unaudited run `20260914_phase8b1_pairwise_inference_final` is retained byte-for-byte for comparison. The correction is limited to the explicit centered-null implementation and finite-replication p-value reporting. No Phase 0–8A artifact or economic input was rewritten.

## A. Invariant checks

- Observed paired metrics changed: **False**. Maximum numeric difference across the observed metric table: `0`.
- Ordinary uncentered percentile CIs changed: **False**. Maximum finite CI difference: `0`.
- Stationary-bootstrap index SHA-256 values changed: **False**.
- Secondary HAC rows changed: **False**. Maximum finite numeric difference: `0`.
- Phase 8A source run and hashes remain unchanged: **True**.
- Phase 0–8A artifacts changed: **False** (the candidate adds only a new Phase 8B-1 run; the canonical Phase 8A hashes above were re-verified).

## B. Explicit null-test correction

For each pair, the production code now constructs `d_t = strategy_return_t - benchmark_return_t`, `observed_mean_daily = mean(d_t)`, and `d0_t = d_t - observed_mean_daily`. The already-frozen index matrix for each block length is applied directly to `d0_t`; the null statistic is `mean(d0_t[indices])`. The reported one-sided p-value is `(1 + count(null_bootstrap_stat >= observed_stat)) / (B + 1)`, with B = 10,000. Ordinary percentile CIs remain on the ordinary uncentered paired strategy/benchmark bootstrap.

The p-value table below includes every one of the 20 comparison/frequency rows for the primary block length and all four sensitivity block lengths. `null_bootstrap_exceedance_count` is the new explicit centered-null tail count.

| comparison_id                  | strategy_frequency   | expected_block_length   | old_p_value    | new_p_value    | p_value_delta   | null_bootstrap_exceedance_count   |
|:-------------------------------|:---------------------|:------------------------|:---------------|:---------------|:----------------|:----------------------------------|
| A_FIXED_MA200_VS_QQQ           | bimonthly            | 5                       | 0.002400000000 | 0.002499750025 | 0.000099750025  | 24                                |
| A_FIXED_MA200_VS_QQQ           | monthly              | 5                       | 0.020500000000 | 0.020597940206 | 0.000097940206  | 205                               |
| A_FIXED_MA200_VS_QQQ           | quarterly            | 5                       | 0.190600000000 | 0.190680931907 | 0.000080931907  | 1906                              |
| A_FIXED_MA200_VS_QQQ           | weekly               | 5                       | 0.019600000000 | 0.019698030197 | 0.000098030197  | 196                               |
| B_PHASE7A_VS_QQQ               | bimonthly            | 5                       | 0.002300000000 | 0.002399760024 | 0.000099760024  | 23                                |
| B_PHASE7A_VS_QQQ               | monthly              | 5                       | 0.019600000000 | 0.019698030197 | 0.000098030197  | 196                               |
| B_PHASE7A_VS_QQQ               | quarterly            | 5                       | 0.200900000000 | 0.200979902010 | 0.000079902010  | 2009                              |
| B_PHASE7A_VS_QQQ               | weekly               | 5                       | 0.017100000000 | 0.017198280172 | 0.000098280172  | 171                               |
| C_PHASE7A_INCREMENTAL_VS_FIXED | bimonthly            | 5                       | 0.190800000000 | 0.190880911909 | 0.000080911909  | 1908                              |
| C_PHASE7A_INCREMENTAL_VS_FIXED | monthly              | 5                       | 0.319400000000 | 0.319468053195 | 0.000068053195  | 3194                              |
| C_PHASE7A_INCREMENTAL_VS_FIXED | quarterly            | 5                       | 0.461200000000 | 0.461253874613 | 0.000053874613  | 4612                              |
| C_PHASE7A_INCREMENTAL_VS_FIXED | weekly               | 5                       | 0.206000000000 | 0.206079392061 | 0.000079392061  | 2060                              |
| D_PHASE7B_MODEL_A_VS_FIXED     | bimonthly            | 5                       | 1.000000000000 | 1.000000000000 | 0.000000000000  | 10000                             |
| D_PHASE7B_MODEL_A_VS_FIXED     | monthly              | 5                       | 1.000000000000 | 1.000000000000 | 0.000000000000  | 10000                             |
| D_PHASE7B_MODEL_A_VS_FIXED     | quarterly            | 5                       | 0.998400000000 | 0.998400159984 | 0.000000159984  | 9984                              |
| D_PHASE7B_MODEL_A_VS_FIXED     | weekly               | 5                       | 1.000000000000 | 1.000000000000 | 0.000000000000  | 10000                             |
| E_PHASE7B_MODEL_B_VS_MODEL_A   | bimonthly            | 5                       | 0.018300000000 | 0.018398160184 | 0.000098160184  | 183                               |
| E_PHASE7B_MODEL_B_VS_MODEL_A   | monthly              | 5                       | 0.075300000000 | 0.075392460754 | 0.000092460754  | 753                               |
| E_PHASE7B_MODEL_B_VS_MODEL_A   | quarterly            | 5                       | 1.000000000000 | 1.000000000000 | 0.000000000000  | 10000                             |
| E_PHASE7B_MODEL_B_VS_MODEL_A   | weekly               | 5                       | 0.144400000000 | 0.144485551445 | 0.000085551445  | 1444                              |
| A_FIXED_MA200_VS_QQQ           | bimonthly            | 10                      | 0.002100000000 | 0.002199780022 | 0.000099780022  | 21                                |
| A_FIXED_MA200_VS_QQQ           | monthly              | 10                      | 0.015700000000 | 0.015798420158 | 0.000098420158  | 157                               |
| A_FIXED_MA200_VS_QQQ           | quarterly            | 10                      | 0.183000000000 | 0.183081691831 | 0.000081691831  | 1830                              |
| A_FIXED_MA200_VS_QQQ           | weekly               | 10                      | 0.019300000000 | 0.019398060194 | 0.000098060194  | 193                               |
| B_PHASE7A_VS_QQQ               | bimonthly            | 10                      | 0.002100000000 | 0.002199780022 | 0.000099780022  | 21                                |
| B_PHASE7A_VS_QQQ               | monthly              | 10                      | 0.016900000000 | 0.016998300170 | 0.000098300170  | 169                               |
| B_PHASE7A_VS_QQQ               | quarterly            | 10                      | 0.191400000000 | 0.191480851915 | 0.000080851915  | 1914                              |
| B_PHASE7A_VS_QQQ               | weekly               | 10                      | 0.017000000000 | 0.017098290171 | 0.000098290171  | 170                               |
| C_PHASE7A_INCREMENTAL_VS_FIXED | bimonthly            | 10                      | 0.180300000000 | 0.180381961804 | 0.000081961804  | 1803                              |
| C_PHASE7A_INCREMENTAL_VS_FIXED | monthly              | 10                      | 0.292200000000 | 0.292270772923 | 0.000070772923  | 2922                              |
| C_PHASE7A_INCREMENTAL_VS_FIXED | quarterly            | 10                      | 0.470000000000 | 0.470052994701 | 0.000052994701  | 4700                              |
| C_PHASE7A_INCREMENTAL_VS_FIXED | weekly               | 10                      | 0.176600000000 | 0.176682331767 | 0.000082331767  | 1766                              |
| D_PHASE7B_MODEL_A_VS_FIXED     | bimonthly            | 10                      | 1.000000000000 | 1.000000000000 | 0.000000000000  | 10000                             |
| D_PHASE7B_MODEL_A_VS_FIXED     | monthly              | 10                      | 1.000000000000 | 1.000000000000 | 0.000000000000  | 10000                             |
| D_PHASE7B_MODEL_A_VS_FIXED     | quarterly            | 10                      | 0.999600000000 | 0.999600039996 | 0.000000039996  | 9996                              |
| D_PHASE7B_MODEL_A_VS_FIXED     | weekly               | 10                      | 1.000000000000 | 1.000000000000 | 0.000000000000  | 10000                             |
| E_PHASE7B_MODEL_B_VS_MODEL_A   | bimonthly            | 10                      | 0.016700000000 | 0.016798320168 | 0.000098320168  | 167                               |
| E_PHASE7B_MODEL_B_VS_MODEL_A   | monthly              | 10                      | 0.066700000000 | 0.066793320668 | 0.000093320668  | 667                               |
| E_PHASE7B_MODEL_B_VS_MODEL_A   | quarterly            | 10                      | 1.000000000000 | 1.000000000000 | 0.000000000000  | 10000                             |
| E_PHASE7B_MODEL_B_VS_MODEL_A   | weekly               | 10                      | 0.129900000000 | 0.129987001300 | 0.000087001300  | 1299                              |
| A_FIXED_MA200_VS_QQQ           | bimonthly            | 20                      | 0.000900000000 | 0.000999900010 | 0.000099900010  | 9                                 |
| A_FIXED_MA200_VS_QQQ           | monthly              | 20                      | 0.014000000000 | 0.014098590141 | 0.000098590141  | 140                               |
| A_FIXED_MA200_VS_QQQ           | quarterly            | 20                      | 0.194400000000 | 0.194480551945 | 0.000080551945  | 1944                              |
| A_FIXED_MA200_VS_QQQ           | weekly               | 20                      | 0.015300000000 | 0.015398460154 | 0.000098460154  | 153                               |
| B_PHASE7A_VS_QQQ               | bimonthly            | 20                      | 0.001200000000 | 0.001299870013 | 0.000099870013  | 12                                |
| B_PHASE7A_VS_QQQ               | monthly              | 20                      | 0.014600000000 | 0.014698530147 | 0.000098530147  | 146                               |
| B_PHASE7A_VS_QQQ               | quarterly            | 20                      | 0.205500000000 | 0.205579442056 | 0.000079442056  | 2055                              |
| B_PHASE7A_VS_QQQ               | weekly               | 20                      | 0.014100000000 | 0.014198580142 | 0.000098580142  | 141                               |
| C_PHASE7A_INCREMENTAL_VS_FIXED | bimonthly            | 20                      | 0.189700000000 | 0.189781021898 | 0.000081021898  | 1897                              |
| C_PHASE7A_INCREMENTAL_VS_FIXED | monthly              | 20                      | 0.289900000000 | 0.289971002900 | 0.000071002900  | 2899                              |
| C_PHASE7A_INCREMENTAL_VS_FIXED | quarterly            | 20                      | 0.474500000000 | 0.474552544746 | 0.000052544746  | 4745                              |
| C_PHASE7A_INCREMENTAL_VS_FIXED | weekly               | 20                      | 0.153600000000 | 0.153684631537 | 0.000084631537  | 1536                              |
| D_PHASE7B_MODEL_A_VS_FIXED     | bimonthly            | 20                      | 1.000000000000 | 1.000000000000 | 0.000000000000  | 10000                             |
| D_PHASE7B_MODEL_A_VS_FIXED     | monthly              | 20                      | 1.000000000000 | 1.000000000000 | 0.000000000000  | 10000                             |
| D_PHASE7B_MODEL_A_VS_FIXED     | quarterly            | 20                      | 0.999600000000 | 0.999600039996 | 0.000000039996  | 9996                              |
| D_PHASE7B_MODEL_A_VS_FIXED     | weekly               | 20                      | 1.000000000000 | 1.000000000000 | 0.000000000000  | 10000                             |
| E_PHASE7B_MODEL_B_VS_MODEL_A   | bimonthly            | 20                      | 0.015200000000 | 0.015298470153 | 0.000098470153  | 152                               |
| E_PHASE7B_MODEL_B_VS_MODEL_A   | monthly              | 20                      | 0.058400000000 | 0.058494150585 | 0.000094150585  | 584                               |
| E_PHASE7B_MODEL_B_VS_MODEL_A   | quarterly            | 20                      | 1.000000000000 | 1.000000000000 | 0.000000000000  | 10000                             |
| E_PHASE7B_MODEL_B_VS_MODEL_A   | weekly               | 20                      | 0.127000000000 | 0.127087291271 | 0.000087291271  | 1270                              |
| A_FIXED_MA200_VS_QQQ           | bimonthly            | 40                      | 0.000700000000 | 0.000799920008 | 0.000099920008  | 7                                 |
| A_FIXED_MA200_VS_QQQ           | monthly              | 40                      | 0.010900000000 | 0.010998900110 | 0.000098900110  | 109                               |
| A_FIXED_MA200_VS_QQQ           | quarterly            | 40                      | 0.208400000000 | 0.208479152085 | 0.000079152085  | 2084                              |
| A_FIXED_MA200_VS_QQQ           | weekly               | 40                      | 0.009300000000 | 0.009399060094 | 0.000099060094  | 93                                |
| B_PHASE7A_VS_QQQ               | bimonthly            | 40                      | 0.000400000000 | 0.000499950005 | 0.000099950005  | 4                                 |
| B_PHASE7A_VS_QQQ               | monthly              | 40                      | 0.010100000000 | 0.010198980102 | 0.000098980102  | 101                               |
| B_PHASE7A_VS_QQQ               | quarterly            | 40                      | 0.220000000000 | 0.220077992201 | 0.000077992201  | 2200                              |
| B_PHASE7A_VS_QQQ               | weekly               | 40                      | 0.008400000000 | 0.008499150085 | 0.000099150085  | 84                                |
| C_PHASE7A_INCREMENTAL_VS_FIXED | bimonthly            | 40                      | 0.210900000000 | 0.210978902110 | 0.000078902110  | 2109                              |
| C_PHASE7A_INCREMENTAL_VS_FIXED | monthly              | 40                      | 0.300100000000 | 0.300169983002 | 0.000069983002  | 3001                              |
| C_PHASE7A_INCREMENTAL_VS_FIXED | quarterly            | 40                      | 0.488900000000 | 0.488951104890 | 0.000051104890  | 4889                              |
| C_PHASE7A_INCREMENTAL_VS_FIXED | weekly               | 40                      | 0.140700000000 | 0.140785921408 | 0.000085921408  | 1407                              |
| D_PHASE7B_MODEL_A_VS_FIXED     | bimonthly            | 40                      | 1.000000000000 | 1.000000000000 | 0.000000000000  | 10000                             |
| D_PHASE7B_MODEL_A_VS_FIXED     | monthly              | 40                      | 0.999900000000 | 0.999900009999 | 0.000000009999  | 9999                              |
| D_PHASE7B_MODEL_A_VS_FIXED     | quarterly            | 40                      | 0.999500000000 | 0.999500049995 | 0.000000049995  | 9995                              |
| D_PHASE7B_MODEL_A_VS_FIXED     | weekly               | 40                      | 0.999900000000 | 0.999900009999 | 0.000000009999  | 9999                              |
| E_PHASE7B_MODEL_B_VS_MODEL_A   | bimonthly            | 40                      | 0.020100000000 | 0.020197980202 | 0.000097980202  | 201                               |
| E_PHASE7B_MODEL_B_VS_MODEL_A   | monthly              | 40                      | 0.059400000000 | 0.059494050595 | 0.000094050595  | 594                               |
| E_PHASE7B_MODEL_B_VS_MODEL_A   | quarterly            | 40                      | 1.000000000000 | 1.000000000000 | 0.000000000000  | 10000                             |
| E_PHASE7B_MODEL_B_VS_MODEL_A   | weekly               | 40                      | 0.127800000000 | 0.127887211279 | 0.000087211279  | 1278                              |
| A_FIXED_MA200_VS_QQQ           | bimonthly            | 60                      | 0.000400000000 | 0.000499950005 | 0.000099950005  | 4                                 |
| A_FIXED_MA200_VS_QQQ           | monthly              | 60                      | 0.008400000000 | 0.008499150085 | 0.000099150085  | 84                                |
| A_FIXED_MA200_VS_QQQ           | quarterly            | 60                      | 0.208800000000 | 0.208879112089 | 0.000079112089  | 2088                              |
| A_FIXED_MA200_VS_QQQ           | weekly               | 60                      | 0.006600000000 | 0.006699330067 | 0.000099330067  | 66                                |
| B_PHASE7A_VS_QQQ               | bimonthly            | 60                      | 0.000500000000 | 0.000599940006 | 0.000099940006  | 5                                 |
| B_PHASE7A_VS_QQQ               | monthly              | 60                      | 0.009400000000 | 0.009499050095 | 0.000099050095  | 94                                |
| B_PHASE7A_VS_QQQ               | quarterly            | 60                      | 0.221100000000 | 0.221177882212 | 0.000077882212  | 2211                              |
| B_PHASE7A_VS_QQQ               | weekly               | 60                      | 0.006300000000 | 0.006399360064 | 0.000099360064  | 63                                |
| C_PHASE7A_INCREMENTAL_VS_FIXED | bimonthly            | 60                      | 0.216100000000 | 0.216178382162 | 0.000078382162  | 2161                              |
| C_PHASE7A_INCREMENTAL_VS_FIXED | monthly              | 60                      | 0.319000000000 | 0.319068093191 | 0.000068093191  | 3190                              |
| C_PHASE7A_INCREMENTAL_VS_FIXED | quarterly            | 60                      | 0.491200000000 | 0.491250874913 | 0.000050874913  | 4912                              |
| C_PHASE7A_INCREMENTAL_VS_FIXED | weekly               | 60                      | 0.128200000000 | 0.128287171283 | 0.000087171283  | 1282                              |
| D_PHASE7B_MODEL_A_VS_FIXED     | bimonthly            | 60                      | 1.000000000000 | 1.000000000000 | 0.000000000000  | 10000                             |
| D_PHASE7B_MODEL_A_VS_FIXED     | monthly              | 60                      | 1.000000000000 | 1.000000000000 | 0.000000000000  | 10000                             |
| D_PHASE7B_MODEL_A_VS_FIXED     | quarterly            | 60                      | 1.000000000000 | 1.000000000000 | 0.000000000000  | 10000                             |
| D_PHASE7B_MODEL_A_VS_FIXED     | weekly               | 60                      | 1.000000000000 | 1.000000000000 | 0.000000000000  | 10000                             |
| E_PHASE7B_MODEL_B_VS_MODEL_A   | bimonthly            | 60                      | 0.023700000000 | 0.023797620238 | 0.000097620238  | 237                               |
| E_PHASE7B_MODEL_B_VS_MODEL_A   | monthly              | 60                      | 0.063600000000 | 0.063693630637 | 0.000093630637  | 636                               |
| E_PHASE7B_MODEL_B_VS_MODEL_A   | quarterly            | 60                      | 1.000000000000 | 1.000000000000 | 0.000000000000  | 10000                             |
| E_PHASE7B_MODEL_B_VS_MODEL_A   | weekly               | 60                      | 0.132100000000 | 0.132186781322 | 0.000086781322  | 1321                              |

## C. Frozen stream and provenance

- Seed: `8301`; replications: `10000`; primary block length: `20`; sensitivities: `5, 10, 40, 60`.
- Index SHA-256 values byte-identical to the prior run: **True**.
- Canonical Phase 8A daily input SHA-256: `0e7b790318cfbe0618305e8dbe9fa301911677667385e8d303ee665c3d1e3ee4`.
- Canonical Phase 8A champion-table SHA-256: `718ca799db65ea03ae625e400634f5246195e58a8b8fc9ec6416852d7a8a53af`.

## D. Candidate output hashes

- `pairwise_observed_metrics.csv`: `bc8bdc6830797267b8046bd61a9ce826748498c9bddf5a085a31b590840e367b`
- `stationary_bootstrap_results.csv`: `7ddb2eaea36fa3ac714669a2f6b69c057b94d43cecbcbb99058714d69f97165b`
- `hac_mean_return_results.csv`: `c5e65dcf8d7871caf1ae690c48b494b905c8044038c59e18036be57f133cf8b1`
- `after_tax_descriptive_comparisons.csv`: `59af7ddb1e879be122b894fbaac3dd151817923275f6728992443f41c1f7fc55`
- `bootstrap_configuration.json`: `2befcea6f833cb83c2cf59389e91212f214fd5e51cba5923909758b3655e5bba`
- `phase8b1_report.md`: `a6aa496fc4435efdc82b4deb7e0d6df7e4ee4ca39b8d9a210d9c2d1d98e179ad`

## E. Interpretation boundary

This is a reporting/statistical-audit correction only. No model or frequency selection, multiple-testing correction, Phase 8B-2 work, or research-conclusion revision was performed. The candidate remains awaiting independent statistical audit.
