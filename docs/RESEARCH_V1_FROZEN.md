# MarketTimingQuant Research v1.0 — Frozen Retrospective Research

Status: **FROZEN**

Tag: `research-v1.0-final`

Commit: `2b2bf987f2e00540412d263a8ef39566af1d1e2a` (`2b2bf98`)

The annotated tag `research-v1.0-final` identifies the exact repository state in
which Phase 0 through Phase 8D completed external audit. The freeze manifest at
`reports/research_v1_freeze_manifest.json` records the runtime, test result,
canonical run IDs, and source/artifact hashes.

## Immutability rule

After `research-v1.0-final`, Phase 0–8D constitutes frozen retrospective
research. The following may not be modified, overwritten, or silently replaced
under Research v1.0:

- historical strategy definitions;
- historical signal definitions;
- historical parameter values;
- historical execution assumptions;
- historical economic paths;
- historical statistical tests;
- historical canonical reports;
- historical raw-data snapshots; and
- accepted research conclusions.

Any future research modification must be issued under a new research version and
must not overwrite Research v1.0 artifacts. A new version must have its own
commit, tag, manifest, source hashes, and audit record.

## Prospective-validation boundary

Prospective validation is a separate activity. Paper-trading observations,
orders, fills, incidents, corrections, and monitoring reports must be stored
under a separate `prospective_validation_v1/` area (with a corresponding
`research_v1/` area for read-only frozen references). They must not be appended
to or mixed into retrospective Phase 0–8D data.

The prospective paper-trading protocol is currently only a draft for audit:
`docs/PAPER_TRADING_VALIDATION_PROTOCOL_V1_DRAFT.md`. No paper-trading engine has
been implemented, no prospective start timestamp has been activated, and no
paper observations have been collected under that draft.

## Governance

Research v1.0 does not select a historical live frequency, authorize live
capital, or automatically promote any model. Any protocol change, new
parameter, new strategy, revised benchmark, revised threshold, or revised
historical conclusion requires a separately labeled research/protocol version
and a fresh external audit.
