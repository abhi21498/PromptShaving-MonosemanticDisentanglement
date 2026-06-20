# Phase 1 — System Architecture

**Question:** What are the boundaries, the architectural style, and the service graph?

## MemoryOps mapping
Monorepo with clear boundaries: `apps/web` (frontend), `services/api` (gateway +
write/read path + governance), `services/worker` (background intelligence),
`infra/db` (schema). The API is layered: `routes → services → db (repository)`,
with `core` cross-cutting (config, logging, reliability, redaction).

## Gate (must be true to pass)
- Each service has a single responsibility and a documented boundary.
- The request path depends only on the repository interface, not a concrete store.
- Cross-cutting concerns live in `core/`, not scattered through services.
- ADRs record the load-bearing decisions.

## Evidence
- [docs/architecture.md](../architecture.md)
- `services/api/app/db/repository.py` (storage abstraction)
- [infra/adr/](../../infra/adr/) (ADR-001..005)

## Status: ✅ Implemented
