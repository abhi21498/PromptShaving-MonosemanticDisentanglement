"""Postgres + pgvector repository (SQLAlchemy).

Same tenant-scoping and deletion semantics as the in-memory backend. Imported
only when MEMORYOPS_STORAGE=postgres.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from ..core.config import get_settings
from ..models.sqlalchemy_models import AuditLogORM, Base, MemoryRecordORM, SettingsORM
from ..schemas.memory import MemoryType, Sensitivity, Source, Status
from .entities import StoredAudit, StoredMemory, StoredSettings
from .repository import Repository

_DELETED = "deleted"
_ACTIVE = "active"


def _norm(text: str) -> str:
    return " ".join(text.lower().split())


def _to_stored(row: MemoryRecordORM) -> StoredMemory:
    return StoredMemory(
        id=row.id,
        tenant_id=row.tenant_id,
        user_id=row.user_id,
        memory_type=MemoryType(row.memory_type),
        content=row.content,
        normalized_content=row.normalized_content or "",
        embedding=list(row.embedding) if row.embedding is not None else [],
        importance=row.importance,
        confidence=row.confidence,
        sensitivity=Sensitivity(row.sensitivity),
        status=Status(row.status),
        source=Source(**(row.source or {})),
        metadata=row.extra_metadata or {},
        weight=row.weight,
        reinforcement_count=row.reinforcement_count,
        created_at=row.created_at,
        updated_at=row.updated_at,
        archived_at=row.archived_at,
        deleted_at=row.deleted_at,
    )


class PostgresRepository(Repository):
    def __init__(self) -> None:
        settings = get_settings()
        self._engine = create_engine(settings.database_url, pool_pre_ping=True, future=True)
        self._Session: sessionmaker[Session] = sessionmaker(self._engine, expire_on_commit=False)
        # Migrations own the canonical schema; create_all is a dev convenience.
        Base.metadata.create_all(self._engine)

    # ── memory ───────────────────────────────────────────────────────────────
    def create_memory(self, memory: StoredMemory) -> StoredMemory:
        if not memory.source:
            raise ValueError("memory.source (provenance) is required")
        with self._Session() as s:
            row = MemoryRecordORM(
                id=memory.id,
                tenant_id=memory.tenant_id,
                user_id=memory.user_id,
                memory_type=memory.memory_type.value,
                content=memory.content,
                normalized_content=memory.normalized_content or _norm(memory.content),
                embedding=memory.embedding or None,
                importance=memory.importance,
                confidence=memory.confidence,
                sensitivity=memory.sensitivity.value,
                status=memory.status.value,
                source=memory.source.model_dump(),
                extra_metadata=memory.metadata,
                weight=memory.weight,
                reinforcement_count=memory.reinforcement_count,
            )
            s.add(row)
            s.commit()
            return _to_stored(row)

    def get_memory(self, tenant_id: str, user_id: str, memory_id: str) -> StoredMemory | None:
        with self._Session() as s:
            row = s.get(MemoryRecordORM, memory_id)
            if row and row.tenant_id == tenant_id and row.user_id == user_id:
                return _to_stored(row)
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
        with self._Session() as s:
            stmt = select(MemoryRecordORM).where(
                MemoryRecordORM.tenant_id == tenant_id,
                MemoryRecordORM.user_id == user_id,
            )
            if not include_deleted:
                stmt = stmt.where(MemoryRecordORM.status != _DELETED)
            if status:
                stmt = stmt.where(MemoryRecordORM.status == status)
            if memory_type:
                stmt = stmt.where(MemoryRecordORM.memory_type == memory_type)
            stmt = stmt.order_by(MemoryRecordORM.created_at.desc())
            return [_to_stored(r) for r in s.scalars(stmt)]

    def update_memory(self, memory: StoredMemory) -> StoredMemory:
        with self._Session() as s:
            row = s.get(MemoryRecordORM, memory.id)
            if not row:
                raise ValueError("memory not found")
            row.content = memory.content
            row.importance = memory.importance
            row.confidence = memory.confidence
            row.sensitivity = memory.sensitivity.value
            row.status = memory.status.value
            row.weight = memory.weight
            row.reinforcement_count = memory.reinforcement_count
            row.updated_at = datetime.now(UTC)
            s.commit()
            return _to_stored(row)

    def soft_delete(self, tenant_id: str, user_id: str, memory_id: str) -> StoredMemory | None:
        with self._Session() as s:
            row = s.get(MemoryRecordORM, memory_id)
            if not row or row.tenant_id != tenant_id or row.user_id != user_id:
                return None
            row.status = _DELETED
            now = datetime.now(UTC)
            row.deleted_at = now
            row.updated_at = now
            s.commit()
            return _to_stored(row)

    def find_similar_active(
        self, tenant_id: str, user_id: str, content: str
    ) -> StoredMemory | None:
        with self._Session() as s:
            stmt = select(MemoryRecordORM).where(
                MemoryRecordORM.tenant_id == tenant_id,
                MemoryRecordORM.user_id == user_id,
                MemoryRecordORM.status == _ACTIVE,
                MemoryRecordORM.normalized_content == _norm(content),
            )
            row = s.scalars(stmt).first()
            return _to_stored(row) if row else None

    def retrieve_active(self, tenant_id: str, user_id: str) -> list[StoredMemory]:
        return self.list_memories(tenant_id, user_id, status=_ACTIVE)

    # ── audit ────────────────────────────────────────────────────────────────
    def add_audit(self, event: StoredAudit) -> StoredAudit:
        with self._Session() as s:
            row = AuditLogORM(
                id=event.id,
                tenant_id=event.tenant_id,
                user_id=event.user_id,
                memory_id=event.memory_id,
                action=event.action,
                reason=event.reason,
                trace_id=event.trace_id,
                extra_metadata=event.metadata,
            )
            s.add(row)
            s.commit()
            return event

    def list_audit(
        self, tenant_id: str, user_id: str | None = None, limit: int = 200
    ) -> list[StoredAudit]:
        with self._Session() as s:
            stmt = select(AuditLogORM).where(AuditLogORM.tenant_id == tenant_id)
            if user_id:
                stmt = stmt.where(AuditLogORM.user_id == user_id)
            stmt = stmt.order_by(AuditLogORM.created_at.desc()).limit(limit)
            return [
                StoredAudit(
                    id=r.id,
                    tenant_id=r.tenant_id,
                    user_id=r.user_id,
                    memory_id=r.memory_id,
                    action=r.action,
                    reason=r.reason,
                    trace_id=r.trace_id,
                    metadata=r.extra_metadata or {},
                    created_at=r.created_at,
                )
                for r in s.scalars(stmt)
            ]

    # ── settings ─────────────────────────────────────────────────────────────
    def get_settings(self, tenant_id: str, user_id: str) -> StoredSettings:
        with self._Session() as s:
            stmt = select(SettingsORM).where(
                SettingsORM.tenant_id == tenant_id, SettingsORM.user_id == user_id
            )
            row = s.scalars(stmt).first()
            if not row:
                return StoredSettings(tenant_id=tenant_id, user_id=user_id)
            return StoredSettings(
                tenant_id=row.tenant_id,
                user_id=row.user_id,
                memory_enabled=row.memory_enabled,
                require_approval_for_sensitive=row.require_approval_for_sensitive,
                temporary_chat=row.temporary_chat,
            )

    def upsert_settings(self, settings: StoredSettings) -> StoredSettings:
        with self._Session() as s:
            stmt = select(SettingsORM).where(
                SettingsORM.tenant_id == settings.tenant_id,
                SettingsORM.user_id == settings.user_id,
            )
            row = s.scalars(stmt).first()
            if not row:
                row = SettingsORM(tenant_id=settings.tenant_id, user_id=settings.user_id)
                s.add(row)
            row.memory_enabled = settings.memory_enabled
            row.require_approval_for_sensitive = settings.require_approval_for_sensitive
            row.temporary_chat = settings.temporary_chat
            row.updated_at = datetime.now(UTC)
            s.commit()
            return settings

    # ── metrics ──────────────────────────────────────────────────────────────
    def metrics(self, tenant_id: str) -> dict:
        with self._Session() as s:
            mems = list(
                s.scalars(
                    select(MemoryRecordORM).where(MemoryRecordORM.tenant_id == tenant_id)
                )
            )
            audit = list(
                s.scalars(select(AuditLogORM).where(AuditLogORM.tenant_id == tenant_id))
            )
        by_status: dict[str, int] = {}
        for m in mems:
            by_status[m.status] = by_status.get(m.status, 0) + 1
        by_action: dict[str, int] = {}
        for e in audit:
            by_action[e.action] = by_action.get(e.action, 0) + 1
        return {
            "total_memories": len(mems),
            "by_status": by_status,
            "audit_events": len(audit),
            "by_action": by_action,
        }
