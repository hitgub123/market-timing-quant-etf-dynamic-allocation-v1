# Research v1.0 Freeze Audit

**Status:** PASS  
**Verification timestamp:** 2026-09-16T04:52:10Z  
**Accepted historical commit:** `2b2bf987f2e00540412d263a8ef39566af1d1e2a` (`2b2bf98`)

## A. Repository gate

- `git rev-parse HEAD` matched the accepted commit exactly.
- The pre-freeze working tree was clean.
- The accepted pre-freeze baseline run of `pytest -q` completed with **371
  passed**, 0 failed. After adding the 13 governance tests, the complete freeze
  package run completed with **384 passed**, 0 failed.
- No paper-trading engine, broker connector, scheduler, order simulator, or
  prospective observation writer was run or added.

## B. Immutable tag

The annotated tag `research-v1.0-final` was created because it did not exist.
It points exactly to `2b2bf987f2e00540412d263a8ef39566af1d1e2a` and has message:

`MarketTimingQuant Research v1.0 — Phase 0–8D audit-accepted historical research freeze`

The tag is an immutable reference to the accepted retrospective research
commit. The freeze/protocol documentation is committed separately and does not
move the tag.

## C. Hash verification

The freeze gate independently verified every hash referenced by Phase 8D before
creating this freeze package:

| Source group | Canonical run | Files verified |
|---|---|---:|
| Phase 7B | `20260914_phase7b_turnover_audit_final` | 6 |
| Phase 8A | `20260914_phase8a_oos_evidence_consolidation_final` | 9 |
| Phase 8B-1 | `20260914_phase8b1_null_test_remediation_candidate` | 7 |
| Phase 8B-2 remediation | `20260915_phase8b2_dsr_remediation_candidate` | 11 |
| Phase 8C | `20260915_phase8c_final_robustness_audit` | 14 |
| Raw snapshots | `data/raw/manifest.yaml` | 5 |
| **Total** |  | **52** |

All seven Phase 8D artifacts were also checked byte-for-byte. Their SHA-256
values are:

| Artifact | SHA-256 |
|---|---|
| `final_evidence_matrix.csv` | `ef35796946bfd587f14311003dfc4575f98657c70f5b9d79992ee70cafc78605` |
| `original_goal_scorecard.csv` | `ad3998d4291cb9a6f77c4a32d09aa6c07f3e82efe4ffdc1d2f087868169ae462` |
| `complexity_incremental_evidence.csv` | `b622514a52fbe60c25a63856684a03004a5a3041a06e1a9d7ca457dc8f8f180f` |
| `final_claim_evidence_ledger.csv` | `92a9c23854dd13302d4ee3f92aa8f37f44988389caa2c0b73bbb5faffe3ec8a5` |
| `phase8d_configuration.json` | `3bee1f2da9872c7338e0b39afadf7def0c13be327c678d835863e7780381362a` |
| `phase8d_final_research_verdict.md` | `4470e42756cb5f02e6cd551224250cd15dc8632463eec273c07b77c9db80b284` |
| `phase8d_audit_diff.md` | `fb9bc23354eb089157ea651c97991673e24e57e805a415295f67332f008e64a7` |

The complete source-by-source hash manifest, canonical run IDs, runtime, and
test record are in `research_v1_freeze_manifest.json`. Its companion SHA-256
file is `research_v1_freeze_manifest.sha256`. The manifest SHA-256 is
`dcb8f9d79de93c61e0bd7d93b743b0356be9eb3b1467acf5db9a58563889d400`.

## D. Freeze scope

Research v1.0 freezes the retrospective Phase 0–8D definitions, data, paths,
reports, tests, and conclusions. Prospective validation remains a separate,
not-yet-frozen design. No prospective start timestamp is active, no paper
observations exist, and no historical frequency or live winner is selected.

The protocol document is explicitly a draft for external audit. It proposes
controls and thresholds without implementing them or collecting observations.
Any threshold or unresolved decision is marked `PROPOSED_NOT_FROZEN` and must be
frozen under a later protocol commit before use.

## E. Accepted conclusions carried into the freeze

- Final research classification: `PROMISING_BUT_INSUFFICIENT`.
- Paper-validation decision: `PROCEED_TO_PAPER_TRADING_VALIDATION` (prospective
  validation only; no live-capital authorization).
- Fixed MA200 evidence: `MODERATE`.
- Phase7A incremental complexity: `NOT_JUSTIFIED`.
- Phase7B: `NO_DEMONSTRATED_VALUE`.
- DSR: `DSR_NOT_IDENTIFIABLE_FROM_FROZEN_ARTIFACTS`.

RESEARCH V1.0 FREEZE PASS
