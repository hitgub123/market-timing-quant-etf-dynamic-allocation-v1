# Paper Trading Protocol v1 — Tiingo Free Account Acceptance Audit

**Date:** 2026-10-02
**Scope:** performance-blind source-account capability acceptance

## Mechanical gate

`SOURCE_ACCEPTANCE_PENDING_OPERATIONAL_LATENCY_EVIDENCE`

The Tiingo credential was available to one isolated process under a
case-insensitive environment-variable name and was normalized only inside that
process. Its value was not printed, logged, hashed, serialized, persisted, or
placed in request URLs or artifacts.

## Authenticated evidence

Metadata and daily-price requests for QQQ and QLD all returned HTTP 200. QQQ
metadata identified NASDAQ and history from 1999-03-10; QLD metadata identified
NYSE and history from 2006-06-21. The requested price interval returned 438
complete unique sessions for each ETF from 2025-01-02 through 2026-10-01.

Every price row contained raw `open`, `high`, `low`, `close`, and `volume`;
adjusted `adjOpen`, `adjHigh`, `adjLow`, `adjClose`, and `adjVolume`; plus
`divCash` and `splitFactor`. Required null count and duplicate-session count
were zero. OHLC, volume, and corporate-action sanity checks passed.

## Provenance and security

All four HTTP bodies were written to a mode-700 external archive as mode-600
files before parsing. Each was read back and reconstructed byte-identically.
The committed artifact contains only sanitized fields, safe headers, byte
lengths, SHA-256 hashes, and counts. Authorization material and the credential
are absent. Exact raw bytes remain outside Git at:

`~/.local/share/market-timing-quant/tiingo-account-acceptance/2026-10-02/`

The sanitized evidence is `reports/tiingo_free_account_acceptance.json`.
Its SHA-256 is
`7171fb3b43e3c3595048cbc142ea1d2c90b43eb812a759ae19663680f8f6c28c`.

## Remaining gate

Official Tiingo documentation states a 5:30 p.m. U.S. Eastern equity/ETF
update frequency and corrections through 8:00 p.m. Eastern. This account has
not yet been observed publishing a newly completed future session across that
window. A separately frozen PRE_START observation is still required. The
failed EODHD session is not reused as Tiingo evidence.

Tiingo is not promoted, and no Final Freeze, engine, scheduler, official
observation, prospective start, acceptance manifest, or Phase 9 artifact is
created. No MA, signal, historical performance, or source selection by return
was calculated.

## Verification

The dedicated Tiingo account-acceptance collector suite passed **13 tests**,
the documentation-candidate suite passed **7 tests**, the combined source and
prospective-governance controls passed **200 tests**, and the full pytest suite
passed **616 tests**. The committed evidence is JSON-equivalent to the external
sanitized evidence and validates against the source-acceptance schema.

`SOURCE_ACCEPTANCE_PENDING_OPERATIONAL_LATENCY_EVIDENCE`

PAPER TRADING TIINGO FREE ACCOUNT ACCEPTANCE COMPLETE — AWAITING LATENCY EVIDENCE AND EXTERNAL AUDIT
