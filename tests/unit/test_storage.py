"""Unit tests for ADAPT SQLite and FTS5 Storage Engine."""

from datetime import datetime, timezone, timedelta
import pytest

from adapt.models.schema import (
    Memory,
    MemoryRelationship,
    MemorySource,
    MemoryStatus,
    MemoryType,
    RelationshipType,
    utc_now_iso,
)
from adapt.storage.sqlite import SQLiteStorage


def test_storage_initialization(storage):
    """Test tables and schema creation."""
    conn = storage._get_connection()
    tables = [
        r[0]
        for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table';"
        ).fetchall()
    ]
    assert "memories" in tables
    assert "memories_fts" in tables
    assert "memory_relationships" in tables
    assert "memory_sources" in tables
    assert "memory_versions" in tables
    assert "agents" in tables
    assert "memory_jobs" in tables


def test_memory_crud_lifecycle(storage):
    """Test full memory create, read, update, and deletion lifecycle."""
    mem = Memory(
        owner_id="alice",
        agent_id="hermes_1",
        project_id="cortex_app",
        memory_type=MemoryType.SEMANTIC,
        content="Alice prefers dark mode in her code editor.",
        importance=0.8,
        confidence=0.95,
        metadata={"category": "ui_preference"},
    )
    saved = storage.create_memory(mem)
    assert saved.id.startswith("mem_")

    # Read
    retrieved = storage.get_memory(saved.id, owner_id="alice")
    assert retrieved is not None
    assert retrieved.content == "Alice prefers dark mode in her code editor."
    assert retrieved.importance == 0.8
    assert retrieved.metadata["category"] == "ui_preference"
    assert retrieved.last_accessed_at is not None

    # Update with versioning
    updated = storage.update_memory(
        memory_id=saved.id,
        owner_id="alice",
        new_content="Alice prefers Solarized Dark theme in VS Code.",
        importance=0.9,
        change_reason="User specified exact theme",
    )
    assert updated is not None
    assert updated.content == "Alice prefers Solarized Dark theme in VS Code."
    assert updated.importance == 0.9

    # Verify version audit trail
    versions = storage.get_versions(saved.id)
    assert len(versions) == 1
    assert versions[0].previous_content == "Alice prefers dark mode in her code editor."
    assert versions[0].new_content == "Alice prefers Solarized Dark theme in VS Code."
    assert versions[0].change_reason == "User specified exact theme"

    # Soft delete
    deleted = storage.delete_memory(saved.id, owner_id="alice", permanent=False)
    assert deleted is True

    # Soft deleted memory cannot be retrieved normally
    assert storage.get_memory(saved.id, owner_id="alice") is None

    # Permanent delete
    storage.delete_memory(saved.id, owner_id="alice", permanent=True)
    assert storage.get_memory(saved.id, owner_id="alice") is None


def test_multi_tenant_isolation(storage):
    """Verify strict tenant isolation between different users."""
    mem_alice = Memory(
        owner_id="alice",
        agent_id="hermes",
        memory_type=MemoryType.SEMANTIC,
        content="Alice's confidential API key pattern is AKIA...",
    )
    storage.create_memory(mem_alice)

    # Bob attempts to get Alice's memory
    assert storage.get_memory(mem_alice.id, owner_id="bob") is None

    # Bob attempts to update Alice's memory
    updated = storage.update_memory(
        memory_id=mem_alice.id,
        owner_id="bob",
        new_content="Overwritten by Bob",
    )
    assert updated is None

    # Bob attempts to delete Alice's memory
    assert storage.delete_memory(mem_alice.id, owner_id="bob") is False

    # Bob lists memories -> Alice's memory is absent
    bob_mems = storage.list_memories(owner_id="bob")
    assert len(bob_mems) == 0

    # Bob searches -> no results
    bob_results = storage.search_lexical(query="confidential", owner_id="bob")
    assert len(bob_results) == 0

    # Alice can retrieve her own memory
    assert storage.get_memory(mem_alice.id, owner_id="alice") is not None


def test_fts5_lexical_search(storage):
    """Test full-text search capabilities using SQLite FTS5."""
    m1 = Memory(
        owner_id="alice",
        memory_type=MemoryType.SEMANTIC,
        content="PostgreSQL 16 is chosen as the primary database for transaction ACID safety.",
    )
    m2 = Memory(
        owner_id="alice",
        memory_type=MemoryType.PROCEDURAL,
        content="To run migrations execute: python -m alembic upgrade head.",
    )
    m3 = Memory(
        owner_id="alice",
        memory_type=MemoryType.EPISODIC,
        content="Meeting with team decided against MongoDB due to consistency needs.",
    )
    storage.create_memory(m1)
    storage.create_memory(m2)
    storage.create_memory(m3)

    # Search for PostgreSQL
    res = storage.search_lexical(query="PostgreSQL", owner_id="alice")
    assert len(res) >= 1
    found_mem, score = res[0]
    assert found_mem.id == m1.id
    assert score > 0.0

    # Search for migration procedural instruction
    res_mig = storage.search_lexical(query="alembic upgrade", owner_id="alice")
    assert len(res_mig) >= 1
    assert res_mig[0][0].id == m2.id

    # Search with special characters (safe sanitization)
    res_punct = storage.search_lexical(query="alembic; DROP TABLE memories; --", owner_id="alice")
    assert len(res_punct) >= 1
    assert res_punct[0][0].id == m2.id

    # Non-existent query
    assert len(storage.search_lexical(query="Kubernetes", owner_id="alice")) == 0


def test_fts5_trigger_synchronization(storage):
    """Verify that updating and deleting memories synchronizes FTS5 index."""
    mem = Memory(
        owner_id="alice",
        content="Original secret blueprint text.",
    )
    storage.create_memory(mem)

    # Initial search matches
    assert len(storage.search_lexical(query="blueprint", owner_id="alice")) == 1

    # Update content
    storage.update_memory(
        memory_id=mem.id,
        owner_id="alice",
        new_content="Replaced text with updated architecture design.",
    )

    # Old term should no longer match
    assert len(storage.search_lexical(query="blueprint", owner_id="alice")) == 0
    # New term should match
    assert len(storage.search_lexical(query="architecture", owner_id="alice")) == 1

    # Soft delete memory
    storage.delete_memory(mem.id, owner_id="alice", permanent=False)
    # Search excludes non-active memories
    assert len(storage.search_lexical(query="architecture", owner_id="alice")) == 0


def test_associative_memory_relationships(storage):
    """Test creating and traversing typed relationships in knowledge graph."""
    m_fact1 = storage.create_memory(Memory(
        owner_id="alice",
        content="Project backend is built with FastAPI.",
    ))
    m_fact2 = storage.create_memory(Memory(
        owner_id="alice",
        content="Authentication uses JWT tokens verified via FastAPI middleware.",
    ))
    m_fact3 = storage.create_memory(Memory(
        owner_id="alice",
        content="Rate limiting is enforced at 100 requests per minute per IP.",
    ))

    # Relate fact1 -> fact2 (RELATES_TO)
    rel1 = storage.create_relationship(
        MemoryRelationship(
            source_memory_id=m_fact1.id,
            target_memory_id=m_fact2.id,
            relationship_type=RelationshipType.RELATES_TO,
            confidence=0.9,
        ),
        owner_id="alice",
    )
    assert rel1.id.startswith("rel_")

    # Relate fact2 -> fact3 (DEPENDS_ON)
    storage.create_relationship(
        MemoryRelationship(
            source_memory_id=m_fact2.id,
            target_memory_id=m_fact3.id,
            relationship_type=RelationshipType.DEPENDS_ON,
            confidence=0.85,
        ),
        owner_id="alice",
    )

    # 1-hop traversal from fact1
    related_1hop = storage.get_related_memories(
        memory_id=m_fact1.id, owner_id="alice", max_depth=1
    )
    assert len(related_1hop) == 1
    assert related_1hop[0].id == m_fact2.id

    # 2-hop traversal from fact1
    related_2hop = storage.get_related_memories(
        memory_id=m_fact1.id, owner_id="alice", max_depth=2
    )
    assert len(related_2hop) == 2
    ids = {m.id for m in related_2hop}
    assert m_fact2.id in ids
    assert m_fact3.id in ids


def test_working_memory_ttl_archival(storage):
    """Test expiration and archival of working memories."""
    past = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
    future = (datetime.now(timezone.utc) + timedelta(hours=10)).isoformat()

    expired_mem = storage.create_memory(Memory(
        owner_id="alice",
        memory_type=MemoryType.WORKING,
        content="Temporary task goal: parse incoming JSON payload.",
        expires_at=past,
    ))

    active_mem = storage.create_memory(Memory(
        owner_id="alice",
        memory_type=MemoryType.WORKING,
        content="Active task goal: write database migration.",
        expires_at=future,
    ))

    # Run TTL archival
    archived_count = storage.archive_expired_working_memories(owner_id="alice")
    assert archived_count == 1

    # Check statuses
    m_exp = storage.list_memories(owner_id="alice", status=MemoryStatus.ARCHIVED)
    assert len(m_exp) == 1
    assert m_exp[0].id == expired_mem.id

    m_act = storage.list_memories(owner_id="alice", status=MemoryStatus.ACTIVE)
    assert len(m_act) == 1
    assert m_act[0].id == active_mem.id


def test_storage_statistics(storage):
    """Test aggregated metrics and statistics."""
    storage.create_memory(Memory(owner_id="alice", memory_type=MemoryType.EPISODIC))
    storage.create_memory(Memory(owner_id="alice", memory_type=MemoryType.SEMANTIC))
    storage.create_memory(Memory(owner_id="alice", memory_type=MemoryType.SEMANTIC))
    m3 = storage.create_memory(Memory(owner_id="alice", memory_type=MemoryType.PROCEDURAL))
    storage.delete_memory(m3.id, owner_id="alice")

    stats = storage.get_stats(owner_id="alice")
    assert stats["total_memories"] == 4
    assert stats["active_memories"] == 3
    assert stats["deleted_memories"] == 1
    assert stats["by_type"]["semantic"] == 2
    assert stats["by_type"]["episodic"] == 1
    assert stats["by_type"]["procedural"] == 1


def test_file_backed_persistence_and_reopen(file_storage, tmp_path):
    """Test that memories survive closing and reopening file-backed storage."""
    db_file = tmp_path / "test_adapt.db"
    mem = Memory(
        owner_id="bob",
        memory_type=MemoryType.SEMANTIC,
        content="Persistent fact that must survive process reboot.",
    )
    saved = file_storage.create_memory(mem)
    mem_id = saved.id
    file_storage.close()

    # Reopen brand new SQLiteStorage instance on the exact same file
    reopened = SQLiteStorage(db_path=str(db_file))
    reopened.initialize()

    loaded = reopened.get_memory(mem_id, owner_id="bob")
    assert loaded is not None
    assert loaded.content == "Persistent fact that must survive process reboot."

    # Test FTS search on reopened database
    results = reopened.search_lexical(query="reboot", owner_id="bob")
    assert len(results) == 1
    assert results[0][0].id == mem_id
    reopened.close()
