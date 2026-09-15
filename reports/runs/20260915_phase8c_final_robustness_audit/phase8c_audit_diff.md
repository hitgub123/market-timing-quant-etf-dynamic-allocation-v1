# Phase 8C audit diff

Phase 8C is a descriptive robustness/economic audit. No accepted Phase 0–8B-2 artifact, strategy definition, signal, selector, accounting convention, or formal statistical result was rewritten.

## Accepted source hash verification

| source | SHA-256 | verified |
|---|---|---|
| `phase8a/aligned_daily_returns.csv` | `0e7b790318cfbe0618305e8dbe9fa301911677667385e8d303ee665c3d1e3ee4` | **True** |
| `phase8a/canonical_source_manifest.csv` | `3ad085ad440090221f4794f456d18ef2cea433a035a288658c50a12ebbabf6dd` | **True** |
| `phase8a/oos_champion_table.csv` | `718ca799db65ea03ae625e400634f5246195e58a8b8fc9ec6416852d7a8a53af` | **True** |
| `phase8b1/after_tax_descriptive_comparisons.csv` | `59af7ddb1e879be122b894fbaac3dd151817923275f6728992443f41c1f7fc55` | **True** |
| `phase8b1/bootstrap_configuration.json` | `2befcea6f833cb83c2cf59389e91212f214fd5e51cba5923909758b3655e5bba` | **True** |
| `phase8b1/hac_mean_return_results.csv` | `c5e65dcf8d7871caf1ae690c48b494b905c8044038c59e18036be57f133cf8b1` | **True** |
| `phase8b1/pairwise_observed_metrics.csv` | `bc8bdc6830797267b8046bd61a9ce826748498c9bddf5a085a31b590840e367b` | **True** |
| `phase8b1/phase8b1_audit_diff.md` | `873cd0fd82b25903734cd01f98f6fc22e4556dc9e1afd4b051bf5a59ae193a86` | **True** |
| `phase8b1/phase8b1_report.md` | `a6aa496fc4435efdc82b4deb7e0d6df7e4ee4ca39b8d9a210d9c2d1d98e179ad` | **True** |
| `phase8b1/stationary_bootstrap_results.csv` | `7ddb2eaea36fa3ac714669a2f6b69c057b94d43cecbcbb99058714d69f97165b` | **True** |
| `phase8b2_accepted/data_snooping_test_results.csv` | `b166f3796f021852948c99834b3d434e5a055eda577b80a8dd4c4bdfa3a68f25` | **True** |
| `phase8b2_accepted/deflated_sharpe_results.csv` | `889a8b5f3355003c478f58a9b11f01fc3ffe481f75d18822445fb6a26ab85f81` | **True** |
| `phase8b2_accepted/effective_trials_sensitivity.csv` | `649f96dded68847eb3326bf70fc99f99fceda6a5572dd96f7c6e919b0f430747` | **True** |
| `phase8b2_accepted/multiple_testing_adjustments.csv` | `688bbbd6f592473c1de7c1dce14059c153b94c7ecfb74b9dbb6e6625e63fb3a5` | **True** |
| `phase8b2_accepted/phase8b2_audit_diff.md` | `e8b14d885edff760479f385e97071fd001b31300df888ba444b4457ce0f4d6b6` | **True** |
| `phase8b2_accepted/phase8b2_configuration.json` | `85b2fa17d3c8b3d90401c0f4b52c735ef5a444dddafc2765ac90db8fd9402493` | **True** |
| `phase8b2_accepted/phase8b2_report.md` | `5ca88803d20b80ae2833b206107d6f79f5906f7e99552f5e639595dd10498e28` | **True** |
| `phase8b2_accepted/research_trial_inventory.csv` | `06f03a36f8b8a76dc5f23d1c5aeaa318fdba578dabe3f30b902601a317cf8387` | **True** |
| `phase8b2_accepted/trial_correlation_summary.csv` | `f1053c9b27f1f9a67c0bd5127d578ac9a073a5dee1f975e97e4fcd41401c4fa3` | **True** |
| `phase8b2_remediation/data_snooping_test_results.csv` | `b166f3796f021852948c99834b3d434e5a055eda577b80a8dd4c4bdfa3a68f25` | **True** |
| `phase8b2_remediation/deflated_sharpe_results.csv` | `1f306a42aa2c40afd2a12bcce722177135082b04364832bdd1a01855cbc9ed69` | **True** |
| `phase8b2_remediation/dsr_trial_universe_audit.csv` | `8d421b30453ec9b5356b6e1342ce9c33c79590d3c3d47e5b088b7ac294a61fca` | **True** |
| `phase8b2_remediation/multiple_testing_adjustments.csv` | `688bbbd6f592473c1de7c1dce14059c153b94c7ecfb74b9dbb6e6625e63fb3a5` | **True** |
| `phase8b2_remediation/phase8b2_audit_diff.md` | `96e260045158c38e7552482bf26b4451a80d43a9b967dfdf8eb3741c8a8152ce` | **True** |
| `phase8b2_remediation/phase8b2_configuration.json` | `d0339ee4c9aa82f7833abab6e50204b050be061d608b5dfb642fa3eb1b6a0c1a` | **True** |
| `phase8b2_remediation/phase8b2_dsr_remediation.md` | `465f4c397f46c0932b773e962097820b0f779880a06b0e960c04026ce693699d` | **True** |
| `phase8b2_remediation/phase8b2_report.md` | `fb30c0b92aec90a730cbc83c7425391d742b171cb316c6922329ab0b17305bca` | **True** |

## Raw snapshot hash verification

| raw snapshot | SHA-256 | verified against manifest |
|---|---|---|
| `raw/QLD.parquet` | `2499976b07ea6711b33befad63bd8e177ab85f0c820662330f9a4ad257532a9f` | **True** |
| `raw/QQQ.parquet` | `fe5aa0db7c8a717e00cd7726d04ba1d2faff627e9f6e48c0952a5e2f235052c6` | **True** |
| `raw/SPY.parquet` | `6a73a96bf408a041bc7e77df51117ae5a0965769c407c6699f52b0fd489b28d8` | **True** |
| `raw/SSO.parquet` | `b0636de318b2d72d4cf774d6af2e11b2bc47904150891a06a39d29355e6e2b5d` | **True** |
| `raw/TQQQ.parquet` | `4b0b5c7500d7510bb2e61607e86130d635a3d05339cf7cde10ab7174551ccf76` | **True** |

## Baseline reproduction

- Rows: **16** (2 primary strategies × 4 frequencies × 2 tax modes).
- Metric gate passed: **True**.
- Economic path/hash gate passed: **True**.
- Baseline gate status: **True**.
- Failure sentinel if the gate had failed: `PHASE8C_BASELINE_REPRODUCTION_FAILURE`.

## Frozen sensitivity grids

- Slippage: **(0.0, 5.0, 10.0, 20.0)** bps.
- Execution: **('next_open', 'next_close', 't2_open')**.
- Start labels: **('2013', '2014', '2015', '2016', '2018', '2020')**, common end **2026-08-31**.
- Scenario rows: **14**; metric rows: **254**.
- Four frequencies present: **True**.
- Every scenario carries frozen parameters and `selection_performed=False`.

## Robustness and complexity checks

- QQQ-relative rows: **224**; all exact start/end checks: **True**.
- Matched Phase 7A-minus-Fixed rows: **56**; all descriptive-only: **True**.
- Terminal-liquidation diagnostics are non-mutating and excluded from primary turnover in every recomputed row.
- Initial deployment is excluded from primary turnover; no hypothetical liquidation trade is added.

## Statistical boundary

- DSR status remains **DSR_NOT_IDENTIFIABLE_FROM_FROZEN_ARTIFACTS**; no SR* or DSR probability is generated.
- No new p-value family, Holm/BH/White Reality Check rerun, model selection, parameter selection, or frequency selection was performed.
- Phase 7B references remain context-only baseline rows.

## Unresolved issues

Phase 8C is intentionally descriptive. A sensitivity contradiction would be reported as an economic stress result, not converted into post-hoc statistical inference. No production winner is declared.

## Test evidence

Dedicated Phase 8C tests: **25 passed** (`tests/test_phase8c_robustness.py`). Full repository pytest: **341 passed**. No Phase 9 work was started.

PHASE 8C FINAL ROBUSTNESS AUDIT COMPLETE — NO MODEL, PARAMETER, OR FREQUENCY SELECTION PERFORMED
