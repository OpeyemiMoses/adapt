"""Unit tests for AdaptEngine core API."""

import pytest

from adapt.core.engine import AdaptEngine
from adapt.core.errors import ValidationError
from adapt.models.schema import MemoryType, RelationshipType
from adapt.storage.sqlite import SQLiteStorage


@pytest.fixture
def engine():
    """AdaptEngine backed by an in-memory SQLite storage."""
    storage = SQLiteStorage(db_path=":memory:")
    eng = AdaptEngine(storage=storage)
    yield eng
    eng.close()


def test_engine_remember_and_get(engine):
    """Test standard remember and retrieval."""
    mem = engine.remember(
        content="User prefers Python over TypeScript for backend development.",
        memory_type=MemoryType.SEMANTIC,
        owner_id="user_42",
        agent_id="hermes_agent",
        importance=0.85,
        source_type="conversation",
        source_identifier="session_101:turn_2",
        metadata={"category": "language_preference"},
    )
    assert mem.id.startswith("mem_")
    assert mem.source_id is not None

    retrieved = engine.get_memory(mem.id, owner_id="user_42")
    assert retrieved is not None
    assert retrieved.content == "User prefers Python over TypeScript for backend development."
    assert retrieved.importance == 0.85
    assert retrieved.source_type == "conversation"


def test_engine_recall_ranking_and_explanation(engine):
    """Test recall returns scored memories with explanation."""
    engine.remember(
        content="PostgreSQL configuration tuning: set shared_buffers to 25% of RAM.",
        owner_id="user_42",
        importance=0.9,
    )
    engine.remember(
        content="Redis cache configuration: maxmemory 2gb with allkeys-lru eviction.",
        owner_id="user_42",
        importance=0.5,
    )

    results = engine.recall(query="PostgreSQL RAM buffers", owner_id="user_42", limit=5)
    assert len(results) >= 1
    top = results[0]
    assert "PostgreSQL" in top.memory.content
    assert top.score > 0
    assert "Lexical BM25" in top.explanation


def test_engine_recall_with_associative_traversal(engine):
    """Test that include_related traverses connected knowledge graph memories."""
    m1 = engine.remember(
        content="Primary payment gateway is Stripe API v2024.",
        owner_id="user_42",
    )
    m2 = engine.remember(
        content="Webhook endpoint for Stripe is /api/v1/payments/webhook.",
        owner_id="user_42",
    )

    # Relate m1 -> m2
    engine.relate(
        source_memory_id=m1.id,
        target_memory_id=m2.id,
        relationship_type=RelationshipType.DEPENDS_ON,
        owner_id="user_42",
    )

    # Query for "Stripe primary gateway" with include_related=True
    recalled = engine.recall(
        query="Stripe primary gateway",
        owner_id="user_42",
        include_related=True,
        limit=5,
    )
    ids = [sm.memory.id for sm in recalled]
    assert m1.id in ids
    assert m2.id in ids  # Associatively fetched!


def test_engine_update_and_versioning(engine):
    """Test update with historical audit log."""
    mem = engine.remember(
        content="API rate limit is 60 requests per minute.",
        owner_id="user_42",
    )

    updated = engine.update_memory(
        memory_id=mem.id,
        owner_id="user_42",
        new_content="API rate limit increased to 120 requests per minute.",
        change_reason="Upgraded tier",
    )
    assert updated.content == "API rate limit increased to 120 requests per minute."

    # Verify history through storage
    versions = engine.storage.get_versions(mem.id)
    assert len(versions) == 1
    assert versions[0].previous_content == "API rate limit is 60 requests per minute."
    assert versions[0].change_reason == "Upgraded tier"


def test_engine_validation_checks(engine):
    """Test input validations."""
    with pytest.raises(ValidationError, match="empty"):
        engine.remember(content="", owner_id="user_42")

    with pytest.raises(ValueError, match="Invalid owner_id"):
        engine.remember(content="test", owner_id="")

    with pytest.raises(ValidationError, match="Invalid memory_type"):
        engine.remember(content="test", memory_type="fantasy_type")


def test_engine_tenant_isolation(engine):
    """Verify tenant isolation at engine layer."""
    mem_a = engine.remember(content="User A's proprietary data", owner_id="tenant_a")

    # Tenant B cannot access or recall Tenant A's memory
    assert engine.get_memory(mem_a.id, owner_id="tenant_b") is None
    assert len(engine.recall(query="proprietary", owner_id="tenant_b")) == 0
    assert engine.forget(mem_a.id, owner_id="tenant_b") is False


def test_engine_stats(engine):
    """Test statistics aggregation."""
    engine.remember(content="Fact 1", memory_type="semantic", owner_id="tenant_x")
    engine.remember(content="Event 1", memory_type="episodic", owner_id="tenant_x")
    stats = engine.get_stats(owner_id="tenant_x")
    assert stats["total_memories"] == 2
    assert stats["active_memories"] == 2
    assert stats["by_type"]["semantic"] == 1
    assert stats["by_type"]["episodic"] == 1

