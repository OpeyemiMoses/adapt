"""Core data models, enums, and schemas for ADAPT memory system."""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional


def utc_now_iso() -> str:
    """Return current UTC timestamp in ISO 8601 format."""
    return datetime.now(timezone.utc).isoformat()


def new_id(prefix: str = "mem") -> str:
    """Generate a prefixed UUID4 identifier."""
    return f"{prefix}_{uuid.uuid4().hex[:16]}"


class MemoryType(str, Enum):
    """Supported memory classifications."""
    EPISODIC = "episodic"      # Past experiences, events, task completions
    SEMANTIC = "semantic"      # Facts, knowledge, user preferences, architecture
    PROCEDURAL = "procedural"  # Workflows, step-by-step instructions
    WORKING = "working"        # Ephemeral active task context, scratchpad


class MemoryStatus(str, Enum):
    """Lifecycle status of a memory."""
    ACTIVE = "active"
    ARCHIVED = "archived"
    DELETED = "deleted"


class RelationshipType(str, Enum):
    """Typed edges for associative knowledge graph."""
    RELATES_TO = "RELATES_TO"
    CONTRADICTS = "CONTRADICTS"
    SUPERSEDES = "SUPERSEDES"
    DERIVED_FROM = "DERIVED_FROM"
    PART_OF = "PART_OF"
    DEPENDS_ON = "DEPENDS_ON"


class JobStatus(str, Enum):
    """Status for background or explicit maintenance jobs."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class Memory:
    """A discrete unit of knowledge preserved across agent interactions."""
    id: str = field(default_factory=lambda: new_id("mem"))
    owner_id: str = "default_user"
    agent_id: str = "hermes"
    project_id: Optional[str] = None
    memory_type: MemoryType = MemoryType.SEMANTIC
    content: str = ""
    normalized_content: Optional[str] = None
    importance: float = 0.5
    confidence: float = 1.0
    source_type: Optional[str] = None
    source_id: Optional[str] = None
    created_at: str = field(default_factory=utc_now_iso)
    updated_at: str = field(default_factory=utc_now_iso)
    last_accessed_at: Optional[str] = None
    expires_at: Optional[str] = None
    status: MemoryStatus = MemoryStatus.ACTIVE
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "owner_id": self.owner_id,
            "agent_id": self.agent_id,
            "project_id": self.project_id,
            "memory_type": self.memory_type.value if isinstance(self.memory_type, MemoryType) else str(self.memory_type),
            "content": self.content,
            "normalized_content": self.normalized_content,
            "importance": self.importance,
            "confidence": self.confidence,
            "source_type": self.source_type,
            "source_id": self.source_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "last_accessed_at": self.last_accessed_at,
            "expires_at": self.expires_at,
            "status": self.status.value if isinstance(self.status, MemoryStatus) else str(self.status),
            "metadata": self.metadata,
        }

    @classmethod
    def from_row(cls, row: Dict[str, Any]) -> Memory:
        """Construct Memory instance from SQLite row dictionary."""
        meta = row.get("metadata")
        if isinstance(meta, str):
            try:
                meta = json.loads(meta)
            except Exception:
                meta = {}
        return cls(
            id=row["id"],
            owner_id=row["owner_id"],
            agent_id=row["agent_id"],
            project_id=row.get("project_id"),
            memory_type=MemoryType(row["memory_type"]),
            content=row["content"],
            normalized_content=row.get("normalized_content"),
            importance=float(row.get("importance", 0.5)),
            confidence=float(row.get("confidence", 1.0)),
            source_type=row.get("source_type"),
            source_id=row.get("source_id"),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            last_accessed_at=row.get("last_accessed_at"),
            expires_at=row.get("expires_at"),
            status=MemoryStatus(row.get("status", "active")),
            metadata=meta or {},
        )


@dataclass
class MemoryRelationship:
    """Directed, typed relationship between two memories."""
    id: str = field(default_factory=lambda: new_id("rel"))
    source_memory_id: str = ""
    target_memory_id: str = ""
    relationship_type: RelationshipType = RelationshipType.RELATES_TO
    confidence: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=utc_now_iso)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "source_memory_id": self.source_memory_id,
            "target_memory_id": self.target_memory_id,
            "relationship_type": self.relationship_type.value if isinstance(self.relationship_type, RelationshipType) else str(self.relationship_type),
            "confidence": self.confidence,
            "metadata": self.metadata,
            "created_at": self.created_at,
        }

    @classmethod
    def from_row(cls, row: Dict[str, Any]) -> MemoryRelationship:
        meta = row.get("metadata")
        if isinstance(meta, str):
            try:
                meta = json.loads(meta)
            except Exception:
                meta = {}
        return cls(
            id=row["id"],
            source_memory_id=row["source_memory_id"],
            target_memory_id=row["target_memory_id"],
            relationship_type=RelationshipType(row["relationship_type"]),
            confidence=float(row.get("confidence", 1.0)),
            metadata=meta or {},
            created_at=row["created_at"],
        )


@dataclass
class MemorySource:
    """Tracks origin/provenance of ingested information."""
    id: str = field(default_factory=lambda: new_id("src"))
    source_type: str = "conversation"
    source_identifier: str = ""
    owner_id: str = "default_user"
    agent_id: str = "hermes"
    created_at: str = field(default_factory=utc_now_iso)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "source_type": self.source_type,
            "source_identifier": self.source_identifier,
            "owner_id": self.owner_id,
            "agent_id": self.agent_id,
            "created_at": self.created_at,
            "metadata": self.metadata,
        }


@dataclass
class MemoryVersion:
    """Historical record created whenever a memory is updated."""
    id: str = field(default_factory=lambda: new_id("ver"))
    memory_id: str = ""
    previous_content: str = ""
    new_content: str = ""
    change_reason: Optional[str] = None
    source_id: Optional[str] = None
    created_at: str = field(default_factory=utc_now_iso)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "memory_id": self.memory_id,
            "previous_content": self.previous_content,
            "new_content": self.new_content,
            "change_reason": self.change_reason,
            "source_id": self.source_id,
            "created_at": self.created_at,
        }


@dataclass
class Agent:
    """Registered agent profile using the memory store."""
    id: str = field(default_factory=lambda: new_id("agt"))
    owner_id: str = "default_user"
    name: str = "hermes"
    framework: str = "hermes"
    configuration: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=utc_now_iso)
    updated_at: str = field(default_factory=utc_now_iso)


@dataclass
class MemoryJob:
    """Tracks maintenance or consolidation task executions."""
    id: str = field(default_factory=lambda: new_id("job"))
    job_type: str = "consolidation"
    status: JobStatus = JobStatus.PENDING
    input_reference: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    created_at: str = field(default_factory=utc_now_iso)
    completed_at: Optional[str] = None


@dataclass
class ScoredMemory:
    """A memory bundled with relevance and ranking scores for contextual recall."""
    memory: Memory
    score: float
    lexical_score: float = 0.0
    semantic_score: float = 0.0
    recency_factor: float = 1.0
    importance_factor: float = 1.0
    explanation: Optional[str] = None


@dataclass
class ConsolidationReport:
    """Summary of operations performed during a memory maintenance cycle."""
    job_id: str
    owner_id: str
    duplicates_detected: int = 0
    duplicates_merged: int = 0
    conflicts_detected: int = 0
    expired_working_memories_archived: int = 0
    recency_scores_updated: int = 0
    details: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=utc_now_iso)
