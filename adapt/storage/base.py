"""Abstract base class for ADAPT storage backends."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple

from adapt.models.schema import (
    JobStatus,
    Memory,
    MemoryJob,
    MemoryRelationship,
    MemorySource,
    MemoryStatus,
    MemoryType,
    MemoryVersion,
    RelationshipType,
)


class StorageBackend(ABC):
    """Abstract interface defining required storage operations."""

    @abstractmethod
    def initialize(self) -> None:
        """Initialize database, run migrations, and ensure indexes."""
        pass

    @abstractmethod
    def close(self) -> None:
        """Close connections and release resources."""
        pass

    # -- Memory CRUD ---------------------------------------------------------

    @abstractmethod
    def create_memory(self, memory: Memory) -> Memory:
        """Store a new memory record."""
        pass

    @abstractmethod
    def get_memory(self, memory_id: str, owner_id: str) -> Optional[Memory]:
        """Retrieve a specific memory enforcing owner isolation."""
        pass

    @abstractmethod
    def update_memory(
        self,
        memory_id: str,
        owner_id: str,
        new_content: Optional[str] = None,
        importance: Optional[float] = None,
        confidence: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None,
        change_reason: Optional[str] = None,
        source_id: Optional[str] = None,
    ) -> Optional[Memory]:
        """Update an existing memory with version audit tracking."""
        pass

    @abstractmethod
    def delete_memory(self, memory_id: str, owner_id: str, permanent: bool = False) -> bool:
        """Soft-delete or permanently purge a memory."""
        pass

    @abstractmethod
    def archive_memory(self, memory_id: str, owner_id: str) -> bool:
        """Move memory to archived status."""
        pass

    @abstractmethod
    def list_memories(
        self,
        owner_id: str,
        agent_id: Optional[str] = None,
        project_id: Optional[str] = None,
        memory_types: Optional[List[MemoryType]] = None,
        status: Optional[MemoryStatus] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Memory]:
        """List memories matching owner and optional filters."""
        pass

    # -- Retrieval Operations ------------------------------------------------

    @abstractmethod
    def search_lexical(
        self,
        query: str,
        owner_id: str,
        agent_id: Optional[str] = None,
        memory_types: Optional[List[MemoryType]] = None,
        project_id: Optional[str] = None,
        limit: int = 20,
    ) -> List[Tuple[Memory, float]]:
        """Perform full-text lexical search returning memories with BM25/rank scores."""
        pass

    # -- Associative Relationships -------------------------------------------

    @abstractmethod
    def create_relationship(self, relationship: MemoryRelationship, owner_id: str) -> MemoryRelationship:
        """Persist a typed relationship between two memories belonging to owner."""
        pass

    @abstractmethod
    def get_relationships(
        self, memory_id: str, relationship_type: Optional[RelationshipType] = None
    ) -> List[MemoryRelationship]:
        """Retrieve outgoing and incoming relationships for a memory."""
        pass

    @abstractmethod
    def get_related_memories(
        self,
        memory_id: str,
        owner_id: str,
        relationship_type: Optional[RelationshipType] = None,
        max_depth: int = 1,
    ) -> List[Memory]:
        """Traverse connected memories up to max_depth hops."""
        pass

    # -- Provenance & Auditing -----------------------------------------------

    @abstractmethod
    def record_source(self, source: MemorySource) -> MemorySource:
        """Record an origin provenance source."""
        pass

    @abstractmethod
    def get_versions(self, memory_id: str) -> List[MemoryVersion]:
        """Retrieve full version history for a memory."""
        pass

    # -- Maintenance & Jobs --------------------------------------------------

    @abstractmethod
    def create_job(self, job: MemoryJob) -> MemoryJob:
        """Record a new maintenance job."""
        pass

    @abstractmethod
    def update_job(
        self,
        job_id: str,
        status: JobStatus,
        result: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
    ) -> Optional[MemoryJob]:
        """Update status and outputs of a maintenance job."""
        pass

    @abstractmethod
    def archive_expired_working_memories(self, owner_id: str) -> int:
        """Archive all working memories whose expires_at is before current time."""
        pass

    @abstractmethod
    def get_stats(self, owner_id: str, agent_id: Optional[str] = None) -> Dict[str, Any]:
        """Compute aggregated statistics for an owner."""
        pass

