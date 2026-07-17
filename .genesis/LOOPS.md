# LOOPS.md — Loop Definitions for MemoryOps-AI Research

**Source:** Agentic-SWE-Kit loop primitives + project-specific loops
**Usage:** Every BUILD/VERIFY cycle follows these loops. Maker executes L1→L4; separate Verifier runs L4.

---

## Core Loop Primitives (Agent-Agnostic)

| Primitive | Purpose | Invocation |
|-----------|---------|------------|
| `G0_PREFLIGHT` | Existence check — repo, deps, env, .genesis/ present | `bash tools/preflight.sh` |
| `L1_BUILD` | Make the change (code, test, doc) | Per milestone KICKOFF |
| `L2_TEST` | Run unit + integration + regression | `pytest` / demo command |
| `L3_INTEGRATE` | Merge to main branch (or feature branch), CI passes | `git push` + CI green |
| `L4_VERIFY` | **Separate context** checks demo, tests, regressions, writes verdict | Verifier runs demo + checks |

**Invariant:** L4_VERIFY **never** runs in the same context as L1-L3. Maker does not grade own work.

---

## Project-Specific Loops

### 1. `memory.write` — Capture → Policy → Store
**Trigger:** User message received at `/api/chat`
**States:** OBSERVED → CLASSIFIED → POLICY_CHECKED → EXECUTED → VERIFIED → AUDITED → COMPLETED
**Gate:** Policy broker decision (SAVE/PENDING/BLOCK/DROP/UPDATE/MERGE)
**Evidence:** `candidate_memories` in response, audit event `memory_created/blocked/...`
**Invariants:** INV-001, INV-003, INV-005, INV-007

### 2. `memory.read` — Retrieve → Rank → Admit → Compose
**Trigger:** User query at `/api/chat` (before write)
**States:** OBSERVED → POLICY_CHECKED → EXECUTED → SAFE_DEGRADED/VERIFIED → AUDITED → COMPLETED
**Gate:** Admission gate (ALLOW vs BLOCK_*)
**Evidence:** `used_memories`, `trace` (MemoryUsageTrace), `retrieval_mode`
**Invariants:** INV-001, INV-002, INV-004, INV-008

### 3. `memory.governance` — Approve/Reject/Archive/Delete
**Trigger:** UI action at `/memories`, `/governance`, `/audit`
**States:** OBSERVED → POLICY_CHECKED → EXECUTED → VERIFIED → AUDITED → COMPLETED
**Gate:** User role (User/Approver/Admin/Auditor) + policy
**Evidence:** Loop run + audit trail per memory
**Invariants:** INV-001, INV-002, INV-007

### 4. `memory.evaluation` — Eval Harness
**Trigger:** CI pipeline, manual `run_evals.py`, PR gate
**States:** OBSERVED → EXECUTED → VERIFIED → COMPLETED
**Gate:** All golden cases pass, adversarial cases flagged
**Evidence:** `eval_passed` / `eval_failed` audit events
**Invariants:** INV-010

### 5. `release.gate` — PR Invariant Evidence Gate
**Trigger:** PR opened/updated
**States:** OBSERVED → POLICY_CHECKED → EXECUTED → VERIFIED → COMPLETED
**Gate:** `scripts/pr_invariant_gate.py` returns 0 (all touched invariants have evidence)
**Evidence:** Gate artifacts attached to PR
**Invariants:** All (evidence-based)

### 6. `learning.continuous` — Reflection Worker
**Trigger:** Scheduler (cron or manual `--job reflection`)
**States:** OBSERVED → CLASSIFIED → POLICY_CHECKED → EXECUTED → VERIFIED → COMPLETED
**Gate:** Proposal-only (never auto-writes active memory)
**Evidence:** `reflection_candidate_detected` audit events
**Invariants:** INV-009, INV-010

### 7. `reflection.sae` — **NEW** SAE Reflection Worker
**Trigger:** Scheduler (`--job reflection_sae`), gated by `MEMORYOPS_REFLECTION_SAE=true`
**States:** OBSERVED → EMBEDDED → ENCODED → PROBED → ATOMIZED → STORED → VERIFIED → COMPLETED
**Gate:** SAE forward pass + top-k extraction + atom storage
**Evidence:** Atoms stored with `is_atom=true`, `sae_embedding`, `origin_memory_id`; loop run recorded
**Invariants:** INV-001, INV-003, INV-007, INV-008 (atoms get trace entries)

---

## Research Milestone Loops (M1–M6)

Each milestone is a **mini-project** with its own L1→L4 cycle.

### M1 Loop: SAE Scaffold
```
L1_BUILD:  Create sae_reflection.py + test_sae_reflection.py + export
L2_TEST:   pytest tests/test_sae_reflection.py -v  (4 tests)
L3_INTEGRATE: git add/commit (feature branch)
L4_VERIFY: [Separate verifier] Runs demo command + full regression
```

### M2 Loop: Runner Integration
```
L1_BUILD:  Add --job reflection_sae to runner.py, feature flag, storage path
L2_TEST:   python -m app.workers.runner --tenant t1 --user u1 --job reflection_sae
           + verify atoms in DB
L3_INTEGRATE: git push, CI passes
L4_VERIFY: [Separate verifier] Runs demo, checks flag toggle, no regressions
```

### M3 Loop: Eval Harness
```
L1_BUILD:  Create evals/run_sae_eval.py with metrics
L2_TEST:   Run baseline + SAE, output comparison table
L3_INTEGRATE: git push
L4_VERIFY: [Separate verifier] Checks table format, metrics computed correctly
```

### M4 Loop: Full Grid Ablation
```
L1_BUILD:  Extend run_sae_eval.py --full-grid, generate figures
L2_TEST:   Run full grid (30-60 min), save JSON + figures
L3_INTEGRATE: git push (figures to paper/figures/)
L4_VERIFY: [Separate verifier] Confirms all conditions run, figures render
```

### M5 Loop: Paper Draft
```
L1_BUILD:  Write draft.tex, embed figures/tables
L2_TEST:   pdflatex compiles cleanly
L3_INTEGRATE: git push (paper/ branch or folder)
L4_VERIFY: [Separate verifier] Compiles, references resolve, within page limit
```

### M6 Loop: Submission Package
```
L1_BUILD:  Create submission.zip with README_REPRODUCE.md
L2_TEST:   Clean clone + run reproduce commands → same results
L3_INTEGRATE: Final commit
L4_VERIFY: [Separate verifier] Reproduces from zip on clean machine
```

---

## Verifier Protocol (L4_VERIFY)

**Mandatory for every loop completion.**

1. **Verifier gets fresh context** — no access to maker's reasoning
2. **Verifier receives:**
   - Milestone ID & demo command (from PLAN.md)
   - Freeze boundary files (from PLAN.md)
   - Definition of Done (from DONE.html)
3. **Verifier executes:**
   ```bash
   # 1. Checkout exact commit
   git checkout <sha>
   # 2. Run demo command
   <demo command from PLAN.md>
   # 3. Run unit tests for touched files
   pytest <test files> -v
   # 4. Run regression suite
   pytest tests/ -q --tb=no -x
   # 5. Check freeze boundary — no unexpected files changed
   git diff --name-only HEAD~1
   ```
4. **Verifier writes verdict to `CURRENT.md`:**
   ```markdown
   ## M<id> Verdict: PASS / FAIL
   - Demo: PASS/FAIL — <output snippet>
   - Unit tests: PASS/FAIL — <count passed>/<total>
   - Regression: PASS/FAIL — <details if fail>
   - Freeze boundary: CLEAN / DIRTY — <files>
   - Notes: ...
   ```
5. **If FAIL:** Maker gets specific reproduction steps. Loop restarts at L1.
   **If PASS:** Milestone frozen. Advance to next milestone.

---

## Loop Execution Commands (Reference)

```bash
# G0 Pre-flight (run once per session)
bash tools/preflight.sh

# M1 L1-L3 (Maker)
cd services/api
# ... edit files per KICKOFF.md ...
pytest tests/test_sae_reflection.py -v
git add -A && git commit -m "M1: SAE Reflection Worker scaffold"

# M1 L4 (Verifier — separate terminal/context)
cd services/api
git checkout <M1-sha>
python -c "from app.workers.sae_reflection import SAEReflector, SAE_CONFIG; import torch; torch.manual_seed(42); r=SAEReflector(SAE_CONFIG); atoms=r.reflect('Test.'); print(len(atoms), SAEReflector.monosemanticity_score(atoms))"
pytest tests/test_sae_reflection.py -v
pytest tests/ -q --tb=no -x
git diff --name-only HEAD~1
# Write verdict to .genesis/CURRENT.md

# Repeat pattern for M2-M6...
```

---

## Loop State Persistence

**File:** `.genesis/CURRENT.md`
**Updated by:** Maker (L1-L3 progress), Verifier (L4 verdict)
**Format:**
```markdown
# Current Loop State

## Active Milestone: M1
## Active Loop: L2_TEST
## Last Maker Action: Wrote test_sae_reflection.py
## Last Verifier Verdict: (none yet)

## History
- M1 L1_BUILD: 2025-01-15 10:30 — Created sae_reflection.py
- M1 L2_TEST: 2025-01-15 10:45 — Tests written, running...
```

**Never edit DONE.html mid-loop.** Scope changes via user only.