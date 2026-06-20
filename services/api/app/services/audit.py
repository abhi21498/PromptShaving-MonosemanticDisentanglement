"""Audit service — append-only lifecycle events (invariant #7, ADR-004).

Every lifecycle action MUST route through here. The event is persisted via the
repository and also emitted to the structured log for operational correlation.
"""

from __future__ import annotations

from ..core.logging import get_logger
from ..db.entities import StoredAudit
from ..db.repository import Repository

logger = get_logger("memoryops.audit")


class AuditService:
    def __init__(self, repo: Repository) -> None:
        self._repo = repo

    def record(
        self,
        *,
        tenant_id: str,
        action: str,
        reason: str,
        user_id: str | None = None,
        memory_id: str | None = None,
        trace_id: str | None = None,
        metadata: dict | None = None,
    ) -> StoredAudit:
        event = StoredAudit(
            tenant_id=tenant_id,
            user_id=user_id,
            memory_id=memory_id,
            action=action,
            reason=reason,
            trace_id=trace_id,
            metadata=metadata or {},
        )
        self._repo.add_audit(event)
        logger.info(reason, extra={"event": action, "status": "audit"})
        return event
