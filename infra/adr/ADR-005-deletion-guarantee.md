# ADR-005 — Deletion guarantee

## Context
"Forget this" must mean it. A deleted memory must never influence a future response (invariant #2),
yet we also need an audit trail proving the deletion happened (invariant #7). These pull in opposite
directions: erase the data vs. keep the record.

## Decision
Use **soft delete as the default**: `DELETE` sets `status='deleted'` and `deleted_at=now()`, and emits
a `memory_deleted` audit event. **All retrieval queries filter `status='active'`**, so deleted rows
are structurally unreachable by the read path. Content erasure (hard delete / crypto-shred) is a
separate, audited operation for right-to-be-forgotten.

## Alternatives considered
- **Hard delete immediately** — satisfies erasure but destroys the ability to audit/recover and
  risks accidental data loss with no undo.
- **Tombstone in app code only** — fragile; a new query path could forget the filter and leak.

## Trade-offs
- Soft delete keeps content until a retention/erasure job runs; we accept this and pair it with a
  documented crypto-shred path for true erasure.
- The guarantee depends on every read filtering status — enforced centrally in the repository and
  verified by `tests/test_deletion.py`.

## Consequences
- Deleted memory is excluded from retrieval and listing-by-default; only audit retains the event.
- DELETE is idempotent and always audited.
- The status filter lives in one place (repository) to avoid per-endpoint drift.

## Exit strategy
Add a retention worker that crypto-shreds content of `deleted` rows past the retention window while
preserving the audit event (id + action + timestamp, no content), supporting DSAR/erasure.
