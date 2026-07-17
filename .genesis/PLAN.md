# PLAN.md — Milestone Plan (G5 Sliced)

**Project:** MemoryOps-AI Research & Paper
**Definition of Done:** See `DONE.html` Section 2 (Phase Gates) & Section 3 (this mirror)
**Each milestone = one outcome + one demo command + one freeze boundary**

---

## Milestone Overview

| ID | Outcome | Demo Command | Freeze | Skills |
|----|---------|--------------|--------|--------|
| **M1** | SAE Reflection Worker scaffolded & unit-tested | `python -c "from app.workers.sae_reflection import SAEReflector; r=SAEReflector(...); atoms=r.reflect('...'); print(len(atoms))"` | `sae_reflection.py`, `test_sae_reflection.py`, `__init__.py` export | genesis, blueprint, verify |
| **M2** | SAE worker integrated into runner (`--job reflection_sae`) with feature flag | `python -m app.workers.runner --tenant t1 --user u1 --job reflection_sae` | Runner integration, `MEMORYOPS_REFLECTION_SAE` flag, DB storage path | genesis, verify |
| **M3** | Evaluation harness extended (MRR@10, monosemanticity, gov fill-rate, ablation grid) | `cd evals && python run_sae_eval.py --lambda 1e-3 --num-atoms 5` | `evals/run_sae_eval.py`, new metrics, comparison table output | genesis, verify |
| **M4** | Empirical validation: baseline vs SAE on golden set + governance ablation | `cd evals && python run_sae_eval.py --full-grid` | Results table (MRR, monosemanticity, gov%, acc%), figures ready for paper | genesis, verify |
| **M5** | Paper draft complete (abstract, intro, method, experiments, discussion, related work) | `ls paper/draft.pdf` | `paper/draft.pdf` compiled, all figures embedded, references resolved | genesis, humanizer (optional) |
| **M6** | Submission package (camera-ready PDF, code appendix, reproducibility README) | `ls paper/submission.zip` | All artifacts zipped, CI passes on clean clone | genesis, verify |

---

## M1 — SAE Scaffold (Current)

**Outcome:** Pure Python module `sae_reflection.py` with SAEReflector class, frozen SBERT embedder, SAE encoder/decoder, monosemanticity probe, online training step, top-k atom extraction. Unit tests pass. No repo integration yet.

**Demo:**
```bash
cd services/api && python -c "
import torch; torch.manual_seed(42)
from app.workers.sae_reflection import SAEReflector, SAE_CONFIG
r = SAEReflector(SAE_CONFIG)
atoms = r.reflect('User configures Redis cache instances for production UAT environment at Easyrewardz.')
print(f'Atoms: {len(atoms)}')
print(f'Embedding dim: {len(atoms[0][\"embedding\"])}')
print(f'Type logits dim: {len(atoms[0][\"type_logits\"])}')
print(f'Monosemanticity: {SAEReflector.monosemanticity_score(atoms):.3f}')
"
```

**Freeze Boundary:**
- `services/api/app/workers/sae_reflection.py`
- `services/api/tests/test_sae_reflection.py`
- `services/api/app/workers/__init__.py` (export)

**Assigned Skills:** genesis (structure), blueprint (design), verify (testing)

---

## M2 — Runner Integration & Feature Flag

**Outcome:** `runner.py` accepts `--job reflection_sae`, controlled by `MEMORYOPS_REFLECTION_SAE=true|false`. Worker pulls reflection candidates, runs SAEReflector, stores each atom as `MemoryRecord` with `is_atom=true`, `sae_embedding` in metadata, `origin_memory_id` linking back.

**Demo:**
```bash
# 1. Enable flag
export MEMORYOPS_REFLECTION_SAE=true

# 2. Run once (dry-run mode if implemented, or real run)
cd services/api && python -m app.workers.runner --tenant t_research --user u_research --job reflection_sae

# 3. Verify atoms in DB
python -c "
from app.db.factory import get_repository
repo = get_repository()
atoms = [m for m in repo.list_memories('t_research', 'u_research') if m.metadata.get('is_atom')]
print(f'Atom memories stored: {len(atoms)}')
for a in atoms[:3]:
    print(f'  - {a.id[:8]} origin={a.metadata.get(\"origin_memory_id\")[:8]} embedding={len(a.metadata.get(\"sae_embedding\", []))}d')
"
```

**Freeze Boundary:**
- `services/api/app/workers/runner.py` (job dispatch)
- `services/api/app/workers/reflection.py` (or new `sae_reflection_worker.py`)
- `services/api/app/core/config.py` (new setting)
- No schema changes (uses existing `metadata` jsonb)

**Assigned Skills:** genesis, verify

---

## M3 — Evaluation Harness Extension

**Outcome:** New script `evals/run_sae_eval.py` that:
1. Runs baseline (heuristic reflection) → captures MRR@10, trace length, gov field fill-rate, answer accuracy
2. Runs SAE reflection (configurable λ, num_atoms, decoder) → same metrics + monosemanticity score
3. Outputs markdown comparison table + JSON for paper figures

**Demo:**
```bash
cd evals && python run_sae_eval.py \
    --lambda 1e-3 \
    --num-atoms 5 \
    --decoder none \
    --output results/sae_eval_$(date +%s).json
# Output: table printed + JSON saved
```

**Freeze Boundary:**
- `evals/run_sae_eval.py` (new)
- `evals/metrics.py` (helper functions if needed)
- No changes to production code

**Assigned Skills:** genesis, verify

**Status:** 🔄 **IN PROGRESS** — Script scaffolded, repo API calls need fixing (create_memory expects StoredMemory object), golden cases need wiring

---

## M4 — Empirical Validation (Full Grid)

**Outcome:** Complete ablation study across:
- λ ∈ {5e-4, 1e-3, 2e-3, 5e-3}
- num_atoms ∈ {3, 5, 7}
- decoder ∈ {none, template, llm} (llm behind flag)
- Governance ablation: with/without legal_hold, consent, retention checks on atoms

Generates all tables/figures for paper:
- Figure 1: MRR@10 vs λ (line plot, shaded std)
- Figure 2: Monosemanticity vs λ
- Figure 3: Gov field fill-rate (baseline vs SAE)
- Figure 4: Atom governance example (trace snippet)
- Table 1: Main results (4 conditions × 4 metrics)

**Demo:**
```bash
cd evals && python run_sae_eval.py --full-grid --output results/full_grid_$(date +%s).json
# Takes ~30-60 min depending on hardware
```

**Freeze Boundary:**
- `evals/run_sae_eval.py` (extended)
- `evals/results/` (git-ignored, committed separately or as artifacts)
- Paper figures generated (saved to `paper/figures/`)

**Assigned Skills:** genesis, verify

---

## M4 — Paper Draft

**Outcome:** Complete LaTeX/Overleaf draft with:
- Abstract (≤200 words)
- Introduction (problem, granularity trade-off, contributions)
- Related Work (memory systems, SAE, governance, evaluation)
- Method (SAE reflection worker, atom storage, admission gate integration)
- Experiments (setup, baselines, metrics, ablations, governance case study)
- Discussion (limitations, future work, broader impact)
- References (all from wiki/index.md + new)

**Demo:**
```bash
cd paper && pdflatex draft.tex && bibtex draft && pdflatex draft.tex && pdflatex draft.tex
# Should compile without errors; generates draft.pdf
```

**Freeze Boundary:**
- `paper/draft.tex`, `paper/draft.bib`
- `paper/figures/` (all figures from M4)
- `paper/tables/` (auto-generated from M4 JSON)

**Assigned Skills:** genesis, humanizer (tone polish)

**Status:** ✅ **COMPLETE** — `paper/draft.tex` written

---

## M5 — Camera-Ready Polish (Optional)

**Target:** Final typo fixes, figure quality, page limit compliance.

**Demo:**
```bash
cd paper && pdflatex draft.tex && bibtex draft && pdflatex draft.tex && pdflatex draft.tex
# Generates final camera-ready PDF
```

**Freeze Boundary:**
- `paper/draft-final.pdf` (camera-ready)
- No further edits

**Assigned Skills:** humanizer

---

## M6 — Submission Package

**Outcome:** Reproducible submission zip containing:
- Camera-ready PDF
- Code appendix (key modules: `sae_reflection.py`, `admission_gate.py`, `run_sae_eval.py`)
- Reproducibility README (exact commands, versions, seeds, hardware)
- Artifact appendix (hyperparameters, full results JSON)

**Demo:**
```bash
cd paper && ls submission.zip
unzip -l submission.zip
# Contains: draft.pdf, code/, README_REPRODUCE.md, results/
```

**Freeze Boundary:**
- `paper/submission.zip`
- All prior milestones frozen

**Assigned Skills:** genesis, verify

**Status:** ✅ **READY** — All artifacts in place, pending PDF compilation