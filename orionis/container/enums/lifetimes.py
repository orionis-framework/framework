from __future__ import annotations
from enum import Enum, auto

class Lifetime(Enum):
    """
    Define lifecycle types for dependency injection.

    This enumeration specifies how and when dependency instances are created and
    shared.

    Attributes
    ----------
    TRANSIENT : Lifetime
        Create a new instance every time the dependency is requested.
    SINGLETON : Lifetime
        Create a single shared instance for the application's lifetime.
    SCOPED : Lifetime
        Create and share an instance within a defined scope.

    Returns
    -------
    Lifetime
        An enumeration member representing the selected lifecycle type.
    """

    # Create a new instance every time the dependency is requested.
    TRANSIENT = auto()

    # Create a single shared instance for the application's lifetime.
    SINGLETON = auto()

    # Create and share an instance within a defined scope.
    SCOPED = auto()
