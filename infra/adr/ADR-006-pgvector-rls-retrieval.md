# ADR-006 — Real embeddings, pgvector retrieval, and enforced RLS

Status: Accepted (v0.3)

## Context
Through v0.2 the read path used a deterministic heuristic embedder and computed
similarity in Python over all active rows, and Postgres RLS was *enabled but not
enforced* (policies commented out). To make the data layer production-style we
need: (1) a swappable embedding provider with an optional real backend, (2)
database-side vector retrieval, and (3) tenant isolation that holds even if
application filtering has a bug.

## Decision
1. **Embedding provider interface** (`app/embeddings/`): a `EmbeddingProvider`
   Protocol with `embed_text` / `embed_batch`. `StubEmbeddingProvider` is the
   deterministic default (hashed bag-of-words → 1536-dim, L2-normalized, no key,
   test-safe). `OpenAIEmbeddingProvider` is used only when `OPENAI_API_KEY` is
   set and degrades to the stub on any failure. `core/embeddings.py` is now a
   thin back-compat shim.
2. **Vector retrieval via the repository**: `Repository.search_candidates()`
   returns tenant+user-scoped `(memory, vector_similarity)` pairs. On Postgres it
   is a pgvector cosine search (`embedding <=> :q`) with an ivfflat index; in
   memory it computes cosine. Keyword overlap is layered on the returned rows and
   the existing weighted ranker blends the signals, now emitting a per-memory
   `score_breakdown` (explainability, invariant #8).
3. **Enforced RLS** (migration `004`): `FORCE ROW LEVEL SECURITY` + a
   tenant-isolation policy on `memory_records`, `memory_audit_logs`,
   `memory_feedback`, `memory_settings`. The Postgres repository sets the
   transaction-local GUC `app.tenant_id` (and `app.user_id`) on every session.
   RLS is tenant-scoped; per-user isolation stays in application SQL so
   tenant-wide admin/metrics reads keep working.

### Sync, not async
The interface is synchronous to match the end-to-end synchronous read path
(retriever → ranker → composer → gateway → FastAPI routes). Real network I/O
happens inside `embed_text`; this avoids a broad async rewrite while keeping
graceful degradation simple.

## Alternatives
- **Async embedding interface** — more future-proof but forces an async rewrite
  of the whole read path for no current benefit. Rejected for now.
- **RLS via a restricted DB role instead of FORCE** — the standard production
  pattern, but harder to prove in tests; `FORCE` makes the guarantee testable as
  any role. Both are compatible; we document the restricted-role deployment.
- **External vector DB (Qdrant/Weaviate/Pinecone)** — unnecessary at this scale;
  pgvector keeps one datastore and one transaction boundary.

## Trade-offs
- The stub embedder approximates semantic similarity via hashed tokens, so true
  paraphrase recall needs the OpenAI provider; hybrid keyword scoring covers the
  gap offline.
- Tenant-scoped (not user-scoped) RLS is a deliberate choice; user isolation is
  defense-in-depth at the app layer and covered by `test_tenant_isolation.py`.

## Consequences
- New surfaces: `app/embeddings/`, `Repository.search_candidates`,
  `infra/db/migrations/004_rls_policies.sql`, `scripts/check_rls_policies.py`.
- Tests: `test_embeddings.py`, `test_pgvector_retrieval.py`,
  `test_hybrid_retrieval.py`, `test_retrieval_degradation.py`, `test_rls.py`
  (DB-guarded; skips without Postgres). Evals add semantic/keyword/archived/
  score-breakdown cases.
- API: `ChatResponse.retrieval_mode` and `UsedMemory.score_breakdown` /
  `memory_type` / `source` are now returned.

## Exit strategy
If pgvector no longer meets latency or recall needs, the vector layer can move
behind the `search_candidates` repository method to Qdrant, Weaviate, Pinecone,
or pgvectorscale without changing memory lifecycle logic. The embedding backend
can likewise change behind `EmbeddingProvider` with no caller changes.
