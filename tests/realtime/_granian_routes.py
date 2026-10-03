from orionis.http import WebSocket  # noqa: TC001 - Runtime handler injection.
from orionis.realtime import Hub, remote
from orionis.support.facades.router import Route


async def echo(socket: WebSocket) -> None:
    """
    Echo normalized text and binary frames through the real server adapter.

    Parameters
    ----------
    socket : WebSocket
        Connection supplied by the real server adapter.

    Returns
    -------
    None
        Accept the connection and echo frames until peer disconnection.
    """
    await socket.accept()
    async for message in socket:
        if message.isText():
            await socket.sendText(message.text)
        elif message.isBytes():
            await socket.sendBytes(message.bytes)


class SmokeHub(Hub):
    """Expose arithmetic and a bidirectional invocation over real TCP sockets."""

    __slots__ = ()

    @remote
    async def add(self, first: int, second: int) -> int:
        """
        Return the sum of two validated client-bound arguments.

        Parameters
        ----------
        first : int
            First client operand.
        second : int
            Second client operand.

        Returns
        -------
        int
            Sum of the validated operands.
        """
        return first + second

    @remote
    async def ask(self) -> object:
        """
        Wait for a client result while the connection reader remains active.

        Returns
        -------
        object
            Client state returned by the correlated invocation.

        Raises
        ------
        TimeoutError
            If sending or receiving the client result exceeds three seconds.
        """
        return await self.clients.caller.invoke("getState", timeout=3)


Route.websocket("/echo", echo)
Route.hub("/json", SmokeHub)
Route.hub("/msgpack", SmokeHub, protocol="msgpack")
