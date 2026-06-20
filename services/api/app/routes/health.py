"""Liveness + readiness probes."""

from __future__ import annotations

from fastapi import APIRouter

from .. import __version__
from ..core.config import get_settings
from ..db.factory import get_repository

router = APIRouter(tags=["ops"])


@router.get("/healthz")
def healthz() -> dict:
    return {"status": "ok", "version": __version__}


@router.get("/readyz")
def readyz() -> dict:
    settings = get_settings()
    ready = True
    detail = "ready"
    try:
        # Touch the repository so a misconfigured DB surfaces as not-ready.
        get_repository().metrics("__readiness_probe__")
    except Exception as exc:  # noqa: BLE001
        ready = False
        detail = f"repository unavailable: {type(exc).__name__}"
    return {
        "ready": ready,
        "storage": settings.storage,
        "llm_provider": settings.llm_provider,
        "detail": detail,
    }
