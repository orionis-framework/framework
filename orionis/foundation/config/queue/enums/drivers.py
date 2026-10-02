from enum import StrEnum

class Drivers(StrEnum):
    """Enumerate supported queue connection drivers."""

    SYNC = "sync"
    DATABASE = "database"
    REDIS = "redis"
