"""Ranker — weighted blend of retrieval + memory signals (ADR-002, ADR-006).

final_score = 0.35·vector_similarity + 0.20·keyword + 0.15·importance
            + 0.10·confidence + 0.10·recency + 0.10·reinforcement

Each ranked memory carries a ``score_breakdown`` of the weighted contributions so
the API and UI can explain exactly why a memory surfaced (invariant #8). If this
formula changes, docs/api-contracts.md and docs/architecture.md must be updated
(enforced by the PR Invariant Evidence Gate).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

from .retriever import ScoredCandidate

W_SEMANTIC = 0.35
W_KEYWORD = 0.20
W_IMPORTANCE = 0.15
W_CONFIDENCE = 0.10
W_RECENCY = 0.10
W_REINFORCEMENT = 0.10

_RECENCY_HALFLIFE_DAYS = 30.0


def _recency(created_at: datetime) -> float:
    age_days = (datetime.now(UTC) - created_at).total_seconds() / 86400.0
    return 0.5 ** (age_days / _RECENCY_HALFLIFE_DAYS)


@dataclass
class RankedMemory:
    candidate: ScoredCandidate
    score: float
    score_breakdown: dict[str, float] = field(default_factory=dict)

    @property
    def memory(self):
        return self.candidate.memory


class Ranker:
    def rank(self, candidates: list[ScoredCandidate], top_k: int = 5) -> list[RankedMemory]:
        ranked: list[RankedMemory] = []
        for c in candidates:
            m = c.memory
            # Raw, normalized [0,1] component signals (explainability, invariant #8).
            breakdown = {
                "vector_similarity": round(c.semantic, 4),
                "keyword_score": round(c.keyword, 4),
                "importance_score": round(m.importance / 10.0, 4),
                "confidence": round(m.confidence, 4),
                "recency": round(_recency(m.created_at), 4),
                "reinforcement": round(min(m.reinforcement_count / 5.0, 1.0), 4),
            }
            score = round(
                W_SEMANTIC * breakdown["vector_similarity"]
                + W_KEYWORD * breakdown["keyword_score"]
                + W_IMPORTANCE * breakdown["importance_score"]
                + W_CONFIDENCE * breakdown["confidence"]
                + W_RECENCY * breakdown["recency"]
                + W_REINFORCEMENT * breakdown["reinforcement"],
                4,
            )
            ranked.append(RankedMemory(candidate=c, score=score, score_breakdown=breakdown))
        ranked.sort(key=lambda r: r.score, reverse=True)
        # Keep only candidates with at least a weak signal.
        return [r for r in ranked if r.score > 0.05][:top_k]
