"""Provider-neutral LLM layer + structured memory intelligence (v0.4, ADR-008).

Public surface:
  * ``get_llm_provider()`` / ``build_llm_provider()`` — settings-selected provider
    (default: deterministic ``StubProvider``).
  * ``extract_memories`` / ``detect_conflicts`` — structured intelligence with
    deterministic heuristic fallback and observability events.
  * Schemas (``MemoryExtractionResult`` etc.) and ``StructuredOutputError`` for
    callers that validate provider output directly.

Design rules (ADR-008): default provider is the stub, tests need no API keys,
provider failures never block chat, and LLM output is always advisory — the
deterministic policy broker stays authoritative.
"""

from __future__ import annotations

from .base import (
    LLMError,
    LLMProvider,
    LLMTimeoutError,
    LLMUnavailableError,
)
from .intelligence import (
    ConflictOutcome,
    ExtractionOutcome,
    detect_conflicts,
    extract_memories,
)
from .registry import build_llm_provider, get_llm_provider
from .schemas import (
    ConflictDetectionResult,
    ConflictItem,
    ExtractedMemory,
    MemoryEvaluationResult,
    MemoryExtractionResult,
    MergeRecommendation,
)
from .stub_provider import StubProvider
from .structured_output import StructuredOutputError, parse_structured

__all__ = [
    "ConflictDetectionResult",
    "ConflictItem",
    "ConflictOutcome",
    "ExtractedMemory",
    "ExtractionOutcome",
    "LLMError",
    "LLMProvider",
    "LLMTimeoutError",
    "LLMUnavailableError",
    "MemoryEvaluationResult",
    "MemoryExtractionResult",
    "MergeRecommendation",
    "StructuredOutputError",
    "StubProvider",
    "build_llm_provider",
    "detect_conflicts",
    "extract_memories",
    "get_llm_provider",
    "parse_structured",
]
