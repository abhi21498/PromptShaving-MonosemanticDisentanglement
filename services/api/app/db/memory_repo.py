"""In-memory repository — default backend for dev/tests (no infra required).

Mirrors the exact query semantics the Postgres backend must honor: tenant+user
scoping on every read, deleted rows excluded from retrieval, append-only audit.
"""

from __future__ import annotations

from datetime import UTC, datetime

from .entities import StoredAudit, StoredMemory, StoredSettings
from .repository import Repository

_ACTIVE = "active"
_DELETED = "deleted"


def _norm(text: str) -> str:
    return " ".join(text.lower().split())


class InMemoryRepository(Repository):
    def __init__(self) -> None:
        self._memories: dict[str, StoredMemory] = {}
        self._audit: list[StoredAudit] = []
        self._settings: dict[tuple[str, str], StoredSettings] = {}

    # ── memory ───────────────────────────────────────────────────────────────
    def create_memory(self, memory: StoredMemory) -> StoredMemory:
        if not memory.source:  # provenance is mandatory (invariant #3)
            raise ValueError("memory.source (provenance) is required")
        self._memories[memory.id] = memory
        return memory

    def _scoped(self, tenant_id: str, user_id: str) -> list[StoredMemory]:
        # Tenant + user isolation enforced here (invariant #1).
        return [
            m
            for m in self._memories.values()
            if m.tenant_id == tenant_id and m.user_id == user_id
        ]

    def get_memory(self, tenant_id: str, user_id: str, memory_id: str) -> StoredMemory | None:
        m = self._memories.get(memory_id)
        if m and m.tenant_id == tenant_id and m.user_id == user_id:
            return m
        return None

    def list_memories(
        self,
        tenant_id: str,
        user_id: str,
        *,
        status: str | None = None,
        memory_type: str | None = None,
        include_deleted: bool = False,
    ) -> list[StoredMemory]:
        rows = self._scoped(tenant_id, user_id)
        if not include_deleted:
            rows = [m for m in rows if m.status.value != _DELETED]
        if status:
            rows = [m for m in rows if m.status.value == status]
        if memory_type:
            rows = [m for m in rows if m.memory_type.value == memory_type]
        return sorted(rows, key=lambda m: m.created_at, reverse=True)

    def update_memory(self, memory: StoredMemory) -> StoredMemory:
        memory.updated_at = datetime.now(UTC)
        self._memories[memory.id] = memory
        return memory

    def soft_delete(self, tenant_id: str, user_id: str, memory_id: str) -> StoredMemory | None:
        m = self.get_memory(tenant_id, user_id, memory_id)
        if not m:
            return None
        from ..schemas.memory import Status

        m.status = Status.deleted
        m.deleted_at = datetime.now(UTC)
        m.updated_at = m.deleted_at
        return m

    def find_similar_active(
        self, tenant_id: str, user_id: str, content: str
    ) -> StoredMemory | None:
        target = _norm(content)
        for m in self._scoped(tenant_id, user_id):
            if m.status.value == _ACTIVE and _norm(m.content) == target:
                return m
        return None

    def retrieve_active(self, tenant_id: str, user_id: str) -> list[StoredMemory]:
        # Only active rows are ever retrievable (invariant #2).
        return [m for m in self._scoped(tenant_id, user_id) if m.status.value == _ACTIVE]

    # ── audit ────────────────────────────────────────────────────────────────
    def add_audit(self, event: StoredAudit) -> StoredAudit:
        self._audit.append(event)  # append-only (invariant #7)
        return event

    def list_audit(
        self, tenant_id: str, user_id: str | None = None, limit: int = 200
    ) -> list[StoredAudit]:
        rows = [e for e in self._audit if e.tenant_id == tenant_id]
        if user_id:
            rows = [e for e in rows if e.user_id == user_id]
        return sorted(rows, key=lambda e: e.created_at, reverse=True)[:limit]

    # ── settings ─────────────────────────────────────────────────────────────
    def get_settings(self, tenant_id: str, user_id: str) -> StoredSettings:
        return self._settings.get(
            (tenant_id, user_id), StoredSettings(tenant_id=tenant_id, user_id=user_id)
        )

    def upsert_settings(self, settings: StoredSettings) -> StoredSettings:
        self._settings[(settings.tenant_id, settings.user_id)] = settings
        return settings

    # ── metrics ──────────────────────────────────────────────────────────────
    def metrics(self, tenant_id: str) -> dict:
        rows = [m for m in self._memories.values() if m.tenant_id == tenant_id]
        by_status: dict[str, int] = {}
        for m in rows:
            by_status[m.status.value] = by_status.get(m.status.value, 0) + 1
        audit = [e for e in self._audit if e.tenant_id == tenant_id]
        by_action: dict[str, int] = {}
        for e in audit:
            by_action[e.action] = by_action.get(e.action, 0) + 1
        return {
            "total_memories": len(rows),
            "by_status": by_status,
            "audit_events": len(audit),
            "by_action": by_action,
        }
