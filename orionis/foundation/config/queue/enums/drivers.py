"""Enumerate supported queue connection drivers."""

from enum import StrEnum


class Drivers(StrEnum):
    """Enumerate supported queue connection drivers."""

    SYNC = "sync"
    """Sync identifier: ``sync``."""
    DATABASE = "database"
    """Database identifier: ``database``."""
    REDIS = "redis"
    """Redis identifier: ``redis``."""
