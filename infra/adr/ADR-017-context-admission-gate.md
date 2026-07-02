# ADR-017 — Context Admission Gate + Memory Usage Trace

- Status: Accepted (v1.3)
- Date: 2026-07-01
- Supersedes: none
- Related: ADR-002 (retrieval/ranking), ADR-006 (RLS/tenant scope), ADR-013
  (retention/legal hold/consent), ADR-015 (Prometheus metrics), ADR-004 (audit)

## Context

Retrieval + ranking answer "is this memory **relevant**?". Field feedback was
consistent: a governed memory system must also answer "is this memory
**allowed** into context for this turn — and can it prove why?". Normal RAG puts
anything similar into the prompt. MemoryOps should admit a memory only if it is
relevant *and* permitted, and should surface the trail behind every answer:
which memories were used, where they came from, when they were stored, whether
they were still valid, and why each was allowed in.

The building blocks already exist: the repository enforces tenant scope + the
deletion guarantee at the source (ADR-006), the ranker emits a `score_breakdown`
(invariant #8), and governance state (consent, retention window, legal hold /
pin / protect) is readable via `app/db/governance.py` (ADR-013). What was
missing was an explicit *admission* stage and an explainable *trace* on the
response.

## Decision

Add a **Context Admission Gate** between the ranker and the context composer, and
a **Memory Usage Trace** on the chat response.

    retrieve → rank → [ADMISSION GATE] → compose → LLM

- **`app/services/admission_gate.py`.** For each ranked candidate the gate returns
  an explainable verdict — `ALLOW` or a specific `BLOCK_*`
  (`WRONG_TENANT`, `DELETED`, `ARCHIVED`, `INACTIVE`, `CONSENT_WITHDRAWN`,
  `EXPIRED`, `SENSITIVE`, `LOW_CONFIDENCE`). Only `ALLOW` memories reach the
  composer.
- **Defense-in-depth, never additive.** The gate only ever *removes* memory from
  context. It cannot resurrect, promote, or add memory, so it strengthens rather
  than weakens invariants #1 (tenant isolation) and #2 (deletion guarantee). The
  repository already filters non-active/wrong-tenant rows, so those `BLOCK_*`
  verdicts are belt-and-suspenders; the load-bearing ones are `BLOCK_EXPIRED` /
  `BLOCK_CONSENT_WITHDRAWN`, which deny *active* memory whose governance turned
  against admission before a lifecycle worker removed it.
- **Conservative defaults preserve behavior.** Deleted/archived/inactive/
  wrong-tenant/consent-withdrawn/retention-expired are blocked by default (no
  observable change, since those either can't be retrieved or shouldn't be used).
  The two stricter gates are **opt-in**: `admission_block_sensitive` (block
  `sensitivity='high'`) and `admission_min_score` (block below a ranked-score
  threshold). Legal hold / pin / protect are *preservation* controls and are
  therefore **retention-exempt** — never blocked by `BLOCK_EXPIRED`.
- **Observe-only (shadow) mode.** `admission_gate_enabled=false` runs the gate
  without enforcement: verdicts are still computed, traced, and counted, but
  nothing is removed. This lets an operator see what *would* be blocked before
  enforcing.
- **Graceful degradation (invariant #4).** The gate runs inside the existing
  no-throw read wrapper; on any failure the read degrades and the response is
  never blocked. Metric recording is no-throw (ADR-015).
- **Auditable (invariant #7).** A single per-turn `context_admission_blocked`
  audit event records the blocked count, decision histogram, and blocked memory
  ids (content-free). A new content-free counter
  `memoryops_admission_decisions_total{decision}` is exposed on `GET /metrics`.
- **Memory Usage Trace (additive).** An optional `trace: MemoryUsageTrace` block
  on `ChatResponse` (responses only gain fields, per the `1.x` promise) lists
  `memories_used` and `memories_blocked`, each with provenance (`source`,
  `stored_at`), `consent_status`, `retention_status`, `status`, `sensitivity`,
  `admission_decision` + `admission_reason`, and the retrieval score/breakdown.
  Toggle with `memory_trace_enabled`. Content is surfaced as a short preview only
  (same tenant trust boundary as the existing `used_memories`).

## Consequences

- Every answer can prove *why each memory was (or was not) allowed into context* —
  the core differentiator over plain RAG.
- Consent-withdrawn / retention-expired active memory is denied context admission
  immediately, not only after the next retention-worker pass — tightening the
  window between a governance change and its effect on output.
- Deterministic and offline-safe: defaults change no behavior, tests need no keys.

## Out of scope (later phases, per the product roadmap)

- Freshness / `last_validated_at` staleness scoring (v1.5).
- Tombstone lineage + derived-artifact blocking + deleted-memory leakage evals
  (v1.3).
- Recall Gate / Output Gate / audience-aware + third-party consent (v1.4).
- Hash-chained audit evidence (v2.0).
