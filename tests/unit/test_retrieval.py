"""Unit tests for ADAPT Hybrid Retrieval Engine."""

import pytest

from adapt.embeddings.providers import (
    DeterministicHashEmbeddingProvider,
    NoOpEmbeddingProvider,
    cosine_similarity,
)
from adapt.memory.retrieval.engine import RetrievalEngine
from adapt.models.schema import Memory, MemoryRelationship, MemoryType, RelationshipType
from adapt.storage.sqlite import SQLiteStorage


@pytest.fixture
def storage():
    s = SQLiteStorage(db_path=":memory:")
    s.initialize()
    yield s
    s.close()


def test_cosine_similarity():
    """Test cosine similarity calculation."""
    v1 = [1.0, 0.0, 0.0]
    v2 = [1.0, 0.0, 0.0]
    assert cosine_similarity(v1, v2) == 1.0

    v3 = [0.0, 1.0, 0.0]
    assert cosine_similarity(v1, v3) == 0.0

    # Orthogonal or empty
    assert cosine_similarity([], []) == 0.0


def test_deterministic_hash_embeddings():
    """Test offline feature hash embeddings."""
    embedder = DeterministicHashEmbeddingProvider(dimension=64)
    assert embedder.is_available() is True
    assert embedder.dimension == 64

    vec1 = embedder.embed_query("PostgreSQL database")
    vec2 = embedder.embed_query("PostgreSQL database engine")
    vec3 = embedder.embed_query("Frontend React components")

    assert len(vec1) == 64
    sim_related = cosine_similarity(vec1, vec2)
    sim_unrelated = cosine_similarity(vec1, vec3)

    assert sim_related > sim_unrelated
    assert sim_related > 0.60


def test_lexical_fallback_mode(storage):
    """Test retrieval when embeddings are unavailable (NoOp)."""
    retriever = RetrievalEngine(
        storage=storage,
        embedding_provider=NoOpEmbeddingProvider(),
    )
    storage.create_memory(Memory(
        owner_id="u1",
        content="Deploy web service to Fly.io using Dockerfile.",
        importance=0.8,
    ))

    results = retriever.retrieve(query="Fly.io Dockerfile", owner_id="u1")
    assert len(results) == 1
    assert results[0].semantic_score == 0.0
    assert results[0].lexical_score > 0.0
    assert "Lexical BM25" in results[0].explanation


def test_hybrid_retrieval_mode(storage):
    """Test hybrid retrieval combining hash embeddings with FTS5 BM25."""
    embedder = DeterministicHashEmbeddingProvider(dimension=64)
    retriever = RetrievalEngine(
        storage=storage,
        embedding_provider=embedder,
        hybrid_alpha=0.5,
    )

    m1 = storage.create_memory(Memory(
        owner_id="u1",
        content="Primary cache is Redis running on port 6379.",
        importance=0.9,
    ))
    m2 = storage.create_memory(Memory(
        owner_id="u1",
        content="Background job queue is Celery with RabbitMQ broker.",
        importance=0.5,
    ))

    results = retriever.retrieve(query="Redis cache", owner_id="u1")
    assert len(results) >= 1
    assert results[0].memory.id == m1.id
    assert results[0].semantic_score > 0.0
    assert results[0].lexical_score > 0.0
    assert "Hybrid match" in results[0].explanation


def test_associative_proximity_boost(storage):
    """Test connected memories are pulled in via knowledge graph edges."""
    retriever = RetrievalEngine(storage=storage)

    m_parent = storage.create_memory(Memory(
        owner_id="u1",
        content="Authentication service uses OAuth2 with PKCE.",
    ))
    m_child = storage.create_memory(Memory(
        owner_id="u1",
        content="Session tokens expire in 15 minutes unless refreshed.",
    ))

    storage.create_relationship(
        MemoryRelationship(
            source_memory_id=m_parent.id,
            target_memory_id=m_child.id,
            relationship_type=RelationshipType.DEPENDS_ON,
        ),
        owner_id="u1",
    )

    results = retriever.retrieve(
        query="OAuth2 PKCE",
        owner_id="u1",
        include_related=True,
    )
    assert len(results) == 2
    ids = [sm.memory.id for sm in results]
    assert m_parent.id in ids
    assert m_child.id in ids
    assert "Associative connection" in results[1].explanation
