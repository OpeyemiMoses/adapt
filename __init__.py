"""Hermes Agent Memory Provider Plugin entry point for ADAPT."""

from __future__ import annotations

import logging

from .provider import AdaptMemoryProvider

logger = logging.getLogger(__name__)


def register(ctx) -> None:
    """Entry point called by the Hermes plugin loader."""
    provider = AdaptMemoryProvider()
    if hasattr(ctx, "register_memory_provider"):
        ctx.register_memory_provider(provider)
    elif hasattr(ctx, "register_provider"):
        ctx.register_provider(provider)
    logger.debug("Registered ADAPT memory provider plugin")


__all__ = ["register", "AdaptMemoryProvider"]

