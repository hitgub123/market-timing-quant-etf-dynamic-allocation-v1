# Paper-Trading Source Freeze Readiness

**Status:** `SOURCE_NOT_READY_FOR_FINAL_FREEZE`
**Scope:** operational capability audit only; no vendor credentials were used,
no historical performance was inspected, and no official observation was
created.

## Decision

Alpha Vantage remains the proposed authoritative source for the adjusted QQQ
close and raw QQQ/QLD fields. The selection is unchanged. Public documentation
supports the endpoint roles, but the intended account/plan was not
authenticated in this remediation. Therefore endpoint entitlement, rate-limit
headroom, after-close publication behavior, account terms, and revision
semantics remain `UNVERIFIED_CAPABILITY` or
`VERIFIED_WITH_ACCOUNT_DEPENDENCY`. This is a critical unresolved source
capability, so the final freeze gate is explicitly
`SOURCE_NOT_READY_FOR_FINAL_FREEZE`.

Massive remains reconciliation-only and its split-only adjustment policy is
not promoted to authoritative adjusted-close status. Its optional quote role
is also account/entitlement dependent. No backup source may silently replace
Alpha Vantage after observing which value is favorable.

## Capability register

| Capability | Classification | Freeze evidence still required |
|---|---|---|
| Alpha Vantage `TIME_SERIES_DAILY_ADJUSTED` for QQQ | `VERIFIED_WITH_ACCOUNT_DEPENDENCY` | Authenticated request under intended plan; response contains adjusted close and documented action fields |
| Alpha Vantage raw daily QQQ/QLD | `VERIFIED_WITH_ACCOUNT_DEPENDENCY` | Authenticated request and raw OHLC response under intended plan |
| Alpha Vantage `SPLITS`/`DIVIDENDS` | `VERIFIED_WITH_ACCOUNT_DEPENDENCY` | Authenticated endpoint access and response semantics |
| Daily after-close publication SLA | `UNVERIFIED_CAPABILITY` | Account-specific publication timing and a versioned polling deadline |
| Immutable vendor revision ID/SLA | `UNVERIFIED_CAPABILITY` | Vendor evidence if available; otherwise leave vendor ID null |
| Rate limits and licensing | `UNVERIFIED_CAPABILITY` | Intended account/terms and rate-limit test without storing credentials |
| Raw-byte archiving | `VERIFIED_BY_PROTOCOL_DESIGN` | Dry-run must hash exact response bytes before parsing and retain sanitized request metadata |
| Protocol snapshot reconstruction | `VERIFIED_BY_PROTOCOL_DESIGN` | Dry-run reconstructs the exact 200 adjusted closes, raw hashes, MA200, and signal |
| Massive raw OHLC reconciliation | `VERIFIED_WITH_ACCOUNT_DEPENDENCY` | Authenticated entitlement, historical access, and field-level comparison |
| Massive quote/executable-side proxy | `UNVERIFIED_CAPABILITY` | Entitlement and timestamp/side semantics; otherwise `NOT_OBSERVABLE_IN_PAPER_MODE` |

## Point-in-time source snapshot

At each scheduled decision, the authoritative raw response used for the
MA200 input is archived before parsing. `source_raw_hash` is SHA-256 over the
exact bytes received before decompression/parsing. `source_snapshot_id` is
`sha256:<source_raw_hash>`; if several responses are required, it is the
SHA-256 of a canonical sorted manifest containing each raw hash, endpoint,
sanitized request parameters, and session date. This protocol-owned ID is the
immutable provenance key. A vendor revision ID is optional and remains null if
the vendor does not provide one; the protocol never invents it.

The acceptance test must prove that the snapshot can reproduce the exact 200
adjusted closes seen at decision time, the raw hashes, the computed MA200, and
the signal. A later vendor revision creates an append-only revision record and
cannot mutate the accepted decision.

## Stale-data gate

Publication delay (`data_available_at`) and acquisition delay
(`data_acquired_at`) are separate metadata. A completed-session close acquired
16 minutes after close is not stale solely because a fixed 15-minute timer
elapsed. `STALE` means wrong session key, duplicate prior-session data while
the expected session is absent, or expiry of a predeclared vendor-compatible
publication deadline. Alpha Vantage's deadline is not yet verified; therefore
the fixed 15-minute rule is classified `STALE_SEMANTICS_UNVERIFIED` and cannot
authorize an official signal.

## Freeze checklist

Before an external Operational Freeze Audit can authorize a start, the auditor
must record:

1. authenticated endpoint and plan evidence for all authoritative fields;
2. after-close publication/rate-limit evidence and the deterministic polling
   deadline;
3. sanitized raw-response archive and snapshot reconstruction fixture;
4. revision behavior, correction procedure, and source-page hashes;
5. reconciliation entitlement and disagreement handling;
6. no-secret logs and immutable archive permissions.

Until every critical item is verified, the status remains
`SOURCE_NOT_READY_FOR_FINAL_FREEZE`. This document does not create an
acceptance manifest, scheduler, engine, or prospective observation.
