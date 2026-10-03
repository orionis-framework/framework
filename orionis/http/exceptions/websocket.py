class WebSocketDisconnected(RuntimeError):
    """Report a terminal connection failure with available close details."""

    def __init__(self, code: int = 1006, reason: str = "") -> None:
        """
        Store the observed close details.

        Parameters
        ----------
        code : int, optional
            Close code, or abnormal closure when unavailable.
        reason : str, optional
            Peer or locally generated close reason.

        Returns
        -------
        None
            Initialize the failure.
        """
        self.code = code
        self.reason = reason
        super().__init__(f"WebSocket disconnected ({code}): {reason}")
