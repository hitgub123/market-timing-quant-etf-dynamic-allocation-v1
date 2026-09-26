# EODHD Free PRE_START Publication-Latency Runbook

**Status:** `READY_FOR_MANUAL_ONE_SHOT_EXECUTION`
**Classification:** nonofficial source-operability evidence only

## Boundary

This runbook closes only the pending EODHD publication-latency gate. It does
not calculate MA200, a signal, performance, an order, a fill, or an official
paper-trading observation. It does not start an engine, scheduler, prospective
clock, Final Freeze, or Phase 9.

The observer is `scripts/eodhd_prestart_latency_observer.py`. It must be
started manually before the expected exchange close. It refuses to start more
than 60 seconds after the close, makes at most four requests, and uses the
frozen offsets 0, 300, 600, and 900 seconds.

## Scheduled control for 2026-09-28

- Expected U.S. session: `2026-09-28`
- Exchange close: `2026-09-28T20:00:00Z`
- Japan close time: `2026-09-29 05:00:00 JST`
- Poll targets in Japan: `05:00`, `05:05`, `05:10`, `05:15`
- Documented deadline: `2026-09-28T20:15:00Z`

The operator should open the existing Codex task by 04:55 JST and request:

`开始 EODHD PRE_START 延迟观测`

No credential is pasted into chat or passed on the command line. The isolated
launcher supplies the external credential to the observer process. The script
prints only credential presence, the planned session/times, the final status,
poll count, and evidence path.

## Raw archive boundary

The default archive is outside Git:

`~/.local/share/market-timing-quant/prestart-latency/2026-09-28/`

The directory is created with mode 700 and raw responses/evidence with mode
600. The observer refuses an archive path inside the repository and refuses to
overwrite an existing session directory. Each raw response is written before
parsing and read back for byte equality. The sanitized evidence contains only:

- expected session and UTC timestamps;
- fixed poll ordinal and schedule;
- HTTP status and allow-listed response headers;
- response byte length and SHA-256;
- archive filename, returned row count, and last session date;
- body classification and first availability time; and
- explicit no-signal/no-performance/no-official-observation controls.

The key, authorization material, and secret-bearing URL are never stored.

## Mechanical classifications

| Condition | Result |
|---|---|
| A valid `2026-09-28` QQQ.US row first appears from a request started no later than the documented deadline | `PASS_WITHIN_DOCUMENTED_WINDOW` |
| A valid row is observed only after the documented deadline | `FAIL_AVAILABLE_AFTER_DOCUMENTED_WINDOW` |
| No valid row appears by the fourth poll | `FAIL_NOT_AVAILABLE_BY_DOCUMENTED_DEADLINE` |
| Observer starts over 60 seconds late | `START_TOO_LATE_FOR_LATENCY_EVIDENCE`; no request is made |
| Wrong date, duplicate expected row, invalid JSON/OHLC, or request error | Preserve sanitized poll evidence and continue only within the four frozen polls |

A pass permits updating the source gate for external audit. It does not itself
authorize Final Freeze or a prospective start. A failure cannot be repaired by
extending the deadline after seeing the result, substituting Massive, or
rerunning the same session into a competing archive.

## Preflight without an API request

`--validate-only` verifies credential presence, archive location, expected
session, close time, and poll count. It does not create the archive or call the
vendor. The live command is intentionally executed by Codex through the
isolated credential launcher so the key never appears in shell history.

## Post-run handling

After the process exits, Codex must:

1. read only the sanitized evidence and verify external raw file hashes;
2. run the evidence-contract and secret-leak tests;
3. update the source acceptance artifact/report with the mechanical result;
4. run dedicated, governance, and full pytest suites;
5. commit the evidence classification separately; and
6. leave Final Freeze, the engine, scheduler, official observation, and Phase 9
   untouched pending external source audit.
