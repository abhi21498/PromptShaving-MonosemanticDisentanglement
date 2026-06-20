"""Memory CRUD: list, patch (edit/approve/reject/archive), delete (soft)."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, Request

from ..db.factory import get_repository
from ..deps import audit_service
from ..schemas.memory import DeleteRequest, MemoryPatch, MemoryRecord, Status

router = APIRouter(prefix="/api/memories", tags=["memories"])


@router.get("", response_model=list[MemoryRecord])
def list_memories(
    tenant_id: str = Query(...),
    user_id: str = Query(...),
    status: str | None = Query(None),
    memory_type: str | None = Query(None),
) -> list[MemoryRecord]:
    repo = get_repository()
    rows = repo.list_memories(
        tenant_id, user_id, status=status, memory_type=memory_type
    )
    return [r.to_schema() for r in rows]


@router.patch("/{memory_id}", response_model=MemoryRecord)
def patch_memory(memory_id: str, patch: MemoryPatch, request: Request) -> MemoryRecord:
    repo = get_repository()
    trace_id = getattr(request.state, "trace_id", "-")
    m = repo.get_memory(patch.tenant_id, patch.user_id, memory_id)
    if not m or m.status == Status.deleted:
        raise HTTPException(status_code=404, detail="memory not found")

    action = "memory_updated"
    reason = "memory edited"
    if patch.content is not None:
        m.content = patch.content
        m.normalized_content = " ".join(patch.content.lower().split())
    if patch.importance is not None:
        m.importance = patch.importance
    if patch.confidence is not None:
        m.confidence = patch.confidence
    if patch.status is not None:
        m.status = patch.status
        if patch.status == Status.active:
            action, reason = "memory_approved", "pending memory approved"
        elif patch.status == Status.rejected:
            action, reason = "memory_rejected", "pending memory rejected"
        elif patch.status == Status.archived:
            action, reason = "memory_archived", "memory archived"

    repo.update_memory(m)
    audit_service().record(
        tenant_id=patch.tenant_id,
        user_id=patch.user_id,
        memory_id=memory_id,
        action=action,
        reason=reason,
        trace_id=trace_id,
    )
    return m.to_schema()


@router.delete("/{memory_id}")
def delete_memory(memory_id: str, body: DeleteRequest, request: Request) -> dict:
    repo = get_repository()
    trace_id = getattr(request.state, "trace_id", "-")
    m = repo.soft_delete(body.tenant_id, body.user_id, memory_id)
    if not m:
        raise HTTPException(status_code=404, detail="memory not found")
    audit_service().record(
        tenant_id=body.tenant_id,
        user_id=body.user_id,
        memory_id=memory_id,
        action="memory_deleted",
        reason="memory soft-deleted; excluded from all future retrieval",
        trace_id=trace_id,
    )
    return {"id": memory_id, "status": "deleted"}
