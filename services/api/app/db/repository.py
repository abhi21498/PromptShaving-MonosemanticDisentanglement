"""Repository interface.

Every method is tenant + user scoped (invariant #1). Reads exclude non-active
status unless explicitly asked (invariant #2). This is the single place where
isolation and deletion guarantees are enforced for all callers.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from .entities import StoredAudit, StoredMemory, StoredSettings


class Repository(ABC):
    # ── memory ───────────────────────────────────────────────────────────────
    @abstractmethod
    def create_memory(self, memory: StoredMemory) -> StoredMemory: ...

    @abstractmethod
    def get_memory(self, tenant_id: str, user_id: str, memory_id: str) -> StoredMemory | None: ...

    @abstractmethod
    def list_memories(
        self,
        tenant_id: str,
        user_id: str,
        *,
        status: str | None = None,
        memory_type: str | None = None,
        include_deleted: bool = False,
    ) -> list[StoredMemory]: ...

    @abstractmethod
    def update_memory(self, memory: StoredMemory) -> StoredMemory: ...

    @abstractmethod
    def soft_delete(self, tenant_id: str, user_id: str, memory_id: str) -> StoredMemory | None: ...

    @abstractmethod
    def find_similar_active(
        self, tenant_id: str, user_id: str, content: str
    ) -> StoredMemory | None: ...

    @abstractmethod
    def retrieve_active(self, tenant_id: str, user_id: str) -> list[StoredMemory]: ...

    # ── audit ────────────────────────────────────────────────────────────────
    @abstractmethod
    def add_audit(self, event: StoredAudit) -> StoredAudit: ...

    @abstractmethod
    def list_audit(
        self, tenant_id: str, user_id: str | None = None, limit: int = 200
    ) -> list[StoredAudit]: ...

    # ── settings ─────────────────────────────────────────────────────────────
    @abstractmethod
    def get_settings(self, tenant_id: str, user_id: str) -> StoredSettings: ...

    @abstractmethod
    def upsert_settings(self, settings: StoredSettings) -> StoredSettings: ...

    # ── metrics ──────────────────────────────────────────────────────────────
    @abstractmethod
    def metrics(self, tenant_id: str) -> dict: ...
