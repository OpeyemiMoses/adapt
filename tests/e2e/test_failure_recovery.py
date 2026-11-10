"""Failure recovery and resilience tests for ADAPT."""

import pytest

from adapt.core.engine import AdaptEngine
from adapt.embeddings.base import EmbeddingProvider
from adapt.storage.sqlite import SQLiteStorage


class FailingEmbeddingProvider(EmbeddingProvider):
    """Simulates an embedding provider that crashes or times out."""

    @property
    def name(self) -> str:
        return "failing_mock"

    @property
    def dimension(self) -> int:
        return 128

    def is_available(self) -> bool:
        return True

    def embed_query(self, text: str):
        raise ConnectionError("Simulated remote embedding API timeout (504 Gateway Timeout)")

    def embed_documents(self, texts):
        raise ConnectionError("Simulated remote embedding API timeout (504 Gateway Timeout)")


def test_graceful_degradation_on_embedding_failure(tmp_path):
    """Scenario 4: If embedding service fails, system seamlessly falls back to FTS5 BM25."""
    storage = SQLiteStorage(db_path=str(tmp_path / "resilience.db"))
    failing_embedder = FailingEmbeddingProvider()

    # Engine initialized with failing embedder
    engine = AdaptEngine(
        storage=storage,
        embedding_provider=failing_embedder,
    )

    # Ingestion works (pure local)
    mem = engine.remember(
        content="Kubernetes cluster is configured with Cilium CNI plugin.",
        owner_id="ops_user",
    )
    assert mem.id.startswith("mem_")

    # Recall falls back gracefully to lexical search instead of raising
    # In RetrievalEngine, if embedding fails, it catches or gracefully handles it
    try:
        results = engine.recall(query="Cilium CNI", owner_id="ops_user")
        # Should still return result via lexical fallback
        assert len(results) >= 1
        assert "Cilium" in results[0].memory.content
    except Exception as e:
        # If not yet wrapped with try/except in RetrievalEngine, test will alert us to wrap it!
        pytest.fail(f"Recall should have fallen back to lexical search, but crashed with: {e}")

    engine.close()
