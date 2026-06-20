# Agentic Engineering Layer — Integrations

MemoryOps AI is not only an AI memory system. It is a **governed engineering
system around memory**. This directory documents the three agentic integrations
that wrap the core — none of them sit in the core chat request path.

| Integration | Role | Where it lives |
|---|---|---|
| [Hermes Agent](hermes-agent.md) | Operator / developer assistant layer | `.hermes/skills/` |
| [agentic-swe-kit](agentic-swe-kit.md) | Engineering phase-gate + architecture discipline | `docs/agentic-swe-kit-map.md`, `docs/phase-gates/` |
| [ai-pr-review-agent](ai-pr-review-agent.md) | PR governance + invariant review pattern | `.github/workflows/pr-invariant-evidence-gate.yml`, `scripts/pr_invariant_gate.py` |

## Design rules

1. **These layers are around the system, not inside the request path.** The memory
   write/read path (`services/api/app/services/*`) has no runtime dependency on any
   of them.
2. **Deterministic first.** The PR gate and operator audits are deterministic and
   require no external LLM call. LLM-assisted variants are roadmap, not v0.2.
3. **No license risk.** We reference architectures and reimplement patterns in our
   own repo; we do not copy code from the reference projects. See each integration
   doc for the specific provenance note.

## Accurate framing

- ✅ "MemoryOps includes a Hermes operator layer for guided engineering workflows,
  release checks, and invariant audits."
- ❌ "MemoryOps is built on Hermes." (It is not — Hermes is an operator assistant
  around the project.)

See the **Agentic Engineering Layer** section of the root [README](../../README.md).
