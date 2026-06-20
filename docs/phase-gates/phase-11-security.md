# Phase 11 — Security Architecture

**Question:** Threat model, prompt injection, Zero Trust, sensitive data.

## MemoryOps mapping
Tenant/user scoping on every query; RLS-ready schema; deterministic secret/PII
detection; prompt-injection / memory-poisoning guard; policy-before-storage;
temporary chat; soft-delete with retrieval-exclusion.

## Gate (must be true to pass)
- No read path returns memory across tenants/users.
- Secret-like content is blocked before storage; PII elevates sensitivity.
- Injection patterns are blocked.
- The four load-bearing boundaries in SECURITY.md hold.

## Evidence
- `services/api/app/core/redaction.py` (detectors + injection guard)
- `services/api/app/services/policy_broker.py`
- `services/api/tests/test_tenant_isolation.py`, `test_policy_broker.py`
- [SECURITY.md](../../SECURITY.md), [docs/security.md](../security.md)
- [ADR-003 policy broker](../../infra/adr/ADR-003-policy-broker.md)

## Gaps to close (→ v0.3+)
- Enforce (not just enable) Postgres RLS; encryption at rest / KMS; auth layer.

## Status: ✅ Implemented (RLS enforcement + encryption are roadmap)
