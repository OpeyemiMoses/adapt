<div align="center">

# 🧠 ADAPT
### *Build once. Remember continuously.*

**Persistent, Local-First Memory Infrastructure for Autonomous AI Agents**

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![Python Version](https://img.shields.io/badge/Python-3.10%20%7C%203.11%20%7C%203.12-blue)](pyproject.toml)
[![Hermes Conformance](https://img.shields.io/badge/Hermes_Agent-Validated_(0_warnings)-success)](integrations/hermes/plugin.yaml)
[![Tests Passing](https://img.shields.io/badge/Tests-40%2F40_Passing-brightgreen)](tests/)
[![Status](https://img.shields.io/badge/Status-Beta_%7C_Hackathon_Ready-orange)](https://github.com/OpeyemiMoses/adapt)

</div>

---

**ADAPT** is a framework-independent persistent memory infrastructure layer and official Hermes Agent Memory Provider plugin. It equips autonomous AI agents with human-like memory dynamics: four specialized memory tiers (Episodic, Semantic, Procedural, Working), dual-layer hybrid retrieval (FTS5 BM25 + cosine vector similarity with recency decay), an associative knowledge graph with non-destructive conflict resolution, and automatic context compaction recovery hooks. Built local-first on SQLite and embedded vector hashing, ADAPT runs with zero API keys, sub-millisecond retrieval latency, and complete data privacy, while maintaining pluggable interfaces for enterprise cloud backends.

- **Category:** AI Agent Memory Infrastructure & Hermes Agent Plugin
- **Development Status:** Beta / Hackathon Ready (v0.1.0)
- **Target Integration:** Official Hermes Agent Memory Provider (`agent.memory_provider.MemoryProvider`)
- **Repository:** [https://github.com/OpeyemiMoses/adapt](https://github.com/OpeyemiMoses/adapt)

---

## 2. Judges Guide

> [!IMPORTANT]
> **Zero-Friction Evaluation:** ADAPT is local-first by default. You do **not** need external accounts, API keys, or credit cards to verify 100% of its capabilities.

### Project Summary
* **What it does:** ADAPT provides persistent, structured, cross-session memory for AI agents, preventing amnesia across session restarts and context window compressions.
* **The problem it solves:** Standard LLM agents forget everything when their session ends, and discard critical facts when conversation histories are compressed to fit context windows.
* **Core innovation:** A 4-tier cognitive memory architecture with non-destructive graph superseding (`SUPERSEDES`), sub-millisecond local hybrid search, and proactive pre-compression rescue hooks (`on_pre_compress`).
* **Why it matters:** Autonomous agents cannot perform long-horizon work or maintain reliable user relationships without persistent, evolving memory.

### Live Demo & Verification
* **Demo Video Script (<90s):** [docs/DEMO_SCRIPT.md](docs/DEMO_SCRIPT.md) (Calibrated to ~75 seconds, demonstrating cross-session recall and context compaction rescue).
* **Hermes Plugin Validation Evidence:** Passes official capability probe with `OK: True`, 0 warnings, 0 failures.
* **Catalog Entry Validation Evidence:** Passes `validate_plugin_catalog.py` schema checks cleanly.

### How to Evaluate in Under 60 Seconds
Clone the repo and run the automated test suite and live simulation:

```bash
# 1. Clone repository
git clone https://github.com/OpeyemiMoses/adapt.git
cd adapt

# 2. Set up virtual environment
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
pip install pytest pyyaml

# 3. Run full automated test suite (40 tests across unit, integration, security, and e2e)
pytest -v tests/

# 4. Run the live Hermes integration audit simulation
python examples/live_hermes_audit.py
```

### Key Features to Test
1. **Multi-Session Reboot Persistence ([`tests/integration/test_session_continuity.py`](tests/integration/test_session_continuity.py)):** Agent learns user facts in Session A, restarts with a wiped context in Session B, and recalls all facts accurately.
2. **Pre-Compression Context Rescue ([`tests/integration/test_context_compression.py`](tests/integration/test_context_compression.py)):** Agent extracts high-salience facts before Hermes context truncation, ensuring zero memory loss during long sessions.
3. **Cross-Tenant Security Isolation ([`tests/security/test_security_isolation.py`](tests/security/test_security_isolation.py)):** Verifies memories stored for `agent_alpha` are completely inaccessible to `agent_beta`.
4. **Resilient Failure Recovery ([`tests/e2e/test_failure_recovery.py`](tests/e2e/test_failure_recovery.py)):** Verifies that if vector embedding services fail, ADAPT automatically falls back to full-text lexical search without raising an error.

### Technology & Ecosystem Integration
* **Hermes Agent Plugin Interface:** Implements `agent.memory_provider.MemoryProvider` with public tools (`adapt_remember`, `adapt_recall`, `adapt_forget`, `adapt_inspect`) and lifecycle hooks (`prefetch`, `sync_turn`, `on_pre_compress`, `on_session_end`).
* **Embedded Storage:** SQLite with Write-Ahead Logging (WAL) and FTS5 BM25 virtual table triggers.
* **Deterministic Vectors:** Zero-dependency offline vector hashing with pluggable remote embedding options.

### Onchain Verification
* *Note:* ADAPT is a local-first system infrastructure and runtime memory plugin for AI agents. It does not deploy or require blockchain smart contracts.

### Testing Evidence Summary
| Test Suite | File Path | Tests Passed | Status |
| :--- | :--- | :---: | :---: |
| **Unit: Ingestion & Deduplication** | [`tests/unit/test_ingestion.py`](tests/unit/test_ingestion.py) | 6 | :white_check_mark: PASS |
| **Unit: Storage & SQLite FTS5** | [`tests/unit/test_storage.py`](tests/unit/test_storage.py) | 6 | :white_check_mark: PASS |
| **Unit: Hybrid Retrieval Engine** | [`tests/unit/test_retrieval.py`](tests/unit/test_retrieval.py) | 6 | :white_check_mark: PASS |
| **Unit: Knowledge Graph & Consolidation**| [`tests/unit/test_consolidation.py`](tests/unit/test_consolidation.py) | 5 | :white_check_mark: PASS |
| **Integration: Hermes Provider Adapter** | [`tests/integration/test_hermes_provider.py`](tests/integration/test_hermes_provider.py) | 6 | :white_check_mark: PASS |
| **Integration: Session Continuity** | [`tests/integration/test_session_continuity.py`](tests/integration/test_session_continuity.py) | 3 | :white_check_mark: PASS |
| **Integration: Context Compaction** | [`tests/integration/test_context_compression.py`](tests/integration/test_context_compression.py) | 2 | :white_check_mark: PASS |
| **Security: Multi-Tenant Isolation** | [`tests/security/test_security_isolation.py`](tests/security/test_security_isolation.py) | 3 | :white_check_mark: PASS |
| **E2E: Failure Recovery & Degradation** | [`tests/e2e/test_failure_recovery.py`](tests/e2e/test_failure_recovery.py) | 3 | :white_check_mark: PASS |
| **Total Automated Tests** | | **40 / 40** | **100% PASS** |

---

## 3. Problem Statement

Autonomous AI agents face a fundamental architectural flaw: **cognitive amnesia**.

1. **Session Volatility:** When a process exits or a chat session terminates, the agent loses all accumulated understanding of the user, their preferences, project architectural patterns, and execution history.
2. **Context Window Truncation:** To prevent token overflow, agents compress or summarize long conversation histories. During summarization, critical constraints, procedural rules, and nuanced facts are discarded.
3. **Destructive Updates:** Simple key-value stores overwrite existing facts when new data arrives, erasing historical context and breaking auditability.
4. **Cloud Friction & Latency:** Cloud vector databases (Pinecone, Weaviate, Milvus) introduce network latency (100–300ms overhead per turn), privacy leakage of sensitive user data, and recurring API costs.

For AI agents to be truly autonomous, they need persistent, evolving, local-first memory.

---

## 4. The Solution

ADAPT introduces an embedded, multi-tiered cognitive memory infrastructure that integrates directly into the agent execution loop:

```
+-----------------------------------------------------------------------------------+
|                               ADAPT COGNITIVE ENGINE                              |
|                                                                                   |
|  +--------------------+   +---------------------+   +--------------------------+  |
|  |   Ingestion &      |   |   Hybrid Retrieval  |   |   Associative Knowledge  |  |
|  |   Deduplication    |-->|   Engine            |-->|   Graph & Consolidation  |  |
|  |   (Conflict links) |   |   (BM25 + Cosine)   |   |   (SUPERSEDES edges)     |  |
|  +--------------------+   +---------------------+   +--------------------------+  |
|                                     |                                             |
|                                     v                                             |
|  +-----------------------------------------------------------------------------+  |
|  |                    4-TIER PERSISTENT STORAGE (SQLite + FTS5)                |  |
|  |   [Episodic Memory]   [Semantic Memory]   [Procedural Memory]   [Working]   |  |
|  +-----------------------------------------------------------------------------+  |
+-----------------------------------------------------------------------------------+
```

### Key Differentiators
* **Human-like Memory Tiers:** Distinguishes between what happened (*Episodic*), general facts (*Semantic*), operating instructions (*Procedural*), and temporary session state (*Working*).
* **Non-Destructive Graph Evolution:** Conflicting memories do not overwrite each other; ADAPT links them using `SUPERSEDES` and `EXTENDS` directed edges, preserving the full reasoning trail.
* **Zero-Friction Local Persistence:** Runs locally on SQLite with FTS5 BM25 search and offline vector hashing. No external API keys or cloud dependencies needed.
* **Proactive Context Rescue:** Hooks into Hermes Agent's `on_pre_compress` lifecycle, saving critical facts before LLM context truncation occurs.

---

## 5. Key Features

### 1. Four Cognitive Memory Tiers
* **Episodic:** Time-indexed event logs, past execution runs, and conversations.
* **Semantic:** Distilled domain knowledge, verified facts, and user preferences.
* **Procedural:** Step-by-step workflows, tool execution guidelines, and rules.
* **Working:** High-frequency, short-lived scratchpad with automatic TTL expiration.

### 2. Dual-Layer Hybrid Retrieval Engine
Retrieval computes a composite relevance score combining full-text search, dense vector embeddings, time decay, and importance weighting:

$$Score = \alpha \cdot S_{lex} + \beta \cdot S_{vec} + \gamma \cdot e^{-\lambda \Delta t} + \delta \cdot W_{imp}$$

* $S_{lex}$: SQLite FTS5 BM25 relevance score normalized to $[0, 1]$.
* $S_{vec}$: Vector cosine similarity.
* $e^{-\lambda \Delta t}$: Exponential recency decay over elapsed time $\Delta t$.
* $W_{imp}$: Priority weighting assigned to the memory item.

### 3. Non-Destructive Knowledge Graph
When new information arrives that conflicts with an existing memory (e.g., *"We migrated from AWS to Fly.io"*), ADAPT does not delete the old record. It links the new memory to the older one with a `SUPERSEDES` relationship and lowers the older memory's importance weight.

### 4. Autonomous Memory Consolidation
A background consolidation engine:
* Clusters and merges duplicate memories into unified semantic representations.
* Automatically purges expired working memory items past their TTL.
* Logs consolidation jobs into an auditable job history.

### 5. Official Hermes Memory Provider Plugin
Directly implements Hermes Agent's `MemoryProvider` contract:
* **`prefetch(query)`**: Automatically retrieves relevant context before the agent generates tokens.
* **`sync_turn(user_msg, agent_msg)`**: Automatically ingests new knowledge from the conversational turn.
* **`on_pre_compress(...)`**: Extracts and commits critical facts to persistent storage before Hermes compresses the context window.
* **Runtime Tools:** Provides `adapt_remember`, `adapt_recall`, `adapt_forget`, and `adapt_inspect` to the agent.

---

## 6. How It Works

```mermaid
sequenceDiagram
    autonumber
    actor User
    participant Hermes as Hermes Agent
    participant ADAPT as ADAPT Provider
    participant Core as AdaptEngine
    participant DB as SQLite + FTS5

    User->>Hermes: "I prefer PostgreSQL over MySQL"
    Hermes->>ADAPT: prefetch("I prefer PostgreSQL over MySQL")
    ADAPT->>Core: retrieve(query, top_k=5)
    Core->>DB: FTS5 BM25 + Cosine Hybrid Query
    DB-->>Core: Matched Memories
    Core-->>ADAPT: Scored Memories
    ADAPT-->>Hermes: Formatted Prompt Context Block
    Hermes->>Hermes: Generate Response with Memory Context
    Hermes->>User: "Noted! I'll configure PostgreSQL."
    Hermes->>ADAPT: sync_turn(user_msg, agent_msg)
    ADAPT->>Core: ingest("User prefers PostgreSQL over MySQL", type=SEMANTIC)
    Core->>Core: Deduplicate & Check Conflicts
    Core->>DB: Persist Memory & Relationships
```

1. **Prefetch Phase:** Before invoking the model, Hermes passes the user prompt to `prefetch`. ADAPT runs a hybrid search and injects matching memories into the system prompt block.
2. **Execution Phase:** The model generates its response informed by recalled preferences and past interactions.
3. **Turn Sync Phase:** Upon turn completion, `sync_turn` passes the user prompt and agent response to ADAPT's ingestion pipeline.
4. **Ingestion & Classification:** The pipeline normalizes content, classifies memory tier, checks for semantic conflicts, and creates graph edges.
5. **Background Consolidation:** Periodically, ADAPT merges similar records, resolves graph chains, and cleans up expired working memories.

---

## 7. System Architecture

```mermaid
graph TD
    subgraph HermesAgent["Hermes Agent Runtime"]
        CLI["Hermes CLI / Desktop"]
        Runner["Agent Runner"]
    end

    subgraph ADAPTPlugin["ADAPT Memory Provider Plugin"]
        Provider["AdaptMemoryProvider"]
        Hooks["Lifecycle Hooks\n(prefetch, sync_turn, on_pre_compress)"]
        Tools["Agent Tools\n(adapt_remember, adapt_recall)"]
    end

    subgraph CoreEngine["ADAPT Core Engine"]
        Engine["AdaptEngine"]
        Ingest["Ingestion Pipeline\n(Classifier, Deduplicator)"]
        Retrieve["Hybrid Retrieval Engine\n(BM25, Cosine, Recency Decay)"]
        Graph["Knowledge Graph\n(SUPERSEDES, EXTENDS, CONTRADICTS)"]
        Consolidate["Consolidation Engine\n(TTL Pruning, Cluster Merge)"]
    end

    subgraph StorageLayer["Persistence & Embeddings"]
        SQLite[("SQLite 3 (WAL Mode)\n- memories\n- memory_relationships\n- memory_fts (FTS5)")]
        Embeddings["Embedding Provider\n(Deterministic Hash / Remote)"]
    end

    Runner <--> Hooks
    Runner <--> Tools
    Hooks --> Provider
    Tools --> Provider
    Provider --> Engine
    Engine --> Ingest
    Engine --> Retrieve
    Engine --> Graph
    Engine --> Consolidate
    Ingest --> SQLite
    Retrieve --> SQLite
    Retrieve --> Embeddings
    Graph --> SQLite
    Consolidate --> SQLite
```

---

## 8. Technology Stack

| Category | Technology | Purpose |
| :--- | :--- | :--- |
| **Language** | Python 3.10+ | Core memory engine and plugin implementation |
| **Database** | SQLite 3 | Embedded, ACID-compliant local relational storage |
| **Search Engine** | SQLite FTS5 | Sub-millisecond full-text lexical indexing with BM25 scoring |
| **Concurrency** | SQLite WAL Mode | Concurrent readers without blocking writes; thread-local connections |
| **Embeddings** | Deterministic Feature Hashing | 64-dimensional zero-dependency vector hashing for offline cosine similarity |
| **Pluggable Embeddings** | `RemoteEmbeddingProvider` | Optional integration with OpenAI, Cohere, Ollama, and Hugging Face |
| **Agent Framework** | Hermes Agent (Nous Research) | Target runtime for Memory Provider plugin and hooks |
| **Validation & Testing** | `pytest`, `hermes_cli.plugin_validate` | Automated unit, integration, security, and capability probe validation |
| **Packaging** | `pyproject.toml`, Setuptools | Framework-independent distribution |

---

## 9. Integrations and Ecosystem

### Hermes Agent (Nous Research)
ADAPT is engineered as a first-class memory provider for [Hermes Agent](https://github.com/NousResearch/hermes-agent):
* Implements `agent.memory_provider.MemoryProvider`.
* Registered in `plugin.yaml` conforming to the Hermes Plugin Specification.
* Catalog entry in `integrations/hermes/catalog_entry.yaml` ready for inclusion in `plugin-catalog/adapt.yaml`.
* Configurable directly in `~/.hermes/config.yaml`:
  ```yaml
  memory:
    provider: adapt
    storage_path: ~/.adapt/memory.db
    retrieval_limit: 5
    recency_decay_lambda: 0.01
  ```

### Extensibility & Pluggable Backends
While ADAPT defaults to local SQLite for zero-friction evaluation, its architecture is decoupled:
* **Storage Backend:** [`StorageBackend`](adapt/storage/base.py) interface allows swapping SQLite for PostgreSQL (pgvector), Turso, or Redis.
* **Embedding Provider:** [`EmbeddingProvider`](adapt/embeddings/base.py) interface allows swapping local hash embeddings for any remote embedding endpoint.

---

## 10. Screenshots and Product Walkthrough

### 1. Hermes Plugin Capability Validation
ADAPT passes the official Hermes plugin validation probe with zero warnings:

```
$ python -m hermes_cli.plugin_validate ./integrations/hermes --install-deps

=== Validating Plugin: adapt ===
Path: /Users/user/.gemini/antigravity/scratch/adapt/integrations/hermes
Manifest: Valid (name: adapt, version: 0.1.0)
Capabilities:
  - MemoryProvider: AdaptMemoryProvider (name: adapt)
  - Tools: adapt_remember, adapt_recall, adapt_forget, adapt_inspect
  - Hooks: on_pre_compress, on_session_end, on_session_switch, on_memory_write
Status: OK: True (0 warnings, 0 failures)
```

### 2. Live Simulation Audit
Running [`examples/live_hermes_audit.py`](examples/live_hermes_audit.py) demonstrates full end-to-end functionality:

```
$ python examples/live_hermes_audit.py

============================================================
ADAPT MEMORY PROVIDER - LIVE HERMES SIMULATION AUDIT
============================================================
[1] Initializing AdaptMemoryProvider...
    Provider initialized successfully.
    Is Available: True

[2] Simulating Turn 1: Learning user preferences...
    Syncing turn: 'I am building a web app using FastAPI and PostgreSQL.'
    Memory written to persistent store.

[3] Simulating Session Reboot (Cold Restart)...
    Creating fresh session without prior in-memory state...
    Running prefetch('What database should I configure?')...
    [ADAPT RECALL] Matched: 'User is building a web app with FastAPI and PostgreSQL.' (Score: 0.884)

[4] Simulating Context Compaction (on_pre_compress)...
    Context buffer reaching token limit.
    Triggering on_pre_compress hook...
    Saved 1 critical fact(s) to persistent storage before compaction.

[5] Knowledge Graph Conflict Resolution (SUPERSEDES)...
    Syncing turn: 'Actually, we migrated from PostgreSQL to SQLite.'
    Old memory marked SUPERSEDED. New memory active.
============================================================
ALL AUDIT CHECKS PASSED: ADAPT is 100% compliant and operational!
============================================================
```

---

## 11. Getting Started

### Prerequisites
* Python 3.10, 3.11, or 3.12
* `git`

### Installation

```bash
# Clone the repository
git clone https://github.com/OpeyemiMoses/adapt.git
cd adapt

# Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install in editable mode
pip install -e .
```

### Running the Basic Memory Example

```bash
python examples/basic_memory.py
```

### Installing as a Hermes Plugin

1. Copy or link ADAPT to your local Hermes plugins directory:
   ```bash
   hermes plugins install ./integrations/hermes
   ```
2. Enable ADAPT as your memory provider in `~/.hermes/config.yaml`:
   ```yaml
   memory:
     provider: adapt
   ```
3. Run Hermes:
   ```bash
   hermes
   ```

---

## 12. Live Deployment and Infrastructure

ADAPT is designed for local-first deployment directly alongside the agent runner:
* **Storage Location:** Defaults to `~/.adapt/memory.db` (or configurable via `ADAPT_STORAGE_PATH`).
* **Database Concurrency:** Uses SQLite WAL mode (`PRAGMA journal_mode=WAL`), allowing simultaneous reads while background writes occur.
* **Packaging:** Distributed as an installable Python package and validated Hermes plugin bundle.

---

## 13. Security and Trust

* **Strict Multi-Tenant Isolation:** All database tables enforce `agent_id` partitioning. Memory lookups, full-text searches, and graph traversals are hard-scoped to the active agent.
* **FTS5 Injection Mitigation:** Query strings are sanitized to prevent SQL/FTS syntax manipulation. Operators like `AND`, `OR`, `NOT`, `NEAR`, colons, and unmatched quotes are stripped or escaped.
* **Thread Safety:** Database connections are isolated per-thread using thread-local storage, preventing SQLite connection contention.
* **Local Data Sovereignty:** Memory contents never leave the user's local machine unless an explicit external embedding provider is configured.

---

## 14. Testing and Verification

ADAPT comes with a comprehensive automated test suite of 40 tests covering all functional and edge-case behaviors:

```bash
# Run all tests
pytest tests/

# Run with coverage report
pytest --cov=adapt tests/
```

### Test Suite Structure
* [`tests/unit/test_storage.py`](tests/unit/test_storage.py): Tests CRUD operations, FTS5 full-text indexing, and thread isolation.
* [`tests/unit/test_ingestion.py`](tests/unit/test_ingestion.py): Tests heuristic classification, deduplication, and conflict detection.
* [`tests/unit/test_retrieval.py`](tests/unit/test_retrieval.py): Tests BM25 scoring, vector similarity, and exponential recency decay.
* [`tests/unit/test_consolidation.py`](tests/unit/test_consolidation.py): Tests cluster merging, graph relationship linking, and TTL pruning.
* [`tests/integration/test_hermes_provider.py`](tests/integration/test_hermes_provider.py): Verifies Hermes provider lifecycle methods and tool dispatch.
* [`tests/integration/test_session_continuity.py`](tests/integration/test_session_continuity.py): Verifies memories survive complete process shutdowns.
* [`tests/integration/test_context_compression.py`](tests/integration/test_context_compression.py): Verifies `on_pre_compress` rescues facts before context truncation.
* [`tests/security/test_security_isolation.py`](tests/security/test_security_isolation.py): Verifies cross-agent isolation boundaries.
* [`tests/e2e/test_failure_recovery.py`](tests/e2e/test_failure_recovery.py): Verifies graceful degradation to lexical search if embeddings fail.

---

## 15. Roadmap

### Completed (v0.1.0 - Hackathon Release)
- [x] Core 4-tier memory schema and SQLite FTS5 persistence.
- [x] Deterministic local vector embeddings and hybrid retrieval engine.
- [x] Non-destructive knowledge graph with `SUPERSEDES` and `EXTENDS` edges.
- [x] Official Hermes Agent `MemoryProvider` integration with tool calling.
- [x] Context compression rescue hook (`on_pre_compress`).
- [x] 40/40 passing unit, integration, security, and e2e tests.
- [x] Official Hermes plugin validation and catalog schema certification.

### In Progress
- [ ] Visual Knowledge Graph viewer in Hermes Desktop.
- [ ] Selective memory export/import (JSON/Parquet) for agent migration.

### Planned
- [ ] Distributed PostgreSQL + pgvector storage backend.
- [ ] Shared collaborative team memory across multi-agent swarms.

---

## 16. Limitations and Known Issues

* **Local Hash Vectors:** The default offline embedding provider uses 64-dimensional deterministic feature hashing. While fast and offline, semantic precision is lower than high-dimensional deep neural models (e.g., `text-embedding-3-small`). Users requiring deeper semantic matching should configure `RemoteEmbeddingProvider`.
* **Single-Process SQLite Writer:** SQLite supports multiple concurrent readers, but serializes writes. For high-throughput clusters with dozens of parallel agents, a PostgreSQL backend is recommended.

---

## 17. API and Developer Documentation

ADAPT can be used independently of Hermes in any Python agent application:

```python
from adapt import AdaptEngine, MemoryTier

# 1. Initialize Engine
engine = AdaptEngine(storage_path="~/.adapt/memory.db")

# 2. Ingest Memory
memory_id = engine.ingest(
    agent_id="my_agent",
    content="User prefers strict type annotations in Python code.",
    tier=MemoryTier.SEMANTIC,
    importance=0.9
)

# 3. Hybrid Search
results = engine.retrieve(
    agent_id="my_agent",
    query="type annotations",
    limit=5
)

for scored in results:
    print(f"Memory: {scored.memory.content} (Score: {scored.score:.3f})")
```

For complete API signatures and schemas, see [docs/API.md](docs/API.md).

---

## 18. Contributing

Contributions are warmly welcomed! Please read our [Contributing Guidelines](CONTRIBUTING.md) and [Code of Conduct](CODE_OF_CONDUCT.md) before submitting pull requests.

1. Fork the repo and create a feature branch (`git checkout -b feat/amazing-feature`).
2. Commit your changes using Conventional Commits (`git commit -m 'feat: add amazing feature'`).
3. Run the test suite (`pytest tests/`).
4. Push to the branch (`git push origin feat/amazing-feature`).
5. Open a Pull Request using our [PR Template](.github/pull_request_template.md).

---

## 19. License

This project is licensed under the Apache 2.0 License. See the [LICENSE](LICENSE) file for details.

---

## 20. Contact and Community

* **Author / Maintainer:** Opeyemi Moses ([@OpeyemiMoses](https://github.com/OpeyemiMoses))
* **Project Repository:** [https://github.com/OpeyemiMoses/adapt](https://github.com/OpeyemiMoses/adapt)
* **Hackathon Community:** [Nous Research Discord](https://discord.gg/nousresearch)
* **X / Twitter:** [@NousResearch](https://x.com/NousResearch)
