# Structured Memory Intelligence (v0.4)

Structured memory intelligence is the set of LLM-backed operations that produce
**schema-validated** structured output to inform the memory lifecycle, layered on
top of the [provider LLM adapters](provider-llm-adapters.md). All of it is
advisory: the deterministic policy broker stays authoritative (ADR-003/008).

## Operations

| Operation | Function | Schema | Prompt |
| --- | --- | --- | --- |
| Extraction | `extract_memories` | `MemoryExtractionResult` | `prompts/memory_extraction.md` |
| Evaluation | (schema + stub) | `MemoryEvaluationResult` | `prompts/memory_evaluation.md` |
| Conflict detection | `detect_conflicts` | `ConflictDetectionResult` | `prompts/conflict_detection.md` |
| Merge recommendation | (schema + stub) | `MergeRecommendation` | `prompts/merge_recommendation.md` |

## Pipeline

```text
provider.complete(system=<prompt>, user=<payload>, task=<task>)
  → structured_output.parse_structured(raw, Schema)   # JSON extract + validate
      → success → trusted structured object
      → StructuredOutputError / provider failure → deterministic heuristic fallback
```

`intelligence.py` orchestrates this and emits observability events. The
`StubProvider` produces deterministic, schema-valid output for every task, so the
default offline behavior is unchanged and reproducible.

## Where it sits in the lifecycle

```text
Capture → [Extract (structured) → Conflict detect (advisory)] → Policy broker (authoritative)
        → Store → Retrieve → Rank → Compose → Update → Forget → Audit
```

- **Extraction** runs inside `services/extractor.py`. Validated `ExtractedMemory`
  objects become `CandidateMemory` with provenance attached (invariant #3).
- **Conflict detection** runs on the gateway write path as advisory metadata. It
  logs `conflict_detection_result` and **never** changes the policy decision.

## Schemas

Defined in [schemas.py](../services/api/app/llm/schemas.py); they reuse the
canonical `MemoryType` and `Sensitivity` enums so extraction stays aligned with
storage. `importance` (0–10) and `confidence` (0–1) are range-validated, so an
out-of-range value from a model is rejected and triggers fallback.

## Guarantees

- Deterministic and offline by default (stub provider).
- Invalid JSON / provider failure → heuristic fallback, never a blocked response.
- LLM output cannot override policy; secrets remain blocked.
- Minimal conflict detection flags contradicting preferences (polarity flip on a
  shared subject) — see `golden-conflict-*` evals.

## Evals

`evals/golden_memory_cases.json` adds `structured` and `conflict` cases;
`evals/adversarial_cases.json` adds structured-secret and policy-override
injection cases that must still BLOCK. Run with `python evals/run_evals.py`.
