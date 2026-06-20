"""POST /api/chat — the write+read path entrypoint."""

from __future__ import annotations

from fastapi import APIRouter, Request

from ..deps import gateway
from ..schemas.memory import ChatRequest, ChatResponse

router = APIRouter(prefix="/api", tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest, request: Request) -> ChatResponse:
    trace_id = getattr(request.state, "trace_id", "-")
    return gateway().handle_chat(req, trace_id=trace_id)
