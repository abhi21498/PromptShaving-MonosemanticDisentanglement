"""Structured output schemas for the LLM intelligence layer (v0.4, ADR-008).

Every provider response that drives a memory decision is validated against one
of these Pydantic models before it is trusted. Invalid JSON or a schema mismatch
is treated as a provider failure and falls back to the deterministic heuristic
(``structured_output_invalid`` → ``llm_fallback_used``). Reusing the canonical
``MemoryType`` / ``Sensitivity`` enums keeps extraction aligned with storage.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from ..schemas.memory import MemoryType, Sensitivity


class ExtractedMemory(BaseModel):
    """One memory candidate proposed by the extraction model."""

    content: str = Field(min_length=1)
    type: MemoryType = MemoryType.semantic
    importance: int = Field(5, ge=0, le=10)
    confidence: float = Field(0.7, ge=0.0, le=1.0)
    sensitivity: Sensitivity = Sensitivity.low
    # Free-text rationale; never used for policy, only explainability.
    rationale: str = ""


class MemoryExtractionResult(BaseModel):
    """Validated extraction output: zero or more candidate memories."""

    memories: list[ExtractedMemory] = Field(default_factory=list)


class MemoryEvaluationResult(BaseModel):
    """Advisory evaluation of a single candidate.

    The ``suggested_*`` fields are advisory only — the policy broker remains
    authoritative and may ignore them entirely (invariant: LLM cannot override
    policy).
    """

    suggested_importance: int = Field(5, ge=0, le=10)
    suggested_sensitivity: Sensitivity = Sensitivity.low
    is_worth_remembering: bool = True
    rationale: str = ""


class ConflictItem(BaseModel):
    """A detected contradiction between a candidate and an existing memory."""

    existing_memory_id: str | None = None
    existing_content: str = ""
    relation: str = "contradicts"  # contradicts | duplicates | refines
    explanation: str = ""


class ConflictDetectionResult(BaseModel):
    """Validated conflict-detection output for one candidate."""

    has_conflict: bool = False
    conflicts: list[ConflictItem] = Field(default_factory=list)


class MergeRecommendation(BaseModel):
    """Advisory recommendation to merge a candidate into an existing memory."""

    should_merge: bool = False
    target_memory_id: str | None = None
    merged_content: str = ""
    rationale: str = ""
