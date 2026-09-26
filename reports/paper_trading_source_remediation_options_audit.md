# Paper Trading Protocol v1 — Source Remediation Options Audit

**Audit type:** performance-blind operational remediation-options audit
**Baseline commit:** `24a759da9a5246a468336dc9e7d11860883467ed`
**Date:** 2026-09-17
**Final source gate:** `SOURCE_REMEDIATION_REQUIRED`

## Scope and boundary

This audit preserves the authenticated source-account acceptance and its
mechanically correct `SOURCE_ACCEPTANCE_FAIL` result. It evaluates only
operational source options needed before the closed Paper Trading Protocol v1
can be accepted. No strategy code, fixed MA200 definition, schedule, costs,
tax rules, thresholds, research artifacts, engine, scheduler, official
observation, or prospective clock was changed. No backtest, return, CAGR,
Sharpe, MaxDD, Calmar, signal ranking, or historical performance comparison
was calculated.

The prior evidence remains in
[`docs/paper_trading_source_account_acceptance.json`](../docs/paper_trading_source_account_acceptance.json)
and
[`reports/paper_trading_source_account_acceptance_audit.md`](paper_trading_source_account_acceptance_audit.md).
The prior gate is intentionally not overwritten.

## Decision summary

No option is mechanically ready for the next account acceptance test. Alpha
Vantage premium and the paid Massive plans are `SOURCE_OPTION_POTENTIALLY_VIABLE`,
but each has account-dependent blockers. Massive Basic is not viable as the
authoritative frozen adjusted-close source because its documented aggregate
adjustment is split-only and its dividend treatment is a separate modeling
choice. A broad alternative-vendor search was not opened while these two paths
remain potentially viable.

The resulting mechanical status is:

`SOURCE_REMEDIATION_REQUIRED`

The next action is an external decision about which potentially viable option
to submit to a fresh source-account acceptance. No plan was purchased and no
source was promoted.

## Remediation matrix

The complete machine-readable matrix is
[`docs/paper_trading_source_remediation_matrix.csv`](../docs/paper_trading_source_remediation_matrix.csv).
Classifications are capability classifications, not historical-result claims.

| Option | Classification | Narrow reason |
|---|---|---|
| Alpha Vantage minimum premium entitlement | `SOURCE_OPTION_POTENTIALLY_VIABLE` | Public documentation describes 25+ years of daily adjusted/full history, but the tested free account was premium-restricted and exact plan entitlement, limits, price, publication, and revision behavior remain unaccepted. |
| Massive Stocks Basic Free | `SOURCE_OPTION_NOT_VIABLE` | Authenticated raw access and >200 observed rows are useful for reconciliation, but aggregate adjustment is split-only and is not the frozen adjusted-close signal. |
| Massive Starter / Developer / Advanced | `SOURCE_OPTION_POTENTIALLY_VIABLE` | Paid plans list sufficient history and call capacity, and corporate-action factors are documented; a deterministic, predeclared split-plus-dividend reconstruction still requires an acceptance test and must prove frozen-signal semantic compatibility without discretionary choices. |
| Alternative vendors | `SOURCE_OPTION_INSUFFICIENT_EVIDENCE` | Not investigated; broad search is outside this remediation scope while A/B remain potentially viable. |

## A. Alpha Vantage premium path

Alpha Vantage's official documentation says the daily adjusted endpoint is a
premium endpoint, covers 25+ years, and includes adjusted close plus historical
split/dividend events; the separate daily endpoint documents compact and full
history behavior. The prior authenticated free-key acceptance recorded the
actual premium restriction, 100-row compact responses, accessible SPLITS and
DIVIDENDS, raw-byte reconstruction, and the observed free-key policy of one
request per second and 25 requests per day. See the [Alpha Vantage API
documentation](https://www.alphavantage.co/documentation/) and [Alpha Vantage
premium page](https://www.alphavantage.co/premium/).

The minimum entitlement is therefore an Alpha plan that demonstrably unlocks
`TIME_SERIES_DAILY_ADJUSTED` for QQQ, full raw daily QQQ/QLD, at least 200
completed adjusted rows, SPLITS, DIVIDENDS, and the conservative operational
request envelope. The official page extraction did not expose a deterministic
numeric current plan price, so no price is invented and no purchase is made.
The option remains potentially viable, not ready.

No deterministic after-close publication SLA or immutable revision guarantee
was established. The existing protocol therefore still requires a
pre-start latency observation if this option proceeds; no polling deadline is
selected from investment outcomes.

## B. Massive candidate path

Massive remains a candidate only; it is not promoted by this audit. Massive's
official custom-bars documentation exposes raw daily aggregates and
an `adjusted` switch. Massive's adjustment policy states that aggregate bars
are split-adjusted by default, `adjusted=false` returns raw values, and
dividend adjustment is not native; dividend handling is a modeling choice.
The official stocks overview and pricing page list Basic (5 calls/minute,
2-year history, EOD), Starter (unlimited calls, 5-year history, 15-minute
delayed), Developer (10-year history), and Advanced (20+ years, realtime).
The new splits/dividends endpoints and adjustment factors are documented as
available across Stocks plans. See [custom bars](https://www.massive.com/docs/rest/stocks/aggregates/custom-bars),
[Stocks overview](https://massive.com/docs/rest/stocks/overview), [pricing](https://massive.com/pricing),
[adjustment policy](https://massive.com/knowledge-base/article/is-massives-stock-data-adjusted-for-splits-or-dividends),
and [splits/dividends endpoints](https://www.massive.com/blog/new-splits-and-dividends-endpoints).

The prior authenticated run observed 501 delayed day-aggregate rows for each
of QQQ and QLD when a much older range was requested. That is account evidence
for raw reconciliation only; it is not evidence that the requested full
history or a frozen adjusted signal is available.

Paid Massive plans are potentially viable only as an operational remediation:
raw bars plus immutable split/dividend responses could feed a single
predeclared factor algorithm. That algorithm would have to be accepted before
use and prove that it is semantically equivalent to the frozen authoritative
adjusted close. If it introduces a discretionary dividend convention or a new
signal definition, it is not a remediation and the option is not viable. No
Massive plan is promoted by this audit.

The listed plan prices are reproduced as public-documentation evidence only;
no purchase or account change occurred. Licensing, exact entitlement, raw
history, revisions, and a deterministic after-close publication SLA remain
unresolved. No deterministic SLA was invented, so PRE_START operational
latency observation remains required for any future candidate.

## Massive Basic Free authenticated feasibility follow-up

On 2026-09-26, a narrow authenticated follow-up tested the existing Massive
Basic Free option without running a strategy, signal, backtest, or historical
performance calculation. The credential was supplied only to an isolated
collector process and was neither printed nor retained. The sanitized evidence
is recorded in
[`docs/paper_trading_massive_basic_free_feasibility.json`](../docs/paper_trading_massive_basic_free_feasibility.json).

Authenticated daily aggregate requests returned 501 unique completed sessions
for each of QQQ raw, QQQ split-adjusted, QLD raw, and QLD split-adjusted data,
from 2024-09-26 through 2026-09-25. Every series included the expected last
completed session, with no missing or duplicate sessions. This passes the
200-observation depth requirement. The observed fields were open, high, low,
close, volume, volume-weighted price, transaction count, and timestamp.

Authenticated corporate-action requests also succeeded. QQQ returned zero
split rows and 65 dividend rows; QLD returned six split rows and 34 dividend
rows. Each of the eight raw HTTP response bodies was archived before parsing,
read back byte-identically, and then removed with the isolated temporary
directory. The evidence artifact records only byte counts and SHA-256 digests,
not request credentials or authorization material.

The account response did not expose an exact plan label or rate-limit headers.
Its two-year/501-session capability is consistent with the documented Basic
plan. Public documentation specifies 5 requests per minute; all eight
authenticated requests succeeded when spaced by 13 seconds. This observation
does not by itself accept the broader operational request-capacity envelope.

The feasibility gate nevertheless fails on frozen-signal semantics. Massive
documents `adjusted=true` as split adjustment and explicitly does not provide
native dividend-adjusted aggregates. Reconstructing a dividend-adjusted close
would require choices about event timing, reinvestment price, tax treatment,
and cash-distribution handling. Those are modeling choices, not authenticated
vendor facts, and they are absent from the frozen source contract. Exact
semantic equivalence to the frozen dividend-adjusted MA200 input is therefore
not proven and cannot be asserted without changing the protocol methodology.

Basic's EOD description also does not establish a deterministic after-close
publication SLA. PRE_START operational latency evidence would still be
required if a semantically compatible option were later accepted. Licensing
for authoritative operational use remains unresolved. No SLA, deadline, or
license permission is invented.

The mechanically correct option classification remains:

`SOURCE_OPTION_NOT_VIABLE`

Massive remains a reconciliation source only. The prior Alpha Vantage gate
remains `SOURCE_ACCEPTANCE_FAIL`; this follow-up does not overwrite it, promote
Massive, authorize a purchase, or start any prospective operation.

## Required next acceptance evidence

The next acceptance must be run against exactly one externally chosen account
option, with the same fail-closed boundary:

1. sanitized entitlement and rate-limit evidence for QQQ and QLD;
2. at least 200 completed adjusted observations plus complete raw OHLCV;
3. SPLITS and DIVIDENDS with field semantics and immutable raw snapshots;
4. a deterministic, vendor-compatible publication/freshness rule or an
   explicit unresolved-latency gate;
5. revision behavior, licensing, and request-capacity evidence;
6. byte reconstruction before parsing, with no credentials in artifacts; and
7. for Massive, a predeclared adjustment algorithm accepted as equivalent to
   the frozen signal before any official observation.

This is an operational source gate only. It does not authorize Final Freeze,
the engine, a scheduler, an official observation, the 36-month clock, or
Phase 9.

## Test and integrity result

Dedicated remediation and Massive Basic feasibility tests verify the matrix
classifications, failed-gate preservation, authenticated history/corporate-
action evidence, byte reconstruction, no-selection/no-performance boundary,
source-role boundaries, official documentation references, and absence of
engine/scheduler/Phase 9 artifacts. The dedicated Massive Basic feasibility
suite passed **9 tests**. The combined remediation, source-acceptance,
prospective-governance, and operational contract controls passed **146 tests**.
The full pytest suite passed **562 tests**. The source-acceptance secret-leak
control remained passing; it scans
tracked files, Git diff, reports, generated metadata, acceptance output, and
sanitized request metadata without exposing credentials.

`SOURCE_REMEDIATION_REQUIRED`

PAPER TRADING SOURCE REMEDIATION OPTIONS AUDIT COMPLETE — AWAITING EXTERNAL AUDIT
