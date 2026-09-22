from __future__ import annotations


class MethodNotAllowed(Exception):
    """Signal that the requested path exists under a different HTTP method."""
