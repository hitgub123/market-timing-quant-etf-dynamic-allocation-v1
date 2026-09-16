# Paper-Trading Operational Runbook

**Status:** `PROPOSED_NOT_FROZEN`  
**Scope:** person-executable future procedure; no scheduler or engine is
implemented by this document.

## 1. Before the scheduled close

1. Confirm the process is on the approved Git commit and protocol version.
2. Verify UTC clock synchronization, process timezone, and
   `America/New_York`/calendar version.
3. Verify that the prior batch manifest hash and last-record hash match.
4. Verify source availability, authentication health, rate-limit headroom, and
   the absence of unsanitized credentials in logs.
5. Resolve whether today is an eligible session and whether it is a scheduled
   weekly/monthly/bimonthly/quarterly observation.
6. If any prerequisite is uncertain, pause and append an incident; do not
   manufacture a session or price.

## 2. At the scheduled close

1. Acquire the authoritative QQQ/QLD response and the reconciliation response.
2. Store exact raw bytes, request metadata, retrieval time, endpoint, and
   SHA-256 before parsing.
3. Validate schema, positive prices, completeness, source session date, and
   freshness. A close acquired more than the fixed 15-minute stale grace after
   the calendar close is an incident and cannot create a signal.
4. Reconcile raw OHLC and corporate-action identifiers. Do not average vendors.
5. Only after the close boundary is reached, calculate the MA200 from exactly
   200 completed adjusted QQQ closes.
6. Append one observation record and extend the hash chain. No observation can
   be edited in place.

## 3. After the decision

1. Evaluate the frozen schedule flag and QQQ MA signal.
2. Append one decision record with previous/new target and state-change flag.
3. If a state change requires a theoretical order, append the order with the
   next eligible session, intended timestamp, target weight, quantity,
   pre-trade NAV, and canonical fill convention.
4. If data are incomplete, append a skipped/incident record instead; never
   backdate the decision or use same-day execution. The runbook must never backdate a decision.
5. Hash every appended record and verify its predecessor hash.

## 4. At the next eligible open

1. Use the calendar's next eligible session and official regular open.
2. Acquire the unadjusted open/reference and reconciliation evidence.
3. Calculate the canonical simulated fill using the immutable 5-bps model
   assumption and zero commission.
4. If a valid quote/auction proxy is available, record it separately with
   timestamp, source, side, signed/absolute proxy, and tracking difference.
   Otherwise record `NOT_OBSERVABLE_IN_PAPER_MODE`.
5. Append fill, NAV, and tax records. Do not create a broker transaction or
   call the simulated price a realized execution.

## 5. End of session

1. Value QLD/CASH and QQQ benchmark on the canonical session.
2. Append pre-tax NAV, tax-paid-to-date NAV, daily return, paired excess,
   drawdown, and turnover components.
3. Reconcile NAV and tax to cent tolerance. Keep terminal liquidation as a
   non-mutating diagnostic only.
4. Verify order/decision/observation/tax links and the complete hash chain.
5. Write a batch manifest with raw hashes, record hashes, code commit, and
   sanitized environment metadata.

## 6. Incident handling

Fail closed on missing, stale, invalid, duplicate, ambiguous, halted,
disagreeing, or revised evidence. Append the incident before any retry. A
retry may re-acquire the same immutable request deterministically; it may not
choose a favorable vendor response or rewrite an old record. Use the fixed
taxonomy in `docs/paper_trading_incident_taxonomy.csv`; operators may not select
severity after observing return performance.

## 7. Manual intervention policy

Allowed only when logged: restart a crashed process, restore connectivity,
refresh credentials through the secret store, append an incident, or rerun a
deterministic computation from immutable raw inputs. Forbidden: alter MA200 or
schedule, choose favorable prices, replace authoritative data silently,
backdate a record, delete a loss, reset the start date, modify thresholds, or
change target state. Any intervention affecting evidence pauses the affected
path until the incident is resolved by the predeclared rule.

## 8. End-of-day handoff

The operator hands off the batch manifest, incident list, source/raw hashes,
schema validation result, reconciliation result, and next-session status. The
handoff must be executable by another operator without private context. A
paper PASS is never produced by the runbook; the deterministic outcome
function and external audit remain separate.
