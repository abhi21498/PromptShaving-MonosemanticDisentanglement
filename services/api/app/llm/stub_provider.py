"""Deterministic, offline StubProvider — the default LLM provider (v0.4).

The stub *is* the heuristic layer expressed as an ``LLMProvider``: same input
always yields the same schema-valid JSON, with no network and no API key. It is
the default provider and the universal fallback target, so the full test suite
and the eval harness run identically to the pre-v0.4 heuristic behavior.

Task payload contract (so the stub can respond deterministically):
  * ``memory_extraction`` — ``user`` is the raw message text.
  * ``memory_evaluation`` — ``user`` is JSON ``{"memory": <ExtractedMemory>}``.
  * ``conflict_detection`` — ``user`` is JSON
    ``{"candidate": str, "existing": [{"id": str, "content": str}, ...]}``.
  * ``merge_recommendation`` — ``user`` is JSON
    ``{"candidate": str, "existing": {"id": str, "content": str}}``.
Real providers receive the same JSON in the user turn alongside the system prompt.
"""

from __future__ import annotations

import json

from .base import (
    TASK_CONFLICT_DETECTION,
    TASK_MEMORY_EVALUATION,
    TASK_MEMORY_EXTRACTION,
    TASK_MERGE_RECOMMENDATION,
)
from .fallback import (
    heuristic_conflicts,
    heuristic_evaluate,
    heuristic_extract,
)
from .schemas import (
    ExtractedMemory,
    MemoryExtractionResult,
    MergeRecommendation,
)


class StubProvider:
    name = "stub"

    def complete(self, *, system: str, user: str, task: str = "general") -> str:
        if task == TASK_MEMORY_EXTRACTION:
            result = MemoryExtractionResult(memories=heuristic_extract(user))
            return result.model_dump_json()
        if task == TASK_MEMORY_EVALUATION:
            memory = self._memory_from_payload(user)
            return heuristic_evaluate(memory).model_dump_json()
        if task == TASK_CONFLICT_DETECTION:
            payload = _load(user)
            existing = [
                (str(e.get("id", "")), str(e.get("content", "")))
                for e in payload.get("existing", [])
            ]
            candidate = str(payload.get("candidate", ""))
            return heuristic_conflicts(candidate, existing).model_dump_json()
        if task == TASK_MERGE_RECOMMENDATION:
            return self._merge(user).model_dump_json()
        # General chat: a deterministic, memory-aware templated answer.
        return (
            "Here is a concise, enterprise-style response based on your request "
            "and any relevant remembered preferences."
        )

    @staticmethod
    def _memory_from_payload(user: str) -> ExtractedMemory:
        payload = _load(user)
        mem = payload.get("memory", payload)
        return ExtractedMemory.model_validate(mem)

    @staticmethod
    def _merge(user: str) -> MergeRecommendation:
        payload = _load(user)
        candidate = str(payload.get("candidate", ""))
        existing = payload.get("existing", {}) or {}
        existing_content = str(existing.get("content", ""))
        # Recommend a merge only when there is meaningful token overlap and no
        # opposing polarity (conflict handling owns contradictions).
        conflicts = heuristic_conflicts(
            candidate, [(str(existing.get("id", "")), existing_content)]
        )
        overlap = bool(existing_content) and not conflicts.has_conflict and (
            len(set(candidate.lower().split()) & set(existing_content.lower().split())) >= 2
        )
        return MergeRecommendation(
            should_merge=overlap,
            target_memory_id=str(existing.get("id")) if overlap else None,
            merged_content=existing_content if overlap else "",
            rationale="heuristic: token overlap" if overlap else "heuristic: no merge",
        )


def _load(user: str) -> dict:
    try:
        data = json.loads(user)
        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, TypeError):
        return {}
