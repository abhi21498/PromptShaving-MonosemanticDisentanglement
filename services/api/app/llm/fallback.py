"""Deterministic heuristics — the universal fallback for the LLM layer (v0.4).

When no provider is configured, a provider fails, times out, or returns invalid
JSON, the structured-intelligence layer degrades to these pure-Python heuristics
(invariant #4). They are deterministic and require no API key, which keeps the
StubProvider and the whole test suite offline-safe.

The extraction heuristic is the canonical behavior the golden evals depend on; it
lived in ``services/extractor.py`` before v0.4 and now has one home so both the
extractor and the StubProvider share it without duplication.
"""

from __future__ import annotations

import re

from ..schemas.memory import MemoryType, Sensitivity
from .schemas import (
    ConflictDetectionResult,
    ConflictItem,
    ExtractedMemory,
    MemoryEvaluationResult,
)

# Cues that a turn contains something worth remembering.
_REMEMBER_CUES = re.compile(
    r"\b(remember|note that|keep in mind|for future reference|don'?t forget|make a note|"
    r"save (this|that|it|for later)|store (this|that|it))\b",
    re.IGNORECASE,
)
_PREFERENCE_CUES = re.compile(
    r"\b(i (prefer|like|love|hate|dislike|always|never|usually|want)|my (preference|style))\b",
    re.IGNORECASE,
)
_CONSTRAINT_CUES = re.compile(
    r"\b(never|do not|don'?t|always|must not|must|avoid)\b", re.IGNORECASE
)
_PROJECT_CUES = re.compile(
    r"\b(i'?m (building|working on)|my project|we'?re building)\b", re.IGNORECASE
)


def _classify(text: str) -> MemoryType:
    if _PROJECT_CUES.search(text):
        return MemoryType.project
    if _PREFERENCE_CUES.search(text):
        # Procedural = how the user wants things done; preference = like/dislike.
        if re.search(r"\b(explain|answer|respond|format|style|tone)\b", text, re.IGNORECASE):
            return MemoryType.procedural
        return MemoryType.preference
    if _CONSTRAINT_CUES.search(text):
        return MemoryType.constraint
    return MemoryType.semantic


def _strip_remember_prefix(text: str) -> str:
    cleaned = re.sub(
        r"^\s*(please\s+)?(remember( that)?|note that|keep in mind( that)?|"
        r"for future reference,?|make a note( that)?|save (this|that|it)( for later)?:?|"
        r"store (this|that|it):?)\s*",
        "",
        text,
        flags=re.IGNORECASE,
    )
    return cleaned.strip().rstrip(".") + "." if cleaned.strip() else text.strip()


def heuristic_extract(message: str) -> list[ExtractedMemory]:
    """Deterministic extraction: recognize explicit/implicit memory statements.

    Returns zero or one ``ExtractedMemory``. Identical in behavior to the pre-v0.4
    extractor so golden evals remain stable; sensitivity is left ``low`` and the
    policy broker assigns the final value.
    """
    text = message.strip()
    if not text:
        return []

    explicit = bool(_REMEMBER_CUES.search(text))
    statement = bool(_PREFERENCE_CUES.search(text) or _PROJECT_CUES.search(text))
    if not (explicit or statement):
        # Pure questions / chit-chat don't produce memory candidates.
        return []

    content = _strip_remember_prefix(text) if explicit else text.rstrip(".") + "."
    mem_type = _classify(text)
    # Explicit "remember" → higher importance/confidence than an inferred one.
    importance = 8 if explicit else 6
    confidence = 0.92 if explicit else 0.7
    return [
        ExtractedMemory(
            content=content,
            type=mem_type,
            importance=importance,
            confidence=confidence,
            sensitivity=Sensitivity.low,
            rationale="heuristic: explicit cue" if explicit else "heuristic: inferred statement",
        )
    ]


def heuristic_evaluate(memory: ExtractedMemory) -> MemoryEvaluationResult:
    """Deterministic advisory evaluation mirroring the extracted scores."""
    return MemoryEvaluationResult(
        suggested_importance=memory.importance,
        suggested_sensitivity=memory.sensitivity,
        is_worth_remembering=memory.importance >= 4,
        rationale="heuristic evaluation",
    )


_NEGATIONS = re.compile(r"\b(no longer|not|never|stop|don'?t|switched? to|instead of)\b", re.I)
_TOKEN = re.compile(r"[a-z0-9]+")


def _content_tokens(text: str) -> set[str]:
    stop = {"i", "a", "an", "the", "to", "of", "my", "is", "are", "that", "this", "it", "for"}
    return {t for t in _TOKEN.findall(text.lower()) if t not in stop and len(t) > 2}


def heuristic_conflicts(
    candidate_content: str, existing: list[tuple[str, str]]
) -> ConflictDetectionResult:
    """Minimal deterministic conflict detection.

    ``existing`` is a list of ``(memory_id, content)``. A conflict is flagged when
    a candidate shares meaningful subject tokens with an existing memory and one
    of the two contains a negation/switch cue the other does not — a cheap proxy
    for "the user changed their mind". This is advisory metadata only.
    """
    cand_tokens = _content_tokens(candidate_content)
    cand_neg = bool(_NEGATIONS.search(candidate_content))
    conflicts: list[ConflictItem] = []
    for mem_id, content in existing:
        overlap = cand_tokens & _content_tokens(content)
        if len(overlap) < 2:
            continue
        exist_neg = bool(_NEGATIONS.search(content))
        if cand_neg != exist_neg:
            conflicts.append(
                ConflictItem(
                    existing_memory_id=mem_id,
                    existing_content=content,
                    relation="contradicts",
                    explanation=(
                        "shared subject "
                        f"({', '.join(sorted(overlap))}) with opposing polarity"
                    ),
                )
            )
    return ConflictDetectionResult(has_conflict=bool(conflicts), conflicts=conflicts)
