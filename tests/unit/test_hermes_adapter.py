"""Unit tests for ADAPT Hermes Memory Provider Plugin Adapter."""

import json
import pytest

from provider import AdaptMemoryProvider


@pytest.fixture
def provider(tmp_path):
    prov = AdaptMemoryProvider()
    prov.initialize(session_id="test_sess_001", hermes_home=str(tmp_path), user_id="alice")
    yield prov
    prov.shutdown()


def test_provider_metadata_and_availability(provider):
    """Test provider naming and availability checks."""
    assert provider.name == "adapt"
    assert provider.is_available() is True
    assert "ADAPT Active" in provider.system_prompt_block()


def test_prefetch_and_trivial_prompt_gate(provider):
    """Test that trivial queries are skipped and non-trivial queries inject context."""
    # 1. Trivial queries return empty without hitting the database
    assert provider.prefetch("ok") == ""
    assert provider.prefetch("thanks!") == ""
    assert provider.prefetch("yes") == ""
    assert provider.recall_status() is None

    # 2. Store memory and test recall prefetch
    provider.engine.remember(
        content="User requires Python 3.12 for all cloud functions.",
        owner_id="alice",
        importance=0.9,
    )

    context = provider.prefetch("What Python version should we use?")
    assert "<recalled_context provider=\"adapt\">" in context
    assert "Python 3.12" in context
    assert provider.recall_status() is not None
    assert provider.recall_status().count >= 1


def test_sync_turn_persistence(provider):
    """Test that sync_turn records episodic turn history and extracts preferences."""
    provider.sync_turn(
        user_content="I prefer using PostgreSQL over MongoDB for databases.",
        assistant_content="Understood, I will configure PostgreSQL.",
        session_id="sess_123",
    )

    # Verify episodic interaction recorded
    memories = provider.engine.storage.list_memories(owner_id="alice")
    contents = [m.content for m in memories]
    assert any("prefer using PostgreSQL" in c for c in contents)


def test_on_pre_compress_preservation(provider):
    """Test that on_pre_compress saves critical context facts before compression."""
    messages = [
        {"role": "user", "content": "We decided the system architecture will use gRPC for internal service communication."},
        {"role": "assistant", "content": "Acknowledged. gRPC configuration noted."},
    ]

    summary = provider.on_pre_compress(messages)
    assert "Preserved 1 critical context memories" in summary

    # Verify the memory actually exists in storage
    all_alice = provider.engine.storage.list_memories(owner_id="alice")
    contents = [m.content for m in all_alice]
    assert any("gRPC" in c for c in contents)


def test_on_session_end_consolidation(provider):
    """Test on_session_end triggers memory consolidation."""
    provider.engine.remember(content="Fact 1", owner_id="alice")
    # Calling on_session_end should not raise
    provider.on_session_end([])


def test_handle_tool_calls_return_json(provider):
    """Verify that all exposed tools execute properly and return valid JSON strings."""
    # 1. adapt_remember
    res_raw = provider.handle_tool_call(
        "adapt_remember",
        {"content": "Database password is rotated every 90 days.", "importance": 0.8},
    )
    res = json.loads(res_raw)
    assert res["status"] == "success"
    mem_id = res["memory"]["id"]

    # 2. adapt_recall
    recall_raw = provider.handle_tool_call(
        "adapt_recall",
        {"query": "password rotation policy", "limit": 3},
    )
    res_rec = json.loads(recall_raw)
    assert res_rec["status"] == "success"
    assert res_rec["count"] >= 1
    assert any("rotated every 90 days" in m["content"] for m in res_rec["memories"])

    # 3. adapt_update
    update_raw = provider.handle_tool_call(
        "adapt_update",
        {"memory_id": mem_id, "new_content": "Database password is rotated every 30 days.", "change_reason": "Compliance upgrade"},
    )
    res_up = json.loads(update_raw)
    assert res_up["status"] == "success"
    assert "30 days" in res_up["memory"]["content"]

    # 4. adapt_relate
    res_m2 = json.loads(provider.handle_tool_call(
        "adapt_remember", {"content": "Rotation audit script is located at scripts/rotate.py"}
    ))
    m2_id = res_m2["memory"]["id"]

    rel_raw = provider.handle_tool_call(
        "adapt_relate",
        {"source_id": mem_id, "target_id": m2_id, "relationship_type": "DEPENDS_ON"},
    )
    res_rel = json.loads(rel_raw)
    assert res_rel["status"] == "success"

    # 5. adapt_stats
    stats_raw = provider.handle_tool_call("adapt_stats", {})
    res_stats = json.loads(stats_raw)
    assert res_stats["status"] == "success"
    assert res_stats["stats"]["total_memories"] >= 2

    # 6. adapt_forget
    forget_raw = provider.handle_tool_call("adapt_forget", {"memory_id": mem_id})
    res_forget = json.loads(forget_raw)
    assert res_forget["status"] == "success"
    assert res_forget["deleted"] is True

