# Hermes Agent Integration Specification

## 1. Overview
ADAPT is integrated into Hermes Agent as an official **Memory Provider Plugin** (not merely an external tool caller). In Hermes Agent, memory providers operate under a single-select model (`memory.provider: adapt`) and hook directly into the agent's turn lifecycle, system prompt compilation, prefetch caching, context compression, and session wrap-up.

## 2. Manifest Contract (`plugin.yaml`)
Hermes discovers and loads plugins via `plugin.yaml`. The ADAPT manifest conforms to the official specification:

```yaml
name: adapt
version: "0.1.0"
description: "ADAPT — Persistent memory infrastructure for AI agents with episodic, semantic, procedural, and working memory."
author: "ADAPT Team"
category: memory
tier: community
requires_hermes: ">=0.20.0"
provides_memory_providers:
  - adapt
config_keys:
  - memory.adapt
config_schema:
  storage_dir:
    type: str
    required: false
  top_k:
    type: int
    required: false
```

## 3. Abstract Base Class Interface (`MemoryProvider`)
Based on `agent.memory_provider.MemoryProvider`, the ADAPT adapter implements:

```python
class AdaptMemoryProvider(MemoryProvider):
    @property
    def name(self) -> str:
        return "adapt"

    def is_available(self) -> bool:
        return True

    def initialize(self, session_id: str, **kwargs) -> None:
        """Invoked once at agent startup. Receives session_id and hermes_home."""
        pass

    def system_prompt_block(self) -> str:
        """Injects stable memory context and capabilities into the system prompt."""
        pass

    def prefetch(self, query: str, *, session_id: str = "") -> str:
        """Invoked before every LLM turn. Returns fast cached/ranked relevant memories."""
        pass

    def sync_turn(self, user_content: str, assistant_content: str, *, session_id: str = "", messages=None) -> None:
        """Processes interaction data from the turn into ADAPT."""
        pass

    def on_pre_compress(self, messages: list[dict[str, Any]]) -> str:
        """Preserves critical decisions before context compaction."""
        pass

    def on_session_end(self, messages: list[dict[str, Any]]) -> None:
        """Triggers consolidation, deduplication, and working memory archival."""
        pass

    def get_tool_schemas(self) -> list[dict[str, Any]]:
        """Declares tools: adapt_remember, adapt_recall, adapt_update, adapt_forget, adapt_relate, adapt_stats."""
        pass

    def handle_tool_call(self, name: str, arguments: dict[str, Any], **kwargs) -> str:
        """Executes LLM tool calls against the ADAPT engine and returns JSON string."""
        pass

    def shutdown(self) -> None:
        """Flushes queues and closes database connections."""
        pass
```

## 4. Official Validation & Catalog Submission
1. Local Validation:
   ```bash
   hermes plugins validate ./integrations/hermes --install-deps
   ```
2. Activation in `~/.hermes/config.yaml`:
   ```yaml
   memory:
     provider: adapt
     adapt:
       storage_dir: ~/.hermes/adapt
       top_k: 5
       hybrid_alpha: 0.5
   ```
3. Catalog Entry (`plugin-catalog/adapt.yaml` in `NousResearch/hermes-agent`):
   ```yaml
   name: adapt
   repo: https://github.com/adapt-memory/adapt
   sha: 3d8dabd46a644cf4dcd866435218a69578975fb1
   subdir: integrations/hermes
   description: "Persistent memory infrastructure layer for AI agents with episodic, semantic, procedural, and working memory, hybrid retrieval, and knowledge graph evolution."
   maintainer: ADAPT Team
   category: memory
   tier: community
   version: "0.1.0"
   requires_hermes: ">=0.20.0"
   readme: true
   ```

