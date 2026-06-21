# Phase 11 — Security Architecture

**Question:** Threat model, prompt injection, Zero Trust, sensitive data.

## MemoryOps mapping
Tenant/user scoping on every query; **enforced** Postgres RLS (v0.3, `FORCE` +
tenant-isolation policy, session GUC `app.tenant_id`); deterministic secret/PII
detection; prompt-injection / memory-poisoning guard; policy-before-storage;
temporary chat; soft-delete with retrieval-exclusion.

## Gate (must be true to pass)
- No read path returns memory across tenants/users.
- Database-level RLS blocks cross-tenant queries even if app filtering fails.
- Secret-like content is blocked before storage; PII elevates sensitivity.
- Injection patterns are blocked.
- The four load-bearing boundaries in SECURITY.md hold.

## Evidence
- `services/api/app/core/redaction.py` (detectors + injection guard)
- `services/api/app/services/policy_broker.py`
- `services/api/tests/test_tenant_isolation.py`, `test_policy_broker.py`, `test_rls.py`
- `infra/db/migrations/004_rls_policies.sql`, `scripts/check_rls_policies.py`
- [SECURITY.md](../../SECURITY.md), [docs/security.md](../security.md)
- [ADR-003 policy broker](../../infra/adr/ADR-003-policy-broker.md), [ADR-006 pgvector/RLS](../../infra/adr/ADR-006-pgvector-rls-retrieval.md)

## Gaps to close (→ v0.4+)
- Encryption at rest / KMS; auth layer; restricted (non-owner) DB role in deployment.

## Status: ✅ Implemented (v0.3 — RLS enforced; encryption + auth are roadmap)
