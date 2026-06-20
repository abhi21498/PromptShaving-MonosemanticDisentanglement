"""Test fixtures — force the in-memory backend and a fresh stack per test."""

from __future__ import annotations

import os

os.environ["MEMORYOPS_STORAGE"] = "memory"

import pytest  # noqa: E402

from app.db.memory_repo import InMemoryRepository  # noqa: E402
from app.services.gateway import Gateway  # noqa: E402


@pytest.fixture
def repo() -> InMemoryRepository:
    return InMemoryRepository()


@pytest.fixture
def gateway(repo: InMemoryRepository) -> Gateway:
    return Gateway(repo)
