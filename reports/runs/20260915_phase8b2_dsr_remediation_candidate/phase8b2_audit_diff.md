# Phase 8B-2 DSR remediation audit diff

This is a Class A methodology/reporting correction. Phase 0–8B-1 and the accepted Phase 8B-2 multiple-testing and White Reality Check outputs remain unchanged.

## Source hashes

| source | SHA-256 |
|---|---|
| `phase8a/aligned_daily_returns.csv` | `0e7b790318cfbe0618305e8dbe9fa301911677667385e8d303ee665c3d1e3ee4` |
| `phase8a/canonical_source_manifest.csv` | `3ad085ad440090221f4794f456d18ef2cea433a035a288658c50a12ebbabf6dd` |
| `phase8a/oos_champion_table.csv` | `718ca799db65ea03ae625e400634f5246195e58a8b8fc9ec6416852d7a8a53af` |
| `phase8b1/after_tax_descriptive_comparisons.csv` | `59af7ddb1e879be122b894fbaac3dd151817923275f6728992443f41c1f7fc55` |
| `phase8b1/bootstrap_configuration.json` | `2befcea6f833cb83c2cf59389e91212f214fd5e51cba5923909758b3655e5bba` |
| `phase8b1/hac_mean_return_results.csv` | `c5e65dcf8d7871caf1ae690c48b494b905c8044038c59e18036be57f133cf8b1` |
| `phase8b1/pairwise_observed_metrics.csv` | `bc8bdc6830797267b8046bd61a9ce826748498c9bddf5a085a31b590840e367b` |
| `phase8b1/phase8b1_audit_diff.md` | `873cd0fd82b25903734cd01f98f6fc22e4556dc9e1afd4b051bf5a59ae193a86` |
| `phase8b1/phase8b1_report.md` | `a6aa496fc4435efdc82b4deb7e0d6df7e4ee4ca39b8d9a210d9c2d1d98e179ad` |
| `phase8b1/stationary_bootstrap_results.csv` | `7ddb2eaea36fa3ac714669a2f6b69c057b94d43cecbcbb99058714d69f97165b` |

## Accepted invariant outputs

| artifact | old SHA-256 | new SHA-256 | byte-identical |
|---|---|---|---|
| `research_trial_inventory.csv` | `06f03a36f8b8a76dc5f23d1c5aeaa318fdba578dabe3f30b902601a317cf8387` | `06f03a36f8b8a76dc5f23d1c5aeaa318fdba578dabe3f30b902601a317cf8387` | **True** |
| `multiple_testing_adjustments.csv` | `688bbbd6f592473c1de7c1dce14059c153b94c7ecfb74b9dbb6e6625e63fb3a5` | `688bbbd6f592473c1de7c1dce14059c153b94c7ecfb74b9dbb6e6625e63fb3a5` | **True** |
| `data_snooping_test_results.csv` | `b166f3796f021852948c99834b3d434e5a055eda577b80a8dd4c4bdfa3a68f25` | `b166f3796f021852948c99834b3d434e5a055eda577b80a8dd4c4bdfa3a68f25` | **True** |
| `trial_correlation_summary.csv` | `f1053c9b27f1f9a67c0bd5127d578ac9a073a5dee1f975e97e4fcd41401c4fa3` | `f1053c9b27f1f9a67c0bd5127d578ac9a073a5dee1f975e97e4fcd41401c4fa3` | **True** |
| `effective_trials_sensitivity.csv` | `649f96dded68847eb3326bf70fc99f99fceda6a5572dd96f7c6e919b0f430747` | `649f96dded68847eb3326bf70fc99f99fceda6a5572dd96f7c6e919b0f430747` | **True** |

## Intentionally changed reporting artifacts

| artifact | old SHA-256 | new SHA-256 | reason |
|---|---|---|---|
| `deflated_sharpe_results.csv` | `889a8b5f3355003c478f58a9b11f01fc3ffe481f75d18822445fb6a26ab85f81` | `1f306a42aa2c40afd2a12bcce722177135082b04364832bdd1a01855cbc9ed69` | Replaced unsupported numeric DSR with explicit non-identifiability status |
| `phase8b2_configuration.json` | `85b2fa17d3c8b3d90401c0f4b52c735ef5a444dddafc2765ac90db8fd9402493` | `d0339ee4c9aa82f7833abab6e50204b050be061d608b5dfb642fa3eb1b6a0c1a` | Records remediation equations, status, and invariant comparisons |
| `phase8b2_report.md` | `5ca88803d20b80ae2833b206107d6f79f5906f7e99552f5e639595dd10498e28` | `fb30c0b92aec90a730cbc83c7425391d742b171cb316c6922329ab0b17305bca` | Documents the corrected DSR interpretation |

## DSR correction

- Old defective DSR artifact SHA-256: `889a8b5f3355003c478f58a9b11f01fc3ffe481f75d18822445fb6a26ab85f81`
- New status artifact SHA-256: `1f306a42aa2c40afd2a12bcce722177135082b04364832bdd1a01855cbc9ed69`
- New status: **DSR_NOT_IDENTIFIABLE_FROM_FROZEN_ARTIFACTS**
- Strict research count preserved: **2,800**
- Conservative research count preserved: **4,164**
- Cross-trial Sharpe dispersion: unavailable from one common accepted OOS calendar; no SR* or DSR probability manufactured.
- Economic paths, pairwise p-values, adjusted p-values, White Reality Check rows, and source files: unchanged.

## Unresolved issue

A future phase would need a pre-specified, comparable historical Sharpe trial distribution (or a justified resampling design) before a numerical Bailey–López de Prado DSR can be accepted. This remediation does not create one.

PHASE 8B-2 DSR REMEDIATION COMPLETE — AWAITING STATISTICAL AUDIT
