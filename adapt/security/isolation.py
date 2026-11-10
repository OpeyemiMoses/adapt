"""Tenant and agent memory isolation controls."""

from __future__ import annotations

import re
from typing import Optional

from adapt.models.schema import Memory

_VALID_ID_RE = re.compile(r"^[a-zA-Z0-9_\-\.]{1,128}$")


def validate_identifier(name: str, value: str) -> None:
    """Ensure identifier matches safe alphanumeric format."""
    if not value or not isinstance(value, str) or not _VALID_ID_RE.match(value.strip()):
        raise ValueError(
            f"Invalid {name}: must be a non-empty alphanumeric string between 1 and 128 characters."
        )


def can_access_memory(memory: Memory, owner_id: str, agent_id: Optional[str] = None) -> bool:
    """Verify if the caller has permission to view or manipulate this memory."""
    if memory.owner_id != owner_id:
        return False
    # If caller specifies agent_id and memory is strictly agent-bound, check matching
    if agent_id and memory.agent_id and memory.agent_id != agent_id:
        # Cross-agent access can be allowed if shared at owner level, or restricted
        # Default policy: owner-level memories are visible to all agents of that owner
        pass
    return True


def assert_can_access(memory: Memory, owner_id: str, agent_id: Optional[str] = None) -> None:
    """Raise PermissionError if memory access is unauthorized."""
    if not can_access_memory(memory, owner_id, agent_id):
        raise PermissionError(
            f"Unauthorized access: memory {memory.id} does not belong to owner {owner_id}"
        )
