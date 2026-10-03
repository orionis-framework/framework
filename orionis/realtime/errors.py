class RPCError(Exception):
    """Report a deliberate, client-safe remote invocation failure."""

    __slots__ = ("code", "message")

    def __init__(self, code: str, message: str) -> None:
        """
        Retain the explicit public error code and message.

        Parameters
        ----------
        code : str
            Stable application or framework error identifier.
        message : str
            Public explanation that must not contain secrets.

        Returns
        -------
        None
            Initialize the controlled invocation error.
        """
        self.code = code
        self.message = message
        super().__init__(message)


class ProtocolError(ValueError):
    """Report an invalid envelope or incompatible WebSocket frame."""

    __slots__ = ("close_code",)

    def __init__(
        self, message: str = "Invalid realtime message", close_code: int = 1002,
    ) -> None:
        """
        Retain a sanitized explanation and the appropriate close code.

        Parameters
        ----------
        message : str, optional
            Safe protocol error description.
        close_code : int, optional
            WebSocket close code; defaults to protocol violation.

        Returns
        -------
        None
            Initialize a connection-level protocol failure.
        """
        self.close_code = close_code
        super().__init__(message)


class ClientInvocationError(RPCError):
    """Report a client completion failure to the invoking application service."""

    __slots__ = ()
