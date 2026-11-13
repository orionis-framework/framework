"""Preserve transport incidents when exposing WebSocket disconnect controls."""

from orionis.failure.runtime import capture, current_operation, handoff
from orionis.http.exceptions.websocket import WebSocketDisconnected


async def disconnected(
    error: Exception,
    *,
    transport: str,
    phase: str,
    expected: bool = False,
) -> WebSocketDisconnected:
    """
    Observe a transport error and associate its public disconnect wrapper.

    Parameters
    ----------
    error : Exception
        Original transport failure.
    transport : str
        Server protocol name.
    phase : str
        Transport operation that failed.
    expected : bool, optional
        Whether the server reports an ordinary closed connection.

    Returns
    -------
    WebSocketDisconnected
        Existing public control exception, associated with the same incident.
    """
    receipt = await capture(
        error,
        flow="websocket",
        phase=phase,
        expected=expected,
        metadata={"transport": transport},
    )
    result = WebSocketDisconnected()
    handoff(result, target=current_operation(), receipt=receipt)
    return result
