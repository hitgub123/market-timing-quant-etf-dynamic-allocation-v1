# Phase 8A OOS Evidence Consolidation — Audit Diff

## A. Test result

- Dedicated Phase 8A tests: **11 passed** (`pytest -q tests/test_phase8a_evidence_consolidation.py`).
- Full repository result: **247 passed** (`pytest -q`).

## B. Consolidation scope and exact counts

- Accepted source run IDs are exactly the Phase 7A, Phase 7B, and Fixed MA200 IDs recorded in `canonical_source_manifest.csv`.
- Common OOS calendar: **2013-01-02 through 2026-08-31**, 3,436 actual sessions.
- `oos_champion_table.csv`: **34 rows** = 2 benchmark rows + 4 strategy families × 4 frozen frequencies × 2 tax modes.
- `benchmark_relative_metrics.csv`: **34 rows**.
- `complexity_comparison.csv`: **8 rows** = 2 descriptive comparisons × 4 frequencies.
- Aligned daily files: **116,824 rows** each; 34 identity paths × 3,436 sessions, with no missing or duplicate identity/date keys.

## C. Economic-path reproduction

The dedicated tests compare every Fixed MA200, Phase 7A, and Phase 7B Model A/Model B row against its accepted source metric row. Ending value, CAGR, MaxDD, Calmar, Sharpe, Sortino, Ulcer Index, recovery, turnover, trade count, completed-episode holding periods, transaction costs, and tax paid reproduce the source values within serialization-safe numerical tolerance. No prior strategy ledger, target, trade, position, or tax-ledger file was written.

## D. Benchmark-relative arithmetic

All relative columns use the single accepted QQQ buy-and-hold benchmark on the exact common calendar. Tests verify each subtraction and the frozen QQQ-dominance boolean exactly. QLD buy-and-hold remains visible as a separate benchmark; no benchmark or frequency is ranked or removed.

## E. Accounting and terminal diagnostics

The consolidated rows copy the audited close-decision → next-open execution, 5 bps slippage, zero commission, zero CASH return, continuous ledger, Japanese 20.315% realized-tax, contemporaneous-open pretrade-equity turnover, initial-deployment exclusion, hypothetical-liquidation exclusion, and completed-risky-episode conventions. Terminal liquidation fields are report-only diagnostics. Accepted source equity, positions, trades, and tax-ledger SHA-256 values were rechecked byte-for-byte.

## F. Source/raw integrity

`canonical_source_manifest.csv` records 28 accepted source artifacts and their SHA-256 hashes. The dedicated integrity test confirms the accepted Phase 7A, Phase 7B, and Fixed MA200 economic-path hashes remain unchanged. Immutable raw data remain untouched; no Phase 0–7 artifact was modified.

## G. Selection boundary

Phase 8A performs no optimization, parameter selection, production recommendation, statistical inference, or winner designation. Phase 7B selected-WF rows are consumed as already accepted evidence only. Phase 8B has not started.

## H. Phase 8A artifact hashes

| artifact | SHA-256 |
|---|---|
| `oos_champion_table.csv` | `718ca799db65ea03ae625e400634f5246195e58a8b8fc9ec6416852d7a8a53af` |
| `benchmark_relative_metrics.csv` | `422ab66af47f4a5fe2b82a6f48b9ba363f949bc2acaa8c27d5272d415f8d9139` |
| `complexity_comparison.csv` | `8b21f8464a0c1630c98e835336bd27781e23d4363e7a8180102c1f8000026c31` |
| `canonical_source_manifest.csv` | `3ad085ad440090221f4794f456d18ef2cea433a035a288658c50a12ebbabf6dd` |
| `aligned_daily_equity.csv` | `4271efc5106fb60229fdb7a43c47158b3f229b7dc1ad7ce012a6f01878b200d0` |
| `aligned_daily_returns.csv` | `0e7b790318cfbe0618305e8dbe9fa301911677667385e8d303ee665c3d1e3ee4` |

PHASE 8A EVIDENCE CONSOLIDATION COMPLETE — NO NEW STRATEGY OR PARAMETER SELECTION PERFORMED
