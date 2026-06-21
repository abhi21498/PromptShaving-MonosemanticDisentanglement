"""Context Composer — compact context block + explainability payload (ADR-002).

Produces (a) a short text block to prepend to the LLM prompt and (b) the list of
UsedMemory records the API returns so the UI can show which memories shaped the
answer (invariant #8). Internal source IDs stay internal; only content + score
are surfaced.
"""

from __future__ import annotations

from ..schemas.memory import UsedMemory
from .ranker import RankedMemory


class ContextComposer:
    def compose(self, ranked: list[RankedMemory]) -> tuple[str, list[UsedMemory]]:
        if not ranked:
            return "", []
        lines = ["Relevant remembered context:"]
        used: list[UsedMemory] = []
        for r in ranked:
            m = r.memory
            lines.append(f"- ({m.memory_type.value}) {m.content}")
            used.append(
                UsedMemory(
                    memory_id=m.id,
                    content=m.content,
                    memory_type=m.memory_type,
                    score=r.score,
                    score_breakdown=r.score_breakdown,
                    reason=f"ranked {r.score} via hybrid retrieval",
                    source=m.source,
                )
            )
        return "\n".join(lines), used
