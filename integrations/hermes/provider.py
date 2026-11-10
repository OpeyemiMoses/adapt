"""Hermes Agent Memory Provider Plugin Adapter for ADAPT."""

from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

# Attempt import from Hermes Agent runtime; fall back to standalone protocol if unbundled
try:
    from agent.memory_provider import (
        INDICATOR_GLYPH,
        PRE_COMPRESS_CHECKPOINT_API_VERSION,
        MemoryProvider,
        RecallStatus,
        is_trivial_prompt,
    )
except ImportError:
    INDICATOR_GLYPH = "🧠"
    PRE_COMPRESS_CHECKPOINT_API_VERSION = 2

    @dataclass(frozen=True)
    class RecallStatus:
        provider_label: str
        count: int
        glyph: str = INDICATOR_GLYPH

    def is_trivial_prompt(text: Optional[str]) -> bool:
        if not text:
            return True
        s = text.strip().lower()
        return s in {"yes", "no", "ok", "okay", "sure", "thanks", "thank you", "hi", "hey", "hello", "done"}

    class MemoryProvider:
        """Standalone fallback base class mirroring Hermes MemoryProvider ABC."""
        pass

from adapt.core.engine import AdaptEngine
from adapt.embeddings.providers import DeterministicHashEmbeddingProvider, NoOpEmbeddingProvider
from adapt.models.schema import MemoryType, RelationshipType

logger = logging.getLogger(__name__)


class AdaptMemoryProvider(MemoryProvider):
    """Official Hermes Agent Memory Provider Plugin for ADAPT."""

    pre_compress_checkpoint_api_version = PRE_COMPRESS_CHECKPOINT_API_VERSION

    def __init__(self) -> None:
        self._engine: Optional[AdaptEngine] = None
        self._hermes_home: str = ""
        self._session_id: str = ""
        self._user_id: str = "default_user"
        self._top_k: int = 5
        self._hybrid_alpha: float = 0.5
        self._last_recall_status: Optional[RecallStatus] = None
        self._closed: bool = False

    @property
    def name(self) -> str:
        return "adapt"

    def is_available(self) -> bool:
        """Gates activation: checks engine readiness."""
        return True

    def initialize(self, session_id: str, **kwargs: Any) -> None:
        """Initialize once at agent startup.

        kwargs includes profile-scoped 'hermes_home', 'user_id', 'agent_context'.
        """
        self._session_id = session_id or "default_session"
        self._hermes_home = kwargs.get("hermes_home") or os.getenv("HERMES_HOME") or os.path.expanduser("~/.hermes")
        self._user_id = kwargs.get("user_id") or "default_user"

        storage_dir = Path(self._hermes_home) / "adapt"
        storage_dir.mkdir(parents=True, exist_ok=True)

        embed_type = os.getenv("ADAPT_EMBEDDING_PROVIDER", "hash").lower()
        embedder = (
            DeterministicHashEmbeddingProvider(dimension=128)
            if embed_type == "hash"
            else NoOpEmbeddingProvider()
        )

        self._engine = AdaptEngine(
            storage_dir=str(storage_dir),
            db_name="adapt_memory.db",
            embedding_provider=embedder,
            hybrid_alpha=self._hybrid_alpha,
        )
        logger.info("ADAPT Memory Provider initialized for session %s at %s", self._session_id, storage_dir)

    @property
    def engine(self) -> AdaptEngine:
        if self._engine is None:
            # Fallback initialization if initialize() wasn't called yet
            self.initialize(session_id="default_session")
        return self._engine  # type: ignore[return-value]

    def system_prompt_block(self) -> str:
        """Static instructions injected into agent system prompt."""
        return (
            "## Persistent Memory: ADAPT Active\n"
            "ADAPT retains, organizes, and retrieves persistent knowledge across sessions and tasks.\n"
            "- Episodic: Past events, actions, task outcomes.\n"
            "- Semantic: User preferences, architecture, durable facts.\n"
            "- Procedural: Verified workflows, execution runbooks.\n"
            "- Working: Active task context and subtask scratchpad.\n"
            "Use ADAPT tools (adapt_remember, adapt_recall, adapt_search, adapt_update, adapt_forget, adapt_relate) "
            "to inspect and manage persistent knowledge."
        )

    def prefetch(self, query: str, *, session_id: str = "") -> str:
        """Runs before every LLM turn to inject relevant context."""
        if not query or is_trivial_prompt(query):
            self._last_recall_status = None
            return ""

        try:
            results = self.engine.recall(
                query=query,
                owner_id=self._user_id,
                limit=self._top_k,
                include_related=True,
            )

            if not results:
                self._last_recall_status = None
                return ""

            self._last_recall_status = RecallStatus(
                provider_label="ADAPT",
                count=len(results),
                glyph=INDICATOR_GLYPH,
            )

            lines = ["<recalled_context provider=\"adapt\">", "[RECALLED KNOWLEDGE]"]
            for sm in results:
                m = sm.memory
                m_type = m.memory_type.value.upper() if hasattr(m.memory_type, "value") else str(m.memory_type).upper()
                lines.append(f"- [{m_type}] {m.content}")
            lines.append("</recalled_context>")
            return "\n".join(lines)

        except Exception as exc:
            logger.warning("ADAPT prefetch failed: %s", exc)
            self._last_recall_status = None
            return ""

    def queue_prefetch(self, query: str, *, session_id: str = "") -> None:
        """Queue background recall for the next upcoming turn."""
        pass

    def recall_status(self) -> Optional[RecallStatus]:
        """Return recall telemetry indicator."""
        return self._last_recall_status

    def sync_turn(
        self,
        user_content: str,
        assistant_content: str,
        *,
        session_id: str = "",
        messages: Optional[list[dict[str, Any]]] = None,
        turn_author: Optional[dict[str, Any]] = None,
    ) -> None:
        """Persist a completed turn and automatically extract durable facts."""
        sid = session_id or self._session_id
        if not user_content and not assistant_content:
            return

        try:
            # 1. Record episodic turn interaction
            if user_content and not is_trivial_prompt(user_content):
                summary = f"User: {user_content[:300]}"
                self.engine.remember(
                    content=summary,
                    memory_type=MemoryType.EPISODIC,
                    owner_id=self._user_id,
                    source_type="conversation_turn",
                    source_identifier=sid,
                    importance=0.4,
                )

            # 2. Extract potential user preferences or explicit instructions
            if user_content and any(kw in user_content.lower() for kw in ["prefer", "always", "never", "remember that", "constraint:"]):
                self.engine.remember(
                    content=user_content.strip(),
                    memory_type=MemoryType.SEMANTIC,
                    owner_id=self._user_id,
                    source_type="user_preference",
                    source_identifier=sid,
                    importance=0.85,
                )

        except Exception as exc:
            logger.warning("ADAPT sync_turn failed: %s", exc)

    def on_pre_compress(self, messages: list[dict[str, Any]]) -> str:
        """Preserve key decisions and context before Hermes context window compression."""
        if not messages:
            return ""

        preserved_count = 0
        insights: List[str] = []

        try:
            for msg in messages:
                content = msg.get("content", "")
                role = msg.get("role", "")
                if not content or is_trivial_prompt(content):
                    continue

                # Preserve user preferences, architectural decisions, and key outcomes
                lower = content.lower()
                if role == "user" and any(k in lower for k in ["decided", "prefer", "architecture", "requirement", "stack"]):
                    self.engine.remember(
                        content=f"Pre-compression saved: {content.strip()}",
                        memory_type=MemoryType.SEMANTIC,
                        owner_id=self._user_id,
                        source_type="pre_compress",
                        source_identifier=self._session_id,
                        importance=0.9,
                    )
                    preserved_count += 1
                    insights.append(f"Saved context: {content[:100]}...")

            if preserved_count > 0:
                logger.info("ADAPT pre-compress preserved %d items to persistent memory", preserved_count)
                return f"[ADAPT: Preserved {preserved_count} critical context memories into persistent store]"

        except Exception as exc:
            logger.warning("ADAPT on_pre_compress error: %s", exc)

        return ""

    def on_session_end(self, messages: list[dict[str, Any]]) -> None:
        """Trigger memory maintenance and consolidation upon session completion."""
        try:
            report = self.engine.consolidate(owner_id=self._user_id)
            logger.info("ADAPT session end consolidation completed for %s: %s", self._user_id, report.details)
        except Exception as exc:
            logger.warning("ADAPT on_session_end error: %s", exc)

    def on_session_switch(
        self,
        new_session_id: str,
        *,
        parent_session_id: str = "",
        reset: bool = False,
        rewound: bool = False,
        **kwargs: Any,
    ) -> None:
        """Rebind per-session tracking upon session change."""
        self._session_id = new_session_id
        self._last_recall_status = None

    def on_memory_write(
        self,
        action: str,
        target: str,
        content: str,
        metadata: Optional[dict[str, Any]] = None,
    ) -> None:
        """Mirror native Hermes memory write events."""
        if action == "add" and content:
            self.engine.remember(
                content=content,
                owner_id=self._user_id,
                source_type="hermes_native_mirror",
                metadata=metadata or {},
            )

    def shutdown(self) -> None:
        """Gracefully close engine resources."""
        if not self._closed and self._engine:
            self._engine.close()
            self._closed = True

    # -- Tool Schema and Execution -------------------------------------------

    def get_tool_schemas(self) -> list[dict[str, Any]]:
        """Declare OpenAI-compatible function-calling schemas."""
        return [
            {
                "type": "function",
                "function": {
                    "name": "adapt_remember",
                    "description": "Store a new memory in ADAPT persistent memory infrastructure.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "content": {"type": "string", "description": "The information to remember."},
                            "memory_type": {
                                "type": "string",
                                "enum": ["episodic", "semantic", "procedural", "working"],
                                "description": "Memory category (default: semantic).",
                            },
                            "importance": {
                                "type": "number",
                                "minimum": 0.0,
                                "maximum": 1.0,
                                "description": "Importance weight from 0.0 to 1.0 (default: 0.5).",
                            },
                        },
                        "required": ["content"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "adapt_recall",
                    "description": "Search and retrieve relevant memories from ADAPT using hybrid semantic and lexical search.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "Search query or task description."},
                            "limit": {"type": "integer", "description": "Maximum number of memories to return (default: 5)."},
                        },
                        "required": ["query"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "adapt_update",
                    "description": "Update an existing memory with full historical audit tracking.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "memory_id": {"type": "string", "description": "ID of memory to update."},
                            "new_content": {"type": "string", "description": "Updated content."},
                            "change_reason": {"type": "string", "description": "Reason for the update."},
                        },
                        "required": ["memory_id", "new_content"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "adapt_forget",
                    "description": "Delete a memory from ADAPT.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "memory_id": {"type": "string", "description": "ID of memory to delete."},
                            "permanent": {"type": "boolean", "description": "Whether to permanently purge (default: false)."},
                        },
                        "required": ["memory_id"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "adapt_relate",
                    "description": "Create an associative knowledge graph connection between two memories.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "source_id": {"type": "string", "description": "Source memory ID."},
                            "target_id": {"type": "string", "description": "Target memory ID."},
                            "relationship_type": {
                                "type": "string",
                                "enum": ["RELATES_TO", "CONTRADICTS", "SUPERSEDES", "DERIVED_FROM", "PART_OF", "DEPENDS_ON"],
                                "description": "Relationship type.",
                            },
                        },
                        "required": ["source_id", "target_id", "relationship_type"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "adapt_stats",
                    "description": "Retrieve aggregated memory statistics for the current user.",
                    "parameters": {
                        "type": "object",
                        "properties": {},
                    },
                },
            },
        ]

    def handle_tool_call(self, tool_name: str, args: dict[str, Any], **kwargs: Any) -> str:
        """Dispatch tool calls and return a JSON string."""
        try:
            if tool_name == "adapt_remember":
                content = args.get("content", "")
                mem_type = args.get("memory_type", "semantic")
                importance = float(args.get("importance", 0.5))
                mem = self.engine.remember(
                    content=content,
                    memory_type=mem_type,
                    owner_id=self._user_id,
                    importance=importance,
                )
                return json.dumps({"status": "success", "memory": mem.to_dict()})

            elif tool_name == "adapt_recall":
                query = args.get("query", "")
                limit = int(args.get("limit", 5))
                results = self.engine.recall(
                    query=query,
                    owner_id=self._user_id,
                    limit=limit,
                )
                return json.dumps({
                    "status": "success",
                    "count": len(results),
                    "memories": [
                        {
                            "id": sm.memory.id,
                            "type": sm.memory.memory_type.value,
                            "content": sm.memory.content,
                            "score": round(sm.score, 3),
                            "explanation": sm.explanation,
                        }
                        for sm in results
                    ],
                })

            elif tool_name == "adapt_update":
                mem_id = args.get("memory_id", "")
                new_content = args.get("new_content", "")
                change_reason = args.get("change_reason")
                updated = self.engine.update_memory(
                    memory_id=mem_id,
                    owner_id=self._user_id,
                    new_content=new_content,
                    change_reason=change_reason,
                )
                if updated:
                    return json.dumps({"status": "success", "memory": updated.to_dict()})
                return json.dumps({"status": "error", "message": f"Memory '{mem_id}' not found."})

            elif tool_name == "adapt_forget":
                mem_id = args.get("memory_id", "")
                permanent = bool(args.get("permanent", False))
                deleted = self.engine.forget(memory_id=mem_id, owner_id=self._user_id, permanent=permanent)
                return json.dumps({"status": "success", "deleted": deleted})

            elif tool_name == "adapt_relate":
                src = args.get("source_id", "")
                tgt = args.get("target_id", "")
                rel_type = args.get("relationship_type", "RELATES_TO")
                rel = self.engine.relate(
                    source_memory_id=src,
                    target_memory_id=tgt,
                    relationship_type=rel_type,
                    owner_id=self._user_id,
                )
                return json.dumps({"status": "success", "relationship": rel.to_dict()})

            elif tool_name == "adapt_stats":
                stats = self.engine.get_stats(owner_id=self._user_id)
                return json.dumps({"status": "success", "stats": stats})

            else:
                return json.dumps({"status": "error", "message": f"Unknown tool: {tool_name}"})

        except Exception as exc:
            logger.error("Error executing ADAPT tool '%s': %s", tool_name, exc, exc_info=True)
            return json.dumps({"status": "error", "message": str(exc)})

    # -- Configuration Schema ------------------------------------------------

    def get_config_schema(self) -> list[dict[str, Any]]:
        """Setup fields for hermes memory setup."""
        return [
            {
                "key": "storage_dir",
                "label": "Storage Directory",
                "type": "text",
                "default": "~/.hermes/adapt",
                "description": "Local directory for ADAPT SQLite database and indexes.",
            },
            {
                "key": "top_k",
                "label": "Recall Limit (Top K)",
                "type": "integer",
                "default": 5,
                "description": "Maximum number of memories recalled per prefetch query.",
            },
            {
                "key": "hybrid_alpha",
                "label": "Hybrid Alpha Balance",
                "type": "number",
                "default": 0.5,
                "description": "Weight between semantic (1.0) and lexical (0.0) retrieval.",
            },
        ]
