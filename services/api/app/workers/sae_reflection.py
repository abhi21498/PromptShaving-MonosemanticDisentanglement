"""
Sparse Autoencoder (SAE) Reflection Worker — Prompt Shaving & Monosemantic Disentanglement.

Maps raw memory strings into monosemantic text atoms via a frozen SBERT embedder +
trainable sparse autoencoder + monosemanticity probe.

Each atom is stored as a first-class MemoryRecord with:
  - is_atom=true
  - sae_embedding: the atom's vector (decoder column × latent activation)
  - origin_memory_id: traceability to source memory
  - Full governance metadata (legal_hold, pinned, protected, retention, consent)

This enables atom-level explainability in the Memory Usage Trace and fine-grained
governance (e.g., withdraw consent on a single atom without blocking the whole memory).
"""

from __future__ import annotations

import math
import random
from typing import List, Dict, Any, Optional, Tuple

import torch
import torch.nn as nn
import torch.nn.functional as F

# Optional: sentence-transformers for frozen embedder
try:
    from sentence_transformers import SentenceTransformer
    _HAS_SBERT = True
except ImportError:
    _HAS_SBERT = False
    SentenceTransformer = None  # type: ignore

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
SAE_CONFIG: Dict[str, Any] = {
    "embedding_model": "sentence-transformers/all-MiniLM-L6-v2",  # 384-dim, fast CPU
    "latent_dim": 128,
    "num_atoms": 5,
    "l1_lambda": 1e-3,
    "recon_loss_weight": 1.0,
    "mono_loss_weight": 0.5,
    "device": "cpu",  # or "cuda"
    "probe_hidden": 64,
    "num_memory_types": 9,  # matches MemoryType enum count
    "seed": 42,
}


# ---------------------------------------------------------------------------
# Embedder (frozen SBERT)
# ---------------------------------------------------------------------------
class Embedder(nn.Module):
    """
    Frozen SentenceTransformer wrapper. Returns L2-normalised embeddings.
    """

    def __init__(self, model_name: str, device: str = "cpu") -> None:
        super().__init__()
        if not _HAS_SBERT:
            raise RuntimeError(
                "sentence-transformers not installed. `pip install sentence-transformers`"
            )
        self.device = torch.device(device)
        self.model = SentenceTransformer(model_name, device=self.device)
        # Freeze all parameters
        for p in self.model.parameters():
            p.requires_grad = False
        self.model.eval()

    @torch.no_grad()
    def encode(self, texts: List[str]) -> torch.Tensor:
        """Encode list of strings -> (batch, D) L2-normalised."""
        emb = self.model.encode(
            texts,
            convert_to_tensor=True,
            device=self.device,
            show_progress_bar=False,
            normalize_embeddings=False,  # Don't use inference mode normalization
        )
        # L2-normalise ourselves so the tensor remains in autograd graph
        return F.normalize(emb, p=2, dim=-1)

    @torch.no_grad()
    def decode(self, embeddings: torch.Tensor) -> List[str]:
        """
        Placeholder decoder. In production, replace with a trained decoder
        (e.g., small transformer or template generator). For now returns
        a string representation of the embedding for traceability.
        """
        # Return a compact representation; real decoder would map to tokens
        return [f"<atom_emb_{i}>" for i in range(embeddings.shape[0])]

    def get_embedding_dim(self) -> int:
        return self.model.get_sentence_embedding_dimension()


# ---------------------------------------------------------------------------
# Sparse Autoencoder
# ---------------------------------------------------------------------------
class SparseAutoencoder(nn.Module):
    """
    Single-layer ReLU encoder + linear decoder (no bias).
    Encourages sparsity via L1 penalty on latent activations.
    """

    def __init__(
        self,
        input_dim: int,
        latent_dim: int,
        l1_lambda: float,
    ) -> None:
        super().__init__()
        self.input_dim = input_dim
        self.latent_dim = latent_dim
        self.l1_lambda = l1_lambda

        self.encoder = nn.Sequential(
            nn.Linear(input_dim, latent_dim),
            nn.ReLU(inplace=True),
        )
        # Decoder without bias; columns are "atom directions" in embedding space
        self.decoder = nn.Linear(latent_dim, input_dim, bias=False)

        # Initialize decoder columns to be roughly orthogonal
        nn.init.orthogonal_(self.decoder.weight)

    def forward(self, x: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        """
        Args:
            x: (batch, input_dim) — L2-normalised embeddings
        Returns:
            z: (batch, latent_dim) — sparse codes (ReLU activations)
            x_hat: (batch, input_dim) — reconstruction
            l1_loss: scalar — mean |z| penalty
        """
        z = self.encoder(x)  # (B, latent)
        l1_loss = self.l1_lambda * z.abs().mean()
        x_hat = self.decoder(z)  # (B, input_dim)
        return z, x_hat, l1_loss


# ---------------------------------------------------------------------------
# Monosemanticity Probe
# ---------------------------------------------------------------------------
class MonosemanticityProbe(nn.Module):
    """
    Lightweight MLP predicting memory-type distribution from a latent code.
    Low entropy of predicted distribution → high monosemanticity.
    """

    def __init__(
        self,
        latent_dim: int,
        hidden_dim: int,
        num_types: int,
    ) -> None:
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(latent_dim, hidden_dim),
            nn.ReLU(inplace=True),
            nn.Linear(hidden_dim, num_types),
        )

    def forward(self, z: torch.Tensor) -> torch.Tensor:
        """
        Args:
            z: (batch, latent_dim)
        Returns:
            probs: (batch, num_types) — softmax probabilities
        """
        logits = self.net(z)
        return F.softmax(logits, dim=-1)


# ---------------------------------------------------------------------------
# High-Level API: SAEReflector
# ---------------------------------------------------------------------------
class SAEReflector:
    """
    Orchestrates the reflection step:
      1. Embed raw memory text (frozen SBERT)
      2. Forward through SAE (trainable)
      3. Compute losses: reconstruction + L1 sparsity + monosemanticity (entropy)
      4. Backward + optimiser step (single-example online SGD)
      5. Extract top-k latent dims as "atoms" via masked decoding
    """

    def __init__(
        self,
        config: Optional[Dict[str, Any]] = None,
    ) -> None:
        cfg = {**SAE_CONFIG, **(config or {})}
        self.cfg = cfg
        self.device = torch.device(cfg["device"])

        # Seed for reproducibility
        seed = cfg.get("seed", 42)
        torch.manual_seed(seed)
        random.seed(seed)

        # Components
        self.embedder = Embedder(cfg["embedding_model"], cfg["device"])
        input_dim = self.embedder.get_embedding_dim()

        self.sae = SparseAutoencoder(
            input_dim=input_dim,
            latent_dim=cfg["latent_dim"],
            l1_lambda=cfg["l1_lambda"],
        ).to(self.device)

        self.probe = MonosemanticityProbe(
            latent_dim=cfg["latent_dim"],
            hidden_dim=cfg["probe_hidden"],
            num_types=cfg["num_memory_types"],
        ).to(self.device)

        # Single optimiser for SAE + probe
        self.optimiser = torch.optim.Adam(
            list(self.sae.parameters()) + list(self.probe.parameters()),
            lr=1e-3,
        )

        # Training state
        self.step_count = 0

    # -----------------------------------------------------------------------
    # Core reflection step
    # -----------------------------------------------------------------------
    def reflect(self, raw_memory: str) -> List[Dict[str, Any]]:
        """
        Perform one online training step on a single memory, then extract atoms.

        Args:
            raw_memory: The memory's normalised_content (or source excerpt).

        Returns:
            List of atom dicts, each containing:
              - "embedding": List[float] (input_dim) — the atom's vector
              - "approx_text": str — placeholder text representation
              - "type_logits": List[float] (num_memory_types) — probe probs
              - "latent_dim": int — which latent dimension this atom corresponds to
        """
        self.sae.train()
        self.probe.train()

        # 1. Embed
        with torch.no_grad():
            x = self.embedder.encode([raw_memory])  # (1, D)
        x = x.to(self.device)

        # 2. Forward
        z, x_hat, l1_loss = self.sae(x)  # z: (1, latent)

        # 3. Losses
        # Reconstruction: cosine similarity (since both L2-normalised)
        recon_loss = 1.0 - F.cosine_similarity(x, x_hat, dim=-1).mean()

        # Monosemanticity: entropy of probe prediction
        type_probs = self.probe(z)  # (1, num_types)
        # Add epsilon for numerical stability
        eps = 1e-8
        entropy = -(type_probs * (type_probs + eps).log()).sum(dim=-1).mean()

        # Total loss
        loss = (
            self.cfg["recon_loss_weight"] * recon_loss
            + l1_loss
            + self.cfg["mono_loss_weight"] * entropy
        )

        # 4. Backward + step
        self.optimiser.zero_grad()
        loss.backward()
        self.optimiser.step()

        self.step_count += 1

        # 5. Extract atoms (eval mode, no grad)
        self.sae.eval()
        self.probe.eval()

        with torch.no_grad():
            # Re-encode for stable extraction
            z_eval, _, _ = self.sae(x)
            # Top-k latent dimensions by absolute activation
            k = min(self.cfg["num_atoms"], self.cfg["latent_dim"])
            _, top_idx = torch.topk(z_eval.abs(), k, dim=-1)  # (1, k)

            atoms = []
            for idx in top_idx[0]:
                # Mask to keep only this latent dimension
                z_masked = torch.zeros_like(z_eval)
                z_masked[0, idx] = z_eval[0, idx]

                # Decode just this dimension's contribution
                atom_emb = self.sae.decoder(z_masked)  # (1, D)
                atom_emb = F.normalize(atom_emb, p=2, dim=-1)

                # Probe prediction for this atom
                atom_probs = self.probe(z_masked)  # (1, num_types)

                # Placeholder text (replace with real decoder if available)
                approx_text = f"<atom_dim_{idx.item()}>"

                atoms.append({
                    "embedding": atom_emb.squeeze(0).cpu().tolist(),
                    "approx_text": approx_text,
                    "type_logits": atom_probs.squeeze(0).cpu().tolist(),
                    "latent_dim": int(idx.item()),
                })

        return atoms

    # -----------------------------------------------------------------------
    # Metrics
    # -----------------------------------------------------------------------
    @staticmethod
    def monosemanticity_score(atoms: List[Dict[str, Any]], num_types: int = 9) -> float:
        """
        Compute average monosemanticity across atoms.
        Score = 1 - mean(entropy / max_entropy) ∈ [0, 1].
        Higher = more monosemantic (lower entropy).
        """
        if not atoms:
            return 0.0

        import numpy as np
        max_ent = math.log(num_types)
        entropies = []
        for a in atoms:
            probs = np.array(a["type_logits"], dtype=np.float64)
            probs = probs / (probs.sum() + 1e-12)
            ent = -np.sum(probs * np.log(probs + 1e-12))
            entropies.append(ent)

        avg_ent = float(np.mean(entropies))
        # Normalize by max possible entropy, clip to [0, 1]
        score = 1.0 - (avg_ent / max_ent)
        return max(0.0, min(1.0, score))

    def get_config(self) -> Dict[str, Any]:
        return dict(self.cfg)

    def state_dict(self) -> Dict[str, Any]:
        """Return serialisable state for checkpointing."""
        return {
            "sae": self.sae.state_dict(),
            "probe": self.probe.state_dict(),
            "optimiser": self.optimiser.state_dict(),
            "step_count": self.step_count,
            "config": self.cfg,
        }

    def load_state_dict(self, state: Dict[str, Any]) -> None:
        self.sae.load_state_dict(state["sae"])
        self.probe.load_state_dict(state["probe"])
        self.optimiser.load_state_dict(state["optimiser"])
        self.step_count = state["step_count"]


# ---------------------------------------------------------------------------
# Convenience: create reflector with default config
# ---------------------------------------------------------------------------
def create_reflector(
    config: Optional[Dict[str, Any]] = None,
) -> SAEReflector:
    """Factory function for dependency injection in workers."""
    return SAEReflector(config)


# ---------------------------------------------------------------------------
# Self-test when run directly
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    # Quick smoke test
    print("Initialising SAEReflector...")
    reflector = create_reflector()
    print(f"Config: {reflector.get_config()}")

    test_memory = (
        "User configures Redis cache instances for the production UAT environment "
        "at Easyrewardz."
    )
    print(f"\nReflecting: {test_memory}")
    atoms = reflector.reflect(test_memory)

    print(f"\nExtracted {len(atoms)} atoms:")
    for i, a in enumerate(atoms):
        print(f"  Atom {i}: dim={a['latent_dim']}, "
              f"emb_norm={math.sqrt(sum(v*v for v in a['embedding'])):.4f}, "
              f"type_dist={a['type_logits']}")

    score = SAEReflector.monosemanticity_score(atoms)
    print(f"\nMonosemanticity score: {score:.4f}")

    # Test idempotency (same input → same top-k dims with fixed seed)
    torch.manual_seed(42)
    random.seed(42)
    reflector2 = create_reflector()
    atoms2 = reflector2.reflect(test_memory)
    dims1 = [a["latent_dim"] for a in atoms]
    dims2 = [a["latent_dim"] for a in atoms2]
    print(f"\nIdempotency check (same seed): dims match = {dims1 == dims2}")
    print("Done.")