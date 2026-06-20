"""Extractor — turns a conversation turn into candidate memories.

Heuristic by default (no API key). It recognizes explicit "remember…" style
requests and stable preference/constraint statements, classifies the memory
type, and assigns importance/confidence while preserving provenance (the source
excerpt). An LLM adapter can replace the heuristic behind this interface.
"""

from __future__ import annotations

import re

from ..schemas.memory import CandidateMemory, MemoryType, Sensitivity, Source

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


class Extractor:
    def extract(self, message: str, source: Source) -> list[CandidateMemory]:
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

        candidate = CandidateMemory(
            content=content,
            type=mem_type,
            confidence=confidence,
            importance=importance,
            sensitivity=Sensitivity.low,  # policy broker sets the final sensitivity
            source=source,
        )
        return [candidate]
