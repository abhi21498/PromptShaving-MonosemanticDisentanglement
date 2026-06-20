# Integration — Hermes Agent (operator layer)

**Reference:** [nousresearch/hermes-agent](https://github.com/nousresearch/hermes-agent)
**Role in MemoryOps:** developer/operator assistant — **not** part of the core API
request path.

## What Hermes is used for

Hermes Agent supports persistent memory, scheduling, delegated subagents,
web/search, and sandboxed execution. That makes it a good fit as an **operator
agent around the project**: it inspects the repo, runs checks, guides releases,
and audits invariants — rather than living inside the memory runtime.

> Accurate: "MemoryOps includes a Hermes operator layer for guided engineering
> workflows, release checks, and invariant audits."
> Not accurate: "MemoryOps is built on Hermes."

## Skills

Local Hermes skills live in [`.hermes/skills/`](../../.hermes/skills/):

| Skill | Responsibility |
|---|---|
| `memoryops-architect` | Reviews architecture docs, ADRs, service boundaries, phase gates, roadmap. |
| `memoryops-release-manager` | Runs validation commands, checks `RELEASING.md`, prepares release notes. |
| `memoryops-invariant-auditor` | Checks tenant isolation, deleted-memory guarantee, policy-before-storage, audit coverage, temporary-chat behavior. |

These are skill definitions (`SKILL.md` routing layers); they orchestrate the
repo's own deterministic commands (`pytest`, `evals/run_evals.py`,
`scripts/pr_invariant_gate.py`). They do not add a runtime dependency.

## What we adopted from Hermes (already in the core)

The hardening patterns Hermes demonstrates are already baked into the API from
v0.1: exact-pinned dependencies (supply-chain blast radius), centralized
structured logging with a **secret-redacting formatter**, `tenacity` retries, and
a `SECURITY.md` with explicit load-bearing boundaries.

## Provenance / license

We reference Hermes's architecture and reuse generic engineering patterns. No
Hermes source code is copied into this repo.
