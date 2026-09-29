from __future__ import annotations

class CacheException(Exception):
    """Base exception for all cache-related errors."""

class CacheStoreException(CacheException):
    """Raised when an unknown or misconfigured cache store is requested."""
