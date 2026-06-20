# Phase 0 — Cognitive Design

**Question:** What thinking should the system perform? What should memory *decide*?

## MemoryOps mapping
Memory is modeled as a governed decision system, not a store. The core cognition
is the **policy decision**: for each candidate memory, decide
`SAVE / PENDING_APPROVAL / BLOCK / DROP_LOW_UTILITY / UPDATE_EXISTING / MERGE`.
The five verbs — capture, store, retrieve, update, forget — are wrapped by
governance.

## Gate (must be true to pass)
- The lifecycle is written down (capture → evaluate → store → retrieve → rank →
  compose → update → forget → audit).
- The seven invariants are explicit and testable.
- Decisions are enumerated and each maps to a storage action + audit verb.

## Evidence
- [README — invariants](../../README.md#enterprise-invariants)
- [docs/architecture.md](../architecture.md), [docs/governance.md](../governance.md)
- `services/api/app/schemas/memory.py` (`Decision` enum)

## Status: ✅ Implemented
