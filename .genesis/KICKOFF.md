# KICKOFF.md — First BUILD Loop Primer

**Project:** MemoryOps-AI Research & Paper
**Milestone:** M1 — SAE Reflection Worker Scaffold
**Loop:** L1 BUILD → L2 TEST → L3 INTEGRATE → L4 VERIFY
**Date:** Genesis G6 Prime

---

## Loop Priming Context (fill before starting L1)

### 1. What exactly are we building? (One sentence)
A **Sparse Autoencoder (SAE) based Reflection Worker** that maps raw memory strings into monosemantic text atoms, each stored as a first-class memory record with full governance metadata, enabling atom-level explainability and fine-grained governance.

### 2. What is the demo command for M1?
```bash
cd services/api && python -c "
from app.workers.sae_reflection import SAEReflector, SAE_CONFIG
r = SAEReflector(SAE_CONFIG)
atoms = r.reflect('User configures Redis cache instances for production UAT environment at Easyrewardz.')
print(f'Atoms: {len(atoms)}')
print(f'Keys: {list(atoms[0].keys())}')
print(f'Monosemanticity: {SAEReflector.monosemanticity_score(atoms):.3f}')
"
# Expected: 5 atoms, each with embedding/type_logits/latent_dim/approx_text, score > 0.5
```

### 3. What is the freeze boundary for M1?
- `services/api/app/workers/sae_reflection.py` — **complete** (encoder, decoder, probe, SAEReflector, monosemanticity_score)
- `services/api/tests/test_sae_reflection.py` — **complete** (4 tests passing)
- `services/api/app/workers/__init__.py` — exports SAEReflector
- No other files modified

### 4. What skills are assigned?
- **Maker (this context):** L1 BUILD, L2 TEST
- **Verifier (separate context):** L4 VERIFY — runs demo command, checks test suite, confirms no regressions

### 5. What is the Definition of Done for M1? (from DONE.html)
- Code compiles, imports resolve
- Single-example forward pass works deterministically (seeded)
- 4 unit tests pass: forward, monosemanticity, idempotency, repo integration
- No new test failures in existing suite (`pytest tests/ -q` still passes)

---

## L1 BUILD — Implementation Steps

### Step 1.1: Create `sae_reflection.py` (core module)
**Location:** `services/api/app/workers/sae_reflection.py`

**Required components:**
1. **`SAE_CONFIG`** — dict with all hyperparameters (embedding_model, latent_dim, num_atoms, l1_lambda, recon_loss_weight, mono_loss_weight, device, probe_hidden, num_memory_types)
2. **`Embedder`** (nn.Module) — frozen SentenceTransformer wrapper
   - `encode(texts: List[str]) -> Tensor` — L2-normalized embeddings
   - `decode(embeddings: Tensor) -> List[str]` — placeholder (returns embeddings as list for now)
3. **`SparseAutoencoder`** (nn.Module)
   - `encoder: Linear + ReLU`
   - `decoder: Linear (no bias)`
   - `forward(x) -> (z, x_hat, l1_loss)`
4. **`MonosemanticityProbe`** (nn.Module)
   - 2-layer MLP: latent_dim → probe_hidden → num_memory_types
   - `forward(z) -> probs (softmax)`
5. **`SAEReflector`** (high-level API)
   - `__init__(config)` — builds embedder, SAE, probe, optimizer (Adam)
   - `reflect(raw_memory: str) -> List[dict]` — single training step + top-k atom extraction
     - Embed → SAE forward → losses (recon + L1 + mono) → backward → step
     - Top-k latent dims by abs(z) → masked decode each → atom dicts
   - `monosemanticity_score(atoms) -> float` — static method, 1 - mean(entropy)

**Atom dict schema:**
```python
{
    "embedding": List[float],      # 384-dim (frozen SBERT space)
    "approx_text": str,            # placeholder "<atom>" for now
    "type_logits": List[float],    # num_memory_types probs from probe
    "latent_dim": int,             # which latent dimension this atom came from
}
```

### Step 1.2: Write `test_sae_reflection.py`
**Location:** `services/api/tests/test_sae_reflection.py`

**Test cases:**
```python
def test_sae_forward_pass():
    """Single memory -> atoms list with correct structure."""
    r = SAEReflector(SAE_CONFIG)
    atoms = r.reflect("Test memory content.")
    assert len(atoms) == SAE_CONFIG["num_atoms"]
    for a in atoms:
        assert set(a.keys()) == {"embedding", "approx_text", "type_logits", "latent_dim"}
        assert len(a["embedding"]) == 384  # MiniLM-L6-v2 dim
        assert len(a["type_logits"]) == SAE_CONFIG["num_memory_types"]

def test_monosemanticity_score():
    """Score in [0,1], higher = more monosemantic."""
    r = SAEReflector(SAE_CONFIG)
    atoms = r.reflect("Test.")
    score = SAEReflector.monosemanticity_score(atoms)
    assert 0.0 <= score <= 1.0

def test_idempotency():
    """Same input + same seed -> same top-k latent dims."""
    r1 = SAEReflector(SAE_CONFIG)
    r2 = SAEReflector(SAE_CONFIG)
    atoms1 = r1.reflect("Deterministic input.")
    atoms2 = r2.reflect("Deterministic input.")
    dims1 = sorted(a["latent_dim"] for a in atoms1)
    dims2 = sorted(a["latent_dim"] for a in atoms2)
    assert dims1 == dims2

def test_integration_with_repo(memory_repo):
    """Atoms stored as MemoryRecord with is_atom=true."""
    from app.workers.sae_reflection import SAEReflector
    from app.schemas.memory import Source, MemoryType, Sensitivity
    from app.db.entities import StoredMemory
    import uuid

    r = SAEReflector(SAE_CONFIG)
    atoms = r.reflect("User prefers Python for data science.")

    # Simulate storing atoms (worker would do this)
    for a in atoms:
        mem = StoredMemory(
            tenant_id="t_test",
            user_id="u_test",
            memory_type=MemoryType.semantic,
            content="<ATOM>",
            normalized_content="",
            importance=5,
            confidence=0.8,
            sensitivity=Sensitivity.low,
            source=Source(kind="reflection"),
            embedding=a["embedding"],
            metadata={"is_atom": True, "sae_embedding": a["embedding"], "origin_memory_id": str(uuid.uuid4())},
        )
        saved = memory_repo.create_memory(mem)
        assert saved.metadata["is_atom"] is True
        assert "sae_embedding" in saved.metadata
```

### Step 1.3: Export from `__init__.py`
**Location:** `services/api/app/workers/__init__.py`

```python
from .sae_reflection import SAEReflector, SAE_CONFIG
__all__ = [..., "SAEReflector", "SAE_CONFIG"]
```

---

## L2 TEST — Local Verification

Run in `services/api/`:
```bash
# 1. Import check
python -c "from app.workers.sae_reflection import SAEReflector, SAE_CONFIG; print('OK')"

# 2. Unit tests
pytest tests/test_sae_reflection.py -v

# 3. Full test suite regression
pytest tests/ -q --tb=no -x
# Must show: all existing tests still pass (no new failures)
```

---

## L3 INTEGRATE — Not for M1
M1 is a pure scaffold milestone. Integration (runner, feature flag, DB storage) happens in **M2**.

---

## L4 VERIFY — Verifier Checklist (separate context!)

| Check | Pass Criteria |
|-------|---------------|
| Demo command runs | Exit 0, prints expected output (5 atoms, score > 0.5) |
| Unit tests pass | 4/4 tests in `test_sae_reflection.py` PASS |
| No regressions | `pytest tests/ -q` shows 0 new failures |
| Imports clean | No circular imports, no missing deps |
| Code style | Black/ruff pass (if configured) |

**Verifier writes verdict to CURRENT.md:**
```markdown
## M1 Verdict: PASS / FAIL
- Demo: PASS/FAIL — <details>
- Unit tests: PASS/FAIL — <details>
- Regression: PASS/FAIL — <details>
- Notes: ...
```
**If FAIL:** Maker gets specific reproduction steps. Scope does not expand.

---

## Post-M1: Advance to M2

On verified PASS:
1. Update `CURRENT.md` → M2 active
2. Prime M2 KICKOFF (runner integration, feature flag)
3. Start L1 BUILD on M2