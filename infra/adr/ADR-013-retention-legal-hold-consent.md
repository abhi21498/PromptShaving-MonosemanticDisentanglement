# ADR-013 — Retention Policies + Legal Hold + Consent-Aware Memory

- Status: Accepted (v0.10)
- Date: 2026-06-22
- Supersedes: none
- Related: ADR-010 (background lifecycle workers), ADR-011 (deletion compaction),
  ADR-012 (worker runtime), ADR-006 (RLS / tenant isolation)

## Context

Through v0.9 MemoryOps could *capture, retrieve, forget, delete, compact, and
verify* memory, but forgetting was driven only by age/usage heuristics and an
explicit user/worker delete. It had no notion of **how long a memory should be
kept**, no way to **freeze** a memory against deletion for compliance, and no
**consent** state to honor when a user withdraws permission to retain their data.
Those are table-stakes for enterprise governance (GDPR/CCPA-style retention,
litigation hold, consent management).

The five lifecycle invariants must still hold: tenant isolation, the deletion
guarantee, provenance, graceful degradation, policy-before-storage, and
auditability. Retention must make the system *more* conservative, never bypass the
policy broker, and never resurrect deleted memory.

## Decision

Add a **retention layer** on top of the existing deletion + compaction pipeline.

1. **Governance state is metadata-driven** (`app/db/governance.py`). Like the v0.7
   compaction tombstone and v0.6 lifecycle markers, legal hold, consent, pins,
   protection, and the computed retention window live in `memory_records.metadata`
   — content-free, round-tripped by both repository backends, and surfaced through
   one helper module so no caller hand-rolls metadata keys. Migration
   `007_retention_legal_hold_consent.sql` adds partial/GIN indexes for efficient
   "on hold" / "consent withdrawn" lookups and documents the contract. (We also
   fixed `postgres_repo.update_memory` to persist `extra_metadata`, which the
   lifecycle markers already relied on.)

2. **A retention policy engine** (`app/services/retention.py`). A named **policy
   pack** maps a memory's sensitivity tier to a retention window in days
   (`default` / `strict` / `extended`, selectable, extensible in code — no DB or
   API keys). `evaluate()` returns an admin-readable `RetentionDecision`
   explaining *why* a memory is retained, held, expired, or had consent revoked.
   The engine decides eligibility; it never deletes.

3. **A retention worker** (`app/workers/retention.py`). It scans *active* memory,
   evaluates each against the policy pack, and soft-deletes memory whose window
   elapsed or whose consent was withdrawn/expired — then the existing
   deletion-verification + compaction workers handle the deleted rows. It is
   **OFF by default** (`workers_retention_enabled`); a disabled or dry run records
   decisions but deletes nothing, so operators can preview impact safely.

4. **Legal hold is a fail-closed override across the whole lifecycle.** A held
   memory is never decayed, never archived, never retention-deleted, never
   compacted (its content is *preserved* for discovery), and the API delete route
   refuses to delete it (HTTP 409). Pins exempt from decay/archive; protection
   exempts from retention auto-deletion. Overrides always win in the engine's
   precedence: `held` > `consent_revoked` > `expired` > `retain`.

5. **An admin/governance API** (`app/routes/retention.py`) to set legal hold /
   pin / protect / consent and to read the read-only retention-decision preview.
   Every mutation appends a content-free audit event.

## Consequences

- Retention/hold/consent ship without a destructive schema change and work
  identically on the in-memory and Postgres backends.
- The policy broker stays authoritative; retention is advisory metadata that only
  ever makes the system more conservative. Deleted memory still flows through the
  v0.7 deletion guarantee + compaction + verification path unchanged.
- Honest scope: legal hold is a **preservation** control (it retains content for
  discovery), not crypto-shred; retention windows are policy, not a legal opinion;
  consent state is recorded and honored but consent *capture* at the UI/SDK edge
  is out of scope for v0.10. Cross-tenant retention scheduling remains explicit
  (per ADR-010/012). Retention is OFF by default and must be enabled per
  deployment.

See docs/retention-policies.md, docs/governance.md, docs/security.md, and
docs/phase-gates/phase-15-governance.md.
