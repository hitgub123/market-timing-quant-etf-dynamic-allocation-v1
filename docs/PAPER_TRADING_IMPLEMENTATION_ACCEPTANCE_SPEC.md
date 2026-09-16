# Paper-Trading Implementation Acceptance Specification

**Status:** `PROPOSED_NOT_FROZEN`  
**Scope:** future audit contract; this phase does not implement the production
paper engine. This specification does not implement the production paper engine.

## 1. Exact equivalence contract

An implementation may be accepted only if deterministic fixture/golden-vector
tests prove equivalence to the closed protocol for:

1. QQQ adjusted-close MA200 using exactly 200 completed observations;
2. NASDAQ calendar schedule eligibility and weekly/monthly/bimonthly/quarterly schedule;
3. strict close-`t` signal boundary and earliest next-eligible-open execution;
4. QQQ/QLD state mapping and zero-CASH-return convention;
5. zero commission and immutable 5-bps canonical simulated fill;
6. theoretical quantity, exact position quantity, target weight, and pre-trade NAV;
7. pre-tax NAV and tax-paid-to-date NAV;
8. 20.315% simplified average-cost immediate realized tax;
9. contemporaneous-pretrade-equity turnover excluding initial deployment and
   terminal liquidation;
10. benchmark NAV, paired daily excess, drawdown, and recovery fields;
11. terminal decision variables and strict outcome priority;
12. append-only IDs, canonical serialization, raw hashes, and hash chain.

The implementation must not add a parameter, indicator, schedule, leverage,
same-day execution, tax treatment, threshold, or outcome rule.

## 2. Required synthetic test families

The acceptance suite uses only `SYNTHETIC_TEST_FIXTURE` inputs and includes:

- 199/200/201 observations, exact-equality/just-above/just-below MA;
- close-to-open lookahead and future-data mutation;
- Monday holiday, month/bimonthly/quarter/year boundary, early close, and DST;
- split/dividend-adjustment and QLD distribution accounting;
- missing close/open, stale close, invalid price, vendor disagreement;
- duplicate execution, restart/recovery, correction/revision, and hash break;
- QLD→CASH and CASH→QLD transitions;
- tax gain, tax loss, average-cost basis, initial deployment, and terminal
  liquidation non-mutation;
- turnover denominator and paired-return alignment;
- every terminal decision region and hard-gate priority.

Expected outputs are written before the test runs and are mathematical fixture
values, never copied from historical strategy outputs. The implementation must
show the fixture status in every test record.

## 3. Evidence and failure

Acceptance evidence includes source code commit, dependency/environment
manifest, fixture inputs/expected outputs, complete pytest output, schema
validation, raw-stub hashes, hash-chain verification, and reviewer sign-off.
Any economic-semantic mismatch fails acceptance, requires a versioned fix and a
complete dry-run restart, and cannot be waived by a favorable return. A broken
provenance boundary is `PROTOCOL_INVALID`, not a performance result.

Production scheduler, official source credentials, official observation
directory, and live capital are outside this specification and remain
inactive.
