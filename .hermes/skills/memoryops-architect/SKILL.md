---
name: memoryops-architect
description: >
  Reviews MemoryOps AI architecture, ADRs, service boundaries, phase gates, and
  production roadmap. Use when planning a feature, evaluating a design change, or
  checking that the repo still matches its documented architecture.
---

# memoryops-architect

An operator/developer skill for the **Hermes operator layer** around MemoryOps AI.
It does not run inside the API request path; it helps a developer reason about and
review the system.

## When to use
- Before starting a feature that touches services, schema, or invariants.
- When reviewing a PR's architectural impact.
- When updating ADRs or phase gates.

## Inputs to read
- `docs/architecture.md` (incl. Mermaid diagrams), `docs/agentic-swe-kit-map.md`
- `infra/adr/ADR-001..005`
- `docs/phase-gates/*`
- `services/api/app/` layering: `routes → services → db`, with `core` cross-cutting

## Procedure
1. Identify which lifecycle phase the change belongs to (see the 5-question
   diagnostic in `docs/agentic-swe-kit-map.md`).
2. Check the change respects the boundaries: request path depends only on the
   repository interface; cross-cutting concerns stay in `core/`.
3. Confirm the seven invariants are preserved (or call out which need new tests).
4. If the change is load-bearing, require a new/updated ADR.
5. Update the relevant `docs/phase-gates/phase-XX-*.md` status.

## Output
A short architecture review: phase, boundaries respected (y/n), invariants at
risk, ADR/phase-gate updates required.

## Guardrails
- Never propose putting an LLM call on the core write/read path without a fallback.
- Never weaken tenant scoping, the deletion guarantee, or policy-before-storage.
