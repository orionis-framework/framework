from __future__ import annotations


class RouteNotFound(Exception):
    """Signal that no route matches the requested path under any HTTP method."""
