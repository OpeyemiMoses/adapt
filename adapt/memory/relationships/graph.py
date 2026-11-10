"""Associative Memory and Knowledge Graph Engine for ADAPT."""

from __future__ import annotations

import logging
from typing import Dict, List, Optional, Set

from adapt.models.schema import Memory, MemoryRelationship, RelationshipType
from adapt.storage.base import StorageBackend

logger = logging.getLogger(__name__)


class KnowledgeGraph:
    """Manages typed knowledge graph edges and multi-hop associative traversal."""

    def __init__(self, storage: StorageBackend) -> None:
        self.storage = storage

    def link(
        self,
        source_id: str,
        target_id: str,
        relationship_type: RelationshipType = RelationshipType.RELATES_TO,
        confidence: float = 1.0,
        metadata: Optional[Dict] = None,
        owner_id: str = "default_user",
    ) -> MemoryRelationship:
        """Create a typed edge between two memories belonging to owner."""
        rel = MemoryRelationship(
            source_memory_id=source_id,
            target_memory_id=target_id,
            relationship_type=relationship_type,
            confidence=confidence,
            metadata=metadata or {},
        )
        return self.storage.create_relationship(rel, owner_id=owner_id)

    def traverse(
        self,
        memory_id: str,
        owner_id: str,
        relationship_type: Optional[RelationshipType] = None,
        max_depth: int = 2,
    ) -> List[Memory]:
        """Traverse connected memories up to max_depth hops."""
        return self.storage.get_related_memories(
            memory_id=memory_id,
            owner_id=owner_id,
            relationship_type=relationship_type,
            max_depth=max_depth,
        )

    def get_subgraph(
        self,
        memory_id: str,
        owner_id: str,
        max_depth: int = 2,
    ) -> Dict[str, Any]:
        """Return a structured subgraph with nodes and edges centered around a memory."""
        nodes: Dict[str, Memory] = {}
        root = self.storage.get_memory(memory_id, owner_id=owner_id)
        if not root:
            return {"nodes": [], "edges": []}

        nodes[root.id] = root
        connected_memories = self.traverse(memory_id, owner_id=owner_id, max_depth=max_depth)
        for m in connected_memories:
            nodes[m.id] = m

        edges: List[MemoryRelationship] = []
        for node_id in nodes:
            rels = self.storage.get_relationships(node_id)
            for r in rels:
                if r.source_memory_id in nodes and r.target_memory_id in nodes:
                    if r not in edges:
                        edges.append(r)

        return {
            "root_id": memory_id,
            "nodes": [m.to_dict() for m in nodes.values()],
            "edges": [e.to_dict() for e in edges],
        }

