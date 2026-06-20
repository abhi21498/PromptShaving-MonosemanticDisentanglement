# ADR-002 — Hybrid retrieval and ranking

## Context
Retrieval must surface the *right* memories for a turn while honoring tenant isolation, status
filtering (no deleted/pending), and graceful degradation. Pure vector search misses exact matches
(names, IDs, exact phrases); pure keyword search misses paraphrase.

## Decision
Use **hybrid retrieval**: vector similarity (pgvector cosine) + keyword/lexical match, combined by a
weighted **ranker**:

```text
final_score = 0.35·semantic + 0.20·keyword + 0.15·importance
            + 0.10·recency + 0.10·confidence + 0.10·reinforcement
```

Retrieval candidates are always filtered by `tenant_id`, `user_id`, `status='active'`, and
sensitivity/permission before ranking. The top-K feed the Context Composer.

## Alternatives considered
- **Vector-only** — simplest, but poor on exact-match recall and recency control.
- **Keyword-only** — no semantic generalization.
- **Learned reranker (cross-encoder/LLM)** — higher quality, higher latency/cost; deferred.

## Trade-offs
- Fixed weights are transparent and tunable but not learned; we accept this for explainability now.
- Hybrid adds a keyword pass alongside the vector query — modest extra cost for big recall gains.

## Consequences
- Interfaces: `retriever.py`, `ranker.py`, `context_composer.py`.
- The composer emits internal source IDs so responses can report `used_memories` (explainability).
- Retrieval is wrapped in try/except so failures degrade to a non-memory answer (invariant #4).

## Exit strategy
Swap the fixed-weight ranker for a learned reranker behind the same `Ranker` interface; tune weights
from `memory_feedback` signals before investing in a model.
