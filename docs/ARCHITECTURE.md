# ADAPT Architecture & Design Specification

## 1. System Overview
ADAPT is a persistent, framework-independent memory infrastructure layer for autonomous AI agents. It transforms unstructured interactions and task executions into structured, connected, evolving, and contextual knowledge.

### Core Principle
> **Agents should not have to start from zero every time they wake up.**

```
+-----------------------------------------------------------------------------------+
|                                 Agent Framework                                   |
|                          (Hermes Agent / Custom Agent)                            |
+-----------------------------------------+-----------------------------------------+
                                          | Lifecycle Hooks / Tool Calls / Prefetch
                                          v
+-----------------------------------------------------------------------------------+
|                   Integration Layer (integrations/hermes/provider.py)             |
+-----------------------------------------+-----------------------------------------+
                                          |
                                          v
+-----------------------------------------------------------------------------------+
|                                   ADAPT CORE                                      |
|                                                                                   |
|  +--------------------+   +---------------------+   +--------------------------+  |
|  |  Ingestion Engine  |   |  Retrieval Engine   |   |   Consolidation Engine   |  |
|  |  - Normalizer      |   |  - FTS5 Keyword     |   |   - Deduplication        |  |
|  |  - Classifier      |   |  - Semantic Vector  |   |   - Contradiction Detect |  |
|  |  - Conflict Check  |   |  - Hybrid Ranker    |   |   - Version Audit        |  |
|  |  - Extractor       |   |  - Recency Decay    |   |   - Working Memory TTL   |  |
|  +---------+----------+   +----------+----------+   +------------+-------------+  |
|            |                         |                           |                |
|            +-------------------------+---------------------------+                |
|                                      |                                            |
|                                      v                                            |
|  +-----------------------------------------------------------------------------+  |
|  |                          Associative Graph Engine                           |  |
|  |      - Typed Edges (RELATES_TO, CONTRADICTS, SUPERSEDES, DEPENDS_ON)        |  |
|  +-----------------------------------+-----------------------------------------+  |
|                                      |                                            |
|  +-----------------------------------+-----------------------------------------+  |
|  |                      Pluggable Storage Layer (SQLite)                       |  |
|  |      - FTS5 Full-Text Index        - Relational Schema                      |  |
|  |      - Audit Versions Table        - Strict Multi-Tenant Isolation          |  |
|  +-----------------------------------------------------------------------------+  |
+-----------------------------------------------------------------------------------+
```

---

## 2. Core Memory Taxonomy

| Memory Type | Purpose | Mutability | Examples |
| :--- | :--- | :--- | :--- |
| **Episodic** | Records experiences, past events, task completions, and decisions with timestamps | Append-heavy with provenance | "User instructed to research project X at 14:00"; "Agent deployed v1.0.1 successfully" |
| **Semantic** | Stores durable facts, knowledge, user preferences, and system architecture | Evolves / Updates with versioning | "User prefers TypeScript over JavaScript"; "Database is PostgreSQL 16" |
| **Procedural** | Stores reusable workflows, step-by-step procedures, and execution runbooks | Validated vs Suggested flags | "Run `docker compose up -d` before starting tests"; "Release checklist" |
| **Working** | Ephemeral context, active task objectives, subtask scratchpad | Time-to-Live (TTL), session-scoped | "Currently processing subtask 2 of 5: generating API models" |

---

## 3. Core Engine Components

### 3.1 Ingestion Engine
1. **Source & Identity Attribution**: Every incoming record carries `owner_id`, `agent_id`, `session_id`, and `source_type`.
2. **Classification**: Automatically classifies input into Episodic, Semantic, Procedural, or Working memory.
3. **Normalization**: Trims noise, normalizes unicode, extracts key entity tags.
4. **Duplicate & Conflict Detection**: Identifies identical facts (avoiding duplicate writes) or contradicting facts.
5. **Non-destructive Conflict Handling**: When a new fact conflicts with an existing one, the old fact is not silently erased. Provenance is maintained, the relationship `CONTRADICTS` or `SUPERSEDES` is recorded, and the conflicting claims remain inspectable.

### 3.2 Storage Engine
- **Local-First SQLite Backend**: Lightweight, zero-external-dependency local storage.
- **SQLite FTS5**: Native BM25 full-text keyword indexing across memory content and metadata.
- **Relational Tables**:
  - `memories`: Core memory records.
  - `memory_relationships`: Typed knowledge graph edges.
  - `memory_sources`: Provenance tracking.
  - `memory_versions`: Immutable audit trail for evolving facts.
  - `memory_jobs`: Asynchronous/batch consolidation job status.
  - `agents`: Registered agents and their configuration.

### 3.3 Pluggable Embedding Engine
- `EmbeddingProvider` interface defining `embed_query(text)` and `embed_documents(texts)`.
- Default: `DeterministicHashEmbeddingProvider` provides zero-dependency offline feature-hash vector embeddings.
- Fallback: `NoOpEmbeddingProvider` provides pure FTS5 BM25 search without errors.
- Optional: `RemoteEmbeddingProvider` for OpenAI-compatible REST endpoints.

### 3.4 Hybrid Retrieval Engine
Combines:
- **Lexical Score ($S_{lex}$)** from SQLite FTS5 BM25.
- **Semantic Score ($S_{sem}$)** from vector cosine similarity.
- **Recency Decay ($S_{rec}$)**: Exponential decay based on `last_accessed_at` / `created_at`.
- **Importance Weight ($W_{imp}$)**: Memory importance coefficient (0.0 to 1.0).
- **Proximity Boost ($S_{graph}$)**: Boost for memories connected via associative graph relationships to already-recalled nodes.

$$Score = ( \alpha \cdot S_{sem} + (1 - \alpha) \cdot S_{lex} ) \times W_{imp} \times S_{rec}$$

### 3.5 Associative Memory & Knowledge Graph
- Typed edges: `RELATES_TO`, `SUPERSEDES`, `CONTRADICTS`, `DERIVED_FROM`, `PART_OF`, `DEPENDS_ON`.
- Graph traversal queries: Retrieve memories 1 or $N$ hops away from seed memories.

### 3.6 Memory Evolution & Consolidation
- Scheduled or session-end maintenance jobs.
- Deduplication of near-identical episodic records.
- Pruning/Archival of expired Working Memory past its TTL.
- Importance recalculation based on access frequency.
