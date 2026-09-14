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

| comparison_id                  | strategy_frequency   |   expected_block_length |   old_p_value |   new_p_value |   p_value_delta |   null_bootstrap_exceedance_count |
|:-------------------------------|:---------------------|------------------------:|--------------:|--------------:|----------------:|----------------------------------:|
| A_FIXED_MA200_VS_QQQ           | bimonthly            |                       5 |        0.0024 |    0.00249975 |     9.975e-05   |                                24 |
| A_FIXED_MA200_VS_QQQ           | monthly              |                       5 |        0.0205 |    0.0205979  |     9.79402e-05 |                               205 |
| A_FIXED_MA200_VS_QQQ           | quarterly            |                       5 |        0.1906 |    0.190681   |     8.09319e-05 |                              1906 |
| A_FIXED_MA200_VS_QQQ           | weekly               |                       5 |        0.0196 |    0.019698   |     9.80302e-05 |                               196 |
| B_PHASE7A_VS_QQQ               | bimonthly            |                       5 |        0.0023 |    0.00239976 |     9.976e-05   |                                23 |
| B_PHASE7A_VS_QQQ               | monthly              |                       5 |        0.0196 |    0.019698   |     9.80302e-05 |                               196 |
| B_PHASE7A_VS_QQQ               | quarterly            |                       5 |        0.2009 |    0.20098    |     7.9902e-05  |                              2009 |
| B_PHASE7A_VS_QQQ               | weekly               |                       5 |        0.0171 |    0.0171983  |     9.82802e-05 |                               171 |
| C_PHASE7A_INCREMENTAL_VS_FIXED | bimonthly            |                       5 |        0.1908 |    0.190881   |     8.09119e-05 |                              1908 |
| C_PHASE7A_INCREMENTAL_VS_FIXED | monthly              |                       5 |        0.3194 |    0.319468   |     6.80532e-05 |                              3194 |
| C_PHASE7A_INCREMENTAL_VS_FIXED | quarterly            |                       5 |        0.4612 |    0.461254   |     5.38746e-05 |                              4612 |
| C_PHASE7A_INCREMENTAL_VS_FIXED | weekly               |                       5 |        0.206  |    0.206079   |     7.93921e-05 |                              2060 |
| D_PHASE7B_MODEL_A_VS_FIXED     | bimonthly            |                       5 |        1      |    1          |     0           |                             10000 |
| D_PHASE7B_MODEL_A_VS_FIXED     | monthly              |                       5 |        1      |    1          |     0           |                             10000 |
| D_PHASE7B_MODEL_A_VS_FIXED     | quarterly            |                       5 |        0.9984 |    0.9984     |     1.59984e-07 |                              9984 |
| D_PHASE7B_MODEL_A_VS_FIXED     | weekly               |                       5 |        1      |    1          |     0           |                             10000 |
| E_PHASE7B_MODEL_B_VS_MODEL_A   | bimonthly            |                       5 |        0.0183 |    0.0183982  |     9.81602e-05 |                               183 |
| E_PHASE7B_MODEL_B_VS_MODEL_A   | monthly              |                       5 |        0.0753 |    0.0753925  |     9.24608e-05 |                               753 |
| E_PHASE7B_MODEL_B_VS_MODEL_A   | quarterly            |                       5 |        1      |    1          |     0           |                             10000 |
| E_PHASE7B_MODEL_B_VS_MODEL_A   | weekly               |                       5 |        0.1444 |    0.144486   |     8.55514e-05 |                              1444 |
| A_FIXED_MA200_VS_QQQ           | bimonthly            |                      10 |        0.0021 |    0.00219978 |     9.978e-05   |                                21 |
| A_FIXED_MA200_VS_QQQ           | monthly              |                      10 |        0.0157 |    0.0157984  |     9.84202e-05 |                               157 |
| A_FIXED_MA200_VS_QQQ           | quarterly            |                      10 |        0.183  |    0.183082   |     8.16918e-05 |                              1830 |
| A_FIXED_MA200_VS_QQQ           | weekly               |                      10 |        0.0193 |    0.0193981  |     9.80602e-05 |                               193 |
| B_PHASE7A_VS_QQQ               | bimonthly            |                      10 |        0.0021 |    0.00219978 |     9.978e-05   |                                21 |
| B_PHASE7A_VS_QQQ               | monthly              |                      10 |        0.0169 |    0.0169983  |     9.83002e-05 |                               169 |
| B_PHASE7A_VS_QQQ               | quarterly            |                      10 |        0.1914 |    0.191481   |     8.08519e-05 |                              1914 |
| B_PHASE7A_VS_QQQ               | weekly               |                      10 |        0.017  |    0.0170983  |     9.82902e-05 |                               170 |
| C_PHASE7A_INCREMENTAL_VS_FIXED | bimonthly            |                      10 |        0.1803 |    0.180382   |     8.19618e-05 |                              1803 |
| C_PHASE7A_INCREMENTAL_VS_FIXED | monthly              |                      10 |        0.2922 |    0.292271   |     7.07729e-05 |                              2922 |
| C_PHASE7A_INCREMENTAL_VS_FIXED | quarterly            |                      10 |        0.47   |    0.470053   |     5.29947e-05 |                              4700 |
| C_PHASE7A_INCREMENTAL_VS_FIXED | weekly               |                      10 |        0.1766 |    0.176682   |     8.23318e-05 |                              1766 |
| D_PHASE7B_MODEL_A_VS_FIXED     | bimonthly            |                      10 |        1      |    1          |     0           |                             10000 |
| D_PHASE7B_MODEL_A_VS_FIXED     | monthly              |                      10 |        1      |    1          |     0           |                             10000 |
| D_PHASE7B_MODEL_A_VS_FIXED     | quarterly            |                      10 |        0.9996 |    0.9996     |     3.9996e-08  |                              9996 |
| D_PHASE7B_MODEL_A_VS_FIXED     | weekly               |                      10 |        1      |    1          |     0           |                             10000 |
| E_PHASE7B_MODEL_B_VS_MODEL_A   | bimonthly            |                      10 |        0.0167 |    0.0167983  |     9.83202e-05 |                               167 |
| E_PHASE7B_MODEL_B_VS_MODEL_A   | monthly              |                      10 |        0.0667 |    0.0667933  |     9.33207e-05 |                               667 |
| E_PHASE7B_MODEL_B_VS_MODEL_A   | quarterly            |                      10 |        1      |    1          |     0           |                             10000 |
| E_PHASE7B_MODEL_B_VS_MODEL_A   | weekly               |                      10 |        0.1299 |    0.129987   |     8.70013e-05 |                              1299 |
| A_FIXED_MA200_VS_QQQ           | bimonthly            |                      20 |        0.0009 |    0.0009999  |     9.99e-05    |                                 9 |
| A_FIXED_MA200_VS_QQQ           | monthly              |                      20 |        0.014  |    0.0140986  |     9.85901e-05 |                               140 |
| A_FIXED_MA200_VS_QQQ           | quarterly            |                      20 |        0.1944 |    0.194481   |     8.05519e-05 |                              1944 |
| A_FIXED_MA200_VS_QQQ           | weekly               |                      20 |        0.0153 |    0.0153985  |     9.84602e-05 |                               153 |
| B_PHASE7A_VS_QQQ               | bimonthly            |                      20 |        0.0012 |    0.00129987 |     9.987e-05   |                                12 |
| B_PHASE7A_VS_QQQ               | monthly              |                      20 |        0.0146 |    0.0146985  |     9.85301e-05 |                               146 |
| B_PHASE7A_VS_QQQ               | quarterly            |                      20 |        0.2055 |    0.205579   |     7.94421e-05 |                              2055 |
| B_PHASE7A_VS_QQQ               | weekly               |                      20 |        0.0141 |    0.0141986  |     9.85801e-05 |                               141 |
| C_PHASE7A_INCREMENTAL_VS_FIXED | bimonthly            |                      20 |        0.1897 |    0.189781   |     8.10219e-05 |                              1897 |
| C_PHASE7A_INCREMENTAL_VS_FIXED | monthly              |                      20 |        0.2899 |    0.289971   |     7.10029e-05 |                              2899 |
| C_PHASE7A_INCREMENTAL_VS_FIXED | quarterly            |                      20 |        0.4745 |    0.474553   |     5.25447e-05 |                              4745 |
| C_PHASE7A_INCREMENTAL_VS_FIXED | weekly               |                      20 |        0.1536 |    0.153685   |     8.46315e-05 |                              1536 |
| D_PHASE7B_MODEL_A_VS_FIXED     | bimonthly            |                      20 |        1      |    1          |     0           |                             10000 |
| D_PHASE7B_MODEL_A_VS_FIXED     | monthly              |                      20 |        1      |    1          |     0           |                             10000 |
| D_PHASE7B_MODEL_A_VS_FIXED     | quarterly            |                      20 |        0.9996 |    0.9996     |     3.9996e-08  |                              9996 |
| D_PHASE7B_MODEL_A_VS_FIXED     | weekly               |                      20 |        1      |    1          |     0           |                             10000 |
| E_PHASE7B_MODEL_B_VS_MODEL_A   | bimonthly            |                      20 |        0.0152 |    0.0152985  |     9.84702e-05 |                               152 |
| E_PHASE7B_MODEL_B_VS_MODEL_A   | monthly              |                      20 |        0.0584 |    0.0584942  |     9.41506e-05 |                               584 |
| E_PHASE7B_MODEL_B_VS_MODEL_A   | quarterly            |                      20 |        1      |    1          |     0           |                             10000 |
| E_PHASE7B_MODEL_B_VS_MODEL_A   | weekly               |                      20 |        0.127  |    0.127087   |     8.72913e-05 |                              1270 |
| A_FIXED_MA200_VS_QQQ           | bimonthly            |                      40 |        0.0007 |    0.00079992 |     9.992e-05   |                                 7 |
| A_FIXED_MA200_VS_QQQ           | monthly              |                      40 |        0.0109 |    0.0109989  |     9.89001e-05 |                               109 |
| A_FIXED_MA200_VS_QQQ           | quarterly            |                      40 |        0.2084 |    0.208479   |     7.91521e-05 |                              2084 |
| A_FIXED_MA200_VS_QQQ           | weekly               |                      40 |        0.0093 |    0.00939906 |     9.90601e-05 |                                93 |
| B_PHASE7A_VS_QQQ               | bimonthly            |                      40 |        0.0004 |    0.00049995 |     9.995e-05   |                                 4 |
| B_PHASE7A_VS_QQQ               | monthly              |                      40 |        0.0101 |    0.010199   |     9.89801e-05 |                               101 |
| B_PHASE7A_VS_QQQ               | quarterly            |                      40 |        0.22   |    0.220078   |     7.79922e-05 |                              2200 |
| B_PHASE7A_VS_QQQ               | weekly               |                      40 |        0.0084 |    0.00849915 |     9.91501e-05 |                                84 |
| C_PHASE7A_INCREMENTAL_VS_FIXED | bimonthly            |                      40 |        0.2109 |    0.210979   |     7.89021e-05 |                              2109 |
| C_PHASE7A_INCREMENTAL_VS_FIXED | monthly              |                      40 |        0.3001 |    0.30017    |     6.9983e-05  |                              3001 |
| C_PHASE7A_INCREMENTAL_VS_FIXED | quarterly            |                      40 |        0.4889 |    0.488951   |     5.11049e-05 |                              4889 |
| C_PHASE7A_INCREMENTAL_VS_FIXED | weekly               |                      40 |        0.1407 |    0.140786   |     8.59214e-05 |                              1407 |
| D_PHASE7B_MODEL_A_VS_FIXED     | bimonthly            |                      40 |        1      |    1          |     0           |                             10000 |
| D_PHASE7B_MODEL_A_VS_FIXED     | monthly              |                      40 |        0.9999 |    0.9999     |     9.999e-09   |                              9999 |
| D_PHASE7B_MODEL_A_VS_FIXED     | quarterly            |                      40 |        0.9995 |    0.9995     |     4.9995e-08  |                              9995 |
| D_PHASE7B_MODEL_A_VS_FIXED     | weekly               |                      40 |        0.9999 |    0.9999     |     9.999e-09   |                              9999 |
| E_PHASE7B_MODEL_B_VS_MODEL_A   | bimonthly            |                      40 |        0.0201 |    0.020198   |     9.79802e-05 |                               201 |
| E_PHASE7B_MODEL_B_VS_MODEL_A   | monthly              |                      40 |        0.0594 |    0.0594941  |     9.40506e-05 |                               594 |
| E_PHASE7B_MODEL_B_VS_MODEL_A   | quarterly            |                      40 |        1      |    1          |     0           |                             10000 |
| E_PHASE7B_MODEL_B_VS_MODEL_A   | weekly               |                      40 |        0.1278 |    0.127887   |     8.72113e-05 |                              1278 |
| A_FIXED_MA200_VS_QQQ           | bimonthly            |                      60 |        0.0004 |    0.00049995 |     9.995e-05   |                                 4 |
| A_FIXED_MA200_VS_QQQ           | monthly              |                      60 |        0.0084 |    0.00849915 |     9.91501e-05 |                                84 |
| A_FIXED_MA200_VS_QQQ           | quarterly            |                      60 |        0.2088 |    0.208879   |     7.91121e-05 |                              2088 |
| A_FIXED_MA200_VS_QQQ           | weekly               |                      60 |        0.0066 |    0.00669933 |     9.93301e-05 |                                66 |
| B_PHASE7A_VS_QQQ               | bimonthly            |                      60 |        0.0005 |    0.00059994 |     9.994e-05   |                                 5 |
| B_PHASE7A_VS_QQQ               | monthly              |                      60 |        0.0094 |    0.00949905 |     9.90501e-05 |                                94 |
| B_PHASE7A_VS_QQQ               | quarterly            |                      60 |        0.2211 |    0.221178   |     7.78822e-05 |                              2211 |
| B_PHASE7A_VS_QQQ               | weekly               |                      60 |        0.0063 |    0.00639936 |     9.93601e-05 |                                63 |
| C_PHASE7A_INCREMENTAL_VS_FIXED | bimonthly            |                      60 |        0.2161 |    0.216178   |     7.83822e-05 |                              2161 |
| C_PHASE7A_INCREMENTAL_VS_FIXED | monthly              |                      60 |        0.319  |    0.319068   |     6.80932e-05 |                              3190 |
| C_PHASE7A_INCREMENTAL_VS_FIXED | quarterly            |                      60 |        0.4912 |    0.491251   |     5.08749e-05 |                              4912 |
| C_PHASE7A_INCREMENTAL_VS_FIXED | weekly               |                      60 |        0.1282 |    0.128287   |     8.71713e-05 |                              1282 |
| D_PHASE7B_MODEL_A_VS_FIXED     | bimonthly            |                      60 |        1      |    1          |     0           |                             10000 |
| D_PHASE7B_MODEL_A_VS_FIXED     | monthly              |                      60 |        1      |    1          |     0           |                             10000 |
| D_PHASE7B_MODEL_A_VS_FIXED     | quarterly            |                      60 |        1      |    1          |     0           |                             10000 |
| D_PHASE7B_MODEL_A_VS_FIXED     | weekly               |                      60 |        1      |    1          |     0           |                             10000 |
| E_PHASE7B_MODEL_B_VS_MODEL_A   | bimonthly            |                      60 |        0.0237 |    0.0237976  |     9.76202e-05 |                               237 |
| E_PHASE7B_MODEL_B_VS_MODEL_A   | monthly              |                      60 |        0.0636 |    0.0636936  |     9.36306e-05 |                               636 |
| E_PHASE7B_MODEL_B_VS_MODEL_A   | quarterly            |                      60 |        1      |    1          |     0           |                             10000 |
| E_PHASE7B_MODEL_B_VS_MODEL_A   | weekly               |                      60 |        0.1321 |    0.132187   |     8.67813e-05 |                              1321 |

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
