# Reproducibility Guide — Prompt Shaving & Monosemantic Disentanglement

This document provides exact commands, versions, seeds, and hardware specs to reproduce all results from the paper.

---

## 1. Environment Setup

### 1.1 Python Dependencies
```bash
# Python 3.11+ (tested on 3.11, 3.12)
pip install torch==2.1.0 --index-url https://download.pytorch.org/whl/cpu
pip install sentence-transformers==2.2.2
pip install fastapi==0.110.0 pydantic==2.7.0 pydantic-settings==2.3.0
pip install pytest==8.0.0
pip install numpy==1.26.0 scipy==1.11.0
```

### 1.2 System Requirements
- **OS:** Linux / macOS / Windows (WSL2)
- **CPU:** Any x86_64 (tested on Intel i7-12700)
- **RAM:** ≥ 8 GB (SBERT model ~90 MB)
- **GPU:** Optional (CPU-only works, tested on CPU)
- **Disk:** ~2 GB for dependencies + results

---

## 2. Repository Structure

```
memoryops-ai/
├── services/api/app/workers/
│   ├── sae_reflection.py          # SAE encoder/decoder/probe + SAEReflector
│   └── sae_reflection_worker.py   # Background worker (LifecycleWorker)
├── services/api/app/services/
│   └── admission_gate.py          # Context Admission Gate (ALLOW/BLOCK_*)
├── evals/
│   └── run_sae_eval.py            # Evaluation harness (MRR@10, ablation grid)
├── paper/
│   ├── draft.tex                  # LaTeX source
│   ├── draft.bib                  # Bibliography
│   ├── compile.sh                 # Compile script
│   └── code/                      # Code appendix (copied from above)
└── .genesis/                      # Project spine (CURRENT.md, PLAN.md, etc.)
```

---

## 3. Random Seeds (Critical for Reproducibility)

All experiments use:
```python
import torch, random
torch.manual_seed(42)
random.seed(42)
```

The SAE reflector also seeds internally:
```python
torch.manual_seed(config.get("seed", 42))
random.seed(config.get("seed", 42))
```

---

## 4. Running Experiments

### 4.1 Baseline (No SAE)
```bash
cd memoryops-ai
PYTHONPATH=services/api python evals/run_sae_eval.py \
  --tenant t_eval --user u_eval \
  --output evals/results/baseline_$(date +%s).json
```

### 4.2 SAE Condition (λ=1e-3, 5 atoms)
```bash
cd memoryops-ai
PYTHONPATH=services/api python evals/run_sae_eval.py \
  --tenant t_eval --user u_eval \
  --lambda 1e-3 --num-atoms 5 \
  --output evals/results/sae_$(date +%s).json
```

### 4.3 Full Ablation Grid (16 configurations)
```bash
cd memoryops-ai
PYTHONPATH=services/api python evals/run_sae_eval.py \
  --tenant t_eval --user u_eval \
  --full-grid \
  --output evals/results/ablation_$(date +%s).json
```

**Expected runtime:** ~3-5 minutes on CPU (16 configs × 4 queries × SBERT loading)

---

## 5. Expected Outputs

### 5.1 Baseline vs SAE Comparison
```json
{
  "baseline": {"MRR@10": 0.75, "AvgTraceLen": 4.0, "GovFieldFill%": 50.0, "AnswerAcc%": 25.0},
  "sae": {"MRR@10": 0.75, "AvgTraceLen": 5.0, "GovFieldFill%": 50.0, "AnswerAcc%": 25.0}
}
```

### 5.2 Ablation Grid (16 configs)
Each entry contains:
```json
{
  "lambda": 0.001,
  "num_atoms": 5,
  "MRR@10": 0.75,
  "AvgTraceLen": 5.0,
  "GovFieldFill%": 50.0,
  "AnswerAcc%": 25.0
}
```

---

## 6. Key Hyperparameters (from paper Appendix B)

| Parameter | Value |
|-----------|-------|
| Embedder | `sentence-transformers/all-MiniLM-L6-v2` (384-dim, frozen) |
| Latent dim | 128 |
| Target atoms (k) | 5 |
| Sparsity (λ₁) | 1e-3 |
| Recon weight | 1.0 |
| Mono weight (α) | 0.5 |
| Probe hidden | 64 |
| Memory types | 9 |
| Optimizer | Adam (lr=1e-3) |
| Update | Single-example online per memory |

---

## 6. Running Unit Tests

```bash
cd memoryops-ai/services/api
python -m pytest tests/test_sae_reflection.py -v
# 15 tests expected to pass

python -m pytest tests/test_memory_usage_trace.py -v
# 3 tests expected to pass

python -m pytest tests/ -q
# Full suite (should pass with 0 new failures)
```

---

## 7. Hardware & Software Versions (Tested)

| Component | Version |
|-----------|---------|
| Python | 3.11.9 / 3.12.3 |
| PyTorch | 2.1.0 (CPU) |
| sentence-transformers | 2.2.2 |
| transformers | 4.36.0 |
| numpy | 1.26.0 |
| scipy | 1.11.0 |
| fastapi | 0.110.0 |
| pydantic | 2.7.0 |
| pytest | 8.0.0 |

---

## 7. Expected Metrics (from Paper)

| Metric | Baseline | SAE (λ=1e-3, k=5) | Delta |
|--------|----------|-------------------|-------|
| MRR@10 | 0.750 | 0.750 | 0.000 |
| AvgTraceLen | 4.00 | 5.00 | +1.0 |
| GovFieldFill% | 50.0% | 50.0% | 0.0% |
| AnswerAcc% | 25.0% | 25.0% | 0.0% |
| MonoScore | 0.31 | 0.78 | +0.47 |

---

## 8. Troubleshooting

| Issue | Solution |
|-------|----------|
| `ModuleNotFoundError: app` | Run from repo root with `PYTHONPATH=services/api` |
| `sentence-transformers` download fails | Set `HF_TOKEN` or use cached model |
| `RuntimeError: CUDA out of memory` | Force CPU: `os.environ["CUDA_VISIBLE_DEVICES"] = ""` |
| Slow SBERT loading | Model caches after first run (~90 MB) |
| Tests fail with `AttributeError: lambda` | Use Python 3.11+ (3.10 has different argparse behavior) |

---

## 8. Contact

For questions about reproduction:
- **Author:** Abhijeet Singh
- **Email:** abhijeetpratapsingh462@gmail.com
- **Repo:** https://github.com/abhijeet/memoryops-ai (branch `sae-reflection`)