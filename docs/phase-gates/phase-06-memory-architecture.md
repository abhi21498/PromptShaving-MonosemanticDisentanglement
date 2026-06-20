# Phase 6 — Memory Architecture

**Question:** Short-term vs long-term, RAG, hybrid retrieval.

## MemoryOps mapping
Typed memory (episodic, semantic, procedural, preference, project, constraint,
workflow, knowledge, system). Long-term memory in Postgres + pgvector; working/
session memory is simplified in v0.1–v0.2. Hybrid retrieval = vector cosine +
keyword overlap, blended by the ranker.

## Gate (must be true to pass)
- Memory types are enumerated and treated differently.
- Retrieval is hybrid and tenant/user/status-filtered.
- Deleted and pending memories are never retrievable.
- Embedding generation degrades gracefully (heuristic fallback).

## Evidence
- `services/api/app/services/{retriever,ranker,context_composer}.py`
- `services/api/app/core/embeddings.py`
- `services/api/tests/test_retrieval.py`
- [ADR-002 retrieval](../../infra/adr/ADR-002-retrieval.md)

## Gaps to close (→ v0.3)
- Real provider embeddings; pgvector ANN query in the retriever (currently
  in-process cosine).
- Working/session memory tier in Redis.

## Status: 🟡 Scaffolded (hybrid logic present; provider embeddings pending)
