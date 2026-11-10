-- ADAPT Initial Schema Migration 001
-- Enables WAL mode and foreign keys for durability and relational integrity
PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

-- 1. Core Memories Table
CREATE TABLE IF NOT EXISTS memories (
    id TEXT PRIMARY KEY,
    owner_id TEXT NOT NULL,
    agent_id TEXT NOT NULL,
    project_id TEXT,
    memory_type TEXT NOT NULL CHECK(memory_type IN ('episodic', 'semantic', 'procedural', 'working')),
    content TEXT NOT NULL,
    normalized_content TEXT,
    importance REAL NOT NULL DEFAULT 0.5 CHECK(importance >= 0.0 AND importance <= 1.0),
    confidence REAL NOT NULL DEFAULT 1.0 CHECK(confidence >= 0.0 AND confidence <= 1.0),
    source_type TEXT,
    source_id TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    last_accessed_at TEXT,
    expires_at TEXT,
    status TEXT NOT NULL DEFAULT 'active' CHECK(status IN ('active', 'archived', 'deleted')),
    metadata TEXT NOT NULL DEFAULT '{}'
);

-- Indexes for efficient tenant isolation and scoped retrieval
CREATE INDEX IF NOT EXISTS idx_memories_owner ON memories(owner_id);
CREATE INDEX IF NOT EXISTS idx_memories_owner_agent ON memories(owner_id, agent_id);
CREATE INDEX IF NOT EXISTS idx_memories_type ON memories(memory_type);
CREATE INDEX IF NOT EXISTS idx_memories_status ON memories(status);
CREATE INDEX IF NOT EXISTS idx_memories_project ON memories(owner_id, project_id);
CREATE INDEX IF NOT EXISTS idx_memories_expiry ON memories(expires_at) WHERE expires_at IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_memories_created ON memories(created_at);

-- 2. Full-Text Search (FTS5) Table for BM25 Lexical Retrieval
CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts USING fts5(
    id UNINDEXED,
    content,
    normalized_content,
    metadata,
    content='memories',
    content_rowid='rowid'
);

-- Triggers to automatically sync memories into memories_fts
CREATE TRIGGER IF NOT EXISTS trg_memories_ai AFTER INSERT ON memories BEGIN
    INSERT INTO memories_fts(rowid, id, content, normalized_content, metadata)
    VALUES (new.rowid, new.id, new.content, new.normalized_content, new.metadata);
END;

CREATE TRIGGER IF NOT EXISTS trg_memories_ad AFTER DELETE ON memories BEGIN
    INSERT INTO memories_fts(memories_fts, rowid, id, content, normalized_content, metadata)
    VALUES ('delete', old.rowid, old.id, old.content, old.normalized_content, old.metadata);
END;

CREATE TRIGGER IF NOT EXISTS trg_memories_au AFTER UPDATE ON memories BEGIN
    INSERT INTO memories_fts(memories_fts, rowid, id, content, normalized_content, metadata)
    VALUES ('delete', old.rowid, old.id, old.content, old.normalized_content, old.metadata);
    INSERT INTO memories_fts(rowid, id, content, normalized_content, metadata)
    VALUES (new.rowid, new.id, new.content, new.normalized_content, new.metadata);
END;

-- 3. Memory Relationships (Associative Knowledge Graph)
CREATE TABLE IF NOT EXISTS memory_relationships (
    id TEXT PRIMARY KEY,
    source_memory_id TEXT NOT NULL REFERENCES memories(id) ON DELETE CASCADE,
    target_memory_id TEXT NOT NULL REFERENCES memories(id) ON DELETE CASCADE,
    relationship_type TEXT NOT NULL CHECK(relationship_type IN (
        'RELATES_TO', 'CONTRADICTS', 'SUPERSEDES', 'DERIVED_FROM', 'PART_OF', 'DEPENDS_ON'
    )),
    confidence REAL NOT NULL DEFAULT 1.0 CHECK(confidence >= 0.0 AND confidence <= 1.0),
    metadata TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_rel_source ON memory_relationships(source_memory_id);
CREATE INDEX IF NOT EXISTS idx_rel_target ON memory_relationships(target_memory_id);
CREATE INDEX IF NOT EXISTS idx_rel_type ON memory_relationships(relationship_type);

-- 4. Memory Sources (Provenance Tracking)
CREATE TABLE IF NOT EXISTS memory_sources (
    id TEXT PRIMARY KEY,
    source_type TEXT NOT NULL,
    source_identifier TEXT NOT NULL,
    owner_id TEXT NOT NULL,
    agent_id TEXT NOT NULL,
    created_at TEXT NOT NULL,
    metadata TEXT NOT NULL DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS idx_sources_owner ON memory_sources(owner_id);
CREATE INDEX IF NOT EXISTS idx_sources_ident ON memory_sources(source_identifier);

-- 5. Memory Versions (Audit Trail for Evolving Facts)
CREATE TABLE IF NOT EXISTS memory_versions (
    id TEXT PRIMARY KEY,
    memory_id TEXT NOT NULL REFERENCES memories(id) ON DELETE CASCADE,
    previous_content TEXT NOT NULL,
    new_content TEXT NOT NULL,
    change_reason TEXT,
    source_id TEXT,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_versions_mem ON memory_versions(memory_id);

-- 6. Agents Registry
CREATE TABLE IF NOT EXISTS agents (
    id TEXT PRIMARY KEY,
    owner_id TEXT NOT NULL,
    name TEXT NOT NULL,
    framework TEXT NOT NULL DEFAULT 'hermes',
    configuration TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_agents_owner ON agents(owner_id);

-- 7. Memory Maintenance Jobs
CREATE TABLE IF NOT EXISTS memory_jobs (
    id TEXT PRIMARY KEY,
    job_type TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending', 'running', 'completed', 'failed')),
    input_reference TEXT,
    result TEXT,
    error TEXT,
    created_at TEXT NOT NULL,
    completed_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_jobs_status ON memory_jobs(status);
