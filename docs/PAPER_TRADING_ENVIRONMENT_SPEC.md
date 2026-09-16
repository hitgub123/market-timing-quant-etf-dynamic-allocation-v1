# Paper-Trading Environment Reproducibility Specification

**Status:** `PROPOSED_NOT_FROZEN`  
**Purpose:** define the environment that a future implementation acceptance
must reproduce; this document does not install or upgrade dependencies.

## 1. Reproducibility tuple

Every future record and batch manifest stores:

- repository Git commit and protocol version;
- OS/container identity and architecture;
- Python interpreter version and implementation;
- exact dependency lock from `requirements.txt` plus any approved source
  client package;
- `pandas_market_calendars` version and IANA timezone database version;
- locale, encoding, and process timezone;
- source client version, endpoint version, and sanitized request parameters;
- calendar version and source-page evidence hashes.

The operator's Japan timezone is never used to define a U.S. session date.
Machine timestamps are UTC plus an `America/New_York` rendering where useful.

## 2. Repository baseline

The current repository dependency contract is the pinned `requirements.txt`:

```text
numpy==2.5.0
pandas==3.0.3
pyarrow==24.0.0
PyYAML==6.0.3
pytest==9.1.1
pandas-market-calendars==5.4.0
matplotlib==3.10.6
```

At preparation review the host reported Python 3.14.4, NumPy 2.5.0, pandas
3.0.3, PyArrow 24.0.0, PyYAML 6.0.3, pandas-market-calendars 5.4.0, tzdata
2026.2, and Matplotlib 3.11.0. The Matplotlib drift is recorded, not silently
accepted as the final operational environment; the future implementation
acceptance must either use the lock exactly or record a versioned, audited
exception. No Research v1 dependency was upgraded in this preparation phase.

## 3. Clock and timezone requirements

- OS clock must be synchronized to a documented UTC source (NTP or an approved
  equivalent); the source and last successful sync are logged.
- Clock drift beyond 1 second from the accepted UTC source is a hard
  pre-start/operational incident; beyond the protocol boundary it pauses data
  acquisition and cannot create a signal.
- Every machine timestamp is timezone-aware ISO-8601 with offset and canonical
  UTC; naive datetimes are rejected by schema validation.
- `America/New_York` is the exchange-local display timezone. DST transitions
  are resolved by the pinned IANA database and calendar, not a fixed UTC-5 or
  Japan-local wall clock.

## 4. Dependency and source acceptance

Before freeze, an auditor records the output of `python --version`, `pip
freeze`/equivalent lock verification, `zoneinfo`/tzdata version, package
metadata, Git commit, OS identity, and source-client versions. The exact source
plan entitlement and license terms are recorded without storing credentials.
An unresolved dependency mismatch is an acceptance FAIL; it is not silently
normalized after observations exist.

## 5. Rebuild procedure

1. Create an isolated environment from the pinned lock.
2. Verify package hashes/metadata and the Git commit.
3. Verify the IANA timezone database and XNYS fixture outputs.
4. Verify canonical serialization and schema validators.
5. Execute the uncounted dry-run fixtures only.
6. Archive a sanitized environment manifest with no tokens or secrets.

No environment step starts a scheduler, creates official observation #1, or
opens the 36-month clock.
