# Paper-trading schema package

All files in this directory are JSON Schema 2020-12 design artifacts. They do
not contain official prospective records. Any test payload must set
`fixture_status` to `SYNTHETIC_TEST_FIXTURE` and remain under tests/fixtures or
an in-memory test object.

Shared invariants:

- timestamps are timezone-aware ISO-8601 date-times;
- `session_date` is an America/New_York exchange date;
- primary keys are immutable and unique;
- `record_hash` is SHA-256 of canonical JSON;
- `previous_record_hash` creates the append-only chain;
- null means unavailable, never zero or forward-filled;
- all official records carry protocol/version/source/code provenance.

Production paper directories are intentionally absent and ignored by Git.
