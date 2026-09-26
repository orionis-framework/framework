from enum import StrEnum

class SessionDriver(StrEnum):
    """
    Enumeration of supported session storage drivers.

    Attributes
    ----------
    MEMORY : str
        In-memory session storage.
    FILE : str
        File-based session storage.
    DATABASE : str
        Database-backed session storage.
    CACHE : str
        Cache-based session storage.
    """

    MEMORY = "memory"
    FILE = "file"
    DATABASE = "database"
    CACHE = "cache"
