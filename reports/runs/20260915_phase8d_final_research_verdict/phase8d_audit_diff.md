# Phase 8D audit diff

## Scope and non-mutation gate

Phase8D is synthesis/governance only. It read accepted Phase8A–8C tables after hash verification and performed no portfolio simulation, signal calculation, optimizer/selector call, economic-path regeneration, new hypothesis test, p-value family, or numerical DSR. No prior canonical artifact was rewritten.

## Complete pytest result

Dedicated Phase8D tests: **30**. Full pytest result: **371 passed** (recorded after generation).

## Evidence and count audit

- OOS common dates: `2013-01-02` through `2026-08-31`; final matrix rows: `17` (QQQ + 16 strategy/frequency rows).
- Goal scorecard rows: `16` (two primary strategies × four frequencies × two tax modes).
- Complexity rows: `4` (four matched frequencies; 14 accepted scenarios per frequency).
- Claim ledger rows: `21`; every major verdict claim has an accepted source artifact/filter.
- All four frequencies remain visible. There is no combined numerical score, live frequency, production winner, or parameter selection.
- Fixed evidence classification: `MODERATE`.
- Phase7A incremental-complexity classification: `NOT_JUSTIFIED`.
- Phase7B classification: `NO_DEMONSTRATED_VALUE`; NO_ELIGIBLE_PARAMETER and CASH_FALLBACK are preserved.
- Overall classification: `PROMISING_BUT_INSUFFICIENT`.
- Paper decision: `PROCEED_TO_PAPER_TRADING_VALIDATION`; no live-capital recommendation.

## Frozen statistical boundary

The exact confirmatory 20-test family, its Bonferroni/Holm/BH survivors, and the accepted global White Reality Check are consumed byte-for-byte. BH is described as FDR control, not FWER. DSR remains `DSR_NOT_IDENTIFIABLE_FROM_FROZEN_ARTIFACTS`; no SR* or numerical DSR is generated.

## Robustness and economic boundary

Phase8C slippage, execution, start-date, tax, frequency-dispersion, Phase7A-vs-Fixed, and QQQ-dominance evidence is consumed without rerunning. Drawdown failures and tax/turnover burdens remain explicit. The simplicity preference is at the model-family level only and does not select a frequency.

## Accepted source SHA-256 values

- `phase7b/phase7b_parameter_grid.yaml`: `da75c45ff1c041e9a954474052a5b47895717b4de8042dfdacc9f2af4039737e`
- `phase7b/phase7b_report.md`: `16cf51aa62c956bea518bb3a2c3a8c4b0793c13c3c13453fb4945f5914a78b2c`
- `phase7b/phase7b_stitched_oos_results.csv`: `765ff383a3bef9fe2120347fe98a49e0d5e57b16ef44c1ed6a2934b93574ddd7`
- `phase7b/selected_parameters_by_fold.csv`: `d27b94dad477d3678c4113cef2895ed67318c1327b6b9bdb620dff277fe71725`
- `phase7b/training_candidate_results.csv`: `0fc0d003df6a10560c820e4156aef5c2707ba0f565c6477a7ce21b66125f6c70`
- `phase7b/walk_forward_folds.csv`: `7786374c1b8d226ff88b6c6b3f09a60bcd4234066b1cfb6117b4d405fefa739f`
- `phase8a/aligned_daily_equity.csv`: `4271efc5106fb60229fdb7a43c47158b3f229b7dc1ad7ce012a6f01878b200d0`
- `phase8a/aligned_daily_returns.csv`: `0e7b790318cfbe0618305e8dbe9fa301911677667385e8d303ee665c3d1e3ee4`
- `phase8a/benchmark_relative_metrics.csv`: `422ab66af47f4a5fe2b82a6f48b9ba363f949bc2acaa8c27d5272d415f8d9139`
- `phase8a/canonical_source_manifest.csv`: `3ad085ad440090221f4794f456d18ef2cea433a035a288658c50a12ebbabf6dd`
- `phase8a/complexity_comparison.csv`: `8b21f8464a0c1630c98e835336bd27781e23d4363e7a8180102c1f8000026c31`
- `phase8a/config_snapshot.yaml`: `43f9a48999eb8dd60e2c39aae7f8610aacf06cb7289a5e7cc7bf1db36d32d964`
- `phase8a/oos_champion_table.csv`: `718ca799db65ea03ae625e400634f5246195e58a8b8fc9ec6416852d7a8a53af`
- `phase8a/phase8a_audit_diff.md`: `8e6c8d0b595e7ccf919f6f1b2fdd557210cc790e439b197d09d82656a7c24c36`
- `phase8a/phase8a_report.md`: `d31769316c58e22e1394afdcfde58e8464e7cc37aabdf3f848544ba14701320c`
- `phase8b1/after_tax_descriptive_comparisons.csv`: `59af7ddb1e879be122b894fbaac3dd151817923275f6728992443f41c1f7fc55`
- `phase8b1/bootstrap_configuration.json`: `2befcea6f833cb83c2cf59389e91212f214fd5e51cba5923909758b3655e5bba`
- `phase8b1/hac_mean_return_results.csv`: `c5e65dcf8d7871caf1ae690c48b494b905c8044038c59e18036be57f133cf8b1`
- `phase8b1/pairwise_observed_metrics.csv`: `bc8bdc6830797267b8046bd61a9ce826748498c9bddf5a085a31b590840e367b`
- `phase8b1/phase8b1_audit_diff.md`: `873cd0fd82b25903734cd01f98f6fc22e4556dc9e1afd4b051bf5a59ae193a86`
- `phase8b1/phase8b1_report.md`: `a6aa496fc4435efdc82b4deb7e0d6df7e4ee4ca39b8d9a210d9c2d1d98e179ad`
- `phase8b1/stationary_bootstrap_results.csv`: `7ddb2eaea36fa3ac714669a2f6b69c057b94d43cecbcbb99058714d69f97165b`
- `phase8b2/data_snooping_test_results.csv`: `b166f3796f021852948c99834b3d434e5a055eda577b80a8dd4c4bdfa3a68f25`
- `phase8b2/deflated_sharpe_results.csv`: `1f306a42aa2c40afd2a12bcce722177135082b04364832bdd1a01855cbc9ed69`
- `phase8b2/dsr_trial_universe_audit.csv`: `8d421b30453ec9b5356b6e1342ce9c33c79590d3c3d47e5b088b7ac294a61fca`
- `phase8b2/effective_trials_sensitivity.csv`: `649f96dded68847eb3326bf70fc99f99fceda6a5572dd96f7c6e919b0f430747`
- `phase8b2/multiple_testing_adjustments.csv`: `688bbbd6f592473c1de7c1dce14059c153b94c7ecfb74b9dbb6e6625e63fb3a5`
- `phase8b2/phase8b2_audit_diff.md`: `96e260045158c38e7552482bf26b4451a80d43a9b967dfdf8eb3741c8a8152ce`
- `phase8b2/phase8b2_configuration.json`: `d0339ee4c9aa82f7833abab6e50204b050be061d608b5dfb642fa3eb1b6a0c1a`
- `phase8b2/phase8b2_dsr_remediation.md`: `465f4c397f46c0932b773e962097820b0f779880a06b0e960c04026ce693699d`
- `phase8b2/phase8b2_report.md`: `fb30c0b92aec90a730cbc83c7425391d742b171cb316c6922329ab0b17305bca`
- `phase8b2/research_trial_inventory.csv`: `06f03a36f8b8a76dc5f23d1c5aeaa318fdba578dabe3f30b902601a317cf8387`
- `phase8b2/trial_correlation_summary.csv`: `f1053c9b27f1f9a67c0bd5127d578ac9a073a5dee1f975e97e4fcd41401c4fa3`
- `phase8c/canonical_baseline_reproduction.csv`: `0f295bd0e93e06d32a1901b2f640f32dfac7ca217eb746fda0f791e496f8d503`
- `phase8c/execution_sensitivity.csv`: `fc6f2e81d7c62af55067cb22389cd4926948bad35b1d88741190d31b704100ae`
- `phase8c/frequency_robustness.csv`: `d9d0f600f7e31f8f0696766e7fe17bfefeff4e067a2086911cad400267458199`
- `phase8c/phase7a_vs_fixed_ma200_robustness.csv`: `0ee51586ccf071ccc19d2f4c75fdbd9f456e8106a3a831e520eea2721029774c`
- `phase8c/phase8c_audit_diff.md`: `6b4d5a003b78935287461dc708f417453631a3c24346acc519551c9fcd97f917`
- `phase8c/phase8c_configuration.json`: `6500cc753f8d86b0e4f0cfe3e050b48c54d58fd6d89459bb4ba662eb160a1c43`
- `phase8c/phase8c_report.md`: `227958ef9f51ee1a4e977f5a5939a971210675cd9798db5e4e312d1f31924a76`
- `phase8c/qqq_relative_robustness.csv`: `877c21ade20361ac13545e58ab7d02adc29e13b446b293805e2c56b99449cbe6`
- `phase8c/robustness_metrics.csv`: `d97800261a5b4a3c08f26a8efebd27b09a115bf3f62a9d1657290e6fcb384c3c`
- `phase8c/robustness_scenarios.csv`: `e43d386ac64f9863ac5391468b1c137417671b096812cfbdae65646bafd13dc6`
- `phase8c/robustness_survival_summary.csv`: `0939378354471bbcdccb5f33115b3a3956bab15780fb24139ee015920272f0cb`
- `phase8c/slippage_sensitivity.csv`: `01f0123b576766de3f56e1bc5766ae1182f060122947149c555d7d67e90b766a`
- `phase8c/start_date_sensitivity.csv`: `c6d6c77ba7359a04fd6ac469a4b1b3ace9416c832f5457c6183480d0f51c09c6`
- `phase8c/tax_robustness.csv`: `5192f6372fe7d2304ede873088290132098781a820bb90a4dc3ae9ad34bb29a8`
- `raw/QLD.parquet`: `2499976b07ea6711b33befad63bd8e177ab85f0c820662330f9a4ad257532a9f`
- `raw/QQQ.parquet`: `fe5aa0db7c8a717e00cd7726d04ba1d2faff627e9f6e48c0952a5e2f235052c6`
- `raw/SPY.parquet`: `6a73a96bf408a041bc7e77df51117ae5a0965769c407c6699f52b0fd489b28d8`
- `raw/SSO.parquet`: `b0636de318b2d72d4cf774d6af2e11b2bc47904150891a06a39d29355e6e2b5d`
- `raw/TQQQ.parquet`: `4b0b5c7500d7510bb2e61607e86130d635a3d05339cf7cde10ab7174551ccf76`

## Phase8D artifact SHA-256 values

- `complexity_incremental_evidence`: `b622514a52fbe60c25a63856684a03004a5a3041a06e1a9d7ca457dc8f8f180f`
- `final_claim_evidence_ledger`: `92a9c23854dd13302d4ee3f92aa8f37f44988389caa2c0b73bbb5faffe3ec8a5`
- `final_evidence_matrix`: `ef35796946bfd587f14311003dfc4575f98657c70f5b9d79992ee70cafc78605`
- `original_goal_scorecard`: `ad3998d4291cb9a6f77c4a32d09aa6c07f3e82efe4ffdc1d2f087868169ae462`
- `phase8d_configuration.json`: `3bee1f2da9872c7338e0b39afadf7def0c13be327c678d835863e7780381362a`
- `report`: `4470e42756cb5f02e6cd551224250cd15dc8632463eec273c07b77c9db80b284`

## Future DSR and deployment boundary

A valid future numerical DSR requires a prospectively designed comparable trial universe; Phase8D does not retrofit Phase1–7 historical trials. Before paper trading, freeze any thresholds prospectively using `REQUIRES_PROSPECTIVE_FREEZE_BEFORE_PAPER_TRADING`; live deployment remains outside this phase.

PHASE 8D FINAL RESEARCH VERDICT COMPLETE — RESEARCH DEVELOPMENT FROZEN
