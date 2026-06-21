# ADR-008 — Provider LLM adapters + structured memory intelligence

Status: Accepted (v0.4)

## Context
Through v0.3.x, MemoryOps' extraction and evaluation were purely heuristic
(regex cues). That keeps the system offline-safe but leaves real LLM reasoning on
the table for richer extraction, evaluation, and conflict detection. We want a
provider-neutral LLM layer — OpenAI, Anthropic, Gemini — **without** weakening any
invariant, making a key a hard dependency, or letting a model override the
deterministic policy broker.

## Decision
Add a provider-neutral LLM layer at `services/api/app/llm/`:

- `base.py` — the synchronous `LLMProvider` protocol (`complete(system, user,
  task) -> str`) and the `LLMError` hierarchy. Sync to match the read/write paths
  (consistent with ADR-006 embeddings and ADR-007 compression).
- `stub_provider.py` — `StubProvider`, the **default** and universal fallback.
  Deterministic, offline, no API key; it expresses the heuristic extraction and
  conflict logic as a provider, so tests and evals are unchanged.
- `openai_provider.py`, `anthropic_provider.py`, `gemini_provider.py` — networked
  adapters over a shared `providers.BaseNetworkProvider` envelope (lazy SDK import,
  retry-with-backoff, every failure normalized to `LLMUnavailableError`).
- `registry.py` — settings-driven selection; a networked provider without its key
  silently degrades to the stub so the app always starts.
- `schemas.py` — Pydantic schemas for extraction, evaluation, conflict detection,
  and merge recommendation, reusing the canonical `MemoryType`/`Sensitivity`.
- `structured_output.py` — extracts and schema-validates JSON; any malformed or
  off-schema output raises `StructuredOutputError`.
- `prompt_registry.py` + `prompts/*.md` — versioned, reviewable system prompts.
- `fallback.py` — deterministic heuristics (the one home for the pre-v0.4
  extraction logic) used whenever a provider fails or returns invalid JSON.
- `intelligence.py` — orchestration: provider → prompt → validate → fallback, with
  observability events. Exposes `extract_memories` and `detect_conflicts`.

The extractor (`services/extractor.py`) now delegates to `extract_memories`, and
the gateway runs advisory `detect_conflicts` on the write path (logging only).

### Where the LLM sits relative to policy
```text
user message
  → extractor → LLM structured extraction (advisory)   ← app/llm
  → policy broker (deterministic; secrets/injection BLOCK, dedup, sensitivity) ← AUTHORITATIVE
  → write service → audit
```
The policy broker runs **after** extraction and is authoritative. An LLM
suggestion — even a high-importance one carrying a secret — cannot bypass it
(covered by `test_llm_fallback.py` and the adversarial evals).

## Rules (enforced in code + tests)
- Default provider is `stub`; tests never require a real API key.
- Provider failures, timeouts, and invalid JSON degrade to the deterministic
  heuristic and never block chat (invariant #4).
- Structured output is schema-validated before it is trusted.
- LLM output is advisory; the policy broker stays deterministic and authoritative.
- Secret-like content is still blocked regardless of what a model proposes.

## Configuration
`MEMORYOPS_LLM_PROVIDER=stub|openai|anthropic|gemini` (default `stub`),
`MEMORYOPS_LLM_REQUIRE_STRUCTURED_OUTPUT`, `MEMORYOPS_LLM_FALLBACK_TO_HEURISTIC`,
`MEMORYOPS_LLM_MAX_RETRIES`, `MEMORYOPS_LLM_TIMEOUT_SECONDS`, plus
`OPENAI_API_KEY`/`OPENAI_MODEL`, `ANTHROPIC_API_KEY`/`ANTHROPIC_MODEL`,
`GEMINI_API_KEY`/`GEMINI_MODEL`.

## Observability
New structured events: `llm_provider_call`, `llm_provider_failure`,
`structured_output_invalid`, `llm_fallback_used`, `memory_extraction_structured`,
`conflict_detection_result`. Emitted through the redacting JSON logger; no raw
secrets, keys, or full user messages are logged.

## Alternatives
- **LangChain / LiteLLM as the abstraction** — heavier dependency surface; our
  needs are a thin protocol + fallback, so a repo-local interface is simpler and
  keeps the governance boundary explicit. Can be slotted behind the same protocol
  later.
- **Let the LLM make storage decisions** — rejected; it would violate the
  policy-before-storage invariant (ADR-003). The LLM is advisory only.
- **No LLM layer (status quo)** — still the default behavior via the stub.

## Trade-offs
- The stub mirrors the heuristic, so "structured mode" by default is heuristic
  under the hood — intentional, for deterministic offline evals.
- Token/timeout costs apply only when a real provider is configured.

## Security considerations
- LLM output never reaches storage without the deterministic policy broker.
- Prompts forbid extracting secrets, but the redaction-based broker is the
  enforcement boundary, not the prompt.
- SDKs are imported lazily; no provider dependency is required to run or test.
