"""Typed application settings (pydantic-settings).

All configuration flows through this single object so behavior is explicit and
testable. Environment variables override defaults; a local .env is honored.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="", env_file=".env", extra="ignore")

    service_name: str = "memoryops-api"
    log_level: str = "INFO"

    # Storage backend: "memory" runs with no infra (default for dev/tests),
    # "postgres" uses SQLAlchemy + pgvector.
    storage: Literal["memory", "postgres"] = "memory"
    database_url: str = "postgresql+psycopg://memoryops:memoryops@localhost:5432/memoryops"

    redis_url: str = "redis://localhost:6379/0"

    # LLM + embeddings. "heuristic" requires no API keys and keeps the system
    # fully functional offline (graceful degradation, invariant #4).
    llm_provider: Literal["heuristic", "openai", "anthropic", "gemini"] = "heuristic"
    embeddings_provider: Literal["heuristic", "openai"] = "heuristic"
    embedding_dim: int = 1536

    openai_api_key: str = ""
    anthropic_api_key: str = ""
    gemini_api_key: str = ""

    # Reliability knobs (used by core.reliability).
    llm_timeout_seconds: float = 8.0
    retrieval_timeout_seconds: float = 3.0
    circuit_breaker_threshold: int = 5
    circuit_breaker_reset_seconds: float = 30.0


@lru_cache
def get_settings() -> Settings:
    # MEMORYOPS_STORAGE is the documented public knob; map it onto `storage`.
    import os

    overrides = {}
    if (val := os.getenv("MEMORYOPS_STORAGE")) in ("memory", "postgres"):
        overrides["storage"] = val
    return Settings(**overrides)
