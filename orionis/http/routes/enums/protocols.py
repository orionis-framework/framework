"""Identify a route's transport independently of its handler action type."""

from enum import StrEnum


class RouteProtocol(StrEnum):
    """Identify a route's transport independently of its handler action type."""

    HTTP = "http"
    """Http identifier: ``http``."""
    WEBSOCKET = "websocket"
    """Websocket identifier: ``websocket``."""
