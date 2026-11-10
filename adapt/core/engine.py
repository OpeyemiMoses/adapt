"""Central orchestration engine for ADAPT memory infrastructure."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from adapt.core.errors import MemoryNotFoundError, UnauthorizedAccessError, ValidationError
from adapt.memory.ingestion.pipeline import IngestionPipeline, IngestionResult
from adapt.models.schema import (
    Memory,
    MemoryRelationship,
    MemorySource,
    MemoryStatus,
    MemoryType,
    RelationshipType,
    ScoredMemory,
    new_id,
    utc_now_iso,
)
from adapt.security.isolation import validate_identifier
from adapt.storage.base import StorageBackend
from adapt.storage.sqlite import SQLiteStorage

logger = logging.getLogger(__name__)


class AdaptEngine:
    """The central ADAPT memory orchestration engine.

    Framework-independent memory infrastructure providing persistence,
    retrieval, associative relationships, and tenant isolation.
    """

    def __init__(
        self,
        storage: Optional[StorageBackend] = None,
        storage_dir: Optional[str] = None,
        db_name: str = "adapt_memory.db",
        working_ttl_hours: int = 24,
    ) -> None:
        if storage is not None:
            self.storage = storage
        else:
            dir_path = storage_dir or os.getenv("ADAPT_STORAGE_DIR", "~/.hermes/adapt")
            full_path = Path(os.path.expanduser(dir_path)) / db_name
            self.storage = SQLiteStorage(db_path=str(full_path))

        self.storage.initialize()
        self.ingestion = IngestionPipeline(storage=self.storage, working_ttl_hours=working_ttl_hours)

    def close(self) -> None:
        """Close storage connections and clean up resources."""
        self.storage.close()

    # -- Core Operations -----------------------------------------------------

    def remember(
        self,
        content: str,
        memory_type: Optional[Union[MemoryType, str]] = None,
        owner_id: str = "default_user",
        agent_id: str = "hermes",
        project_id: Optional[str] = None,
        importance: float = 0.5,
        confidence: float = 1.0,
        source_type: Optional[str] = None,
        source_identifier: Optional[str] = None,
        expires_at: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        link_conflicts: bool = True,
    ) -> Memory:
        """Persist a new memory with source provenance and tenant isolation."""
        if not content or not content.strip():
            raise ValidationError("Memory content cannot be empty.")

        validate_identifier("owner_id", owner_id)
        validate_identifier("agent_id", agent_id)

        parsed_type: Optional[MemoryType] = None
        if memory_type is not None:
            if isinstance(memory_type, str):
                try:
                    parsed_type = MemoryType(memory_type.lower())
                except ValueError:
                    raise ValidationError(f"Invalid memory_type '{memory_type}'. Must be one of {[t.value for t in MemoryType]}")
            else:
                parsed_type = memory_type

        ingest_result = self.ingestion.ingest(
            raw_content=content,
            owner_id=owner_id,
            agent_id=agent_id,
            project_id=project_id,
            explicit_type=parsed_type,
            importance=importance,
            confidence=confidence,
            source_type=source_type,
            source_identifier=source_identifier,
            metadata=metadata,
            link_conflicts=link_conflicts,
        )
        return ingest_result.memory

    def recall(
        self,
        query: str,
        owner_id: str = "default_user",
        agent_id: Optional[str] = None,
        project_id: Optional[str] = None,
        limit: int = 5,
        memory_types: Optional[List[Union[MemoryType, str]]] = None,
        include_related: bool = False,
    ) -> List[ScoredMemory]:
        """Perform context-aware recall matching the agent's current task or query."""
        validate_identifier("owner_id", owner_id)
        if not query or not query.strip():
            return []

        parsed_types: Optional[List[MemoryType]] = None
        if memory_types:
            parsed_types = [
                MemoryType(t.lower()) if isinstance(t, str) else t
                for t in memory_types
            ]

        # Lexical FTS5 retrieval (M1 base; expanded to hybrid in M3)
        lexical_results = self.storage.search_lexical(
            query=query,
            owner_id=owner_id,
            agent_id=agent_id,
            memory_types=parsed_types,
            project_id=project_id,
            limit=limit,
        )

        scored_results: List[ScoredMemory] = []
        for mem, score in lexical_results:
            # Factor in importance
            final_score = score * (0.5 + 0.5 * mem.importance)
            scored_results.append(
                ScoredMemory(
                    memory=mem,
                    score=final_score,
                    lexical_score=score,
                    importance_factor=mem.importance,
                    explanation=f"Lexical BM25 match ({score:.2f}) weighted by importance ({mem.importance:.2f})",
                )
            )

        if include_related and scored_results:
            # Associative traversal for top result
            top_mem = scored_results[0].memory
            related = self.storage.get_related_memories(
                memory_id=top_mem.id,
                owner_id=owner_id,
                max_depth=1,
            )
            existing_ids = {sm.memory.id for sm in scored_results}
            for rel_mem in related:
                if rel_mem.id not in existing_ids:
                    scored_results.append(
                        ScoredMemory(
                            memory=rel_mem,
                            score=scored_results[0].score * 0.75,
                            explanation=f"Associatively related to '{top_mem.id}'",
                        )
                    )

        # Sort descending by final score
        scored_results.sort(key=lambda sm: sm.score, reverse=True)
        return scored_results[:limit]

    def search(
        self,
        query: str,
        owner_id: str = "default_user",
        agent_id: Optional[str] = None,
        memory_types: Optional[List[Union[MemoryType, str]]] = None,
        project_id: Optional[str] = None,
        limit: int = 20,
    ) -> List[Memory]:
        """Search memories directly by keyword."""
        results = self.recall(
            query=query,
            owner_id=owner_id,
            agent_id=agent_id,
            project_id=project_id,
            limit=limit,
            memory_types=memory_types,
            include_related=False,
        )
        return [sm.memory for sm in results]

    def get_memory(self, memory_id: str, owner_id: str = "default_user") -> Optional[Memory]:
        """Retrieve a specific memory by ID."""
        validate_identifier("owner_id", owner_id)
        return self.storage.get_memory(memory_id=memory_id, owner_id=owner_id)

    def update_memory(
        self,
        memory_id: str,
        owner_id: str = "default_user",
        new_content: Optional[str] = None,
        importance: Optional[float] = None,
        confidence: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None,
        change_reason: Optional[str] = None,
        source_id: Optional[str] = None,
    ) -> Optional[Memory]:
        """Update an existing memory with version provenance."""
        validate_identifier("owner_id", owner_id)
        return self.storage.update_memory(
            memory_id=memory_id,
            owner_id=owner_id,
            new_content=new_content,
            importance=importance,
            confidence=confidence,
            metadata=metadata,
            change_reason=change_reason,
            source_id=source_id,
        )

    def forget(self, memory_id: str, owner_id: str = "default_user", permanent: bool = False) -> bool:
        """Delete a memory (soft-delete by default, permanent on request)."""
        validate_identifier("owner_id", owner_id)
        return self.storage.delete_memory(memory_id=memory_id, owner_id=owner_id, permanent=permanent)

    def archive(self, memory_id: str, owner_id: str = "default_user") -> bool:
        """Archive a memory."""
        validate_identifier("owner_id", owner_id)
        return self.storage.archive_memory(memory_id=memory_id, owner_id=owner_id)

    def relate(
        self,
        source_memory_id: str,
        target_memory_id: str,
        relationship_type: Union[RelationshipType, str] = RelationshipType.RELATES_TO,
        confidence: float = 1.0,
        metadata: Optional[Dict[str, Any]] = None,
        owner_id: str = "default_user",
    ) -> MemoryRelationship:
        """Connect two memories in the associative knowledge graph."""
        validate_identifier("owner_id", owner_id)
        if isinstance(relationship_type, str):
            relationship_type = RelationshipType(relationship_type)

        rel = MemoryRelationship(
            source_memory_id=source_memory_id,
            target_memory_id=target_memory_id,
            relationship_type=relationship_type,
            confidence=confidence,
            metadata=metadata or {},
        )
        return self.storage.create_relationship(rel, owner_id=owner_id)

    def get_related(
        self,
        memory_id: str,
        relationship_type: Optional[Union[RelationshipType, str]] = None,
        max_depth: int = 1,
        owner_id: str = "default_user",
    ) -> List[Memory]:
        """Traverse connected memories in the associative knowledge graph."""
        validate_identifier("owner_id", owner_id)
        rel_type = (
            RelationshipType(relationship_type)
            if isinstance(relationship_type, str)
            else relationship_type
        )
        return self.storage.get_related_memories(
            memory_id=memory_id,
            owner_id=owner_id,
            relationship_type=rel_type,
            max_depth=max_depth,
        )

    def get_stats(self, owner_id: str = "default_user", agent_id: Optional[str] = None) -> Dict[str, Any]:
        """Retrieve aggregated telemetry on memory usage."""
        validate_identifier("owner_id", owner_id)
        return self.storage.get_stats(owner_id=owner_id, agent_id=agent_id)
