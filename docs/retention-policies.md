# Retention Policies + Legal Hold + Consent-Aware Memory (v0.10)

> Adds enterprise retention rules on top of the v0.6–v0.7 lifecycle/deletion
> infrastructure. Retention is **OFF by default** and must be enabled per
> deployment (`MEMORYOPS_WORKERS_RETENTION_ENABLED` / `workers_retention_enabled`).
> See [ADR-013](../infra/adr/ADR-013-retention-legal-hold-consent.md).

## What this adds

| Capability | Meaning |
|---|---|
| **Retention policy packs** | Named bundles mapping a memory's **sensitivity tier** → retention window (days). `default`, `strict`, `extended`. |
| **Legal hold** | A fail-closed override that blocks **all** forgetting (decay, archive, retention-delete, compaction) and the API delete route. Preserves content for discovery. |
| **Consent-aware memory** | Memory carries consent state (`granted` / `withdrawn` / `expired` / `not_required`). Withdrawn or expired consent makes a memory eligible for deletion regardless of age. |
| **Pinned / protected** | Pinned = exempt from decay + archive. Protected = exempt from retention auto-deletion. |
| **Admin-readable decisions** | Every evaluation yields a content-free `RetentionDecision` explaining *why* a memory is retained / held / expired / consent-revoked. |

## Where it lives

```text
services/api/app/db/governance.py        # metadata-driven governance state (helpers)
services/api/app/services/retention.py   # policy packs + evaluate() → RetentionDecision
services/api/app/workers/retention.py    # RetentionWorker (soft-deletes eligible memory)
services/api/app/routes/retention.py     # /api/retention admin/governance API
infra/db/migrations/007_retention_legal_hold_consent.sql
```

Governance state is **metadata-driven** — like the v0.7 compaction tombstone, it
lives in `memory_records.metadata`, so there is no destructive schema change and
both repository backends round-trip it:

```jsonc
metadata = {
  "pinned": true,                 // exempt from decay/archive
  "protected": true,              // exempt from retention auto-deletion
  "governance": {
    "legal_hold": true,           // fail-closed: blocks ALL forgetting
    "legal_hold_reason": "litigation",
    "consent":   { "status": "withdrawn", "captured_at": "…", "expires_at": null },
    "retention": { "policy": "default", "expires_at": "…", "evaluated_at": "…" }
  }
}
```

## Retention policy packs

| Pack | low | medium | high |
|---|---|---|---|
| `default` | 365d | 180d | 90d |
| `strict` | 180d | 90d | 30d |
| `extended` | never | 365d | 180d |

Higher sensitivity → shorter retention. A window of *never* means no time-based
expiry for that tier. Packs are defined in code (`app/services/retention.py`) and
selected by name via `retention_default_policy`; the worker and the API both
accept a policy override.

## Decision precedence (most conservative wins)

```text
1. legal hold / pinned / protected   → held         (never eligible)
2. consent withdrawn or expired      → consent_revoked (eligible now)
3. retention window elapsed          → expired       (eligible)
4. otherwise                         → retain
```

## The retention worker

`RetentionWorker` runs as lifecycle job `retention` (in `DEFAULT_JOB_ORDER`,
before deletion compaction). For each **active** memory in scope it evaluates the
decision, stamps the computed window, and — when enabled — soft-deletes eligible
memory. The deletion then flows through the existing deletion-verification and
compaction workers. Safety rails:

- **OFF by default**; a disabled or `--dry-run` run records decisions but deletes
  nothing (preview mode).
- Legal hold / pin / protection are honored absolutely.
- Only active rows are scanned — the deletion guarantee is preserved and deleted
  memory is never resurrected.
- Tenant + user scoped, idempotent, and content-free in all audit metadata.

```bash
# Preview (records decisions, deletes nothing):
python -m app.workers.runner --tenant t1 --user u1 --job retention --dry-run
# Enabled run (requires workers_retention_enabled=true):
MEMORYOPS_WORKERS_RETENTION_ENABLED=1 \
  python -m app.workers.runner --tenant t1 --user u1 --job retention
```

## Legal hold, end to end

A memory on legal hold survives every forgetting path:

| Path | Behavior under hold |
|---|---|
| decay | skipped (importance frozen) |
| archive | skipped (stays active) |
| retention worker | skipped (`memory_retention_hold_respected`) |
| deletion compaction | **content + vector preserved** (`memory_legal_hold_compaction_blocked`) |
| `DELETE /api/memories/{id}` | refused with **HTTP 409**, attempt audited |

Legal hold is a **preservation** control for compliance/discovery — it is *not*
crypto-shred and does not erase anything.

## API

See [api-contracts.md](api-contracts.md#retention--legal-hold--consent-v010).
All endpoints are tenant + user scoped and audited:

```text
POST /api/retention/legal-hold   {tenant_id,user_id,memory_id,on,reason?}
POST /api/retention/pin          {tenant_id,user_id,memory_id,on}
POST /api/retention/protect      {tenant_id,user_id,memory_id,on}
POST /api/retention/consent      {tenant_id,user_id,memory_id,status,expires_at?}
GET  /api/retention/policies
GET  /api/retention/decisions?tenant_id&user_id&policy?   # read-only preview
GET  /api/retention/memory/{id}?tenant_id&user_id&policy?
```

## Audit vocabulary (content-free)

`retention_scan_started`, `retention_scan_completed`, `retention_decision_recorded`,
`memory_retention_expired`, `memory_consent_revoked`, `memory_retention_hold_respected`,
`memory_legal_hold_compaction_blocked`, `memory_legal_hold_set` /
`memory_legal_hold_released`, `memory_legal_hold_delete_blocked`,
`memory_consent_updated`, `memory_pinned` / `memory_protected`.

## Honest limitations

- Legal hold is preservation, not crypto-shred / physical erasure.
- Retention windows are policy configuration, not legal advice.
- Consent state is recorded and honored; consent *capture* at the UI/SDK edge is
  out of scope for v0.10.
- No cross-tenant retention scheduler — scopes stay explicit (ADR-010/012).
- Retention is OFF by default; enable it deliberately per deployment.
