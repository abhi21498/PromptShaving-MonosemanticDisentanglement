# Phase 5 — LLM Reasoning & Provider Abstraction

**Question:** How does the system use LLM reasoning, and how is it abstracted
across providers without becoming a hard dependency or a governance hole?

## MemoryOps mapping
A provider-neutral LLM layer ([services/api/app/llm/](../../services/api/app/llm/),
v0.4, [ADR-008](../../infra/adr/ADR-008-provider-llm-adapters.md)) exposes one
synchronous `LLMProvider` protocol with a deterministic `StubProvider` default and
OpenAI / Anthropic / Gemini adapters. It powers **structured memory intelligence**
— extraction, evaluation, conflict detection — with schema-validated output and a
deterministic heuristic fallback. The LLM is advisory; the deterministic policy
broker runs after extraction and stays authoritative.

See [provider-llm-adapters.md](../provider-llm-adapters.md) and
[structured-memory-intelligence.md](../structured-memory-intelligence.md).

## Gate (must be true to pass)
- Default provider is `stub`; the app starts and tests pass with **no API key**.
- Networked providers are selected only when their key is present; otherwise
  selection degrades to the stub.
- Every provider response that drives a decision is schema-validated; invalid
  JSON or a provider failure degrades to the heuristic and never blocks chat.
- LLM output is advisory only — it cannot override the policy broker, and
  secret-like content is still blocked.
- Prompts are versioned, reviewable assets; the PR gate requires a doc/eval update
  when prompts change and provider tests when the LLM layer changes.

## Evidence
- `services/api/app/llm/{base,registry,stub_provider,openai_provider,
  anthropic_provider,gemini_provider,schemas,structured_output,prompt_registry,
  fallback,intelligence}.py`
- `services/api/app/llm/prompts/*.md`
- `services/api/tests/test_llm_provider_registry.py`,
  `test_stub_llm_provider.py`, `test_structured_memory_extraction.py`,
  `test_structured_output_validation.py`, `test_llm_fallback.py`,
  `test_conflict_detection.py`
- `evals/golden_memory_cases.json` (`structured`, `conflict`),
  `evals/adversarial_cases.json` (structured-secret, policy-override injection)

## Current result
`pytest -q` → all green; `python evals/run_evals.py` → 21/21, RESULT: PASS.

## Status: ✅ Implemented (LLM-as-judge evaluation is roadmap)
