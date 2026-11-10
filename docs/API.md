# ADAPT Developer API Reference

The ADAPT Core API is framework-agnostic. All agent adapters (including Hermes) interact with the memory infrastructure through this consistent interface.

## Core Operations

### 1. `remember`
Persists a new piece of information into memory.
```python
memory = adapt.remember(
    content="User prefers using PostgreSQL for relational data and Redis for cache.",
    memory_type="semantic",  # episodic, semantic, procedural, working
    owner_id="user_123",
    agent_id="hermes_primary",
    project_id="ecommerce_v2",
    importance=0.8,
    confidence=0.95,
    source_type="conversation",
    source_identifier="session_abc:turn_4",
    metadata={"domain": "database", "verified": True}
)
```

### 2. `recall`
Performs context-aware hybrid retrieval matching the agent's current task or query.
```python
results = adapt.recall(
    query="What database should we use for caching?",
    owner_id="user_123",
    agent_id="hermes_primary",
    project_id="ecommerce_v2",
    limit=5,
    memory_types=["semantic", "procedural"],
    include_related=True
)
# Returns List[ScoredMemory] ranked by hybrid relevance
```

### 3. `search`
Direct keyword and metadata search over memory store.
```python
memories = adapt.search(
    query="PostgreSQL",
    owner_id="user_123",
    memory_types=["semantic"],
    limit=10
)
```

### 4. `get_memory` & `update_memory`
Retrieves or updates an existing memory with full version provenance.
```python
memory = adapt.get_memory(memory_id="mem_xyz", owner_id="user_123")

updated = adapt.update_memory(
    memory_id="mem_xyz",
    new_content="User migrated cache from Redis to Dragonfly.",
    change_reason="User switched stack in session_def",
    owner_id="user_123"
)
# Automatically archives previous version in memory_versions table
```

### 5. `forget` & `archive`
Safe soft-deletion or explicit archiving.
```python
# Soft delete (status = 'deleted', excluded from search & recall)
adapt.forget(memory_id="mem_xyz", owner_id="user_123", permanent=False)

# Archive (status = 'archived')
adapt.archive(memory_id="mem_xyz", owner_id="user_123")
```

### 6. `relate` & `get_related`
Creates and traverses typed knowledge graph edges between memories.
```python
# Relate memories
rel = adapt.relate(
    source_memory_id="mem_1",
    target_memory_id="mem_2",
    relationship_type="SUPERSEDES",  # RELATES_TO, CONTRADICTS, SUPERSEDES, DEPENDS_ON
    confidence=0.9,
    owner_id="user_123"
)

# Traverse connected memories
connected = adapt.get_related(
    memory_id="mem_1",
    relationship_type=None,  # None = any relationship
    max_depth=2,
    owner_id="user_123"
)
```

### 7. `consolidate`
Runs maintenance jobs: deduplication, conflict resolution, working memory TTL eviction, and recency adjustments.
```python
report = adapt.consolidate(
    owner_id="user_123",
    agent_id="hermes_primary"
)
# Returns ConsolidationReport(duplicates_merged=..., expired_pruned=..., conflicts_flagged=...)
```

### 8. `get_stats`
Provides aggregated telemetry on memory counts, types, storage usage, and active sessions.
```python
stats = adapt.get_stats(owner_id="user_123")
```
