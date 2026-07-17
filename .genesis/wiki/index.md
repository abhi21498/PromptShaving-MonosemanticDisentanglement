# Project Wiki — MemoryOps-AI Research

**Purpose:** Quick navigation to canonical concept pages, ADRs, and external references used in this project. Mirrors the agentic-swe-kit structure for loop-based development.

---

## 📐 Architecture & Design (Phase Gates 1, 6)

| Concept | Local Reference | Agentic-SWE-Kit Phase Gate |
|---------|-----------------|----------------------------|
| System Architecture | `docs/architecture.md` | [Phase 1 — System Architecture](docs/phase-gates/phase-01-system-architecture.md) |
| Memory Architecture | `docs/architecture.md#typed-memory-model` | [Phase 6 — Memory Architecture](docs/phase-gates/phase-06-memory-architecture.md) |
| Loop Engineering | `docs/loop-engineering.md` | [Phase 4 — Workflow Orchestration](docs/phase-gates/phase-04-workflow-orchestration.md) |
| Loop Contracts | `docs/loop-contracts.md` | [Phase 4 — Workflow Orchestration](docs/phase-gates/phase-04-workflow-orchestration.md) |
| Worker Runtime | `docs/worker-runtime.md` | [Phase 12 — Background Lifecycle Workers](docs/phase-gates/phase-12-background-lifecycle-workers.md) |

---

## 🛡 Governance & Security (Phase Gates 11, 15)

| Concept | Local Reference | Agentic-SWE-Kit Phase Gate |
|---------|-----------------|----------------------------|
| Governance Model | `docs/governance.md` | [Phase 15 — Governance](docs/phase-gates/phase-15-governance.md) |
| Security & Invariants | `docs/security.md` | [Phase 11 — Security](docs/phase-gates/phase-11-security.md) |
| Memory Control Plane | `docs/memory-control-plane.md` | [Phase 15 — Governance](docs/phase-gates/phase-15-governance.md) |
| Governance UI | `docs/governance-ui.md` | [Phase 15 — Governance](docs/phase-gates/phase-15-governance.md) |
| Retention, Legal Hold, Consent | `docs/retention-policies.md` | [Phase 13 — Retention/Deletion](docs/phase-gates/phase-13-deletion-compaction-vector-purge.md) |
| Deletion Compaction | `docs/deletion-compaction.md` | [Phase 13 — Deletion Compaction](docs/phase-gates/phase-13-deletion-compaction-vector-purge.md) |
| Vector Purge Verification | `docs/vector-purge-verification.md` | [Phase 13 — Deletion Compaction](docs/phase-gates/phase-13-deletion-compaction-vector-purge.md) |

---

## 🔍 Retrieval & Evaluation (Phase Gates 9, 6)

| Concept | Local Reference | Agentic-SWE-Kit Phase Gate |
|---------|-----------------|----------------------------|
| Hybrid Retrieval | `docs/architecture.md#read-path` | [Phase 6 — Memory Architecture](docs/phase-gates/phase-06-memory-architecture.md) |
| Evaluation Harness | `evals/run_evals.py` | [Phase 9 — Evaluation](docs/phase-gates/phase-09-evaluation.md) |
| Golden Cases | `evals/golden_memory_cases.json` | [Phase 9 — Evaluation](docs/phase-gates/phase-09-evaluation.md) |
| Adversarial Cases | `evals/adversarial_cases.json` | [Phase 9 — Evaluation](docs/phase-gates/phase-09-evaluation.md) |
| Lost in the Middle | `docs/architecture.md#context-composer` | [Phase 6 — Memory Architecture](docs/phase-gates/phase-06-memory-architecture.md) |

---

## 🧠 LLM & Intelligence Layer (Phase Gate 5)

| Concept | Local Reference | Agentic-SWE-Kit Phase Gate |
|---------|-----------------|----------------------------|
| Provider-Neutral LLM | `docs/provider-llm-adapters.md` | [Phase 5 — LLM Reasoning](docs/phase-gates/phase-05-llm-reasoning.md) |
| Structured Extraction | `docs/structured-memory-intelligence.md` | [Phase 5 — LLM Reasoning](docs/phase-gates/phase-05-llm-reasoning.md) |
| Conflict Detection | `services/api/app/llm/intelligence.py` | [Phase 5 — LLM Reasoning](docs/phase-gates/phase-05-llm-reasoning.md) |
| Context Compression | `docs/token-compression.md` | [Phase 5 — LLM Reasoning](docs/phase-gates/phase-05-llm-reasoning.md) |

---

## 🏗 Infrastructure & Deployment (Phase Gate 13)

| Concept | Local Reference | Agentic-SWE-Kit Phase Gate |
|---------|-----------------|----------------------------|
| Railway Deployment | `docs/deployment/railway.md` | [Phase 13 — Infrastructure](docs/phase-gates/phase-13-infrastructure.md) |
| Environment Matrix | `docs/deployment/railway-env.md` | [Phase 13 — Infrastructure](docs/phase-gates/phase-13-infrastructure.md) |
| Smoke Tests | `docs/deployment/railway-smoke-test.md` | [Phase 13 — Infrastructure](docs/phase-gates/phase-13-infrastructure.md) |
| PR Invariant Gate | `scripts/pr_invariant_gate.py` | [Phase 18 — CI/CD for AI](docs/phase-gates/phase-18-ci-cd-for-ai.md) |

---

## 📚 External Research References (for Paper)

### Foundational Memory Systems
- **Generative Agents** (Park et al., 2023) — Cognitive memory streams, retrieval scoring → `services/api/app/services/ranker.py`
- **MemGPT** (Packer et al., 2023) — Virtual memory management, context window as RAM → Typed memory stores
- **Lost in the Middle** (Liu et al., 2023) — Positional bias → ContextComposer layout strategy

### Attribution & Citations
- **AIS Framework** (Rashkin et al., 2023) — Source attribution metrics → `MemoryTraceEntry.admission_reason`
- **ALCE** (Gao et al., 2023) — Citation enforcement → `ChatResponse.trace` structure

### Sparse Autoencoders & Disentanglement
- **SAE for Interpretability** (Bricken et al., 2023) — Monosemantic features from LLM activations
- **Transformer Memory as Differentiable Search Index** (Wu et al., 2022) — Differentiable retrieval
- **MEMIT/ROME/SERAC** — Model editing → Inspiration for memory editing via reflection worker

### Memory Editing & Unlearning
- **Right to be Forgotten in ML** (Ginart et al., 2019) → Deletion compaction worker
- **Machine Unlearning** surveys → Selective forgetting via atom-level governance

### Governance & Accountability
- **Accountability in AI** (Raji et al., 2020) → Audit trail design
- **Differential Privacy** (Dwork & Roth, 2014) → Future: private memory aggregation
- **Federated Learning** (Kairouz et al., 2021) → Future: cross-tenant memory sharing

---

## 🔧 Local Code Pointers (for Loop Workers)

### Write Path
- Gateway: `services/api/app/services/gateway.py` → `handle_chat()`
- Extractor: `services/api/app/services/extractor.py`
- Policy Broker: `services/api/app/services/policy_broker.py`
- Write Service: `services/api/app/services/write_service.py`
- Admission Gate: `services/api/app/services/admission_gate.py` ← **NEW governance checks**

### Read Path
- Retriever: `services/api/app/services/retriever.py`
- Ranker: `services/api/app/services/ranker.py`
- Context Composer: `services/api/app/services/context_composer.py`

### Workers (Background Loops)
- Runner: `services/api/app/workers/runner.py`
- Orchestrator: `services/api/app/workers/orchestrator.py`
- Scheduler: `services/api/app/workers/scheduler.py`
- Locks: `services/api/app/workers/locks.py`
- Retry: `services/api/app/workers/retry.py`
- **NEW:** SAE Reflection: `services/api/app/workers/sae_reflection.py`

### Governance Metadata
- `services/api/app/db/governance.py` — `is_legal_hold`, `is_pinned`, `is_protected`, `consent_status`, `retention_state`
- `services/api/app/db/entities.py` — `StoredMemory`, compaction markers

### Schemas (API Contracts)
- `services/api/app/schemas/memory.py` — `MemoryTraceEntry` ← **NEW governance fields**

---

## 🎯 Invariants (from context-graph.json)

1. **Tenant Isolation** — Every query filtered by `tenant_id` + `user_id` (RLS FORCE)
2. **Deletion Guarantee** — `status='deleted'` rows never retrieved
3. **Provenance** — Every memory has non-null `source`
4. **Graceful Degradation** — Retrieval failure never blocks response
5. **Policy Before Storage** — Policy broker runs before write service
6. **Temporary Chat** — `temporary_chat=true` → no read, no write
7. **Auditability** — Every lifecycle action appends audit event
8. **Explainability** — Trace shows which memories affected answer + why admitted/blocked
9. **Typed Memory** — 9 distinct types with different semantics
10. **Evaluation** — Golden + adversarial sets, not manual inspection

---

## 🔄 Loop Definitions (for BUILD/VERIFY)

| Loop ID | Name | Trigger | Gate | Evidence |
|---------|------|---------|------|----------|
| `memory.write` | Capture → Policy → Store | User message | Policy decision + audit | `candidate_memories` in response |
| `memory.read` | Retrieve → Rank → Admit → Compose | User query | Admission gate + trace | `used_memories` + `trace` |
| `memory.governance` | Approve/Reject/Archive/Delete | UI action | Audit + loop event | `loop_run` + audit trail |
| `memory.evaluation` | Eval run | CI / manual | Gate: all golden pass | `eval_passed` / `eval_failed` |
| `release.gate` | PR opened | PR event | Invariant gate passes | `pr_invariant_gate` artifacts |
| `learning.continuous` | Reflection worker | Schedule | Proposal only (no auto-write) | `reflection_candidate_detected` |

---

## 📝 ADR Index (for Paper Method Section)

| ADR | Title | Relevance to Paper |
|-----|-------|-------------------|
| ADR-001 | Storage Abstraction | Repository pattern enables SAE atom storage |
| ADR-002 | Hybrid Retrieval | Ranker formula (0.35/0.2/0.15/0.1/0.1/0.1) |
| ADR-003 | Policy Broker | Authoritative decisions, LLM advisory only |
| ADR-004 | Observability | Metrics for evaluation |
| ADR-005 | Deletion Guarantee | Compaction preserves governance tombstone |
| ADR-006 | pgvector + RLS | Tenant isolation at DB level |
| ADR-007 | Headroom Compression | Optional, post-governance |
| ADR-008 | Provider LLM Adapters | Structured extraction + heuristic fallback |
| ADR-009 | Memory Control Plane | UI for governance actions |
| ADR-010 | Background Workers | Off-chat-path lifecycle |
| ADR-011 | Deletion Compaction | Content/vector purge, tombstone preserved |
| ADR-012 | Worker Runtime | Leases, retries, dead-letters, health |
| ADR-013 | Retention/Legal Hold/Consent | Governance metadata model |
| ADR-014 | Assistant SDK | Client wrapper |
| ADR-015 | Prometheus Metrics | Observability |
| ADR-016 | Economics Estimation | Token/cost tracking |
| ADR-017 | Context Admission Gate | **Core for paper** — per-memory admission verdicts |
| **ADR-018 (planned)** | **SAE Reflection Worker** | **Core for paper** — monosemantic atoms |

---

## 🚀 Quick Commands

```bash
# Run API (dev)
cd services/api && MEMORYOPS_STORAGE=memory uvicorn app.main:app --reload

# Run tests
cd services/api && pytest -q

# Run eval harness
cd evals && python run_evals.py

# Run worker (reflection)
cd services/api && python -m app.workers.runner --tenant t1 --user u1 --job reflection

# Check RLS policies (needs Postgres)
python scripts/check_rls_policies.py

# PR invariant gate (local)
python scripts/pr_invariant_gate.py --base HEAD~1 --head HEAD
```