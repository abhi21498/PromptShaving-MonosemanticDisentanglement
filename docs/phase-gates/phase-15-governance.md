# Phase 15 — Governance & Compliance

**Question:** Audit trails, explainability, data residency, deletion.

## MemoryOps mapping
Typed lifecycle states with approve/reject/edit/archive/delete; append-only audit;
provenance on every memory; explainable `used_memories` on every response;
soft-delete guarantee that deleted memory is never retrieved.

## Gate (must be true to pass)
- Every memory has non-null provenance (`source`).
- Every lifecycle action is audited.
- Deleted memory is excluded from all reads.
- Responses can report which memories shaped them.

## Evidence
- `services/api/app/services/{write_service,audit}.py`
- `services/api/app/routes/memories.py` (approve/reject/archive/delete)
- `services/api/tests/test_deletion.py`
- [docs/governance.md](../governance.md)
- [ADR-005 deletion guarantee](../../infra/adr/ADR-005-deletion-guarantee.md)

## Deployment governance (v0.3.2)
Deployment is a single, auditable target — **Railway only**, one project, config
as code in `railway/`. No Vercel or ad-hoc host. This keeps the data-residency
and access story in one place; see
[phase-13-infrastructure.md](phase-13-infrastructure.md) and
[docs/deployment/railway.md](../deployment/railway.md).

## Gaps to close (→ later)
- Retention/legal-hold/export (DSAR), regional residency, crypto-shred worker.

## Status: ✅ Implemented (retention/residency are roadmap)

## v0.5 Governance UI / Control Plane Evidence

The v0.5 governance UI adds human-in-the-loop memory review and audit surfaces for the MemoryOps control plane.

Evidence added in this milestone:

- `docs/governance-ui.md`
- `docs/memory-control-plane.md`
- `docs/phase-gates/phase-06-human-in-the-loop.md`
- `infra/adr/ADR-009-memory-control-plane.md`
- `services/api/tests/test_governance_api.py`

Governance requirements covered:

- memory detail visibility
- memory provenance visibility
- memory audit timeline visibility
- memory-specific audit filtering
- tenant/user scoped memory access
- deletion and isolation tests
- UI surfaces for memory governance workflows

Runtime lifecycle workers (v0.6), physical vector compaction + deletion purge
verification (v0.7), and the worker runtime (v0.8) have since landed.

## Retention + legal hold + consent (v0.10)

This phase now also covers enterprise retention governance (ADR-013,
[retention-policies.md](../retention-policies.md)):

- **Retention policy packs** (sensitivity tier → window) drive a `retention`
  worker that soft-deletes expired / consent-revoked memory; OFF by default, with
  an admin-readable decision preview.
- **Legal hold** is a fail-closed override across the lifecycle (decay, archive,
  retention, compaction) and the API delete route (HTTP 409) — a *preservation*
  control for discovery, not crypto-shred.
- **Consent-aware memory**: withdrawn/expired consent makes memory eligible for
  the normal soft-delete → verification → compaction path.

Gate evidence: `tests/test_retention_policy.py`, `tests/test_retention_worker.py`,
`tests/test_legal_hold.py`, `tests/test_governance_flags.py`,
`tests/test_retention_api.py`, plus retention/legal-hold assertions added to
`tests/test_deletion.py`, `tests/test_tenant_isolation.py`,
`tests/test_deletion_compaction_worker.py`, and `tests/test_governance_api.py`.
Governance state is content-free metadata and every action is audited.
