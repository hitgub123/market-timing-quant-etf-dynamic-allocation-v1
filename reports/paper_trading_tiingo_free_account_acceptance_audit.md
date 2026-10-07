# Paper Trading Protocol v1 — Tiingo Free Account Acceptance Audit

**Date:** 2026-10-07
**Scope:** performance-blind account capability and frozen PRE_START publication acceptance

## Mechanical gate

`SOURCE_ACCEPTANCE_PENDING_OPERATIONAL_LATENCY_EVIDENCE`

The observed availability is favorable, but the prior source-readiness document
and the frozen Tiingo-specific plan leave a polling-budget conflict unresolved.
No source promotion or Final Freeze is authorized.

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

The combined sanitized evidence is `reports/tiingo_free_account_acceptance.json`
(SHA-256 `da0540300ccee7b302a3b36afef2dfa03b35aa859010aa36ba6d20a2125fed9b`).
The original capability-only artifact had SHA-256
`7171fb3b43e3c3595048cbc142ea1d2c90b43eb812a759ae19663680f8f6c28c`;
only the publication subsection and gate were added to that result.

## Publication observation

Official Tiingo documentation describes most U.S. equity prices as available
at about 5:30 p.m. Eastern and corrections through 8:00 p.m. Eastern. It is
not treated as a guarantee of an exact publication instant. The 2026-10-06
U.S. session was observed on a schedule frozen before that session opened:

| New York / Tokyo time | QQQ | QLD |
|---|---|---|
| 16:00 / 05:00 | HTTP 200, empty array | HTTP 200, empty array |
| 17:30 / 06:30 | valid completed-session row | valid completed-session row |
| 18:00 / 07:00 | valid completed-session row | valid completed-session row |
| 19:00 / 08:00 | valid completed-session row | valid completed-session row |
| 20:00 / 09:00 | valid completed-session row | valid completed-session row |

The first *observed* availability was poll 2, 5,400 scheduled seconds after
the close, for both symbols. Actual publication is interval-censored: after
the close poll and no later than the poll-2 responses at
2026-10-06T21:30:01.151318Z (QQQ) and 21:30:02.100283Z (QLD). No exact
publication timestamp or daily SLA is invented. All ten fixed requests
returned HTTP 200. Every response was archived outside Git before parsing,
reconstructed byte-identically, and independently checked for the expected
session and required fields. The private archive is mode 700; all ten raw
files and its evidence JSON are mode 600. The committed sanitized copy
`reports/tiingo_prestart_latency_evidence.json` is byte-identical to the
external evidence JSON, SHA-256
`94abcdcf26d1123afc037f544dcf9ecb81cd5d8189919a7e7529518d391bf39d`.
The failed EODHD session was not reused as Tiingo evidence.

## Frozen-contract conflict — acceptance blocker

`docs/PAPER_TRADING_SOURCE_FREEZE_READINESS.md` says the latency check **must
stay within the accepted four-poll budget**. That sentence predates the Tiingo
candidate and was not removed when its surrounding text was updated for
Tiingo. The later Tiingo-specific plan requires poll times, maximum requests,
and deadline to be frozen before the future session but does not explicitly
supersede the four-poll cap. The 2026-10-06 observer was committed before the
session with **five** fixed poll times and ran all five for each symbol (ten
requests). Treating poll 5 as nonexistent or retroactively redefining the
budget would be post-hoc. We therefore do not assert `SOURCE_ACCEPTANCE_PASS`
without external adjudication of which frozen instruction controls. The
mechanical gate remains pending.

The readiness document also calls for returned last date and safe rate
headers in the diagnostic record. Last dates are reconstructible from the
archived raw bodies, but the observer recorded `content_type` rather than
allow-listed response rate headers. The account-capability run observed no
rate-limit headers, yet the publication-run header presence cannot be
reconstructed now. External audit must judge whether this is material. No
missing header or timestamp is invented.

Tiingo is not promoted, and no Final Freeze, engine, scheduler, official
observation, prospective start, acceptance manifest, or Phase 9 artifact is
created. No MA, signal, historical performance, or source selection by return
was calculated.

## PRE_START chronology and interruption

On 2026-10-05 at 19:57:51 UTC, an attempted observer for the 2026-10-05
session was started before market close but after that session had opened.
The acceptance plan requires the schedule to be fixed before the chosen
session. The process was terminated before its first poll; it made zero API
requests and is excluded from acceptance. Its external evidence is marked
`ABORTED_BEFORE_FIRST_POLL`.

The corrected one-shot observer was frozen in commit
`229d6246423c1859191e3732196aad78ef317297` before the next U.S. session
opened and began at 2026-10-05 19:59:30 UTC. Its target was the 2026-10-06
session, with QQQ and QLD polled at 20:00, 21:30, 22:00, 23:00 UTC on
2026-10-06 and 00:00 UTC on 2026-10-07 (ten requests maximum). The final
poll is the prospectively fixed 8:00 p.m. New York correction-window cutoff.
The private raw/evidence archive is
`~/.local/share/market-timing-quant/tiingo-prestart-latency/2026-10-06/`.

On 2026-10-06 at 19:41:51 UTC, before the first scheduled poll, the original
command-session process was found stopped. At that point the evidence had zero
polls and zero raw files. Network resolution was checked after the user
reported reconnection. A guarded resume was added without changing the target
session, symbols, schedule, maximum request count, or deadline. It requires
the original observer to have started before the session opened, the archive
to have no prior polls or raw files, and the resumed process to start before
the first scheduled poll. The detached one-shot process resumed at
2026-10-06 19:47:17 UTC; the interruption is recorded in the private evidence.
Recovery code was committed as `29ed1f820dc04a18a213b605da86ef2392dc1b7a`
before the first poll. No poll was missed, moved, duplicated, or added. The
resumed execution did not alter the pre-session-frozen measurement contract.
This interruption and its recovery remain explicit for external audit.

## Verification

The dedicated capability, candidate, and new publication-audit suites passed
**34 tests** (13 capability, 7 candidate, 14 publication). The combined
source/prospective-governance selection passed **225 tests** and full pytest
passed **630 tests**. The new offline audit rejects missing or changed raw
bytes, wrong permissions,
missing polls, altered schedule, late resume, wrong row count, wrong
classification, and scope violations. Both committed
evidence JSON files validate against their source-acceptance schemas. A
credential-value leak scan covers tracked files, Git diff, reports, metadata,
the external raw responses, and observer log; only a boolean result is
reported. The final scan result is **PASS**. No historical performance,
signal, or strategy result was computed.

`SOURCE_ACCEPTANCE_PENDING_OPERATIONAL_LATENCY_EVIDENCE`

PAPER TRADING TIINGO FREE ACCOUNT ACCEPTANCE PENDING — FROZEN POLL-BUDGET CONFLICT
