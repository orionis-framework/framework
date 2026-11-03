"""Define enumeration of route types for the framework."""

from enum import StrEnum


class RouteType(StrEnum):
    """
    Define enumeration of route types for the framework.

    This enumeration specifies the different types of routes that can be
    defined in the framework, each with distinct handling behavior.
    """

    CONTROLLER = "controller"
    """Controller identifier: ``controller``."""
    FUNCTION = "function"
    """Function identifier: ``function``."""
    INVOKABLE = "invokable"
    """Invokable identifier: ``invokable``."""
    VIEW = "view"
    """View identifier: ``view``."""
    HUB = "hub"
    """Hub identifier: ``hub``."""
