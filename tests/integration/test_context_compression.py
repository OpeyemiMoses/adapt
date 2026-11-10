"""Integration tests for Context Window Compression Preservation."""

from integrations.hermes.provider import AdaptMemoryProvider


def test_context_compression_preservation(tmp_path):
    """Scenario 2: Verify memories survive context window compaction."""
    provider = AdaptMemoryProvider()
    provider.initialize(session_id="session_long_thread", hermes_home=str(tmp_path), user_id="charlie")

    # Simulate messages about to be pruned by Hermes during context compression
    messages_to_compress = [
        {"role": "user", "content": "Hello, let's start planning the API architecture."},
        {"role": "assistant", "content": "Sure, what framework do you prefer?"},
        {
            "role": "user",
            "content": "We decided the system architecture requirement is gRPC for inter-service RPC calls with Protobuf 3.",
        },
        {"role": "assistant", "content": "Understood. Creating the proto definitions."},
        {"role": "user", "content": "Also, the staging database password must never be logged."},
    ]

    # Hook runs right before Hermes compacts the conversation history
    compression_summary = provider.on_pre_compress(messages_to_compress)
    assert "Preserved" in compression_summary

    # Fast forward: After compaction, agent starts fresh turn with truncated messages
    # Prefetch query requiring the preserved decision
    recalled = provider.prefetch("What RPC protocol did we pick for inter-service calls?")
    assert "gRPC" in recalled
    assert "Protobuf 3" in recalled

    provider.shutdown()
