"""Contextual Hybrid Retrieval Engine for ADAPT memory system."""

from __future__ import annotations

import logging
import math
from datetime import datetime, timezone
from typing import Dict, List, Optional, Set, Tuple

from adapt.embeddings.base import EmbeddingProvider
from adapt.embeddings.providers import NoOpEmbeddingProvider, cosine_similarity
from adapt.models.schema import Memory, MemoryStatus, MemoryType, ScoredMemory
from adapt.storage.base import StorageBackend

logger = logging.getLogger(__name__)


class RetrievalEngine:
    """Hybrid retrieval engine combining SQLite FTS5 BM25 and vector embeddings."""

    def __init__(
        self,
        storage: StorageBackend,
        embedding_provider: Optional[EmbeddingProvider] = None,
        hybrid_alpha: float = 0.5,
        min_score: float = 0.20,
        recency_decay_lambda: float = 0.05,
    ) -> None:
        self.storage = storage
        self.embedding_provider = embedding_provider or NoOpEmbeddingProvider()
        self.hybrid_alpha = max(0.0, min(1.0, hybrid_alpha))
        self.min_score = min_score
        self.recency_decay_lambda = recency_decay_lambda

    def _calculate_recency(self, memory: Memory) -> float:
        """Calculate exponential recency decay based on time elapsed since last access."""
        ts_str = memory.last_accessed_at or memory.created_at
        try:
            ts = datetime.fromisoformat(ts_str)
            now = datetime.now(timezone.utc)
            delta_days = max(0.0, (now - ts).total_seconds() / 86400.0)
            # Bounded decay so ancient memories still retain at least ~20% of their recency weight
            return math.exp(-self.recency_decay_lambda * min(delta_days, 30.0))
        except Exception:
            return 1.0

    def retrieve(
        self,
        query: str,
        owner_id: str,
        agent_id: Optional[str] = None,
        project_id: Optional[str] = None,
        limit: int = 5,
        memory_types: Optional[List[MemoryType]] = None,
        include_related: bool = True,
    ) -> List[ScoredMemory]:
        """Execute contextual hybrid retrieval matching current query and filters."""
        query = query.strip()
        if not query:
            return []

        # 1. Lexical retrieval via SQLite FTS5 BM25
        lexical_candidates = self.storage.search_lexical(
            query=query,
            owner_id=owner_id,
            agent_id=agent_id,
            memory_types=memory_types,
            project_id=project_id,
            limit=limit * 3,
        )

        candidate_map: Dict[str, Tuple[Memory, float]] = {
            m.id: (m, score) for m, score in lexical_candidates
        }

        # 2. Semantic retrieval if embedding provider is available
        has_semantic = self.embedding_provider.is_available()
        query_vec: List[float] = []
        doc_vectors: List[List[float]] = []

        if has_semantic:
            try:
                query_vec = self.embedding_provider.embed_query(query)
                # Also fetch recent memories to give non-keyword semantic matches a chance
                additional_active = self.storage.list_memories(
                    owner_id=owner_id,
                    agent_id=agent_id,
                    project_id=project_id,
                    memory_types=memory_types,
                    status=MemoryStatus.ACTIVE,
                    limit=limit * 3,
                )
                for m in additional_active:
                    if m.id not in candidate_map:
                        candidate_map[m.id] = (m, 0.0)

                doc_texts = [m.content for m, _ in candidate_map.values()]
                if query_vec and doc_texts:
                    doc_vectors = self.embedding_provider.embed_documents(doc_texts)
            except Exception as exc:
                logger.warning(
                    "Embedding provider %s failed (%s); falling back to lexical FTS5 BM25.",
                    self.embedding_provider.name,
                    exc,
                )
                has_semantic = False
                query_vec = []
                doc_vectors = []

        scored_list: List[ScoredMemory] = []

        for i, (m_id, (mem, lex_score)) in enumerate(candidate_map.items()):
            sem_score = 0.0
            if has_semantic and doc_vectors and i < len(doc_vectors) and doc_vectors[i]:
                sem_score = cosine_similarity(query_vec, doc_vectors[i])

            # Hybrid score combination
            if has_semantic:
                base_score = (self.hybrid_alpha * sem_score) + ((1.0 - self.hybrid_alpha) * lex_score)
            else:
                base_score = lex_score

            recency = self._calculate_recency(mem)
            importance = 0.5 + (0.5 * mem.importance)

            final_score = base_score * importance * recency

            if final_score >= self.min_score or (lex_score > 0 and not has_semantic):
                explanation = (
                    f"Hybrid match (sem={sem_score:.2f}, lex={lex_score:.2f}, "
                    f"imp={mem.importance:.2f}, rec={recency:.2f})"
                    if has_semantic
                    else f"Lexical BM25 match ({lex_score:.2f}) weighted by importance ({mem.importance:.2f})"
                )
                scored_list.append(
                    ScoredMemory(
                        memory=mem,
                        score=final_score,
                        lexical_score=lex_score,
                        semantic_score=sem_score,
                        recency_factor=recency,
                        importance_factor=mem.importance,
                        explanation=explanation,
                    )
                )

        # 3. Associative Graph Proximity Boost
        if include_related and scored_list:
            scored_list.sort(key=lambda s: s.score, reverse=True)
            top_mem = scored_list[0].memory
            related = self.storage.get_related_memories(
                memory_id=top_mem.id,
                owner_id=owner_id,
                max_depth=1,
            )
            existing_ids: Set[str] = {sm.memory.id for sm in scored_list}
            for rel_mem in related:
                if rel_mem.id not in existing_ids:
                    rel_score = scored_list[0].score * 0.70
                    scored_list.append(
                        ScoredMemory(
                            memory=rel_mem,
                            score=rel_score,
                            explanation=f"Associative connection to '{top_mem.id}'",
                        )
                    )

        # Sort descending and enforce limit
        scored_list.sort(key=lambda s: s.score, reverse=True)
        return scored_list[:limit]
