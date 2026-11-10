"""Memory Evolution and Consolidation Engine for ADAPT."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Set

from adapt.memory.ingestion.pipeline import ContentNormalizer, DeduplicationEngine
from adapt.models.schema import (
    ConsolidationReport,
    JobStatus,
    Memory,
    MemoryJob,
    MemoryRelationship,
    MemoryStatus,
    MemoryType,
    RelationshipType,
    new_id,
    utc_now_iso,
)
from adapt.storage.base import StorageBackend

logger = logging.getLogger(__name__)


class ConsolidationEngine:
    """Manages memory maintenance, deduplication, conflict linking, and archival."""

    def __init__(self, storage: StorageBackend) -> None:
        self.storage = storage

    def consolidate(
        self, owner_id: str, agent_id: Optional[str] = None
    ) -> ConsolidationReport:
        """Execute a full memory maintenance cycle."""
        job = self.storage.create_job(
            MemoryJob(
                job_type="consolidation",
                status=JobStatus.RUNNING,
                input_reference=f"owner:{owner_id}",
            )
        )

        duplicates_merged = 0
        conflicts_flagged = 0
        details: List[str] = []

        try:
            # 1. Prune expired working memories
            expired_archived = self.storage.archive_expired_working_memories(owner_id=owner_id)
            if expired_archived > 0:
                details.append(f"Archived {expired_archived} expired working memories.")

            # 2. Fetch active memories for consolidation review
            active_mems = self.storage.list_memories(
                owner_id=owner_id,
                agent_id=agent_id,
                status=MemoryStatus.ACTIVE,
                limit=500,
            )

            # 3. Deduplication pass
            seen_fingerprints: Dict[str, Memory] = {}
            for mem in active_mems:
                fp = ContentNormalizer.compute_fingerprint(mem.content)
                if fp in seen_fingerprints:
                    primary = seen_fingerprints[fp]
                    # Merge metadata and archive redundant duplicate
                    merged_meta = {**primary.metadata, **mem.metadata}
                    higher_importance = max(primary.importance, mem.importance)
                    self.storage.update_memory(
                        memory_id=primary.id,
                        owner_id=owner_id,
                        importance=higher_importance,
                        metadata=merged_meta,
                        change_reason=f"Consolidated duplicate memory {mem.id}",
                    )
                    self.storage.archive_memory(mem.id, owner_id=owner_id)
                    duplicates_merged += 1
                    details.append(f"Merged duplicate {mem.id} into primary {primary.id}.")
                else:
                    seen_fingerprints[fp] = mem

            # 4. Semantic Contradiction & Evolution pass
            semantic_mems = [m for m in seen_fingerprints.values() if m.memory_type == MemoryType.SEMANTIC]
            linked_pairs: Set[Tuple[str, str]] = set()

            for i in range(len(semantic_mems)):
                for j in range(i + 1, len(semantic_mems)):
                    m1 = semantic_mems[i]
                    m2 = semantic_mems[j]

                    # Check for conflict
                    conflicts = DeduplicationEngine.check_conflict(m2.content, [m1])
                    if conflicts:
                        pair = tuple(sorted([m1.id, m2.id]))
                        if pair not in linked_pairs:
                            linked_pairs.add(pair)
                            # Verify if already linked
                            existing_rels = self.storage.get_relationships(m1.id)
                            already_linked = any(
                                (r.source_memory_id == m2.id or r.target_memory_id == m2.id)
                                for r in existing_rels
                            )
                            if not already_linked:
                                # Determine newer fact
                                newer, older = (m2, m1) if m2.created_at >= m1.created_at else (m1, m2)
                                self.storage.create_relationship(
                                    MemoryRelationship(
                                        source_memory_id=newer.id,
                                        target_memory_id=older.id,
                                        relationship_type=RelationshipType.SUPERSEDES,
                                        confidence=0.85,
                                        metadata={"discovered_by": "consolidation_job"},
                                    ),
                                    owner_id=owner_id,
                                )
                                conflicts_flagged += 1
                                details.append(f"Linked conflicting semantic facts: {newer.id} supersedes {older.id}")

            report = ConsolidationReport(
                job_id=job.id,
                owner_id=owner_id,
                duplicates_merged=duplicates_merged,
                conflicts_detected=conflicts_flagged,
                expired_working_memories_archived=expired_archived,
                details=details,
            )

            self.storage.update_job(
                job_id=job.id,
                status=JobStatus.COMPLETED,
                result={
                    "duplicates_merged": duplicates_merged,
                    "conflicts_detected": conflicts_flagged,
                    "expired_archived": expired_archived,
                },
            )
            return report

        except Exception as exc:
            logger.error("Consolidation job %s failed: %s", job.id, exc, exc_info=True)
            self.storage.update_job(
                job_id=job.id,
                status=JobStatus.FAILED,
                error=str(exc),
            )
            raise
