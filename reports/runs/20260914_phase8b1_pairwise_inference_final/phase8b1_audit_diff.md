# Phase 8B-1 Pairwise Inference — Audit Diff

## A. Test result

- Dedicated Phase 8B-1 tests: **16 passed** (`pytest -q tests/test_phase8b1_pairwise_inference.py`).
- Full repository result: **264 passed** (`pytest -q`).

## B. Canonical input and source integrity

- Source run: `20260914_phase8a_oos_evidence_consolidation_final`.
- `aligned_daily_returns.csv` SHA-256: `0e7b790318cfbe0618305e8dbe9fa301911677667385e8d303ee665c3d1e3ee4`.
- Phase 8A champion-table SHA-256: `718ca799db65ea03ae625e400634f5246195e58a8b8fc9ec6416852d7a8a53af`.
- Phase 8A source artifacts were read-only; dedicated tests confirm the accepted Phase 8A hashes remain byte-identical.

## C. Exact paired calendar

- OOS period: **2013-01-02 through 2026-08-31**.
- Exact paired sessions: **3,436**.
- Every Phase 8A identity has the same date index with no missing or duplicate dates.

## D. Frozen comparison grid

- Comparisons A–E are all present: Fixed MA200 vs QQQ, Phase 7A vs QQQ, Phase 7A vs Fixed MA200, Model A vs Fixed MA200, and Model B vs Model A.
- Weekly, monthly, bimonthly, and quarterly frequencies are all retained.
- Observed metrics: **20 rows**.
- Stationary bootstrap: **600 rows** = 20 comparison/frequency pairs × 5 block lengths × 6 metrics.
- HAC cross-check: **20 rows**.
- After-tax descriptive comparisons: **20 rows**.

## E. Primary inference method

Primary inference uses paired pre-tax daily return differences, d_t = strategy − benchmark, with the same dates for both members. The Politis–Romano stationary bootstrap uses seed **8301**, **10,000** replications, primary expected block length **20**, and sensitivity lengths **5/10/40/60**. Shared index matrices are applied to both members of every pair. Percentile 95% intervals, probabilities, and the centered-null one-sided return tail probability are recorded. MaxDD and Calmar outputs are labeled path-dependent diagnostics.

## F. HAC cross-check

Newey–West HAC is secondary only. The deterministic lag rule is `floor(4 * (T / 100)^(2/9))`, producing lag **8** for T = 3,436. Daily mean, HAC standard error, annualized mean difference, test statistic, and one-sided p-value are present for every comparison/frequency.

## G. After-tax and CASH behavior

After-tax CAGR tax-paid-to-date, terminal-liquidation after-tax CAGR, and realized-tax differences are copied from Phase 8A as descriptive-only values. Terminal liquidation is explicitly not a daily return observation. Model A and Model B zero-return CASH fallback sessions remain in the paired daily input and are not removed.

## H. Selection boundary

Configuration metadata and tests confirm no model selection, frequency selection, parameter optimization, winner designation, or Phase 8B-2 method was started. No comparison or frequency was removed because of descriptive performance. Multiple-testing correction, Deflated Sharpe Ratio, White Reality Check, Hansen SPA, and new model research remain deferred.

## I. Delivered artifact hashes

| artifact | SHA-256 |
|---|---|
| `pairwise_observed_metrics.csv` | `bc8bdc6830797267b8046bd61a9ce826748498c9bddf5a085a31b590840e367b` |
| `stationary_bootstrap_results.csv` | `5d4717d9f46f81da7c8b4089d16690c6824b21fe7494df9cc5c8dadd4e50e6c2` |
| `hac_mean_return_results.csv` | `c5e65dcf8d7871caf1ae690c48b494b905c8044038c59e18036be57f133cf8b1` |
| `after_tax_descriptive_comparisons.csv` | `59af7ddb1e879be122b894fbaac3dd151817923275f6728992443f41c1f7fc55` |
| `bootstrap_configuration.json` | `87aeb247f72d7902ed1fbfa01b3d179bbdfebe09e8cb040019cc8d38421cbb2c` |
| `phase8b1_report.md` | `4defef48205ab8950aaf8508ca07c412d9017a9d05dfcdcc9f9b87e9a1b3323e` |

## J. Unresolved issues

None within the frozen Phase 8B-1 scope. Undefined Sharpe/Calmar values for zero-volatility/zero-drawdown CASH paths remain unavailable rather than coerced to zero.

PHASE 8B-1 PAIRWISE INFERENCE COMPLETE — NO MODEL OR FREQUENCY SELECTION PERFORMED
