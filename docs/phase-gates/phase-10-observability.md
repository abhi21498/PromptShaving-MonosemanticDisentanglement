# Phase 10 — Observability

**Question:** Traces, token cost, alerts, prompt inspection.

## MemoryOps mapping
Two streams: append-only audit log (business events) and structured JSON logs with
a secret-redacting formatter + per-request `trace_id`. Metrics are derived and
surfaced on the admin dashboard and `GET /api/metrics`.

## Gate (must be true to pass)
- Every lifecycle action emits an audit event.
- Every request log line carries `trace_id` and never leaks secrets.
- Metrics (writes, blocks, deletes, retrievals, audit count) are queryable.

## Evidence
- `services/api/app/core/logging.py` (redacting JSON formatter)
- `services/api/app/services/audit.py`, `routes/audit.py`
- [infra/observability/README.md](../../infra/observability/README.md)
- [ADR-004 observability](../../infra/adr/ADR-004-observability.md)

## Gaps to close (→ v0.3+)
- OpenTelemetry traces → Tempo/Jaeger; Prometheus/Grafana metrics; Langfuse LLM
  traces; per-write/retrieval cost attribution.

## Status: 🟡 Partial (logs + audit + metrics done; OTel/Prom/Langfuse roadmap)
