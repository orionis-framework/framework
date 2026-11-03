"""Enumerate supported cache drivers."""

from enum import StrEnum

class Drivers(StrEnum):
    """
    Enumerate supported cache drivers.

    Attributes
    ----------
    FILE : str
        Represents a file-based cache driver.
    MEMCACHED : str
        Represents a Memcached cache driver.
    REDIS : str
        Represents a Redis cache driver.

    Returns
    -------
    orionis.foundation.config.cache.Drivers
        An enumeration member representing a cache driver.
    """

    FILE = "file"
    MEMCACHED = "memcached"
    MEMORY = "memory"
    """Memory identifier: ``memory``."""
    REDIS = "redis"
    DATABASE = "database"
    """Database identifier: ``database``."""
