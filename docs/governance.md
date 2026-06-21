# Governance — MemoryOps AI

Governance wraps the five verbs (Capture, Store, Retrieve, Update, Forget). It answers: *who* can
do *what* to memory, *why* it happened, and *how* it is proven.

## Memory lifecycle states

```text
            ┌────────── extractor ──────────┐
            ▼                                │
   (candidate) ─▶ policy broker ─▶ decision ─┤
                                             │
   SAVE             ─────────────▶ active ───┼──▶ archived (decayed/aged)
   PENDING_APPROVAL ─────────────▶ pending ──┼──▶ active (approved) / rejected
   BLOCK            ─────────────▶ blocked (never stored content; audit only)
   DROP_LOW_UTILITY ─────────────▶ (discarded; audit only)
   UPDATE_EXISTING  ─────────────▶ active (existing row updated, reinforcement++)
   MERGE_WITH_EXISTING ──────────▶ active (existing row merged)

   active ─▶ (DELETE) ─▶ deleted   [never retrievable again]
```

### LLM extraction is advisory (v0.4)

The extractor may use an LLM provider (`app/llm/`, ADR-008) to propose candidates,
but the **policy broker remains the single authoritative decision point**. LLM
output is schema-validated and advisory only: it cannot upgrade, bypass, or
override a policy decision, and secret-like content is blocked regardless of what
a model proposes. A provider failure or invalid JSON degrades to the deterministic
heuristic and never blocks the response. Conflict detection (`detect_conflicts`)
is observability-only metadata (`conflict_detection_result`) and changes no
decision.

## Decision semantics

| Decision             | Stored? | Retrievable? | Audit action            |
|----------------------|---------|--------------|-------------------------|
| `SAVE`               | yes     | yes          | `memory_created`        |
| `PENDING_APPROVAL`   | yes     | no (pending) | `memory_pending_approval` |
| `BLOCK`              | no      | no           | `memory_blocked`        |
| `DROP_LOW_UTILITY`   | no      | no           | `memory_dropped`        |
| `UPDATE_EXISTING`    | yes     | yes          | `memory_updated`        |
| `MERGE_WITH_EXISTING`| yes     | yes          | `memory_merged`         |

## Roles (target)

- **User** — view, approve/reject, edit, archive, delete own memory; toggle settings.
- **Approver** — clear the pending queue for a tenant.
- **Admin** — tenant metrics, settings, lifecycle oversight (no covert read of raw content beyond
  policy).
- **Auditor** — read-only access to `memory_audit_logs`.

## Audit events (append-only)

`memory_created`, `memory_retrieved`, `memory_updated`, `memory_deleted`, `memory_blocked`,
`memory_dropped`, `memory_pending_approval`, `memory_approved`, `memory_rejected`,
`memory_archived`, `retrieval_failed`, `policy_violation`, `temporary_chat_skipped`,
`cross_tenant_test_passed`, `eval_passed`, `eval_failed`.

Each event records `tenant_id`, `user_id`, `memory_id` (nullable), `action`, `reason`, `metadata`,
`created_at`. Audit logs are never updated or deleted through the API.

## Explainability (invariant #8)

Every chat response carries `used_memories` (the memory IDs + reasons that shaped the answer) and
`candidate_memories` (what the extractor proposed and what the policy broker decided). The dashboard
surfaces both so a user/judge can see *why* the assistant said what it said.

As of v0.3 each `used_memory` also carries a `score_breakdown` (the raw vector / keyword /
importance / confidence / recency / reinforcement signals behind its rank) and `memory_type` /
`source`, and the response reports a `retrieval_mode` (`hybrid` | `fallback` | `none`). This makes
ranking auditable — a reviewer can see not just *that* a memory was used, but exactly which signals
caused it to surface. See [ADR-006](../infra/adr/ADR-006-pgvector-rls-retrieval.md) and
[api-contracts.md](api-contracts.md).

## Context compression & governance order (v0.2.1)

Optional token compression (Headroom, ADR-007) runs strictly **after** governance:
policy checks, retrieval filtering, and context composition all complete first.
Compression touches only the composed, governed context block sent to the LLM —
never the raw user message and never pre-policy content — so the policy broker
always inspects raw content, and deleted / wrong-tenant / temporary-chat content
is never compressed (it is never retrieved/composed in the first place).
Explainability metadata (`used_memories` + score breakdown) is built on the
uncompressed path. See [docs/token-compression.md](token-compression.md).

## Loop governance (v0.3.1)

The governance surface is modeled as `memory.governance`. Viewing, editing,
approving, rejecting, archiving, and deleting memory emits loop events with
structured evidence and links to audit events where a governance record is
written. This keeps operational loop traces separate from append-only audit
records while making the state transition visible.

## Retention & feedback

- `memory_feedback` captures `helpful | wrong | outdated | sensitive | not_relevant` and feeds the
  decay/reflection workers and the eval golden set.
- Retention policy, legal hold, and export are documented in [security.md](security.md) as roadmap.
