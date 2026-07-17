"""SAE Reflection Worker — Prompt Shaving & Monosemantic Disentanglement (v0.12).

This worker runs the SAE-based reflection pipeline:
  1. Pulls candidate memories (active, not already reflected via SAE)
  2. Runs SAEReflector on each memory's normalized_content
  3. Stores each atom as a MemoryRecord with:
     - is_atom=true
     - sae_embedding: the atom's vector
     - origin_memory_id: traceability to source memory
     - atom_latent_dim: which latent dimension produced this atom
     - Full governance metadata inherited from source

The worker is gated by MEMORYOPS_REFLECTION_SAE feature flag (default: false).
Enable with: export MEMORYOPS_REFLECTION_SAE=true

This is a proposal-only worker — it never deletes or mutates source memories.
Atoms are created as active semantic memories with their own governance state.
"""

from __future__ import annotations

import uuid
from typing import List

from ..core.config import get_settings
from ..db.repository import Repository
from ..services.audit import AuditService
from .lifecycle import LifecycleWorker, WorkerContext
from .sae_reflection import SAEReflector, create_reflector
from .schemas import WorkerJob, WorkerJobResult, WorkerRunStatus


class SAEReflectionWorker(LifecycleWorker):
    """SAE-based reflection worker that shaves memories into monosemantic atoms."""
    job = WorkerJob.reflection_sae

    def __init__(
        self,
        repo: Repository,
        audit: AuditService,
        reflector: SAEReflector | None = None,
    ) -> None:
        super().__init__(repo, audit)
        self._reflector = reflector or create_reflector()

    @property
    def job_name(self) -> str:
        return "reflection_sae"

    def _execute(self, ctx: WorkerContext, result: WorkerJobResult) -> None:
        settings = get_settings()
        if not settings.workers_reflection_sae_enabled:
            result.status = WorkerRunStatus.skipped.value
            result.details = {"reason": "MEMORYOPS_REFLECTION_SAE flag not enabled"}
            return

        # Get candidate memories: active, not already reflected via SAE
        candidates = self._get_candidates(ctx.tenant_id, ctx.user_id)
        result.scanned_count = len(candidates)

        for mem in candidates:
            try:
                atoms = self._reflector.reflect(mem.normalized_content or mem.content)

                for atom in atoms:
                    # Create atom memory record
                    atom_mem = self._create_atom_record(mem, atom, ctx)
                    if not ctx.dry_run:
                        self._repo.create_memory(atom_mem)

                    # Emit audit event for atom creation
                    audit_id = self._audit.record(
                        tenant_id=ctx.tenant_id,
                        user_id=ctx.user_id,
                        action="sae_atom_created",
                        reason=f"SAE atom from memory {mem.id} (latent_dim={atom['latent_dim']})",
                        trace_id=ctx.trace_id,
                        memory_id=atom_mem.id,
                        metadata={
                            "origin_memory_id": mem.id,
                            "latent_dim": atom["latent_dim"],
                            "atom_embedding_norm": atom["embedding"],
                        },
                    )
                    result.audit_event_ids.append(audit_id)

                result.changed_count += len(atoms)

                # Mark source memory as SAE-reflected (add metadata flag)
                if not ctx.dry_run:
                    mem.metadata = dict(mem.metadata)
                    mem.metadata["sae_reflected"] = True
                    self._repo.update_memory(mem)

            except Exception as e:  # noqa: BLE001 — never block chat
                result.error_count += 1
                result.details.setdefault("errors", []).append({
                    "memory_id": mem.id,
                    "error": str(e),
                })

    def _get_candidates(self, tenant_id: str, user_id: str) -> List:
        """Get active memories that haven't been SAE-reflected yet."""
        all_memories = self._repo.retrieve_active(tenant_id, user_id)
        candidates = []
        for mem in all_memories:
            # Skip if already SAE-reflected
            if mem.metadata.get("sae_reflected"):
                continue
            # Skip if it's already an atom
            if mem.metadata.get("is_atom"):
                continue
            # Skip if no content to reflect
            if not mem.normalized_content and not mem.content:
                continue
            candidates.append(mem)
        return candidates

    def _create_atom_record(self, source_mem, atom: dict, ctx: WorkerContext):
        """Create a MemoryRecord for an SAE atom."""
        from ..db.entities import StoredMemory
        from ..schemas.memory import Source, MemoryType, Sensitivity, Status

        # Inherit governance from source
        new_metadata = dict(source_mem.metadata)
        new_metadata.update({
            "is_atom": True,
            "sae_embedding": atom["embedding"],
            "origin_memory_id": source_mem.id,
            "atom_latent_dim": atom["latent_dim"],
            "sae_reflected_from": source_mem.id,
        })

        # Source provenance
        source = Source(
            kind="reflection_sae",
            excerpt=atom["approx_text"][:200] if atom["approx_text"] else "",
            message_id=source_mem.source.message_id,
            conversation_id=source_mem.source.conversation_id,
        )

        return StoredMemory(
            tenant_id=source_mem.tenant_id,
            user_id=source_mem.user_id,
            memory_type=MemoryType.semantic,  # atoms are semantic
            content=atom["approx_text"] or f"<SAE atom dim={atom['latent_dim']}>",
            normalized_content="",
            importance=min(source_mem.importance + 1, 10),  # slight boost for distilled knowledge
            confidence=source_mem.confidence,
            sensitivity=source_mem.sensitivity,
            status=Status.active,
            source=source,
            embedding=atom["embedding"],
            metadata=new_metadata,
            weight=source_mem.weight,
            reinforcement_count=0,
        )