"""Internal storage entities shared by repository implementations.

Distinct from the API schemas: these carry the embedding and bookkeeping fields
the store needs but the API never returns.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime

from ..schemas.memory import MemoryRecord, MemoryType, Sensitivity, Source, Status


def _now() -> datetime:
    return datetime.now(UTC)


def new_id() -> str:
    return str(uuid.uuid4())


@dataclass
class StoredMemory:
    tenant_id: str
    user_id: str
    memory_type: MemoryType
    content: str
    importance: int
    confidence: float
    sensitivity: Sensitivity
    status: Status
    source: Source
    embedding: list[float] = field(default_factory=list)
    normalized_content: str = ""
    metadata: dict = field(default_factory=dict)
    weight: float = 1.0
    reinforcement_count: int = 0
    id: str = field(default_factory=new_id)
    created_at: datetime = field(default_factory=_now)
    updated_at: datetime = field(default_factory=_now)
    archived_at: datetime | None = None
    deleted_at: datetime | None = None

    def to_schema(self) -> MemoryRecord:
        return MemoryRecord(
            id=self.id,
            tenant_id=self.tenant_id,
            user_id=self.user_id,
            memory_type=self.memory_type,
            content=self.content,
            importance=self.importance,
            confidence=self.confidence,
            sensitivity=self.sensitivity,
            status=self.status,
            source=self.source,
            metadata=self.metadata,
            weight=self.weight,
            reinforcement_count=self.reinforcement_count,
            created_at=self.created_at,
            updated_at=self.updated_at,
        )


@dataclass
class StoredAudit:
    tenant_id: str
    action: str
    reason: str
    user_id: str | None = None
    memory_id: str | None = None
    trace_id: str | None = None
    metadata: dict = field(default_factory=dict)
    id: str = field(default_factory=new_id)
    created_at: datetime = field(default_factory=_now)


@dataclass
class StoredSettings:
    tenant_id: str
    user_id: str
    memory_enabled: bool = True
    require_approval_for_sensitive: bool = True
    temporary_chat: bool = False
