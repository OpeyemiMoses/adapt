"""Unit tests for ADAPT Intelligent Ingestion Engine."""

import pytest

from adapt.memory.ingestion.pipeline import (
    ContentNormalizer,
    DeduplicationEngine,
    IngestionPipeline,
    MemoryClassifier,
)
from adapt.models.schema import Memory, MemoryType, RelationshipType
from adapt.storage.sqlite import SQLiteStorage


@pytest.fixture
def pipeline():
    storage = SQLiteStorage(db_path=":memory:")
    storage.initialize()
    pipe = IngestionPipeline(storage=storage, working_ttl_hours=12)
    yield pipe
    storage.close()


def test_content_normalizer():
    """Test whitespace, unicode, and entity extraction."""
    raw = "   User  likes   `FastAPI`    for   APIs.   "
    clean = ContentNormalizer.normalize_text(raw)
    assert clean == "User likes `FastAPI` for APIs."

    # Multi-paragraph preservation
    multi = "Paragraph 1.\n\n\n\nParagraph 2."
    clean_multi = ContentNormalizer.normalize_text(multi)
    assert clean_multi == "Paragraph 1.\n\nParagraph 2."

    # Fingerprint consistency
    fp1 = ContentNormalizer.compute_fingerprint("User likes FastAPI")
    fp2 = ContentNormalizer.compute_fingerprint("user likes fastapi!!!")
    assert fp1 == fp2

    # Keyword extraction
    keywords = ContentNormalizer.extract_keywords("Deploy `FastAPI` to Kubernetes using Docker.")
    assert "FastAPI" in keywords
    assert "Kubernetes" in keywords
    assert "Docker" in keywords


def test_memory_classifier():
    """Test classification heuristics."""
    # Procedural
    proc_text = "How to deploy: 1. run `docker build` then execute `docker run`."
    assert MemoryClassifier.classify(proc_text) == MemoryType.PROCEDURAL

    # Episodic
    ep_text = "Yesterday user requested to refactor the authentication module."
    assert MemoryClassifier.classify(ep_text) == MemoryType.EPISODIC

    # Working
    work_text = "Currently working on subtask 3 of 5: adding validation tests."
    assert MemoryClassifier.classify(work_text) == MemoryType.WORKING

    # Semantic (default)
    sem_text = "The user prefers dark mode and vim keybindings."
    assert MemoryClassifier.classify(sem_text) == MemoryType.SEMANTIC


def test_deduplication_engine():
    """Test duplicate and conflict detection."""
    existing = [
        Memory(owner_id="u1", content="User prefers PostgreSQL over MongoDB."),
        Memory(owner_id="u1", content="Deploy application with Docker Compose."),
    ]

    # Exact duplicate
    dup = DeduplicationEngine.check_duplicate(
        "User prefers PostgreSQL over MongoDB.", existing
    )
    assert dup is not None
    assert "PostgreSQL" in dup.content

    # Non-duplicate
    non_dup = DeduplicationEngine.check_duplicate(
        "Redis is used for caching session state.", existing
    )
    assert non_dup is None

    # Conflict detection
    conflicts = DeduplicationEngine.check_conflict(
        "User prefers MySQL over PostgreSQL for legacy reasons.", existing
    )
    assert len(conflicts) == 1
    assert "PostgreSQL" in conflicts[0].content


def test_ingestion_pipeline_end_to_end(pipeline):
    """Test pipeline ingestion, deduplication, and non-destructive conflict handling."""
    # 1. Ingest initial fact
    res1 = pipeline.ingest(
        raw_content="User prefers PostgreSQL for relational databases.",
        owner_id="alice",
        source_type="chat",
        source_identifier="turn_1",
    )
    assert res1.action_taken == "created"
    assert res1.is_duplicate is False
    assert res1.memory.memory_type == MemoryType.SEMANTIC
    assert res1.memory.source_id is not None

    # 2. Re-ingesting identical content triggers deduplication
    res2 = pipeline.ingest(
        raw_content="  User   prefers   PostgreSQL  for relational databases.  ",
        owner_id="alice",
    )
    assert res2.is_duplicate is True
    assert res2.action_taken == "deduplicated"
    assert res2.memory.id == res1.memory.id

    # 3. Ingesting conflicting information links via SUPERSEDES without overwriting
    res3 = pipeline.ingest(
        raw_content="User prefers CockroachDB over PostgreSQL for relational databases due to multi-region needs.",
        owner_id="alice",
        link_conflicts=True,
    )
    assert res3.action_taken == "updated_with_conflict"
    assert len(res3.conflicts_detected) == 1
    assert res3.conflicts_detected[0] == res1.memory.id

    # Verify both memories still exist
    all_alice = pipeline.storage.list_memories(owner_id="alice")
    assert len(all_alice) == 2

    # Verify relationship was created
    rels = pipeline.storage.get_relationships(res3.memory.id)
    assert len(rels) >= 1
    assert rels[0].relationship_type == RelationshipType.SUPERSEDES


def test_working_memory_ttl_assignment(pipeline):
    """Test that working memory automatically receives an expires_at timestamp."""
    res = pipeline.ingest(
        raw_content="Currently debugging test_ingestion failure.",
        owner_id="alice",
    )
    assert res.memory.memory_type == MemoryType.WORKING
    assert res.memory.expires_at is not None
