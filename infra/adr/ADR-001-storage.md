# ADR-001 — Storage engine for memory records

## Context
MemoryOps AI must store typed memory records with semantic search, strict tenant scoping, an
append-only audit trail, and a credible production path. We also want the project to run and be
testable without standing up infrastructure.

## Decision
Use **PostgreSQL + pgvector** as the system of record for long-term memory, audit logs, feedback, and
settings. Behind the API, access goes through a **repository abstraction** with two implementations:
`postgres` (default in Docker Compose) and `memory` (in-process, default for local/dev/tests).

## Alternatives considered
- **Dedicated vector DB (Pinecone/Weaviate/Qdrant)** — great ANN, but splits the source of truth
  from relational governance data (tenancy, audit, status) and adds an external dependency.
- **SQLite + FAISS** — simple locally, weak multi-tenant/RLS story, poor concurrency for a service.
- **Postgres only (no pgvector)** — loses native vector search; would require app-side similarity.

## Trade-offs
- One engine for relational + vector keeps tenancy, status, and embeddings transactionally
  consistent — at the cost of pgvector ANN being less specialized than purpose-built vector DBs.
- The repository abstraction adds an interface layer but enables zero-infra tests and a clean swap.

## Consequences
- Schema in `infra/db/migrations`; RLS-ready. Embedding column is `vector(1536)` with an ivfflat index.
- Tenant scoping is enforced in repository methods today and RLS-enforceable later.
- The in-memory repo must mirror the same query semantics (tenant filter, exclude deleted).

## Exit strategy
If pgvector recall/latency becomes a bottleneck, introduce a dedicated vector index for the embedding
field only, keyed by `memory_id`, while Postgres remains the system of record. The repository
interface localizes that change.
