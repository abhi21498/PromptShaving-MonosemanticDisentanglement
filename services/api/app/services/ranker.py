"""Ranker — weighted blend of retrieval + memory signals (ADR-002).

final_score = 0.35·semantic + 0.20·keyword + 0.15·importance
            + 0.10·recency + 0.10·confidence + 0.10·reinforcement
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from .retriever import ScoredCandidate

W_SEMANTIC = 0.35
W_KEYWORD = 0.20
W_IMPORTANCE = 0.15
W_RECENCY = 0.10
W_CONFIDENCE = 0.10
W_REINFORCEMENT = 0.10

_RECENCY_HALFLIFE_DAYS = 30.0


def _recency(created_at: datetime) -> float:
    age_days = (datetime.now(UTC) - created_at).total_seconds() / 86400.0
    return 0.5 ** (age_days / _RECENCY_HALFLIFE_DAYS)


@dataclass
class RankedMemory:
    candidate: ScoredCandidate
    score: float

    @property
    def memory(self):
        return self.candidate.memory


class Ranker:
    def rank(self, candidates: list[ScoredCandidate], top_k: int = 5) -> list[RankedMemory]:
        ranked: list[RankedMemory] = []
        for c in candidates:
            m = c.memory
            score = (
                W_SEMANTIC * c.semantic
                + W_KEYWORD * c.keyword
                + W_IMPORTANCE * (m.importance / 10.0)
                + W_RECENCY * _recency(m.created_at)
                + W_CONFIDENCE * m.confidence
                + W_REINFORCEMENT * min(m.reinforcement_count / 5.0, 1.0)
            )
            ranked.append(RankedMemory(candidate=c, score=round(score, 4)))
        ranked.sort(key=lambda r: r.score, reverse=True)
        # Keep only candidates with at least a weak signal.
        return [r for r in ranked if r.score > 0.05][:top_k]
