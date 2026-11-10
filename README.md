# ADAPT
## Persistent Memory Infrastructure for AI Agents

**Tagline:** Build once. Remember continuously.

**ADAPT** is a local-first, cloud-ready memory infrastructure layer that helps AI agents retain, organize, retrieve, connect, and evolve knowledge across conversations, sessions, tasks, and time.

Agents should not have to start from zero every time they wake up. ADAPT gives them continuity.

> **Core idea:** Turn interactions into structured, connected, reusable knowledge, then retrieve the right context when an agent needs it.

---

## Table of Contents

- [The Problem](#the-problem)
- [What ADAPT Does](#what-adapt-does)
- [Core Capabilities](#core-capabilities)
- [Memory Types](#memory-types)
- [Architecture](#architecture)
- [Hermes Integration](#hermes-integration)
- [Security and Privacy](#security-and-privacy)
- [MVP Scope](#mvp-scope)
- [Repository Structure](#repository-structure)
- [Development Principles](#development-principles)
- [Testing and Acceptance Criteria](#testing-and-acceptance-criteria)
- [Roadmap](#roadmap)
- [Official Developer Resources](#official-developer-resources)

---

## The Problem

AI agents increasingly work across multiple sessions and long-running tasks, but useful context is easily lost when conversations end, context windows are compressed, or agents restart.

Common problems include:

- **Context loss:** Important information disappears between sessions.
- **Fragmented knowledge:** Decisions, facts, and experiences remain scattered across conversations.
- **Weak retrieval:** Similarity search alone does not always identify what matters to the current task.
- **Duplicate memories:** The same information is repeatedly stored.
- **Stale information:** Outdated facts remain active after circumstances change.
- **Poor continuity:** Users must repeatedly explain projects, preferences, and previous decisions.

ADAPT addresses these problems with a dedicated memory infrastructure that turns interactions into persistent, structured, searchable, and connected knowledge.

## What ADAPT Does

ADAPT is not a conversation-history dump or a thin wrapper around a vector database.

It is a memory system designed to:

1. Identify information worth retaining.
2. Classify and structure memories.
3. Preserve source and ownership information.
4. Connect related memories.
5. Retrieve relevant knowledge for the current task.
6. Detect duplicates and conflicting information.
7. Update knowledge while preserving its history.
8. Give users and agents controlled ways to inspect and manage memory.

ADAPT is framework-independent at its core. **Hermes Agent is the first native integration.**

## Core Capabilities

### Persistent memory
Store useful information beyond the lifetime of an individual conversation or process.

### Intelligent ingestion
Convert incoming interactions and agent observations into structured memory candidates. Ingestion should be configurable; not every message should become permanent memory.

### Contextual retrieval
Retrieve a bounded set of relevant memories using hybrid search: lexical matching, semantic similarity, metadata filters, recency, importance, and relationship context.

### Associative memory
Represent relationships between memories, projects, entities, decisions, events, and procedures.

### Memory evolution
Support deduplication, consolidation, updates, contradiction detection, superseded records, expiration, and archival. Never silently overwrite conflicting information.

### Memory inspection and control
Allow authorized users and agents to search, inspect, correct, archive, and delete memories.

## Memory Types

ADAPT should support distinct memory types rather than treating all stored information equally.

| Type | Purpose | Example |
|---|---|---|
| Episodic | Experiences and events | A task was completed; a decision was made |
| Semantic | Facts and established knowledge | A project's architecture or a user preference |
| Procedural | Reusable instructions and workflows | Steps for deploying a particular application |
| Working | Temporary active-task context | Current objective, constraints, and unfinished subtasks |

Working memory should support configurable expiration and persistence behavior. Procedural memories should distinguish verified procedures from suggestions or untested instructions.

## Architecture

ADAPT should use modular components with clear interfaces.

| Component | Responsibility |
|---|---|
| ADAPT Core | Orchestrates memory operations and enforces access rules |
| Ingestion Engine | Normalizes, classifies, and evaluates memory candidates |
| Storage Engine | Persists structured memory records and indexes |
| Embedding Provider | Supplies optional vector representations |
| Retrieval Engine | Performs hybrid search and ranking |
| Relationship Engine | Creates and traverses typed memory relationships |
| Consolidation Engine | Detects duplicates, conflicts, and stale information |
| Integration Layer | Connects agent frameworks to the core |

### Initial local-first storage

Start with SQLite for local persistence and SQLite FTS5 for full-text search. Put storage behind an interface so other backends can be added without changing the public API.

Use a pluggable vector index for semantic retrieval. ADAPT must remain useful when an embedding provider is unavailable; keyword retrieval should continue to work.

Embedding providers must be configurable and version-aware so memories can be re-indexed when models change.

### Core data entities

The initial logical data model should include:

- **Memory:** owner, agent, type, content, importance, confidence, source, scope, timestamps, expiry, status, and metadata.
- **MemoryRelationship:** source memory, target memory, relationship type, confidence, and metadata.
- **MemorySource:** source type, source identifier, owner, agent, timestamp, and metadata.
- **MemoryVersion:** previous content, new content, change reason, source, and timestamp.
- **Agent:** owner, name, framework, configuration, and timestamps.
- **MemoryJob:** job type, status, input reference, result, error, and timestamps.

Define exact schemas, constraints, indexes, migrations, and ownership rules during implementation.

## Hermes Integration

ADAPT's first release should be a genuine **Hermes Memory Provider Plugin**, not merely a general-purpose tool plugin that searches an external database.

The integration must follow the current official Hermes memory-provider contract. Inspect the current documentation and repository before implementing; do not invent method signatures or rely on stale examples.

The current provider contract documents required methods including:

- `name`
- `is_available()`
- `initialize(session_id, **kwargs)`
- `get_tool_schemas()`
- `handle_tool_call(...)` when provider tools are exposed
- `get_config_schema()`
- `save_config(...)` unless configuration is environment-variable-only

Optional lifecycle hooks include:

- `prefetch(query, *, session_id="")`
- `queue_prefetch(query, *, session_id="")`
- `sync_turn(user, assistant, *, session_id="", messages=None)`
- `on_session_end(messages)`
- `on_pre_compress(messages)`
- `on_memory_write(...)`
- `shutdown()`

Use the exact current signatures and semantics from the official guide.

### Integration requirements

Hermes should be able to:

1. Persist useful information from completed turns.
2. Retrieve relevant memories before a model call.
3. Preserve important context before compression.
4. Maintain continuity across sessions and restarts.
5. Inspect and manage memories through authorized provider tools.
6. Continue operating if optional embedding services are unavailable.

Memory ingestion and consolidation should not introduce unnecessary latency into agent execution. Use bounded work, clear timeouts, and safe background processing where appropriate.

### Installation and configuration

A normal Hermes user should be able to install ADAPT, configure the provider, and start using persistent memory without manually creating databases or managing embedding indexes.

The provider should ship clear setup instructions and sensible defaults. Do not require a hosted account for local-first operation.

Note: Hermes memory providers are a single-select provider surface. ADAPT must document how users select it as their active memory provider and what happens to existing provider configuration.

## Security and Privacy

Memory can contain sensitive information. Security is a core requirement.

- Enforce strict owner and agent isolation.
- Keep local data under the user's control.
- Do not expose a network service by default.
- Support explicit memory inspection and deletion.
- Track provenance and source references.
- Handle secrets through supported configuration mechanisms.
- Never treat retrieved memories as trusted executable instructions.
- Distinguish stored claims from verified facts.
- Provide configurable retention and expiration.
- For future cloud deployments, add authentication, authorization, encrypted transport, and encryption-at-rest controls.

Retrieved memories are contextual data, not system instructions.

## MVP Scope

The hackathon MVP should prioritize a reliable, installable Hermes integration over a large dashboard or an ambitious hosted platform.

### Required for v0.1

- [ ] ADAPT Core with a stable internal API.
- [ ] Local SQLite persistence and migrations.
- [ ] Memory create, retrieve, update, archive, and delete operations.
- [ ] Source and ownership tracking.
- [ ] Basic episodic, semantic, procedural, and working memory support.
- [ ] Automatic or configurable memory ingestion.
- [ ] Keyword retrieval.
- [ ] Pluggable embeddings and semantic retrieval, with keyword fallback.
- [ ] Bounded hybrid retrieval.
- [ ] Basic typed memory relationships.
- [ ] Duplicate detection and safe conflict handling.
- [ ] Memory version history.
- [ ] Hermes Memory Provider Plugin.
- [ ] Cross-session continuity.
- [ ] Pre-compression preservation where supported by the current Hermes contract.
- [ ] User-controlled memory inspection and deletion.
- [ ] Automated tests for critical paths.
- [ ] Installation, configuration, and troubleshooting documentation.
- [ ] Successful official Hermes plugin validation and catalog submission.

### Defer until after v0.1

- Full hosted multi-tenant service.
- Complex visual knowledge graph.
- Organization/team administration.
- Many framework integrations at once.
- Advanced behavioral profiling.
- Model training or fine-tuning.

## Repository Structure

A proposed starting point:

```text
adapt/
├── README.md
├── LICENSE
├── pyproject.toml
├── .env.example
├── .gitignore
├── docs/
│   ├── ARCHITECTURE.md
│   ├── API.md
│   ├── INSTALLATION.md
│   ├── CONFIGURATION.md
│   ├── SECURITY.md
│   └── CONTRIBUTING.md
├── adapt/
│   ├── core/
│   ├── memory/
│   │   ├── ingestion/
│   │   ├── retrieval/
│   │   ├── consolidation/
│   │   └── relationships/
│   ├── storage/
│   ├── embeddings/
│   ├── models/
│   ├── api/
│   ├── security/
│   └── config/
├── integrations/
│   └── hermes/
│       ├── plugin.yaml
│       ├── __init__.py
│       ├── adapter.py
│       └── README.md
├── migrations/
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── security/
│   └── e2e/
└── examples/
    └── basic_memory.py
```

Adjust this structure to the actual Hermes packaging and plugin discovery requirements. Avoid unnecessary abstraction and excessive package fragmentation.

## Development Principles

1. Build working functionality, not placeholders.
2. Do not simulate successful memory operations.
3. Do not claim completion without implementation and test evidence.
4. Verify Hermes interfaces against current official documentation and source.
5. Keep the memory engine independent of Hermes.
6. Keep storage and embedding providers behind interfaces.
7. Enforce ownership and isolation in every relevant operation.
8. Preserve provenance and meaningful version history.
9. Never silently discard conflicting memories.
10. Ensure deleted or unauthorized memories are not returned by retrieval.
11. Add automated tests for critical capabilities.
12. Document configuration, limitations, and operational requirements.
13. Prioritize reliability and usability over feature count.

### Milestone workflow

Work one milestone at a time:

1. Inspect the existing implementation.
2. Identify the missing requirements.
3. Implement the milestone.
4. Run relevant tests.
5. Fix failures.
6. Record evidence.
7. Produce a concise milestone report.
8. Identify the next milestone.

Do not skip verification to move faster.

## Testing and Acceptance Criteria

ADAPT v0.1 is not complete until the following scenarios pass.

### Session continuity
1. Store useful project information during one agent session.
2. End the session and restart the agent.
3. Ask a question that requires the previous information.
4. Verify ADAPT retrieves the correct memory and source.

### Context compression
1. Create a session with important information.
2. Trigger context compression.
3. Continue the interaction.
4. Verify that important information remains retrievable.

### Memory evolution
1. Store a fact.
2. Submit updated information.
3. Verify the active record reflects the update.
4. Verify the previous version remains traceable.

### Associative retrieval
1. Store related memories.
2. Create typed relationships.
3. Ask a question requiring those connections.
4. Verify relevant related memories are returned.

### Isolation
1. Create separate owners and agents.
2. Store distinct memories.
3. Attempt unauthorized cross-owner and cross-agent retrieval.
4. Verify access is denied.

### Failure recovery
1. Interrupt an ingestion operation.
2. Restart the application.
3. Verify database consistency.
4. Verify incomplete jobs can be retried safely.

### Deletion
1. Store a memory.
2. Delete it.
3. Verify it is absent from normal retrieval and search.
4. Verify associated indexes and relationships are handled according to the deletion policy.

### Performance and resilience
- Retrieval is bounded by configurable limits.
- Embedding-provider failure does not disable keyword search.
- Repeated ingestion is idempotent where applicable.
- Storage errors are visible and do not produce false success responses.

## Roadmap

### Phase 1 — ADAPT Core
Reliable local-first memory engine, storage, ingestion, retrieval, and management.

### Phase 2 — Framework Integrations
Add adapters for OpenClaw, LangGraph, CrewAI, and other agent frameworks based on validated demand and their official extension interfaces.

### Phase 3 — Developer Platform
Public API, Python SDK, TypeScript SDK, namespaces, agent registration, and developer documentation.

### Phase 4 — Hosted ADAPT
Managed memory infrastructure, cloud synchronization, multi-agent environments, team support, and scalable storage backends.

### Phase 5 — Advanced Memory Intelligence
Temporal knowledge graphs, improved consolidation, cross-project discovery, adaptive importance, and more advanced retrieval.

## Official Developer Resources

These links are the starting point for implementing and validating the first Hermes integration. Always check the live documentation before relying on a particular API or command.

- [Hermes Agent — Memory Provider Plugin Guide](https://hermes-agent.nousresearch.com/docs/developer-guide/memory-provider-plugin)
- [Hermes Agent — Build a Plugin](https://hermes-agent.nousresearch.com/docs/developer-guide/plugins)
- [Hermes Agent — Developer Documentation](https://hermes-agent.nousresearch.com/docs/developer)
- [NousResearch Hermes Agent — GitHub Repository](https://github.com/NousResearch/hermes-agent)
- [Hermes Agent — Plugin Catalog](https://hermes-agent.nousresearch.com/plugins)

### Hackathon submission checklist

- [ ] Publish the ADAPT plugin repository.
- [ ] Validate the plugin using the current Hermes validation workflow.
- [ ] Open a pull request to add ADAPT to the official plugin catalog.
- [ ] Record a demo video under 90 seconds showing real functionality.
- [ ] Publish the demo on X and tag [@NousResearch](https://x.com/NousResearch).
- [ ] Submit the pull request and demo links through the [hackathon submission form](https://form.typeform.com/to/FwJLvOln).

---

## Product Philosophy

ADAPT should not attempt to remember everything.

It should remember what matters, understand how information connects, recognize when knowledge changes, and retrieve the right context at the right time.

The quality of a memory system is not measured by how much information it stores. It is measured by how effectively an agent uses what it remembers.

**ADAPT exists to give AI agents something they fundamentally lack: continuity.**

**Build once. Remember continuously.**
