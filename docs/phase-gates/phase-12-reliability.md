# Phase 12 — Reliability Engineering

**Question:** Circuit breakers, idempotency, checkpointing, graceful degradation.

## MemoryOps mapping
Reliability primitives wrap fallible external calls (LLM, embeddings, DB reads):
timeout, retry-with-backoff, a circuit breaker, and `safe_call` for graceful
degradation. Retrieval failure never blocks a response (invariant #4). Dedup +
`UPDATE_EXISTING` give write idempotency for repeated facts.

## Gate (must be true to pass)
- Retrieval failures degrade to a non-memory answer, not an error.
- Embedding failures fall back to the heuristic embedder.
- Repeated identical captures reinforce, not duplicate.

## Evidence
- `services/api/app/core/reliability.py` (timeout / retry / breaker / safe_call)
- `services/api/app/services/gateway.py` (read path wrapped in `safe_call`)
- `services/api/tests/test_write_path.py::test_duplicate_updates_instead_of_duplicating`

## Status: ✅ Implemented
