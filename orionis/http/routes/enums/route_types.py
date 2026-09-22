from enum import StrEnum


class RouteType(StrEnum):
    """
    Define enumeration of route types for the framework.

    This enumeration specifies the different types of routes that can be
    defined in the framework, each with distinct handling behavior.
    """

    CONTROLLER = "controller"
    FUNCTION = "function"
    INVOKABLE = "invokable"
    VIEW = "view"
