"""Provide mcp operations.

Includes ``McpProtocolException``, ``McpInvalidParams``,
``McpAuthorizationException``.
"""

import msgspec

class McpProtocolException(Exception):
    """Carry an explicitly safe JSON-RPC error and HTTP status."""

    __slots__ = ("code", "data", "message", "status")
    """Declare the instance attribute slots reserved by this class."""

    def __init__(
        self, code: int, message: str, *, status: int = 400,
        data: object = msgspec.UNSET,
    ) -> None:
        """
        Store safe public error details without exposing a cause.

        Parameters
        ----------
        code : int
            Value supplied for ``code``.
        message : str
            Value supplied for ``message``.
        status : int
            Value supplied for ``status``.
        data : object
            Value supplied for ``data``.

        Returns
        -------
        None
            Complete the documented operation without returning a value.
        """
        super().__init__(message)
        self.code = code
        """Value supplied for ``code``."""
        self.message = message
        """Value supplied for ``message``."""
        self.status = status
        """Value supplied for ``status``."""
        self.data = data
        """Value supplied for ``data``."""

class McpInvalidParams(McpProtocolException):
    """Reject malformed method parameters."""

    __slots__ = ()
    """Declare that this class introduces no additional instance slots."""

    def __init__(
        self, message: str = "Invalid params", *, data: object = msgspec.UNSET,
    ) -> None:
        """
        Use the standard JSON-RPC invalid-params code.

        Parameters
        ----------
        message : str
            Value supplied for ``message``.
        data : object
            Value supplied for ``data``.

        Returns
        -------
        None
            Complete the documented operation without returning a value.
        """
        super().__init__(-32602, message, data=data)

class McpAuthorizationException(McpProtocolException):
    """Deny a primitive through its explicit authorization hook."""

    __slots__ = ()
    """Declare that this class introduces no additional instance slots."""

    def __init__(self) -> None:
        """
        Avoid revealing policy or identity details.

        Returns
        -------
        None
            Complete the documented operation without returning a value.
        """
        super().__init__(-32602, "Access denied", status=403)
