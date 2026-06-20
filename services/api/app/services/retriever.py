"""Retriever — hybrid candidate fetch (ADR-002).

Phase 1/2: pulls active, tenant+user-scoped memories and computes semantic
(embedding cosine) and keyword overlap signals. Deleted/pending rows are never
returned because the repository's ``retrieve_active`` filters status.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from ..core.embeddings import cosine, embed
from ..db.entities import StoredMemory
from ..db.repository import Repository

_WORD = re.compile(r"[a-z0-9]+")


def _keywords(text: str) -> set[str]:
    return set(_WORD.findall(text.lower()))


@dataclass
class ScoredCandidate:
    memory: StoredMemory
    semantic: float
    keyword: float


class Retriever:
    def __init__(self, repo: Repository) -> None:
        self._repo = repo

    def retrieve(self, tenant_id: str, user_id: str, query: str) -> list[ScoredCandidate]:
        active = self._repo.retrieve_active(tenant_id, user_id)
        if not active:
            return []
        q_embedding = embed(query)
        q_words = _keywords(query)
        scored: list[ScoredCandidate] = []
        for m in active:
            semantic = cosine(q_embedding, m.embedding) if m.embedding else 0.0
            m_words = _keywords(m.content)
            overlap = len(q_words & m_words)
            keyword = overlap / len(q_words) if q_words else 0.0
            scored.append(ScoredCandidate(memory=m, semantic=semantic, keyword=keyword))
        return scored
