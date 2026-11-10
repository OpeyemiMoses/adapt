"""Core exception classes for ADAPT memory system."""

from __future__ import annotations


class AdaptError(Exception):
    """Base exception for all ADAPT operations."""
    pass


class MemoryNotFoundError(AdaptError):
    """Raised when requested memory does not exist or has been deleted."""
    pass


class UnauthorizedAccessError(AdaptError):
    """Raised when memory access violates tenant isolation."""
    pass


class ValidationError(AdaptError):
    """Raised when incoming parameters or schema validation fails."""
    pass
