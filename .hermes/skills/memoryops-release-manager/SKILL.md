---
name: memoryops-release-manager
description: >
  Runs MemoryOps AI validation commands, checks RELEASING.md discipline, and
  prepares release notes. Use when cutting a version (vX.Y) or verifying main is
  release-ready.
---

# memoryops-release-manager

Operator skill for preparing and validating MemoryOps AI releases. Deterministic;
no LLM call required to produce a pass/fail.

## When to use
- Before tagging a release.
- To confirm `main` is green and the version story is coherent.

## Validation commands (must all pass)
```bash
cd services/api && pytest -q
cd services/api && ruff check app
python evals/run_evals.py
cd apps/web && npm run build
python scripts/pr_invariant_gate.py --base HEAD~1 --head HEAD
```

## Procedure
1. Run every validation command; collect pass/fail + key output.
2. Read `RELEASING.md`; confirm the version follows `vMAJOR.MINOR[.PATCH]` and the
   milestone matches the planned roadmap.
3. Draft release notes using the template (Summary / What changed / Why /
   Validation), citing the actual command outputs.
4. Propose the exact tag + `gh release create` commands. **Do not run them without
   explicit human approval** — releases are outward-facing.

## Output
A release-readiness report: command results, proposed version + title, and draft
notes ready to paste.

## Guardrails
- Never tag or publish a release autonomously.
- Never add AI co-author trailers to commits.
- If any validation command fails, mark NOT READY and stop.
