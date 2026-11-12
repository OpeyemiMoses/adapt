"""SQLite and FTS5 storage backend implementation for ADAPT."""

from __future__ import annotations

import json
import logging
import os
import re
import sqlite3
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

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
    new_id,
    utc_now_iso,
)
from adapt.storage.base import StorageBackend

logger = logging.getLogger(__name__)


def _sanitize_fts5_query(query: str) -> str:
    """Sanitize user input for safe SQLite FTS5 MATCH queries.

    Cleans punctuation and joins terms with OR and prefix wildcards so that
    multi-term queries match resiliently while BM25 ranks higher-frequency matches first.
    """
    clean = re.sub(r'[^\w\s]', ' ', query)
    tokens = clean.strip().split()
    if not tokens:
        return '""'
    clauses = []
    for token in tokens:
        if len(token) >= 2:
            clauses.append(f'"{token}"*')
        else:
            clauses.append(f'"{token}"')
    return " OR ".join(clauses)


class SQLiteStorage(StorageBackend):
    """Local-first SQLite persistence engine with FTS5 lexical indexing.

    Thread-safe via thread-local connections and WAL mode.
    """

    def __init__(self, db_path: str = ":memory:", migration_dir: Optional[str] = None) -> None:
        if db_path != ":memory:":
            self.db_path = str(Path(os.path.expanduser(db_path)).resolve())
            Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        else:
            self.db_path = ":memory:"

        self._migration_dir = migration_dir
        self._local = threading.local()
        self._lock = threading.Lock()
        self._closed = False

    def _get_connection(self) -> sqlite3.Connection:
        """Retrieve or create thread-local connection."""
        if self._closed:
            raise RuntimeError("SQLiteStorage is closed.")

        if not hasattr(self._local, "conn") or self._local.conn is None:
            conn = sqlite3.connect(
                self.db_path,
                timeout=30.0,
                check_same_thread=False,
                isolation_level=None,  # Autocommit mode; explicit transactions used where needed
            )
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys = ON;")
            if self.db_path != ":memory:":
                conn.execute("PRAGMA journal_mode = WAL;")
                conn.execute("PRAGMA busy_timeout = 30000;")
            self._local.conn = conn
        return self._local.conn

    def initialize(self) -> None:
        """Run database migrations and verify FTS5 virtual table."""
        conn = self._get_connection()
        migration_sql = self._load_migration_sql()
        with conn:
            conn.executescript(migration_sql)
        logger.debug("SQLiteStorage initialized successfully at %s", self.db_path)

    def _load_migration_sql(self) -> str:
        """Load migration SQL script from disk."""
        if self._migration_dir:
            sql_file = Path(self._migration_dir) / "001_initial_schema.sql"
        else:
            # Default to migrations sibling directory
            sql_file = Path(__file__).resolve().parent.parent.parent / "migrations" / "001_initial_schema.sql"

        if sql_file.exists():
            return sql_file.read_text(encoding="utf-8")

        raise FileNotFoundError(f"Migration script not found at {sql_file}")

    def close(self) -> None:
        """Close connections on current thread."""
        self._closed = True
        if hasattr(self._local, "conn") and self._local.conn is not None:
            try:
                self._local.conn.close()
            except Exception:
                pass
            self._local.conn = None

    # -- Memory CRUD ---------------------------------------------------------

    def create_memory(self, memory: Memory) -> Memory:
        conn = self._get_connection()
        now = utc_now_iso()
        memory.created_at = memory.created_at or now
        memory.updated_at = now
        memory.last_accessed_at = now

        meta_json = json.dumps(memory.metadata or {})
        type_str = memory.memory_type.value if isinstance(memory.memory_type, MemoryType) else str(memory.memory_type)
        status_str = memory.status.value if isinstance(memory.status, MemoryStatus) else str(memory.status)

        query = """
        INSERT INTO memories (
            id, owner_id, agent_id, project_id, memory_type, content,
            normalized_content, importance, confidence, source_type, source_id,
            created_at, updated_at, last_accessed_at, expires_at, status, metadata
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """
        with conn:
            conn.execute(
                query,
                (
                    memory.id,
                    memory.owner_id,
                    memory.agent_id,
                    memory.project_id,
                    type_str,
                    memory.content,
                    memory.normalized_content or memory.content,
                    memory.importance,
                    memory.confidence,
                    memory.source_type,
                    memory.source_id,
                    memory.created_at,
                    memory.updated_at,
                    memory.last_accessed_at,
                    memory.expires_at,
                    status_str,
                    meta_json,
                ),
            )
        return memory

    def get_memory(self, memory_id: str, owner_id: str) -> Optional[Memory]:
        conn = self._get_connection()
        now = utc_now_iso()
        query = "SELECT * FROM memories WHERE id = ? AND owner_id = ? AND status != 'deleted';"
        row = conn.execute(query, (memory_id, owner_id)).fetchone()
        if not row:
            return None

        # Touch last_accessed_at
        with conn:
            conn.execute("UPDATE memories SET last_accessed_at = ? WHERE id = ?;", (now, memory_id))

        mem_dict = dict(row)
        mem_dict["last_accessed_at"] = now
        return Memory.from_row(mem_dict)

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
        conn = self._get_connection()
        current = self.get_memory(memory_id, owner_id)
        if not current:
            return None

        now = utc_now_iso()

        # If content has changed, record historical audit version
        if new_content is not None and new_content != current.content:
            version_id = new_id("ver")
            ver_query = """
            INSERT INTO memory_versions (id, memory_id, previous_content, new_content, change_reason, source_id, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?);
            """
            with conn:
                conn.execute(
                    ver_query,
                    (version_id, memory_id, current.content, new_content, change_reason, source_id, now),
                )
            current.content = new_content
            current.normalized_content = new_content

        if importance is not None:
            current.importance = max(0.0, min(1.0, float(importance)))
        if confidence is not None:
            current.confidence = max(0.0, min(1.0, float(confidence)))
        if metadata is not None:
            current.metadata = {**current.metadata, **metadata}

        current.updated_at = now
        meta_json = json.dumps(current.metadata)

        update_query = """
        UPDATE memories SET
            content = ?, normalized_content = ?, importance = ?, confidence = ?,
            metadata = ?, updated_at = ?
        WHERE id = ? AND owner_id = ?;
        """
        with conn:
            conn.execute(
                update_query,
                (
                    current.content,
                    current.normalized_content,
                    current.importance,
                    current.confidence,
                    meta_json,
                    current.updated_at,
                    memory_id,
                    owner_id,
                ),
            )
        return current

    def delete_memory(self, memory_id: str, owner_id: str, permanent: bool = False) -> bool:
        conn = self._get_connection()
        # Verify ownership
        current = conn.execute(
            "SELECT id FROM memories WHERE id = ? AND owner_id = ?;", (memory_id, owner_id)
        ).fetchone()
        if not current:
            return False

        with conn:
            if permanent:
                conn.execute("DELETE FROM memories WHERE id = ? AND owner_id = ?;", (memory_id, owner_id))
            else:
                conn.execute(
                    "UPDATE memories SET status = 'deleted', updated_at = ? WHERE id = ? AND owner_id = ?;",
                    (utc_now_iso(), memory_id, owner_id),
                )
        return True

    def archive_memory(self, memory_id: str, owner_id: str) -> bool:
        conn = self._get_connection()
        with conn:
            cur = conn.execute(
                "UPDATE memories SET status = 'archived', updated_at = ? WHERE id = ? AND owner_id = ? AND status = 'active';",
                (utc_now_iso(), memory_id, owner_id),
            )
            return cur.rowcount > 0

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
        conn = self._get_connection()
        clauses = ["owner_id = ?"]
        params: List[Any] = [owner_id]

        if agent_id:
            clauses.append("agent_id = ?")
            params.append(agent_id)

        if project_id:
            clauses.append("project_id = ?")
            params.append(project_id)

        if memory_types:
            placeholders = ",".join("?" for _ in memory_types)
            clauses.append(f"memory_type IN ({placeholders})")
            params.extend(t.value if isinstance(t, MemoryType) else str(t) for t in memory_types)

        if status:
            clauses.append("status = ?")
            params.append(status.value if isinstance(status, MemoryStatus) else str(status))
        else:
            clauses.append("status != 'deleted'")

        params.extend([limit, offset])
        query = f"""
        SELECT * FROM memories
        WHERE {' AND '.join(clauses)}
        ORDER BY created_at DESC
        LIMIT ? OFFSET ?;
        """
        rows = conn.execute(query, params).fetchall()
        return [Memory.from_row(dict(r)) for r in rows]

    # -- Retrieval Operations ------------------------------------------------

    def search_lexical(
        self,
        query: str,
        owner_id: str,
        agent_id: Optional[str] = None,
        memory_types: Optional[List[MemoryType]] = None,
        project_id: Optional[str] = None,
        limit: int = 20,
    ) -> List[Tuple[Memory, float]]:
        conn = self._get_connection()
        sanitized = _sanitize_fts5_query(query)
        if not sanitized or sanitized == '""':
            return []

        clauses = ["m.owner_id = ?", "m.status = 'active'"]
        params: List[Any] = [sanitized, owner_id]

        if agent_id:
            clauses.append("m.agent_id = ?")
            params.append(agent_id)

        if project_id:
            clauses.append("m.project_id = ?")
            params.append(project_id)

        if memory_types:
            placeholders = ",".join("?" for _ in memory_types)
            clauses.append(f"m.memory_type IN ({placeholders})")
            params.extend(t.value if isinstance(t, MemoryType) else str(t) for t in memory_types)

        params.append(limit)

        sql = f"""
        SELECT m.*, bm25(memories_fts) as rank
        FROM memories m
        JOIN memories_fts f ON m.rowid = f.rowid
        WHERE memories_fts MATCH ? AND {' AND '.join(clauses)}
        ORDER BY rank ASC
        LIMIT ?;
        """
        try:
            rows = conn.execute(sql, params).fetchall()
        except sqlite3.OperationalError as exc:
            logger.debug("FTS5 query failed (%s), falling back to LIKE: %s", sanitized, exc)
            return self._fallback_like_search(query, owner_id, agent_id, memory_types, project_id, limit)

        results: List[Tuple[Memory, float]] = []
        for r in rows:
            row_dict = dict(r)
            # SQLite bm25 returns negative values where lower is more relevant (e.g. -5.2)
            raw_rank = float(row_dict.pop("rank", 0.0))
            score = 1.0 / (1.0 + abs(raw_rank))
            results.append((Memory.from_row(row_dict), score))
        return results

    def _fallback_like_search(
        self,
        query: str,
        owner_id: str,
        agent_id: Optional[str] = None,
        memory_types: Optional[List[MemoryType]] = None,
        project_id: Optional[str] = None,
        limit: int = 20,
    ) -> List[Tuple[Memory, float]]:
        """Fallback to standard SQL LIKE matching when FTS5 syntax fails."""
        conn = self._get_connection()
        like_pat = f"%{query.strip()}%"
        clauses = ["owner_id = ?", "status = 'active'", "(content LIKE ? OR metadata LIKE ?)"]
        params: List[Any] = [owner_id, like_pat, like_pat]

        if agent_id:
            clauses.append("agent_id = ?")
            params.append(agent_id)

        if project_id:
            clauses.append("project_id = ?")
            params.append(project_id)

        if memory_types:
            placeholders = ",".join("?" for _ in memory_types)
            clauses.append(f"memory_type IN ({placeholders})")
            params.extend(t.value if isinstance(t, MemoryType) else str(t) for t in memory_types)

        params.append(limit)
        sql = f"""
        SELECT * FROM memories
        WHERE {' AND '.join(clauses)}
        ORDER BY created_at DESC
        LIMIT ?;
        """
        rows = conn.execute(sql, params).fetchall()
        return [(Memory.from_row(dict(r)), 0.5) for r in rows]

    # -- Associative Relationships -------------------------------------------

    def create_relationship(self, relationship: MemoryRelationship, owner_id: str) -> MemoryRelationship:
        conn = self._get_connection()
        # Verify both memories belong to owner
        check_sql = "SELECT COUNT(*) FROM memories WHERE id IN (?, ?) AND owner_id = ? AND status != 'deleted';"
        count = conn.execute(
            check_sql, (relationship.source_memory_id, relationship.target_memory_id, owner_id)
        ).fetchone()[0]
        if count < 2:
            raise ValueError("Both source and target memories must exist and belong to the same owner.")

        now = utc_now_iso()
        relationship.created_at = relationship.created_at or now
        type_str = (
            relationship.relationship_type.value
            if isinstance(relationship.relationship_type, RelationshipType)
            else str(relationship.relationship_type)
        )
        meta_json = json.dumps(relationship.metadata or {})

        sql = """
        INSERT INTO memory_relationships (id, source_memory_id, target_memory_id, relationship_type, confidence, metadata, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?);
        """
        with conn:
            conn.execute(
                sql,
                (
                    relationship.id,
                    relationship.source_memory_id,
                    relationship.target_memory_id,
                    type_str,
                    relationship.confidence,
                    meta_json,
                    relationship.created_at,
                ),
            )
        return relationship

    def get_relationships(
        self, memory_id: str, relationship_type: Optional[RelationshipType] = None
    ) -> List[MemoryRelationship]:
        conn = self._get_connection()
        clauses = ["(source_memory_id = ? OR target_memory_id = ?)"]
        params: List[Any] = [memory_id, memory_id]

        if relationship_type:
            clauses.append("relationship_type = ?")
            params.append(
                relationship_type.value
                if isinstance(relationship_type, RelationshipType)
                else str(relationship_type)
            )

        sql = f"SELECT * FROM memory_relationships WHERE {' AND '.join(clauses)} ORDER BY created_at DESC;"
        rows = conn.execute(sql, params).fetchall()
        return [MemoryRelationship.from_row(dict(r)) for r in rows]

    def get_related_memories(
        self,
        memory_id: str,
        owner_id: str,
        relationship_type: Optional[RelationshipType] = None,
        max_depth: int = 1,
    ) -> List[Memory]:
        conn = self._get_connection()
        visited: Set[str] = {memory_id}
        current_layer: Set[str] = {memory_id}
        result_memories: List[Memory] = []

        type_filter = ""
        type_param: List[Any] = []
        if relationship_type:
            type_filter = "AND relationship_type = ?"
            type_param = [
                relationship_type.value
                if isinstance(relationship_type, RelationshipType)
                else str(relationship_type)
            ]

        for _ in range(max(1, min(max_depth, 3))):
            if not current_layer:
                break
            placeholders = ",".join("?" for _ in current_layer)
            sql = f"""
            SELECT target_memory_id as neighbor_id FROM memory_relationships
            WHERE source_memory_id IN ({placeholders}) {type_filter}
            UNION
            SELECT source_memory_id as neighbor_id FROM memory_relationships
            WHERE target_memory_id IN ({placeholders}) {type_filter};
            """
            params = list(current_layer) + type_param + list(current_layer) + type_param
            rows = conn.execute(sql, params).fetchall()

            next_layer: Set[str] = set()
            for r in rows:
                nid = r["neighbor_id"]
                if nid not in visited:
                    visited.add(nid)
                    next_layer.add(nid)

            if next_layer:
                m_placeholders = ",".join("?" for _ in next_layer)
                mem_sql = f"""
                SELECT * FROM memories
                WHERE id IN ({m_placeholders}) AND owner_id = ? AND status = 'active';
                """
                mem_rows = conn.execute(mem_sql, list(next_layer) + [owner_id]).fetchall()
                for mr in mem_rows:
                    result_memories.append(Memory.from_row(dict(mr)))

            current_layer = next_layer

        return result_memories

    # -- Provenance & Auditing -----------------------------------------------

    def record_source(self, source: MemorySource) -> MemorySource:
        conn = self._get_connection()
        now = utc_now_iso()
        source.created_at = source.created_at or now
        meta_json = json.dumps(source.metadata or {})

        sql = """
        INSERT INTO memory_sources (id, source_type, source_identifier, owner_id, agent_id, created_at, metadata)
        VALUES (?, ?, ?, ?, ?, ?, ?);
        """
        with conn:
            conn.execute(
                sql,
                (
                    source.id,
                    source.source_type,
                    source.source_identifier,
                    source.owner_id,
                    source.agent_id,
                    source.created_at,
                    meta_json,
                ),
            )
        return source

    def get_versions(self, memory_id: str) -> List[MemoryVersion]:
        conn = self._get_connection()
        sql = "SELECT * FROM memory_versions WHERE memory_id = ? ORDER BY created_at ASC;"
        rows = conn.execute(sql, (memory_id,)).fetchall()
        return [
            MemoryVersion(
                id=r["id"],
                memory_id=r["memory_id"],
                previous_content=r["previous_content"],
                new_content=r["new_content"],
                change_reason=r["change_reason"],
                source_id=r["source_id"],
                created_at=r["created_at"],
            )
            for r in rows
        ]

    # -- Maintenance & Jobs --------------------------------------------------

    def create_job(self, job: MemoryJob) -> MemoryJob:
        conn = self._get_connection()
        now = utc_now_iso()
        job.created_at = job.created_at or now
        res_json = json.dumps(job.result) if job.result else None
        status_str = job.status.value if isinstance(job.status, JobStatus) else str(job.status)

        sql = """
        INSERT INTO memory_jobs (id, job_type, status, input_reference, result, error, created_at, completed_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?);
        """
        with conn:
            conn.execute(
                sql,
                (
                    job.id,
                    job.job_type,
                    status_str,
                    job.input_reference,
                    res_json,
                    job.error,
                    job.created_at,
                    job.completed_at,
                ),
            )
        return job

    def update_job(
        self,
        job_id: str,
        status: JobStatus,
        result: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
    ) -> Optional[MemoryJob]:
        conn = self._get_connection()
        now = utc_now_iso()
        res_json = json.dumps(result) if result else None
        status_str = status.value if isinstance(status, JobStatus) else str(status)

        sql = """
        UPDATE memory_jobs SET
            status = ?, result = ?, error = ?, completed_at = ?
        WHERE id = ?;
        """
        with conn:
            conn.execute(sql, (status_str, res_json, error, now if status in (JobStatus.COMPLETED, JobStatus.FAILED) else None, job_id))

        row = conn.execute("SELECT * FROM memory_jobs WHERE id = ?;", (job_id,)).fetchone()
        if not row:
            return None
        r = dict(row)
        res = json.loads(r["result"]) if r.get("result") else None
        return MemoryJob(
            id=r["id"],
            job_type=r["job_type"],
            status=JobStatus(r["status"]),
            input_reference=r["input_reference"],
            result=res,
            error=r["error"],
            created_at=r["created_at"],
            completed_at=r["completed_at"],
        )

    def archive_expired_working_memories(self, owner_id: str) -> int:
        conn = self._get_connection()
        now = utc_now_iso()
        sql = """
        UPDATE memories SET status = 'archived', updated_at = ?
        WHERE owner_id = ? AND memory_type = 'working' AND status = 'active'
          AND expires_at IS NOT NULL AND expires_at < ?;
        """
        with conn:
            cur = conn.execute(sql, (now, owner_id, now))
            return cur.rowcount

    def get_stats(self, owner_id: str, agent_id: Optional[str] = None) -> Dict[str, Any]:
        conn = self._get_connection()
        params: List[Any] = [owner_id]
        agent_clause = ""
        if agent_id:
            agent_clause = "AND agent_id = ?"
            params.append(agent_id)

        # Total memories and counts by type
        sql_types = f"""
        SELECT memory_type, status, COUNT(*) as cnt
        FROM memories
        WHERE owner_id = ? {agent_clause}
        GROUP BY memory_type, status;
        """
        rows = conn.execute(sql_types, params).fetchall()

        by_type: Dict[str, int] = {t.value: 0 for t in MemoryType}
        by_status: Dict[str, int] = {s.value: 0 for s in MemoryStatus}
        total = 0

        for r in rows:
            mtype = r["memory_type"]
            mstatus = r["status"]
            cnt = r["cnt"]
            total += cnt
            by_type[mtype] = by_type.get(mtype, 0) + cnt
            by_status[mstatus] = by_status.get(mstatus, 0) + cnt

        # Relationship count
        rel_sql = """
        SELECT COUNT(*) FROM memory_relationships r
        JOIN memories m ON r.source_memory_id = m.id
        WHERE m.owner_id = ?;
        """
        rel_count = conn.execute(rel_sql, (owner_id,)).fetchone()[0]

        # Version count
        ver_sql = """
        SELECT COUNT(*) FROM memory_versions v
        JOIN memories m ON v.memory_id = m.id
        WHERE m.owner_id = ?;
        """
        ver_count = conn.execute(ver_sql, (owner_id,)).fetchone()[0]

        return {
            "owner_id": owner_id,
            "total_memories": total,
            "active_memories": by_status.get(MemoryStatus.ACTIVE.value, 0),
            "archived_memories": by_status.get(MemoryStatus.ARCHIVED.value, 0),
            "deleted_memories": by_status.get(MemoryStatus.DELETED.value, 0),
            "by_type": by_type,
            "relationships_count": rel_count,
            "versions_count": ver_count,
        }
