---
name: memoryops-invariant-auditor
description: >
  Audits the MemoryOps AI invariants: tenant isolation, deleted-memory guarantee,
  policy-before-storage, audit coverage, and temporary-chat behavior. Use to
  verify safety properties still hold after a change.
---

# memoryops-invariant-auditor

Operator skill that checks the load-bearing safety properties of MemoryOps AI.
Deterministic: it drives the repo's own tests and eval harness.

## The invariants under audit
1. Tenant isolation — no cross-tenant/user retrieval.
2. Deletion guarantee — deleted memory never retrieved.
3. Provenance — every memory has a source.
4. Graceful degradation — retrieval failure never blocks a response.
5. Policy-before-storage — the broker runs before any write.
6. Temporary chat — no read, no write.
7. Auditability — every lifecycle action is audited.

## Procedure
```bash
cd services/api && pytest -q tests/test_tenant_isolation.py tests/test_deletion.py \
    tests/test_policy_broker.py tests/test_temporary_chat.py
python evals/run_evals.py        # critical kinds: block, deleted, isolation, temporary
```
1. Run the invariant tests + eval harness.
2. For each invariant, map a passing test/eval case to it; flag any unmapped.
3. Inspect recent diffs to `services/api/app/db/`,
   `services/api/app/services/policy_broker.py`, and `gateway.py` for changes that
   could bypass a guarantee.
4. Confirm `AuditService.record` is called on every new lifecycle action.

## Output
An audit table: invariant → evidence (test/eval) → pass/fail, plus any risks.

## Guardrails
- A failing critical eval case (`block`, `deleted`, `isolation`, `temporary`) is a
  hard stop — report FAIL and do not rationalize it away.
