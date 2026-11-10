"""Intelligent Ingestion Pipeline for ADAPT memory infrastructure."""

from __future__ import annotations

import hashlib
import logging
import re
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Set, Tuple

from adapt.models.schema import (
    Memory,
    MemoryRelationship,
    MemorySource,
    MemoryStatus,
    MemoryType,
    RelationshipType,
    new_id,
    utc_now_iso,
)
from adapt.storage.base import StorageBackend

logger = logging.getLogger(__name__)


# ─── Heuristic Patterns for Classification ────────────────────────────────────

_PROCEDURAL_PATTERNS = [
    re.compile(r"\b(how to|steps to|workflow|procedure|instructions|runbook|guide)\b", re.IGNORECASE),
    re.compile(r"^\s*(\d+[\.\)]|\-|\*)\s+(run|execute|install|configure|start|build|deploy)\b", re.MULTILINE | re.IGNORECASE),
    re.compile(r"\b(first|then|next|finally|after that)\s*,\s*(run|open|type|click|create)\b", re.IGNORECASE),
    re.compile(r"\b(`[^`]+`\s*(to|before|after|then))\b", re.IGNORECASE),
]

_EPISODIC_PATTERNS = [
    re.compile(r"\b(user (asked|requested|instructed|wanted|rejected|approved|decided))\b", re.IGNORECASE),
    re.compile(r"\b(agent (completed|failed|executed|generated|investigated|fixed))\b", re.IGNORECASE),
    re.compile(r"\b(yesterday|earlier today|last session|in the previous turn|at \d{1,2}:\d{2})\b", re.IGNORECASE),
    re.compile(r"\b(we (decided|discussed|agreed|finished))\b", re.IGNORECASE),
]

_WORKING_PATTERNS = [
    re.compile(r"\b(currently|in progress|active goal|current objective|scratchpad|subtask|todo)\b", re.IGNORECASE),
    re.compile(r"\b(processing \d+ of \d+|next step is|working on)\b", re.IGNORECASE),
    re.compile(r"^goal:\s*", re.IGNORECASE),
]


# ─── Normalizer ───────────────────────────────────────────────────────────────

class ContentNormalizer:
    """Cleans, normalizes, and extracts structured entities from raw memory text."""

    @staticmethod
    def normalize_text(text: str) -> str:
        """Strip redundant whitespace, normalize unicode, and trim boilerplate."""
        if not text:
            return ""
        # Unicode normalization (NFKC decomposes compatibility chars and composes canonicals)
        normalized = unicodedata.normalize("NFKC", text)
        # Collapse repeated spaces/tabs while preserving paragraphs
        lines = [re.sub(r"[ \t]+", " ", line).strip() for line in normalized.splitlines()]
        # Remove repeated empty lines
        compact_lines = []
        for line in lines:
            if line or (compact_lines and compact_lines[-1]):
                compact_lines.append(line)
        return "\n".join(compact_lines).strip()

    @staticmethod
    def compute_fingerprint(text: str) -> str:
        """Produce a deterministic SHA-256 hash of normalized lowercase alphanumeric text."""
        alphanumeric = re.sub(r"[^\w]", "", text.lower())
        return hashlib.sha256(alphanumeric.encode("utf-8")).hexdigest()

    @staticmethod
    def extract_keywords(text: str) -> List[str]:
        """Extract high-signal technical terms, tool names, preferences, and identifiers."""
        # Find backtick code terms, URLs, and capitalized technical nouns
        terms: Set[str] = set()
        for match in re.finditer(r"`([^`]+)`", text):
            terms.add(match.group(1).strip())
        for match in re.finditer(r"\b([A-Z][a-zA-Z0-9_\-\.]{2,})\b", text):
            terms.add(match.group(1).strip())
        return sorted(terms)


# ─── Classifier ───────────────────────────────────────────────────────────────

class MemoryClassifier:
    """Classifies memory candidates into Episodic, Semantic, Procedural, or Working."""

    @staticmethod
    def classify(content: str, default: MemoryType = MemoryType.SEMANTIC) -> MemoryType:
        """Deterministically determine memory classification using pattern heuristics."""
        # 1. Procedural check
        for pat in _PROCEDURAL_PATTERNS:
            if pat.search(content):
                return MemoryType.PROCEDURAL

        # 2. Working memory check
        for pat in _WORKING_PATTERNS:
            if pat.search(content):
                return MemoryType.WORKING

        # 3. Episodic check
        for pat in _EPISODIC_PATTERNS:
            if pat.search(content):
                return MemoryType.EPISODIC

        # 4. Default: Semantic (factual knowledge, preferences, state)
        return default


# ─── Deduplication & Conflict Detection ───────────────────────────────────────

class DeduplicationEngine:
    """Detects exact duplicates and potential conflicting facts across memories."""

    @staticmethod
    def token_set_jaccard(text_a: str, text_b: str) -> float:
        """Calculate word-level Jaccard similarity between two texts."""
        words_a = set(re.findall(r"\w+", text_a.lower()))
        words_b = set(re.findall(r"\w+", text_b.lower()))
        if not words_a or not words_b:
            return 0.0
        intersection = words_a.intersection(words_b)
        union = words_a.union(words_b)
        return len(intersection) / len(union)

    @classmethod
    def check_duplicate(
        cls,
        new_content: str,
        existing_memories: List[Memory],
        similarity_threshold: float = 0.92,
    ) -> Optional[Memory]:
        """Check if an exact or near-identical memory already exists."""
        new_fp = ContentNormalizer.compute_fingerprint(new_content)
        for mem in existing_memories:
            if mem.status != MemoryStatus.ACTIVE:
                continue
            if ContentNormalizer.compute_fingerprint(mem.content) == new_fp:
                return mem
            if cls.token_set_jaccard(new_content, mem.content) >= similarity_threshold:
                return mem
        return None

    @classmethod
    def check_conflict(
        cls,
        new_content: str,
        existing_memories: List[Memory],
        min_containment: float = 0.60,
    ) -> List[Memory]:
        """Detect potentially conflicting or superseding semantic memories.

        Evaluates term containment and Jaccard overlap:
        e.g., "User prefers PostgreSQL" vs "User prefers CockroachDB over PostgreSQL".
        """
        conflicts: List[Memory] = []
        new_words = set(re.findall(r"\w+", new_content.lower()))
        new_fp = ContentNormalizer.compute_fingerprint(new_content)

        for mem in existing_memories:
            if mem.status != MemoryStatus.ACTIVE or mem.memory_type != MemoryType.SEMANTIC:
                continue
            exist_words = set(re.findall(r"\w+", mem.content.lower()))
            if not exist_words:
                continue

            inter = new_words.intersection(exist_words)
            containment = len(inter) / len(exist_words)
            jaccard = len(inter) / len(new_words.union(exist_words))
            exist_fp = ContentNormalizer.compute_fingerprint(mem.content)

            # If high containment of prior topic (>60%) or high Jaccard (>40%) and distinct content:
            if (containment >= min_containment or jaccard >= 0.40) and new_fp != exist_fp:
                conflicts.append(mem)

        return conflicts


# ─── Ingestion Pipeline ───────────────────────────────────────────────────────

@dataclass
class IngestionResult:
    """Outcome of an ingestion operation."""
    memory: Memory
    is_duplicate: bool = False
    action_taken: str = "created"  # created | deduplicated | updated_with_conflict
    conflicts_detected: List[str] = field(default_factory=list)
    relationships_created: List[str] = field(default_factory=list)


class IngestionPipeline:
    """End-to-end memory ingestion processor."""

    def __init__(self, storage: StorageBackend, working_ttl_hours: int = 24) -> None:
        self.storage = storage
        self.working_ttl_hours = working_ttl_hours

    def ingest(
        self,
        raw_content: str,
        owner_id: str,
        agent_id: str = "hermes",
        project_id: Optional[str] = None,
        explicit_type: Optional[MemoryType] = None,
        importance: float = 0.5,
        confidence: float = 1.0,
        source_type: Optional[str] = None,
        source_identifier: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        link_conflicts: bool = True,
    ) -> IngestionResult:
        """Process, normalize, classify, deduplicate, and persist incoming information."""
        # 1. Normalize
        normalized = ContentNormalizer.normalize_text(raw_content)
        if not normalized:
            raise ValueError("Ingestion content cannot be empty after normalization.")

        # 2. Classify
        mem_type = explicit_type or MemoryClassifier.classify(normalized)

        # 3. Handle Working Memory Expiration
        expires_at = None
        if mem_type == MemoryType.WORKING:
            expires_at = (datetime.now(timezone.utc) + timedelta(hours=self.working_ttl_hours)).isoformat()

        # 4. Extract Entity Tags
        keywords = ContentNormalizer.extract_keywords(normalized)
        meta = metadata or {}
        if keywords:
            meta["keywords"] = keywords

        # 5. Fetch existing active memories for owner to check duplicates and conflicts
        existing = self.storage.list_memories(
            owner_id=owner_id,
            project_id=project_id,
            memory_types=[mem_type],
            status=MemoryStatus.ACTIVE,
            limit=50,
        )

        # 6. Deduplication Check
        duplicate = DeduplicationEngine.check_duplicate(normalized, existing)
        if duplicate:
            logger.debug("Deduplicated incoming memory against existing %s", duplicate.id)
            # Touch last_accessed_at and boost importance if re-asserted
            new_importance = min(1.0, duplicate.importance + 0.05)
            updated = self.storage.update_memory(
                memory_id=duplicate.id,
                owner_id=owner_id,
                importance=new_importance,
            )
            return IngestionResult(
                memory=updated or duplicate,
                is_duplicate=True,
                action_taken="deduplicated",
            )

        # 7. Provenance Source Tracking
        source_id = None
        if source_type and source_identifier:
            src = self.storage.record_source(
                MemorySource(
                    source_type=source_type,
                    source_identifier=source_identifier,
                    owner_id=owner_id,
                    agent_id=agent_id,
                )
            )
            source_id = src.id

        # 8. Create Memory Record
        new_mem = Memory(
            owner_id=owner_id,
            agent_id=agent_id,
            project_id=project_id,
            memory_type=mem_type,
            content=normalized,
            normalized_content=normalized,
            importance=importance,
            confidence=confidence,
            source_type=source_type,
            source_id=source_id,
            expires_at=expires_at,
            metadata=meta,
        )
        saved = self.storage.create_memory(new_mem)

        # 9. Conflict Detection & Non-Destructive Linking
        created_rels: List[str] = []
        conflict_ids: List[str] = []

        if link_conflicts and mem_type == MemoryType.SEMANTIC:
            semantic_existing = self.storage.list_memories(
                owner_id=owner_id,
                project_id=project_id,
                memory_types=[MemoryType.SEMANTIC],
                status=MemoryStatus.ACTIVE,
                limit=50,
            )
            # Exclude the newly saved memory
            candidates = [m for m in semantic_existing if m.id != saved.id]
            conflicts = DeduplicationEngine.check_conflict(normalized, candidates)

            for conf in conflicts:
                conflict_ids.append(conf.id)
                # Link conflicting memory with CONTRADICTS / SUPERSEDES edge
                rel = self.storage.create_relationship(
                    MemoryRelationship(
                        source_memory_id=saved.id,
                        target_memory_id=conf.id,
                        relationship_type=RelationshipType.SUPERSEDES,
                        confidence=0.85,
                        metadata={"reason": "newer_claim_supersedes_prior"},
                    ),
                    owner_id=owner_id,
                )
                created_rels.append(rel.id)
                logger.info("Conflict detected between new %s and prior %s; linked with SUPERSEDES", saved.id, conf.id)

        action = "updated_with_conflict" if conflict_ids else "created"
        return IngestionResult(
            memory=saved,
            is_duplicate=False,
            action_taken=action,
            conflicts_detected=conflict_ids,
            relationships_created=created_rels,
        )
