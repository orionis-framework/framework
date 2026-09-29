from __future__ import annotations
from enum import StrEnum

class Visibility(StrEnum):
    """
    Enumerate the visibility levels supported by storage drivers.

    Members inherit from :class:`str`, so they can be passed anywhere a
    plain visibility string is accepted.

    Attributes
    ----------
    PUBLIC : str
        The object is readable by anyone (e.g. world-readable file or
        publicly accessible cloud object).
    PRIVATE : str
        The object is only readable by the owning application.
    """

    PUBLIC = "public"
    PRIVATE = "private"
