# PR Review Agent — Roadmap

The current gate ([`scripts/pr_invariant_gate.py`](../scripts/pr_invariant_gate.py))
is deterministic and rule-based. This roadmap describes how it can grow toward the
[ai-pr-review-agent](https://github.com/ayush488-glitch/ai-pr-review-agent) pattern
without ever putting an LLM on the memory runtime's critical path.

## v0.2 (now) — Deterministic invariant gate
- Rule engine over the PR diff; fails when sensitive surfaces change without
  evidence (tests / evals / docs / ADRs).
- Four reviewer domains as rule groups: Security, Memory Correctness, Evaluation,
  Docs/ADR.
- Runs in CI; posts an evidence checklist; no LLM call.

## v0.3 — Context-aware findings
- Add semantic retrieval over the codebase (reuse pgvector) so a reviewer rule can
  cite the specific function/ADR a change should update.
- Severity scoring; low-confidence findings are advisory only.

## v0.4 — Specialist LLM sub-agents (optional, off the runtime path)
- Four parallel sub-agents (security, code quality, test coverage, docs) reasoning
  over the diff + retrieved context, aggregated into one structured review.
- LangGraph-style fan-out/aggregate; ARQ/Redis for queueing; HITL routing for
  low-confidence findings.
- Strictly a developer-time tool; gated behind explicit opt-in and never invoked by
  the memory API.

## v0.5 — Learning loop
- Track merged-vs-rejected findings to tune rule weights and reviewer prompts.
- Cost + latency dashboards per review (economics plane).

## Non-negotiables across all versions
- The memory write/read path never depends on the review agent.
- Deterministic checks remain the source of truth; LLM findings are advisory.
- No code is copied from the reference project without a confirmed license.
