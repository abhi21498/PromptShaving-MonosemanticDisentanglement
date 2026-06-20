# ADR-004 — Observability and audit

## Context
An enterprise memory system must be explainable and operable: we need to know what was stored,
retrieved, blocked, and deleted, with latency and counts — and to prove lifecycle integrity to an
auditor (invariant #7, #8).

## Decision
Two complementary streams:

1. **Audit log** (`memory_audit_logs`) — append-only, business-level lifecycle events
   (`memory_created`, `memory_blocked`, `memory_deleted`, …). Source of truth for governance.
2. **Structured operational logs** — one JSON line per request with `trace_id`, `tenant_id`,
   `user_id`, `event`, `latency_ms`, `memory_count`, `status`. OpenTelemetry-ready span boundaries.

Admin metrics are derived from these: write/retrieval/block/delete counts, retrieval latency,
candidate→saved rate, correction rate, helpfulness rate.

## Alternatives considered
- **Logs only** — no immutable governance trail; can't answer "prove this was deleted".
- **Audit only** — no operational latency/throughput visibility.
- **Full Grafana/Tempo/Langfuse now** — valuable but heavy for Phase 1; documented as roadmap.

## Trade-offs
- Two streams mean two write paths; we accept this because audit and ops have different retention,
  access, and immutability requirements.

## Consequences
- `AuditService.record(...)` is called by every lifecycle action; missing it is a review failure.
- `app/core/logging.py` emits structured JSON; `trace_id` is generated per request in the gateway.
- `GET /api/audit` and the admin dashboard surface both streams.

## Exit strategy
Export OTel traces to Tempo/Jaeger and metrics to Prometheus/Grafana; ship LLM traces to Langfuse.
The `trace_id` and structured fields are already present, so this is a transport change.
