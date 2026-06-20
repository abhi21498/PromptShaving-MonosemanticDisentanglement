"""Shared dependencies (repository + gateway singletons)."""

from __future__ import annotations

from functools import lru_cache

from .db.factory import get_repository
from .services.audit import AuditService
from .services.gateway import Gateway


@lru_cache
def gateway() -> Gateway:
    return Gateway(get_repository())


@lru_cache
def audit_service() -> AuditService:
    return AuditService(get_repository())
