"""Small protocol error hierarchy with sanitized public messages."""

import msgspec


class McpProtocolException(Exception):
    """Carry an explicitly safe JSON-RPC error and HTTP status."""

    __slots__ = ("code", "data", "message", "status")

    def __init__(
        self, code: int, message: str, *, status: int = 400,
        data: object = msgspec.UNSET,
    ) -> None:
        """Store safe public error details without exposing a cause."""
        super().__init__(message)
        self.code = code
        self.message = message
        self.status = status
        self.data = data


class McpInvalidParams(McpProtocolException):
    """Reject malformed method parameters."""

    __slots__ = ()

    def __init__(
        self, message: str = "Invalid params", *, data: object = msgspec.UNSET,
    ) -> None:
        """Use the standard JSON-RPC invalid-params code."""
        super().__init__(-32602, message, data=data)


class McpAuthorizationException(McpProtocolException):
    """Deny a primitive through its explicit authorization hook."""

    __slots__ = ()

    def __init__(self) -> None:
        """Avoid revealing policy or identity details."""
        super().__init__(-32602, "Access denied", status=403)
