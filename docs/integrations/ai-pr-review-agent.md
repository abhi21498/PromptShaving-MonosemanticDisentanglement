# Integration — AI PR Review Agent (PR governance layer)

**Reference:** [ayush488-glitch/ai-pr-review-agent](https://github.com/ayush488-glitch/ai-pr-review-agent)
**Role in MemoryOps:** the architectural pattern behind our **PR Invariant
Evidence Gate**.

## What the reference is

A production-grade AI PR review service: a GitHub PR webhook fires, four specialist
sub-agents run in parallel (security, code quality, test coverage, docs), each
reasons over the diff plus codebase context (RAG), an aggregator merges findings
and posts a structured review, and low-confidence findings route to a human queue.
It uses FastAPI, LangGraph, ARQ/Redis, semantic memory, observability, cost
dashboards, and HITL routing.

## What MemoryOps implements now (v0.2)

We **do not** copy the service. We reimplement the *idea* as a deterministic,
repo-local gate:

- [`scripts/pr_invariant_gate.py`](../../scripts/pr_invariant_gate.py) — checks a
  PR diff and fails when sensitive surfaces change without matching evidence
  (tests / evals / docs / ADRs). No LLM call.
- [`.github/workflows/pr-invariant-evidence-gate.yml`](../../.github/workflows/pr-invariant-evidence-gate.yml)
  — runs the gate + `pytest` + the eval harness on every PR and posts an evidence
  checklist comment.
- Policy: [`docs/ai-pr-review-policy.md`](../ai-pr-review-policy.md).
- Roadmap to the fuller agent: [`docs/pr-review-agent-roadmap.md`](../pr-review-agent-roadmap.md).

## Reviewer domains (mapped to MemoryOps)

| Reviewer | Checks |
|---|---|
| Security Reviewer | tenant filters, RLS changes, PII policy, secret redaction, auth boundaries |
| Memory Correctness Reviewer | extractor, policy broker, retrieval, ranking, deletion behavior |
| Evaluation Reviewer | memory/eval changes include golden or adversarial tests |
| Docs/ADR Reviewer | architecture, API, migration, policy changes update docs/ADRs |

In v0.2 these "reviewers" are deterministic rule groups in the gate script. The
LLM-backed multi-agent version is v0.3/v0.4 roadmap.

## Provenance / license

The fetched reference did not show a clear license marker, so **no code is copied**
from it. We reference the architecture and reimplement the pattern. If/when the
license is confirmed permissive, deeper reuse can be reconsidered.
