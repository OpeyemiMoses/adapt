"""Declarative configuration schema for ADAPT Hermes plugin."""

from __future__ import annotations

try:
    from plugins.memory.config_schema import (
        KIND_NUMBER,
        KIND_TEXT,
        ProviderConfigSchema,
        ProviderField,
    )
    SCHEMA = ProviderConfigSchema(
        name="adapt",
        label="ADAPT Memory",
        fields=(
            ProviderField(
                key="storage_dir",
                label="Storage Directory",
                kind=KIND_TEXT,
                default="~/.hermes/adapt",
                description="Local directory for ADAPT SQLite persistence.",
            ),
            ProviderField(
                key="top_k",
                label="Recall Limit (Top K)",
                kind=KIND_NUMBER,
                default="5",
                description="Number of memories recalled into prefetch prompt.",
            ),
        ),
    )
except ImportError:
    SCHEMA = None
