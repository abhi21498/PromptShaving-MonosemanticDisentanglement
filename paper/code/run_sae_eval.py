#!/usr/bin/env python3
"""
SAE Reflection Evaluation Harness (M3).

Runs baseline vs SAE reflection comparison on seeded memory cases.
Metrics: MRR@10, Monosemanticity, Gov Field Fill%, Answer Accuracy.
"""

from __future__ import annotations

import argparse
import json
import os
import random
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

import torch

# Ensure env vars are set before importing settings
if "MEMORYOPS_WORKERS_REFLECTION_SAE" not in os.environ:
    os.environ["MEMORYOPS_WORKERS_REFLECTION_SAE"] = "false"

# Add services/api to path so 'app' module is importable
sys.path.insert(0, str(Path(__file__).parent.parent / "services" / "api"))

from app.core.config import get_settings
from app.db.factory import get_repository
from app.db.repository import Repository
from app.services.audit import AuditService
from app.workers.sae_reflection_worker import SAEReflectionWorker
from app.workers.sae_reflection import create_reflector
from app.schemas.memory import Source, MemoryType, Sensitivity, Status


def mrr_at_k(ranked_list: list[str], relevant: set[str], k: int = 10) -> float:
    """Mean Reciprocal Rank @ k."""
    for rank, doc_id in enumerate(ranked_list[:k], 1):
        if doc_id in relevant:
            return 1.0 / rank
    return 0.0


def run_condition(
    repo: Repository,
    audit: AuditService,
    tenant_id: str,
    user_id: str,
    enable_sae: bool,
    sae_config: dict | None = None,
) -> dict:
    """Run a single evaluation condition and return metrics."""
    # Enable/disable SAE reflection
    if enable_sae:
        os.environ["MEMORYOPS_WORKERS_REFLECTION_SAE"] = "true"
        if sae_config:
            for k, v in sae_config.items():
                os.environ[f"MEMORYOPS_WORKERS_REFLECTION_SAE_{k.upper()}"] = str(v)
        get_settings.cache_clear()
    else:
        os.environ["MEMORYOPS_WORKERS_REFLECTION_SAE"] = "false"
        get_settings.cache_clear()

    settings = get_settings()
    print(f"  SAE enabled: {settings.workers_reflection_sae_enabled}")

    # First, populate seed memories
    from app.schemas.memory import ChatRequest, Source, MemoryType, Sensitivity
    from app.workers.lifecycle import WorkerContext
    from app.workers.schemas import WorkerJobResult, WorkerRunStatus
    import uuid

    # Clear existing memories for this tenant/user
    if hasattr(repo, "_memories"):
        repo._memories = {
            k: v for k, v in repo._memories.items()
            if not (v.tenant_id == tenant_id and v.user_id == user_id)
        }

    seed_memories = [
        {
            "content": "User prefers Python for data science and machine learning tasks.",
            "memory_type": MemoryType.semantic,
            "importance": 8,
            "confidence": 0.9,
        },
        {
            "content": "User works at Easyrewardz Software Services Private Limited.",
            "memory_type": MemoryType.semantic,
            "importance": 7,
            "confidence": 0.95,
        },
        {
            "content": "User configures Redis cache instances for production UAT environment.",
            "memory_type": MemoryType.episodic,
            "importance": 6,
            "confidence": 0.8,
        },
        {
            "content": "User prefers concise, enterprise-style explanations.",
            "memory_type": MemoryType.procedural,
            "importance": 7,
            "confidence": 0.85,
        },
    ]

    for mem in seed_memories:
        from app.db.entities import StoredMemory
        from app.schemas.memory import Source

        stored = StoredMemory(
            tenant_id=tenant_id,
            user_id=user_id,
            memory_type=mem["memory_type"],
            content=mem["content"],
            normalized_content=mem["content"],
            importance=mem["importance"],
            confidence=mem["confidence"],
            sensitivity=Sensitivity.low,
            status=Status.active,
            source=Source(kind="chat", excerpt=mem["content"]),
        )
        repo.create_memory(stored)

    # Run SAE reflection worker if enabled
    if enable_sae:
        reflector = create_reflector(sae_config)
        worker = SAEReflectionWorker(repo, audit, reflector)
        ctx = WorkerContext(
            tenant_id=tenant_id,
            user_id=user_id,
            trace_id=f"eval_{int(time.time())}",
            now=datetime.now(UTC),
            dry_run=False,
        )
        result = WorkerJobResult(
            job="reflection_sae",
            tenant_id=tenant_id,
            user_id=user_id,
            started_at=datetime.now(UTC),
        )
        worker._execute(ctx, result)
        print(f"  SAE reflection: scanned={result.scanned_count}, changed={result.changed_count}")

    # Run evaluation queries
    from app.services.gateway import Gateway

    gateway = Gateway(repo)

    queries = [
        ("What programming language does the user prefer for data science?", {"python"}),
        ("Where does the user work?", {"easyrewardz"}),
        ("What does the user configure for production?", {"redis"}),
        ("How detailed should explanations be?", {"concise", "enterprise"}),
    ]

    mrrs = []
    trace_lengths = []
    gov_fill_rates = []
    answer_correct = []

    for query, relevant_terms in queries:
        chat_req = ChatRequest(
            tenant_id=tenant_id,
            user_id=user_id,
            message=query,
            temporary_chat=False,
        )
        response = gateway.handle_chat(chat_req, trace_id=f"eval_{uuid.uuid4()}")

        # MRR@10
        used_ids = [m.memory_id for m in response.used_memories]
        mrr = 0.0
        # For simplicity, check if any used memory content contains relevant term
        for rank, mid in enumerate(used_ids[:10], 1):
            mem = repo.get_memory(tenant_id, user_id, mid)
            if mem and any(term in mem.content.lower() for term in relevant_terms):
                mrr = 1.0 / rank
                break
        mrrs.append(mrr)

        # Trace length
        trace_lengths.append(len(response.used_memories))

        # Gov field fill rate
        if response.trace:
            filled = 0
            total = 0
            for mem in response.trace.memories_used:
                total += 6
                if mem.legal_hold is not None:
                    filled += 1
                if mem.legal_hold_reason is not None:
                    filled += 1
                if mem.pinned is not None:
                    filled += 1
                if mem.protected is not None:
                    filled += 1
                if mem.retention_policy is not None:
                    filled += 1
                if mem.retention_expires_at is not None:
                    filled += 1
            gov_fill_rates.append(filled / max(total, 1))

        # Answer correctness (simple keyword match)
        answer_lower = response.assistant_message.lower()
        correct = any(term in answer_lower for term in relevant_terms)
        answer_correct.append(1.0 if correct else 0.0)

    return {
        "MRR@10": sum(mrrs) / max(len(mrrs), 1),
        "AvgTraceLen": sum(trace_lengths) / max(len(trace_lengths), 1),
        "GovFieldFill%": sum(gov_fill_rates) / max(len(gov_fill_rates), 1) * 100,
        "AnswerAcc%": sum(answer_correct) / max(len(answer_correct), 1) * 100,
    }


def run_ablation(
    repo: Repository,
    audit: AuditService,
    tenant_id: str,
    user_id: str,
    lambdas: list[float],
    num_atoms_list: list[int],
) -> list[dict]:
    """Run ablation sweep over λ and num_atoms."""
    results = []

    for lmb in lambdas:
        for num_atoms in num_atoms_list:
            print(f"\n=== Ablation: λ={lmb}, num_atoms={num_atoms} ===")

            sae_config = {
                "l1_lambda": lmb,
                "num_atoms": num_atoms,
            }

            metrics = run_condition(
                repo, audit, tenant_id, user_id,
                enable_sae=True,
                sae_config=sae_config,
            )

            result = {
                "lambda": lmb,
                "num_atoms": num_atoms,
                **metrics,
            }
            results.append(result)
            print(f"  MRR@10: {metrics['MRR@10']:.4f}")
            print(f"  AvgTraceLen: {metrics['AvgTraceLen']:.2f}")
            print(f"  GovFieldFill%: {metrics['GovFieldFill%']:.1f}")
            print(f"  AnswerAcc%: {metrics['AnswerAcc%']:.1f}")

    return results


def main():
    parser = argparse.ArgumentParser(description="SAE Reflection Evaluation Harness")
    parser.add_argument("--lambda", type=float, default=1e-3, help="L1 sparsity strength")
    parser.add_argument("--num-atoms", type=int, default=5, help="Number of atoms per memory")
    parser.add_argument("--tenant", default="t_eval", help="Tenant ID")
    parser.add_argument("--user", default="u_eval", help="User ID")
    parser.add_argument("--full-grid", action="store_true", help="Run full ablation grid")
    parser.add_argument("--output", help="Output JSON file")
    args = parser.parse_args()

    # lambda is a Python keyword, so access via getattr
    lambda_val = getattr(args, 'lambda')

    # Set seed for reproducibility
    random.seed(42)
    torch.manual_seed(42)

    tenant_id = args.tenant
    user_id = args.user

    repo = get_repository()
    audit = AuditService(repo)

    # Run baseline
    print("=== Baseline (no SAE) ===")
    baseline = run_condition(repo, audit, tenant_id, user_id, enable_sae=False)
    print(f"  MRR@10: {baseline['MRR@10']:.4f}")
    print(f"  AvgTraceLen: {baseline['AvgTraceLen']:.2f}")
    print(f"  GovFieldFill%: {baseline['GovFieldFill%']:.1f}")
    print(f"  AnswerAcc%: {baseline['AnswerAcc%']:.1f}")

    # Run SAE condition
    lambda_val = getattr(args, 'lambda')
    print(f"\n=== SAE (lambda={lambda_val}, atoms={args.num_atoms}) ===")
    sae_config = {
        "l1_lambda": lambda_val,
        "num_atoms": args.num_atoms,
    }
    sae_metrics = run_condition(repo, audit, tenant_id, user_id, enable_sae=True, sae_config=sae_config)
    print(f"  MRR@10: {sae_metrics['MRR@10']:.4f}")
    print(f"  AvgTraceLen: {sae_metrics['AvgTraceLen']:.2f}")
    print(f"  GovFieldFill%: {sae_metrics['GovFieldFill%']:.1f}")
    print(f"  AnswerAcc%: {sae_metrics['AnswerAcc%']:.1f}")

    # Summary table
    print("\n=== Summary ===")
    print(f"{'Condition':<20} {'MRR@10':<10} {'TraceLen':<10} {'GovFill%':<10} {'Acc%':<10}")
    print("-" * 60)
    print(f"{'Baseline':<20} {baseline['MRR@10']:<10.4f} {baseline['AvgTraceLen']:<10.2f} {baseline['GovFieldFill%']:<10.1f} {baseline['AnswerAcc%']:<10.1f}")
    print(f"{'SAE':<20} {sae_metrics['MRR@10']:<10.4f} {sae_metrics['AvgTraceLen']:<10.2f} {sae_metrics['GovFieldFill%']:<10.1f} {sae_metrics['AnswerAcc%']:<10.1f}")

    # Ablation grid
    if args.full_grid:
        print("\n=== Full Ablation Grid ===")
        lambdas = [5e-4, 1e-3, 2e-3, 5e-3]
        num_atoms_list = [3, 5, 7, 10]
        ablation_results = run_ablation(repo, audit, tenant_id, user_id, lambdas, num_atoms_list)

        # Save results
        if args.output:
            with open(args.output, "w") as f:
                json.dump({
                    "baseline": baseline,
                    "sae": sae_metrics,
                    "ablation": ablation_results,
                }, f, indent=2)
            print(f"\nResults saved to {args.output}")

    # Save simple results
    if args.output and not args.full_grid:
        with open(args.output, "w") as f:
            json.dump({
                "baseline": baseline,
                "sae": sae_metrics,
            }, f, indent=2)
        print(f"\nResults saved to {args.output}")


if __name__ == "__main__":
    main()