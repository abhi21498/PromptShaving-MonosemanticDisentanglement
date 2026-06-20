"""Repository factory — selects the backend from settings (ADR-001)."""

from __future__ import annotations

from functools import lru_cache

from ..core.config import get_settings
from .repository import Repository


@lru_cache
def get_repository() -> Repository:
    settings = get_settings()
    if settings.storage == "postgres":
        # Lazy import so the in-memory backend needs no sqlalchemy/pgvector.
        from .postgres_repo import PostgresRepository

        return PostgresRepository()
    from .memory_repo import InMemoryRepository

    return InMemoryRepository()
