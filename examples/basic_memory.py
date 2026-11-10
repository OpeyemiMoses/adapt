#!/usr/bin/env python3
"""Basic standalone example demonstrating ADAPT persistent memory operations."""

import os
import shutil
from pathlib import Path

from adapt.core.engine import AdaptEngine
from adapt.models.schema import MemoryType, RelationshipType


def main() -> None:
    demo_dir = Path("/tmp/adapt_demo_storage")
    if demo_dir.exists():
        shutil.rmtree(demo_dir)

    print("=== ADAPT: Persistent Memory Infrastructure ===")
    print(f"Initializing ADAPT engine at {demo_dir}...")
    engine = AdaptEngine(storage_dir=str(demo_dir))

    # 1. Store Semantic Knowledge (User Preferences & Architecture)
    print("\n1. Ingesting memories...")
    mem_pref = engine.remember(
        content="User prefers Python with FastAPI for backend and Tailwind CSS for frontend styling.",
        memory_type=MemoryType.SEMANTIC,
        owner_id="alice",
        agent_id="hermes_primary",
        importance=0.9,
        source_type="conversation",
        source_identifier="session_01:turn_1",
    )
    print(f"   [+] Stored Semantic Memory: '{mem_pref.content}' (ID: {mem_pref.id})")

    mem_arch = engine.remember(
        content="Primary production database is PostgreSQL 16 hosted on Supabase with connection pooling enabled.",
        memory_type=MemoryType.SEMANTIC,
        owner_id="alice",
        agent_id="hermes_primary",
        importance=0.95,
        source_type="conversation",
        source_identifier="session_01:turn_2",
    )
    print(f"   [+] Stored Architecture Fact: '{mem_arch.content}' (ID: {mem_arch.id})")

    mem_proc = engine.remember(
        content="To execute database migrations: export DATABASE_URL and run `alembic upgrade head`.",
        memory_type=MemoryType.PROCEDURAL,
        owner_id="alice",
        agent_id="hermes_primary",
        importance=0.8,
        source_type="runbook",
        source_identifier="docs/deploy.md",
    )
    print(f"   [+] Stored Procedural Runbook: '{mem_proc.content}' (ID: {mem_proc.id})")

    # 2. Form Associative Knowledge Graph Connections
    print("\n2. Linking related knowledge in graph...")
    rel = engine.relate(
        source_memory_id=mem_arch.id,
        target_memory_id=mem_proc.id,
        relationship_type=RelationshipType.DEPENDS_ON,
        confidence=1.0,
        owner_id="alice",
    )
    print(f"   [+] Linked: Database Fact --({rel.relationship_type.value})--> Migration Runbook")

    # 3. Contextual Recall with Associative Traversal
    print("\n3. Recalling context for query: 'PostgreSQL database'...")
    recalled = engine.recall(
        query="PostgreSQL database",
        owner_id="alice",
        include_related=True,
        limit=5,
    )
    for i, scored in enumerate(recalled, 1):
        print(f"   Match {i}: [{scored.score:.2f}] ({scored.memory.memory_type.value.upper()}) {scored.memory.content}")
        if scored.explanation:
            print(f"            Reason: {scored.explanation}")

    # 4. Evolving Knowledge (Updating with Provenance History)
    print("\n4. Evolving knowledge (updating fact)...")
    updated = engine.update_memory(
        memory_id=mem_pref.id,
        owner_id="alice",
        new_content="User prefers Python with FastAPI for backend and Shadcn UI with Tailwind CSS for frontend.",
        change_reason="User refined frontend component library preference",
    )
    print(f"   [+] Updated content: '{updated.content}'")

    versions = engine.storage.get_versions(mem_pref.id)
    print(f"   [+] Verified audit version history (Count: {len(versions)}):")
    for v in versions:
        print(f"       Previous: '{v.previous_content}' | Reason: {v.change_reason}")

    # 5. Telemetry & Stats
    print("\n5. Memory System Statistics for Alice:")
    stats = engine.get_stats(owner_id="alice")
    for k, v in stats.items():
        print(f"   {k}: {v}")

    engine.close()
    print("\n=== Demo completed successfully! ===")


if __name__ == "__main__":
    main()

