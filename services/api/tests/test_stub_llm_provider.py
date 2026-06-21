"""StubProvider: deterministic, schema-valid output for every task, no network."""

from __future__ import annotations

import json

from app.llm import StubProvider
from app.llm.base import (
    TASK_CONFLICT_DETECTION,
    TASK_MEMORY_EVALUATION,
    TASK_MEMORY_EXTRACTION,
    TASK_MERGE_RECOMMENDATION,
)
from app.llm.schemas import (
    ConflictDetectionResult,
    MemoryEvaluationResult,
    MemoryExtractionResult,
    MergeRecommendation,
)


def test_extraction_output_is_deterministic_and_valid() -> None:
    stub = StubProvider()
    msg = "Remember that I prefer dark mode dashboards."
    out1 = stub.complete(system="", user=msg, task=TASK_MEMORY_EXTRACTION)
    out2 = stub.complete(system="", user=msg, task=TASK_MEMORY_EXTRACTION)
    assert out1 == out2  # deterministic
    result = MemoryExtractionResult.model_validate_json(out1)
    assert len(result.memories) == 1
    assert "dark mode" in result.memories[0].content.lower()
    assert result.memories[0].importance == 8  # explicit "remember"


def test_extraction_returns_empty_for_trivia() -> None:
    out = StubProvider().complete(
        system="", user="The weather is nice.", task=TASK_MEMORY_EXTRACTION
    )
    assert MemoryExtractionResult.model_validate_json(out).memories == []


def test_evaluation_output_valid() -> None:
    payload = json.dumps(
        {"memory": {"content": "I prefer concise answers.", "type": "preference",
                    "importance": 8, "confidence": 0.9, "sensitivity": "low"}}
    )
    out = StubProvider().complete(system="", user=payload, task=TASK_MEMORY_EVALUATION)
    ev = MemoryEvaluationResult.model_validate_json(out)
    assert ev.suggested_importance == 8
    assert ev.is_worth_remembering is True


def test_conflict_output_valid_and_detects_polarity_flip() -> None:
    payload = json.dumps(
        {
            "candidate": "I no longer prefer dark mode dashboards.",
            "existing": [{"id": "m1", "content": "I prefer dark mode dashboards."}],
        }
    )
    out = StubProvider().complete(system="", user=payload, task=TASK_CONFLICT_DETECTION)
    result = ConflictDetectionResult.model_validate_json(out)
    assert result.has_conflict is True
    assert result.conflicts[0].existing_memory_id == "m1"


def test_merge_output_valid() -> None:
    payload = json.dumps(
        {
            "candidate": "I prefer dark mode dashboards always.",
            "existing": {"id": "m1", "content": "I prefer dark mode dashboards."},
        }
    )
    out = StubProvider().complete(system="", user=payload, task=TASK_MERGE_RECOMMENDATION)
    rec = MergeRecommendation.model_validate_json(out)
    assert rec.should_merge is True
    assert rec.target_memory_id == "m1"


def test_general_task_returns_text() -> None:
    out = StubProvider().complete(system="", user="hello", task="general")
    assert isinstance(out, str) and out
