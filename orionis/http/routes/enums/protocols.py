from enum import StrEnum


class RouteProtocol(StrEnum):
    """Identify a route's transport independently of its handler action type."""

    HTTP = "http"
    WEBSOCKET = "websocket"
