"""Integration tests for Cross-Session Memory Continuity."""

from provider import AdaptMemoryProvider


def test_cross_session_continuity_after_restart(tmp_path):
    """Scenario 1: Verify memory survives process restart across independent sessions."""
    # Session 1: Agent learns user architectural preferences
    provider_1 = AdaptMemoryProvider()
    provider_1.initialize(session_id="session_alpha", hermes_home=str(tmp_path), user_id="charlie")

    provider_1.sync_turn(
        user_content="We decided that all background tasks will run using Celery workers with Redis broker.",
        assistant_content="Got it. I have noted Celery with Redis for background workers.",
        session_id="session_alpha",
    )
    # Session wraps up
    provider_1.on_session_end([])
    provider_1.shutdown()

    # --- PROCESS RESTART SIMULATION ---

    # Session 2: A brand new agent session starts
    provider_2 = AdaptMemoryProvider()
    provider_2.initialize(session_id="session_beta", hermes_home=str(tmp_path), user_id="charlie")

    # Agent prefetch before user prompt
    prompt = "How should we implement the async video export job?"
    recalled_context = provider_2.prefetch(prompt, session_id="session_beta")

    assert "<recalled_context provider=\"adapt\">" in recalled_context
    assert "Celery" in recalled_context
    assert "Redis" in recalled_context
    assert provider_2.recall_status() is not None
    assert provider_2.recall_status().count >= 1

    provider_2.shutdown()

