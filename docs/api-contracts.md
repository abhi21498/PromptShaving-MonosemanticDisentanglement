# API Contracts — MemoryOps AI

Canonical reference for the HTTP surface. Changes to `services/api/app/routes/**`
must update this file (enforced by the PR Invariant Evidence Gate).

Base URL (dev): `http://localhost:8000`. Interactive docs: `/docs`.

## POST /api/chat
Write + read path for a turn.

Request:
```json
{ "tenant_id": "tenant_demo", "user_id": "user_demo",
  "message": "Remember that I prefer enterprise-style explanations.",
  "temporary_chat": false, "conversation_id": null }
```
Response:
```json
{ "assistant_message": "...",
  "used_memories": [{ "memory_id": "...", "content": "...", "score": 0.42, "reason": "..." }],
  "candidate_memories": [{ "content": "...", "decision": "SAVE", "type": "procedural",
    "confidence": 0.92, "importance": 8, "sensitivity": "low", "reason": "...", "memory_id": "..." }],
  "audit_event_ids": ["..."], "temporary_chat": false, "trace_id": "..." }
```
`decision ∈ {SAVE, PENDING_APPROVAL, BLOCK, DROP_LOW_UTILITY, UPDATE_EXISTING, MERGE_WITH_EXISTING}`.

## GET /api/memories
Query: `tenant_id` (req), `user_id` (req), `status` (opt), `memory_type` (opt).
Returns `MemoryRecord[]`. Excludes `deleted` by default.

## PATCH /api/memories/{id}
Body: `{ tenant_id, user_id, content?, importance?, confidence?, status? }`.
`status=active` approves a pending memory; `rejected` rejects; `archived` archives.
Returns the updated `MemoryRecord`. Emits an audit event.

## DELETE /api/memories/{id}
Body: `{ tenant_id, user_id }`. Soft delete: `status=deleted`, `deleted_at=now()`,
audit `memory_deleted`. The memory is never retrievable again.

## GET /api/audit
Query: `tenant_id` (req), `user_id` (opt), `limit` (opt, ≤1000).
Returns `AuditEvent[]` (append-only), newest first.

## GET /api/metrics
Query: `tenant_id` (req). Returns counts:
`{ total_memories, by_status, audit_events, by_action }`.

## POST /api/evals/run
Runs the invariant eval harness in-process. Returns
`{ total, passed, failed, pass_rate, results[] }`.

## Ops
- `GET /healthz` → `{ status, version }`
- `GET /readyz` → `{ ready, storage, llm_provider, detail }`
- Every response carries an `x-trace-id` header.
