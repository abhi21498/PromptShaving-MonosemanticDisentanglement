"""Versioned prompt registry (v0.4).

System prompts for each structured-intelligence task live as Markdown files in
``app/llm/prompts/`` so they are reviewable, diffable, and covered by the PR gate
(a prompt change must ship with a doc or eval update). The registry loads and
caches them by name; a missing prompt is a programming error, not a runtime
degradation, so it raises.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from .base import (
    TASK_CONFLICT_DETECTION,
    TASK_MEMORY_EVALUATION,
    TASK_MEMORY_EXTRACTION,
    TASK_MERGE_RECOMMENDATION,
)

_PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"

# Task name → prompt file. Keeps task identifiers and prompt assets in sync.
_TASK_PROMPTS = {
    TASK_MEMORY_EXTRACTION: "memory_extraction.md",
    TASK_MEMORY_EVALUATION: "memory_evaluation.md",
    TASK_CONFLICT_DETECTION: "conflict_detection.md",
    TASK_MERGE_RECOMMENDATION: "merge_recommendation.md",
}


class PromptNotFoundError(KeyError):
    """Raised when a prompt asset is missing for a known task."""


@lru_cache
def get_prompt(name: str) -> str:
    """Return the system-prompt text for a task name (e.g. ``memory_extraction``)."""
    filename = _TASK_PROMPTS.get(name)
    if filename is None:
        raise PromptNotFoundError(f"no prompt registered for task '{name}'")
    path = _PROMPTS_DIR / filename
    if not path.exists():
        raise PromptNotFoundError(f"prompt file missing: {path}")
    return path.read_text(encoding="utf-8")


def available_tasks() -> list[str]:
    return sorted(_TASK_PROMPTS)
