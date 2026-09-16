# Paper-Trading Golden Fixture Specification

**Status:** `PROPOSED_NOT_FROZEN`  
**Fixture status:** every case is `SYNTHETIC_TEST_FIXTURE`.

## 1. Fixture contract

Fixtures are small, deterministic, versioned inputs with expected outputs
written before execution. They must not use research-v1 historical rows or be
copied into a future official prospective directory. Each fixture carries an
ID, schema version, input hash, expected-output hash, and source-independent
timezone-aware timestamps.

## 2. Required cases

| Fixture ID | Required edge case | Expected invariant |
|---|---|---|
| `MA_199` | 199 completed closes | MA is null; no valid signal/trade |
| `MA_200` | exactly 200 completed closes | MA becomes valid only at the 200th close |
| `MA_201` | 201st close | rolling window drops oldest close deterministically |
| `MA_EQUAL` | close exactly equals MA | strict `close > MA` is false → CASH |
| `MA_ABOVE` | close just above MA | signal is QLD, execution next eligible open |
| `MA_BELOW` | close just below MA | signal is CASH, execution next eligible open |
| `MONDAY_HOLIDAY` | Monday market holiday | weekly schedule is Tuesday/first eligible session |
| `MONTH_BOUNDARY` | first eligible month session | monthly schedule only on first eligible session |
| `BIMONTHLY_BOUNDARY` | odd/even month boundary | only January/March/May/July/September/November schedule |
| `QUARTER_BOUNDARY` | quarter start | first eligible Jan/Apr/Jul/Oct session |
| `YEAR_BOUNDARY` | Dec→Jan | January first eligible session is selected |
| `EARLY_CLOSE` | published early close | close timestamp is calendar close, not 16:00 assumption |
| `DST_SPRING` | New York spring transition | UTC offset changes without changing local session rule |
| `DST_AUTUMN` | New York autumn transition | UTC offset changes without Japan-local inference |
| `SPLIT` | split factor | raw and adjusted fields/revision link remain distinct |
| `DIVIDEND` | dividend adjustment | QQQ MA uses adjusted close; raw open remains unadjusted |
| `MISSING_CLOSE` | no scheduled close | WAIT/SKIP with incident, no signal |
| `MISSING_OPEN` | no next open | no backdated fill; skipped order incident |
| `STALE_CLOSE` | close beyond grace | fail closed; no forward-fill |
| `VENDOR_DISAGREEMENT` | source mismatch | preserve both raw payloads; no averaging |
| `QLD_TO_CASH` | state transition | one SELL/target change at next eligible open |
| `CASH_TO_QLD` | state transition | one BUY/target change at next eligible open |
| `TAX_GAIN` | realized gain | immediate 20.315% tax under average cost |
| `TAX_LOSS` | realized loss | frozen loss/tax semantics, no invented tax |
| `INITIAL_DEPLOYMENT` | initial portfolio | excluded from turnover |
| `TERMINAL_DIAGNOSTIC` | hypothetical liquidation | no SELL, no turnover/tax/holding mutation |
| `HASH_BREAK` | tampered predecessor | protocol-invalidating incident and stop |

## 3. Golden-output rules

Expected outputs are written before execution and are mathematical fixture
values, never copied from historical strategy outputs. They are never copied
from historical strategy outputs. Expected session dates, schedule flags,
signal, target, intended execution, fill, tax, NAV, turnover, hash links, and
incident action are specified as exact fixture values. Any test that needs a market-data quote marks the quote
as synthetic and does not claim an executable broker fill. No expected return
or PASS/FAIL value is selected from historical performance.
