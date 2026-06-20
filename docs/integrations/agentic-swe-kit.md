# Integration — agentic-swe-kit (engineering discipline layer)

**Reference:** [ayush488-glitch/agentic-swe-kit](https://github.com/ayush488-glitch/agentic-swe-kit)
**Role in MemoryOps:** project governance / phase-gate review framework.

## What it is

agentic-swe-kit is a knowledge + skills kit organized into seven domain skills —
engineering mindset, modular architecture, production readiness, distributed
systems, security engineering, data systems engineering, and LLMOps/AI agents —
plus a master orchestrator that routes work across a **20-phase production
lifecycle**.

## How MemoryOps uses it

As a **phase-gate review framework**. Each major feature must pass through (and
update) the relevant phase gate before it ships. The mapping lives in
[`docs/agentic-swe-kit-map.md`](../agentic-swe-kit-map.md); the individual gates
live in [`docs/phase-gates/`](../phase-gates/).

| Phase | MemoryOps focus |
|---|---|
| 0 Cognitive Design | What should memory decide? |
| 1 System Architecture | Service boundaries and invariants |
| 6 Memory Architecture | Short/long-term, RAG, hybrid retrieval |
| 9 Evaluation Systems | Golden memory cases, adversarial tests |
| 10 Observability | Traces, audit, latency, cost |
| 11 Security Architecture | Tenant isolation, PII, secret blocking |
| 12 Reliability Engineering | Retries, circuit breakers, graceful degradation |
| 15 Governance & Compliance | Deletion, provenance, explainability |
| 18 CI/CD for AI | Invariant evidence gates |
| 20 Continuous Learning | Decay, reflection, feedback loops |

## Diagnostic (adopted into CLAUDE.md)

The kit's 5-question diagnostic is part of how we route work on this repo:

1. New project, existing codebase, or live incident?
2. Any AI / LLM components involved?
3. Distributed or multi-service?
4. Auth or sensitive data in scope?
5. Which lifecycle phase is the project in?

## Provenance / license

We reference the kit's framework and lifecycle. We do not vendor its wiki or
skills into this repo; the phase-gate docs here are MemoryOps-specific.
