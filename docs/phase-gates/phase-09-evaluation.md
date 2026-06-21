# Phase 9 — Evaluation Systems

**Question:** Golden datasets, LLM-as-judge, regression gates.

## MemoryOps mapping
Deterministic golden + adversarial cases run against an isolated stack. Each case
maps to an invariant (save / drop / block / pending / deleted / isolation /
temporary / archived / retrieve / breakdown). The runner enforces a pass-rate
floor and zero critical failures. v0.3 adds semantic + keyword retrieval,
archived-exclusion, and score-breakdown-present cases.

## Gate (must be true to pass)
- A golden set and an adversarial set exist as data, not code.
- The runner exits non-zero on any critical-invariant failure or sub-80% rate.
- Memory/eval changes are required (by the PR gate) to update the cases.

## Evidence
- `evals/golden_memory_cases.json`, `evals/adversarial_cases.json`
- `evals/run_evals.py`, `services/api/app/services/eval_harness.py`
- `services/api/tests/test_retrieval.py::test_eval_harness_runs`

## Current result
`python evals/run_evals.py` → 15/15, RESULT: PASS.

## Status: ✅ Implemented (LLM-as-judge is roadmap)
