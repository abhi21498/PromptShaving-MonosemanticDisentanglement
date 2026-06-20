"""Gateway — orchestrates the read + write paths for a chat turn.

Order of operations (enforces several invariants):
  1. Load settings. If temporary_chat or memory disabled → no read, no write (#6).
  2. READ: retrieve → rank → compose context (wrapped for graceful degradation #4).
  3. Generate the assistant response (heuristic LLM by default).
  4. WRITE: extract → policy broker (before storage #5) → write service → audit (#7).
"""

from __future__ import annotations

import time

from ..core.llm import get_llm
from ..core.logging import get_logger
from ..core.reliability import safe_call
from ..db.repository import Repository
from ..schemas.memory import (
    ChatRequest,
    ChatResponse,
    Source,
    UsedMemory,
)
from .audit import AuditService
from .context_composer import ContextComposer
from .extractor import Extractor
from .policy_broker import PolicyBroker
from .ranker import Ranker
from .retriever import Retriever
from .write_service import WriteService

logger = get_logger("memoryops.gateway")


class Gateway:
    def __init__(self, repo: Repository) -> None:
        self._repo = repo
        self._audit = AuditService(repo)
        self._extractor = Extractor()
        self._policy = PolicyBroker(repo)
        self._writer = WriteService(repo, self._audit)
        self._retriever = Retriever(repo)
        self._ranker = Ranker()
        self._composer = ContextComposer()
        self._llm = get_llm()

    def handle_chat(self, req: ChatRequest, trace_id: str) -> ChatResponse:
        start = time.monotonic()
        settings = self._repo.get_settings(req.tenant_id, req.user_id)

        # ── Invariant #6: temporary chat / memory off → no read, no write ──────
        if req.temporary_chat or not settings.memory_enabled:
            reason = "temporary_chat" if req.temporary_chat else "memory_disabled"
            self._audit.record(
                tenant_id=req.tenant_id,
                user_id=req.user_id,
                action="temporary_chat_skipped",
                reason=f"memory bypassed: {reason}",
                trace_id=trace_id,
            )
            answer = self._llm.complete(system="", user=req.message)
            return ChatResponse(
                assistant_message=answer,
                used_memories=[],
                candidate_memories=[],
                audit_event_ids=[],
                temporary_chat=req.temporary_chat,
                trace_id=trace_id,
            )

        # ── READ path (graceful degradation: never blocks the response) ────────
        used_memories: list[UsedMemory] = []
        context_block = ""

        def _read() -> tuple[str, list[UsedMemory]]:
            scored = self._retriever.retrieve(req.tenant_id, req.user_id, req.message)
            ranked = self._ranker.rank(scored)
            return self._composer.compose(ranked)

        context_block, used_memories = safe_call(_read, default=("", []), label="retrieval")
        if used_memories:
            self._audit.record(
                tenant_id=req.tenant_id,
                user_id=req.user_id,
                action="memory_retrieved",
                reason=f"retrieved {len(used_memories)} memory(ies) for context",
                trace_id=trace_id,
                metadata={"memory_count": len(used_memories)},
            )

        # ── Response generation ────────────────────────────────────────────────
        answer = self._llm.complete(system=context_block, user=req.message)

        # ── WRITE path (policy before storage) ─────────────────────────────────
        source = Source(kind="chat", excerpt=req.message, conversation_id=req.conversation_id)
        candidates = self._extractor.extract(req.message, source)
        decisions = []
        audit_ids: list[str] = []
        for cand in candidates:
            outcome = self._policy.evaluate(
                cand, tenant_id=req.tenant_id, user_id=req.user_id, settings=settings
            )
            decision_view, ids = self._writer.commit(
                outcome, tenant_id=req.tenant_id, user_id=req.user_id, trace_id=trace_id
            )
            decisions.append(decision_view)
            audit_ids.extend(ids)

        latency_ms = int((time.monotonic() - start) * 1000)
        logger.info(
            "chat handled",
            extra={
                "event": "chat",
                "latency_ms": latency_ms,
                "memory_count": len(used_memories),
                "status": "success",
            },
        )

        return ChatResponse(
            assistant_message=answer,
            used_memories=used_memories,
            candidate_memories=decisions,
            audit_event_ids=audit_ids,
            temporary_chat=False,
            trace_id=trace_id,
        )
