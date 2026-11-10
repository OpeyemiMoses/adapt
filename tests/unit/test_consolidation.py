"""Unit tests for ADAPT Associative Graph and Consolidation Engine."""

from datetime import datetime, timezone, timedelta
import pytest

from adapt.core.engine import AdaptEngine
from adapt.memory.consolidation.engine import ConsolidationEngine
from adapt.memory.relationships.graph import KnowledgeGraph
from adapt.models.schema import (
    JobStatus,
    Memory,
    MemoryStatus,
    MemoryType,
    RelationshipType,
)
from adapt.storage.sqlite import SQLiteStorage


@pytest.fixture
def storage():
    s = SQLiteStorage(db_path=":memory:")
    s.initialize()
    yield s
    s.close()


def test_knowledge_graph_subgraph(storage):
    """Test KnowledgeGraph node and edge representation."""
    kg = KnowledgeGraph(storage=storage)
    m1 = storage.create_memory(Memory(owner_id="alice", content="Core microservice A"))
    m2 = storage.create_memory(Memory(owner_id="alice", content="Downstream service B"))

    kg.link(
        source_id=m1.id,
        target_id=m2.id,
        relationship_type=RelationshipType.DEPENDS_ON,
        confidence=0.95,
        owner_id="alice",
    )

    subgraph = kg.get_subgraph(memory_id=m1.id, owner_id="alice", max_depth=1)
    assert subgraph["root_id"] == m1.id
    assert len(subgraph["nodes"]) == 2
    assert len(subgraph["edges"]) == 1
    assert subgraph["edges"][0]["relationship_type"] == "DEPENDS_ON"


def test_consolidation_prunes_expired_working_memories(storage):
    """Test consolidation archives expired working memories."""
    past = (datetime.now(timezone.utc) - timedelta(hours=5)).isoformat()
    storage.create_memory(Memory(
        owner_id="alice",
        memory_type=MemoryType.WORKING,
        content="Temporary execution scratchpad",
        expires_at=past,
    ))
    storage.create_memory(Memory(
        owner_id="alice",
        memory_type=MemoryType.WORKING,
        content="Current active task",
        expires_at=None,
    ))

    engine = ConsolidationEngine(storage=storage)
    report = engine.consolidate(owner_id="alice")

    assert report.expired_working_memories_archived == 1
    # Verify job record
    conn = storage._get_connection()
    job_row = conn.execute("SELECT * FROM memory_jobs WHERE id = ?;", (report.job_id,)).fetchone()
    assert job_row["status"] == JobStatus.COMPLETED.value


def test_consolidation_merges_duplicates_and_links_conflicts(storage):
    """Test consolidation identifies duplicate records and links unlinked conflicts."""
    # 1. Duplicates
    m1 = storage.create_memory(Memory(
        owner_id="alice",
        memory_type=MemoryType.SEMANTIC,
        content="User prefers dark theme in UI.",
        importance=0.6,
        metadata={"source": "chat"},
    ))
    m2 = storage.create_memory(Memory(
        owner_id="alice",
        memory_type=MemoryType.SEMANTIC,
        content="User prefers dark theme in UI.",
        importance=0.8,
        metadata={"client": "web"},
    ))

    # 2. Conflicting facts (unlinked)
    m_old = storage.create_memory(Memory(
        owner_id="alice",
        memory_type=MemoryType.SEMANTIC,
        content="User prefers PostgreSQL database for projects.",
        created_at="2026-01-01T00:00:00+00:00",
    ))
    m_new = storage.create_memory(Memory(
        owner_id="alice",
        memory_type=MemoryType.SEMANTIC,
        content="User prefers MySQL database over PostgreSQL for projects.",
        created_at="2026-02-01T00:00:00+00:00",
    ))

    engine = ConsolidationEngine(storage=storage)
    report = engine.consolidate(owner_id="alice")

    assert report.duplicates_merged == 1
    assert report.conflicts_detected >= 1

    # Verify duplicate was archived and primary kept with merged metadata
    # (m2 was created after m1 so m2 is primary in descending order)
    primary = storage.get_memory(m2.id, owner_id="alice")
    assert primary is not None
    assert primary.status == MemoryStatus.ACTIVE
    assert primary.importance == 0.8  # higher importance preserved
    assert primary.metadata.get("source") == "chat"

    # m1 is archived
    m1_archived = storage.get_memory(m1.id, owner_id="alice")
    assert m1_archived is not None
    assert m1_archived.status == MemoryStatus.ARCHIVED

    # Active listing only shows primary, not the archived duplicate
    active_mems = storage.list_memories(owner_id="alice", status=MemoryStatus.ACTIVE)
    active_ids = {m.id for m in active_mems}
    assert m2.id in active_ids
    assert m1.id not in active_ids

    # Verify conflicting facts are linked and neither is deleted
    assert storage.get_memory(m_old.id, owner_id="alice") is not None
    assert storage.get_memory(m_new.id, owner_id="alice") is not None
    rels = storage.get_relationships(m_new.id)
    assert len(rels) >= 1
    assert rels[0].relationship_type == RelationshipType.SUPERSEDES


def test_engine_consolidate_api():
    """Test AdaptEngine.consolidate API call."""
    eng = AdaptEngine(storage=SQLiteStorage(db_path=":memory:"))
    eng.remember(content="Fact A", owner_id="bob")
    report = eng.consolidate(owner_id="bob")
    assert report.owner_id == "bob"
    eng.close()
