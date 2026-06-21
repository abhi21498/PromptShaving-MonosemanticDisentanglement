"""Structured memory intelligence orchestration (v0.4, ADR-008).

Ties providers → prompts → schema validation → deterministic fallback, and emits
the v0.4 observability events. Two operations are exposed:

  * ``extract_memories`` — structured extraction with heuristic fallback.
  * ``detect_conflicts`` — minimal conflict detection with heuristic fallback.

Hard rules enforced here:
  * A provider failure, timeout, or invalid JSON never blocks chat — it degrades
    to the deterministic heuristic (invariant #4).
  * The result is advisory: the policy broker remains authoritative and may
    ignore everything here. LLM output can never override policy (ADR-003/008).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field

from ..core.config import Settings, get_settings
from ..core.logging import get_logger
from .base import (
    TASK_CONFLICT_DETECTION,
    TASK_MEMORY_EXTRACTION,
    LLMProvider,
)
from .fallback import heuristic_conflicts, heuristic_extract
from .prompt_registry import get_prompt
from .schemas import ConflictDetectionResult, ExtractedMemory, MemoryExtractionResult
from .structured_output import StructuredOutputError, parse_structured

logger = get_logger("memoryops.llm")


@dataclass
class ExtractionOutcome:
    memories: list[ExtractedMemory] = field(default_factory=list)
    mode: str = "structured"  # structured | heuristic | strict_empty
    provider: str = "stub"


@dataclass
class ConflictOutcome:
    result: ConflictDetectionResult = field(default_factory=ConflictDetectionResult)
    mode: str = "structured"  # structured | heuristic
    provider: str = "stub"


def extract_memories(
    provider: LLMProvider, message: str, *, settings: Settings | None = None
) -> ExtractionOutcome:
    """Run structured extraction; fall back to the heuristic on any failure."""
    settings = settings or get_settings()
    name = getattr(provider, "name", "unknown")
    try:
        raw = provider.complete(
            system=get_prompt(TASK_MEMORY_EXTRACTION), user=message, task=TASK_MEMORY_EXTRACTION
        )
        result = parse_structured(raw, MemoryExtractionResult)
        logger.info(
            "llm structured extraction",
            extra={
                "event": "memory_extraction_structured",
                "provider": name,
                "candidate_count": len(result.memories),
            },
        )
        return ExtractionOutcome(memories=result.memories, mode="structured", provider=name)
    except StructuredOutputError:
        logger.warning(
            "structured extraction output invalid; falling back",
            extra={"event": "structured_output_invalid", "provider": name,
                   "task": TASK_MEMORY_EXTRACTION},
        )
    except Exception:  # noqa: BLE001 — includes LLMError; degradation boundary
        logger.warning(
            "llm extraction failed; falling back",
            extra={"event": "llm_provider_failure", "provider": name,
                   "task": TASK_MEMORY_EXTRACTION},
        )
    return _fallback_extract(message, settings, name)


def _fallback_extract(message: str, settings: Settings, provider: str) -> ExtractionOutcome:
    if settings.llm_fallback_to_heuristic:
        logger.info(
            "llm fallback to heuristic extraction",
            extra={"event": "llm_fallback_used", "provider": provider, "fallback": True},
        )
        return ExtractionOutcome(heuristic_extract(message), mode="heuristic", provider=provider)
    # Strict mode: no heuristic rescue. Safe (stores nothing), still never blocks.
    logger.warning(
        "structured output required and unavailable; extracting nothing",
        extra={"event": "llm_fallback_used", "provider": provider, "fallback": False},
    )
    return ExtractionOutcome([], mode="strict_empty", provider=provider)


def detect_conflicts(
    provider: LLMProvider,
    candidate_content: str,
    existing: list[tuple[str, str]],
    *,
    settings: Settings | None = None,
) -> ConflictOutcome:
    """Detect conflicts between a candidate and existing memories (advisory)."""
    settings = settings or get_settings()
    name = getattr(provider, "name", "unknown")
    mode = "structured"
    try:
        payload = json.dumps(
            {
                "candidate": candidate_content,
                "existing": [{"id": mid, "content": c} for mid, c in existing],
            }
        )
        raw = provider.complete(
            system=get_prompt(TASK_CONFLICT_DETECTION), user=payload, task=TASK_CONFLICT_DETECTION
        )
        result = parse_structured(raw, ConflictDetectionResult)
    except StructuredOutputError:
        logger.warning(
            "conflict detection output invalid; falling back",
            extra={"event": "structured_output_invalid", "provider": name,
                   "task": TASK_CONFLICT_DETECTION},
        )
        result, mode = _fallback_conflicts(candidate_content, existing, settings, name)
    except Exception:  # noqa: BLE001 — includes LLMError; degradation boundary
        logger.warning(
            "conflict detection failed; falling back",
            extra={"event": "llm_provider_failure", "provider": name,
                   "task": TASK_CONFLICT_DETECTION},
        )
        result, mode = _fallback_conflicts(candidate_content, existing, settings, name)

    logger.info(
        "conflict detection complete",
        extra={
            "event": "conflict_detection_result",
            "provider": name,
            "conflict_count": len(result.conflicts),
        },
    )
    return ConflictOutcome(result=result, mode=mode, provider=name)


def _fallback_conflicts(
    candidate_content: str, existing: list[tuple[str, str]], settings: Settings, provider: str
) -> tuple[ConflictDetectionResult, str]:
    if settings.llm_fallback_to_heuristic:
        logger.info(
            "llm fallback to heuristic conflict detection",
            extra={"event": "llm_fallback_used", "provider": provider, "fallback": True},
        )
        return heuristic_conflicts(candidate_content, existing), "heuristic"
    return ConflictDetectionResult(), "heuristic"
