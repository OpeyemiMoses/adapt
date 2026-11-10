"""Security and Tenant Isolation Tests for ADAPT."""

import pytest

from adapt.core.engine import AdaptEngine
from adapt.storage.sqlite import SQLiteStorage


def test_cross_tenant_isolation_enforcement(tmp_path):
    """Scenario 3: Multi-tenant memory boundaries are strictly enforced."""
    db_file = tmp_path / "multi_tenant.db"
    storage = SQLiteStorage(db_path=str(db_file))
    engine = AdaptEngine(storage=storage)

    # 1. Tenant A stores private knowledge
    mem_a = engine.remember(
        content="Tenant A proprietary API secret token: sk-live-99999999",
        owner_id="tenant_alpha",
    )

    # 2. Tenant B attempts direct lookup
    assert engine.get_memory(mem_a.id, owner_id="tenant_beta") is None

    # 3. Tenant B attempts hybrid recall with exact token
    recalled_b = engine.recall(
        query="sk-live-99999999",
        owner_id="tenant_beta",
    )
    assert len(recalled_b) == 0

    # 4. Tenant B attempts keyword search
    search_b = engine.search(
        query="proprietary secret",
        owner_id="tenant_beta",
    )
    assert len(search_b) == 0

    # 5. Tenant B attempts modification
    assert engine.update_memory(
        memory_id=mem_a.id,
        owner_id="tenant_beta",
        new_content="Hacked content",
    ) is None

    # 6. Tenant B attempts deletion
    assert engine.forget(memory_id=mem_a.id, owner_id="tenant_beta") is False

    # 7. Tenant B cannot link Tenant A's memory in knowledge graph
    mem_b = engine.remember(content="Tenant B memory", owner_id="tenant_beta")
    with pytest.raises(ValueError, match="same owner"):
        engine.relate(
            source_memory_id=mem_a.id,
            target_memory_id=mem_b.id,
            owner_id="tenant_beta",
        )

    engine.close()

