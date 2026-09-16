# Paper-Trading Calendar and Schedule Specification

**Status:** `PROPOSED_NOT_FROZEN`  
**Canonical calendar:** `pandas_market_calendars.get_calendar("NASDAQ")`,
version pinned by `requirements.txt`, with published Nasdaq and NYSE calendars
as independent verification sources. QQQ and QLD are Nasdaq-listed ETFs, so
the Nasdaq schedule is the primary exchange calendar for this protocol.

## 1. Session ontology

The canonical session timezone is `America/New_York`. A session date is the
local New York civil date on which the regular U.S. equity core session is
scheduled. The regular core session is 09:30:00–16:00:00 New York time. An
early-close session uses the calendar's published `market_close` (normally
13:00:00 on the day after Thanksgiving and Christmas Eve when published), not
an assumed 16:00 close. The calendar's open/close values are timezone-aware;
their UTC equivalents are stored for machine comparison.

The NYSE and Nasdaq published holiday calendars are evidence sources, not
runtime substitutes. A calendar version and source-page hash are recorded at
operational freeze. The IANA timezone database supplies daylight-saving rules;
the operator's Japan timezone never defines a session date.

## 2. Deterministic functions

Let `eligible_sessions` be the sorted session dates returned by the pinned NASDAQ
calendar. A session is eligible only if it appears in that calendar and has
valid timezone-aware open and close timestamps.

```text
next_eligible_session(d) = first s in eligible_sessions with s > d

is_scheduled_session(session_date, "weekly") =
    session_date is the first eligible date in its Monday–Sunday calendar week

is_scheduled_session(session_date, "monthly") =
    session_date is the first eligible date in its calendar month

is_scheduled_session(session_date, "bimonthly") =
    session_date is the first eligible date in an odd-numbered calendar month
    (January, March, May, July, September, November)

is_scheduled_session(session_date, "quarterly") =
    session_date is the first eligible date in its calendar quarter
```

The bimonthly definition preserves the frozen historical convention: January
is the first selected month, then every second month. It does not mean the
first session after an arbitrary two-month elapsed interval. Year boundaries
are handled by the calendar month/quarter period itself: January 1 is selected
only when it is an eligible session; otherwise the first eligible January
session is selected. A holiday Monday therefore moves the weekly scheduled
session to Tuesday. A month/quarter/year boundary uses the first eligible
session in that period, never the first row returned by a vendor.

No function depends on price, performance, target state, missing data, or a
preferred outcome. The canonical calendar is never inferred from observed price rows.
Schedule flags are stored in the observation ledger before
signal evaluation.

## 3. Exceptional sessions

- **Holiday:** absent from the calendar; no scheduled observation or execution.
- **Monday holiday:** the first eligible session later that week is weekly.
- **Early close:** remains eligible; `exchange_close_at` is the published early
  close and the close must be acquired after that boundary.
- **Unscheduled closure:** the calendar revision/incident ledger records it; no
  backdated session is invented.
- **Trading halt:** a calendar-eligible day can still be an incident and have
  no usable price; it is not converted into a favorable close or open.
- **DST transition:** local New York timestamps are generated from the timezone
  database, then converted to UTC. No fixed Japan-local clock is used.

## 4. Required fixture coverage

The pre-start fixture suite must include, with expected flags written before
execution:

1. normal full weeks;
2. Monday holidays and Tuesday weekly scheduling;
3. month-end and first-session-of-month boundaries;
4. January/February and December/January year boundaries;
5. January/April/July/October quarter boundaries;
6. January/March selected bimonthly months and February/April exclusions;
7. early-close days with a 13:00 calendar close;
8. unscheduled-closure and halt incident examples;
9. both New York DST transitions;
10. next-eligible-session after a holiday and early close.

These are `SYNTHETIC_TEST_FIXTURE` cases only. They are not official
prospective observation rows and must live under tests or fixture documentation
outside any future `paper/observations/` directory.

## 5. Calendar acceptance gates

Before freeze, an auditor must verify the pinned package version, IANA timezone
database version, NASDAQ output for all fixture cases, and agreement with the
published NYSE/Nasdaq holiday and early-close schedules. A disagreement that
cannot be resolved from versioned calendar evidence is a pre-start acceptance
FAIL, is recorded as `CALENDAR_FIXTURE_MISMATCH`, and prevents protocol freeze;
it never changes a historical research result.
