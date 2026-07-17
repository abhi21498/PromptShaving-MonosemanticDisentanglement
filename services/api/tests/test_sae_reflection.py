"""Tests for SAE Reflection Worker (Prompt Shaving & Monosemantic Disentanglement)."""

from __future__ import annotations

import math
import random

import pytest
import torch

# Import the SAE components
from app.workers.sae_reflection import (
    SAEReflector,
    SAE_CONFIG,
    create_reflector,
    Embedder,
    SparseAutoencoder,
    MonosemanticityProbe,
)


@pytest.fixture
def reflector():
    """Create a seeded reflector for deterministic tests."""
    torch.manual_seed(42)
    random.seed(42)
    return create_reflector()


# ---------------------------------------------------------------------------
# TestSAEComponents
# ---------------------------------------------------------------------------
class TestSAEComponents:
    """Unit tests for individual SAE components."""

    def test_sae_forward_shape(self):
        """SAE forward pass returns correct shapes."""
        sae = SparseAutoencoder(input_dim=384, latent_dim=128, l1_lambda=1e-3)
        x = torch.randn(2, 384)
        x = torch.nn.functional.normalize(x, p=2, dim=-1)

        z, x_hat, l1_loss = sae(x)

        assert z.shape == (2, 128), f"Expected (2, 128), got {z.shape}"
        assert x_hat.shape == (2, 384), f"Expected (2, 384), got {x_hat.shape}"
        assert l1_loss.dim() == 0, "l1_loss should be scalar"
        assert l1_loss.item() >= 0, "l1_loss should be non-negative"

    def test_probe_forward_shape(self):
        """Probe returns probability distribution over memory types."""
        probe = MonosemanticityProbe(latent_dim=128, hidden_dim=64, num_types=9)
        z = torch.randn(3, 128)

        probs = probe(z)

        assert probs.shape == (3, 9), f"Expected (3, 9), got {probs.shape}"
        # Probabilities should sum to 1 per row
        sums = probs.sum(dim=-1)
        assert torch.allclose(sums, torch.ones(3), atol=1e-5)

    def test_embedder_encode_shape(self):
        """Embedder returns L2-normalised vectors of correct dimension."""
        if not pytest.importorskip("sentence_transformers", reason="sentence-transformers not installed"):
            return

        embedder = Embedder("sentence-transformers/all-MiniLM-L6-v2", device="cpu")
        texts = ["Test memory one.", "Another test memory."]
        emb = embedder.encode(texts)

        assert emb.shape == (2, 384), f"Expected (2, 384), got {emb.shape}"
        # Check L2 norm ≈ 1
        norms = emb.norm(p=2, dim=-1)
        assert torch.allclose(norms, torch.ones(2), atol=1e-4)


class TestSAEReflector:
    """Integration tests for SAEReflector."""

    def test_reflect_returns_atoms(self, reflector):
        """reflect() returns list of atom dicts with correct structure."""
        atoms = reflector.reflect("User prefers Python for data science.")

        assert len(atoms) == SAE_CONFIG["num_atoms"]
        for a in atoms:
            assert set(a.keys()) == {"embedding", "approx_text", "type_logits", "latent_dim"}
            assert isinstance(a["embedding"], list)
            assert len(a["embedding"]) == 384  # MiniLM-L6-v2 dimension
            assert isinstance(a["approx_text"], str)
            assert isinstance(a["type_logits"], list)
            assert len(a["type_logits"]) == SAE_CONFIG["num_memory_types"]
            assert isinstance(a["latent_dim"], int)
            assert 0 <= a["latent_dim"] < SAE_CONFIG["latent_dim"]

    def test_embedding_norm_preserved(self, reflector):
        """Atom embeddings should be L2-normalised (approximately)."""
        atoms = reflector.reflect("Test memory content.")

        for a in atoms:
            norm = math.sqrt(sum(v * v for v in a["embedding"]))
            assert abs(norm - 1.0) < 1e-3, f"Embedding not normalised: {norm}"

    def test_type_logits_valid_probs(self, reflector):
        """type_logits should be valid probability distribution."""
        atoms = reflector.reflect("Test.")

        for a in atoms:
            probs = a["type_logits"]
            total = sum(probs)
            assert abs(total - 1.0) < 1e-4, f"Probs don't sum to 1: {total}"

    def test_monosemanticity_score_range(self, reflector):
        """Monosemanticity score should be in [0, 1]."""
        atoms = reflector.reflect("Test memory for scoring.")
        score = SAEReflector.monosemanticity_score(atoms)

        assert 0.0 <= score <= 1.0, f"Score out of range: {score}"

    def test_monosemanticity_score_perfect(self):
        """Score should be 1.0 for perfectly monosemantic (one-hot) atoms."""
        # Create atoms with one-hot type_logits
        atoms = [
            {"type_logits": [1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]},
            {"type_logits": [0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]},
        ]
        score = SAEReflector.monosemanticity_score(atoms)
        assert abs(score - 1.0) < 1e-6, f"Expected 1.0, got {score}"

    def test_monosemanticity_score_uniform(self):
        """Score should be ~0.0 for uniform (polysemantic) atoms."""
        n_types = 9
        uniform = [1.0 / n_types] * n_types
        atoms = [{"type_logits": uniform}, {"type_logits": uniform}]
        score = SAEReflector.monosemanticity_score(atoms)
        assert score < 0.1, f"Expected near 0, got {score}"

    def test_idempotency_same_seed(self):
        """Same seed + same input → same top-k latent dims."""
        torch.manual_seed(123)
        random.seed(123)
        r1 = create_reflector(SAE_CONFIG)
        atoms1 = r1.reflect("Deterministic input for idempotency test.")

        torch.manual_seed(123)
        random.seed(123)
        r2 = create_reflector(SAE_CONFIG)
        atoms2 = r2.reflect("Deterministic input for idempotency test.")

        dims1 = sorted(a["latent_dim"] for a in atoms1)
        dims2 = sorted(a["latent_dim"] for a in atoms2)

        assert dims1 == dims2, f"Latent dims differ: {dims1} vs {dims2}"

    def test_state_dict_roundtrip(self, reflector):
        """State dict can be saved and loaded."""
        # Do a few steps
        for _ in range(3):
            reflector.reflect("Memory for state test.")

        state = reflector.state_dict()

        # Create new reflector and load
        torch.manual_seed(42)
        random.seed(42)
        new_reflector = create_reflector(SAE_CONFIG)
        new_reflector.load_state_dict(state)

        # Should produce same atoms for same input
        atoms1 = reflector.reflect("State test memory.")
        atoms2 = new_reflector.reflect("State test memory.")

        dims1 = sorted(a["latent_dim"] for a in atoms1)
        dims2 = sorted(a["latent_dim"] for a in atoms2)
        assert dims1 == dims2

    def test_get_config(self, reflector):
        """get_config returns a copy of the config."""
        cfg = reflector.get_config()
        assert isinstance(cfg, dict)
        assert cfg["latent_dim"] == SAE_CONFIG["latent_dim"]
        assert cfg["num_atoms"] == SAE_CONFIG["num_atoms"]

    def test_factory_function(self):
        """create_reflector factory works."""
        r = create_reflector(SAE_CONFIG)
        assert isinstance(r, SAEReflector)


class TestSAEIntegration:
    """Tests that verify integration with the broader system (mocked repo)."""

    def test_atom_structure_for_storage(self, reflector):
        """Atoms have fields needed for MemoryRecord storage."""
        atoms = reflector.reflect("Integration test memory.")

        for a in atoms:
            # These are the fields worker would store in metadata
            assert "embedding" in a
            assert "latent_dim" in a
            assert "type_logits" in a

            # Embedding is serialisable
            import json
            json.dumps(a["embedding"])

    def test_multiple_reflections_increase_step_count(self, reflector):
        """Step count increments on each reflect call."""
        initial = reflector.step_count
        reflector.reflect("First.")
        reflector.reflect("Second.")
        reflector.reflect("Third.")
        assert reflector.step_count == initial + 3


# ---------------------------------------------------------------------------
# Pytest configuration
# ---------------------------------------------------------------------------
def pytest_configure(config):
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "gpu: marks tests as requiring GPU"
    )