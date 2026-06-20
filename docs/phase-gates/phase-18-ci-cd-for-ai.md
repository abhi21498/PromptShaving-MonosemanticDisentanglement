# Phase 18 — CI/CD for AI

**Question:** Prompt versioning, eval gates, shadow + canary, invariant gates.

## MemoryOps mapping
CI runs tests + lint + the eval harness. A deterministic **PR Invariant Evidence
Gate** fails when security/governance-sensitive surfaces change without matching
evidence (tests / evals / docs / ADRs).

## Gate (must be true to pass)
- CI runs `pytest`, `ruff`, the eval harness, and the web build on every PR.
- The invariant gate enforces evidence for sensitive changes (no LLM call).
- The gate posts an advisory evidence checklist on the PR.

## Evidence
- `.github/workflows/ci.yml`
- `.github/workflows/pr-invariant-evidence-gate.yml`
- `scripts/pr_invariant_gate.py`
- [docs/ai-pr-review-policy.md](../ai-pr-review-policy.md)
- [docs/pr-review-agent-roadmap.md](../pr-review-agent-roadmap.md)

## Status: ✅ Implemented (deterministic; LLM multi-agent review is roadmap)
