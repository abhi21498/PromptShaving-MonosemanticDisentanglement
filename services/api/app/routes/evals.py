"""POST /api/evals/run — run the invariant eval harness."""

from __future__ import annotations

from fastapi import APIRouter

from ..services.eval_harness import run_evals

router = APIRouter(prefix="/api/evals", tags=["evaluation"])


@router.post("/run")
def run() -> dict:
    return run_evals().to_dict()
