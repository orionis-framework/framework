import asyncio
from collections import OrderedDict
from typing import TYPE_CHECKING
from orionis.mcp.contracts.event_bus import IMcpEventBus
from orionis.mcp.exceptions import McpProtocolException
from orionis.mcp.streams import AsyncClosable

if TYPE_CHECKING:
    from collections.abc import AsyncIterator
    from orionis.mcp.protocol.requests import SubscriptionFilter

type Change = tuple[str, str | None]

class _Listener:
    """Retain only a server key, accepted filter and bounded pending changes."""

    __slots__ = ("closed", "filters", "pending", "ready", "server")

    def __init__(self, server: type, filters: SubscriptionFilter) -> None:
        """
        Create an empty process-local listener.

        Parameters
        ----------
        server : type
            Value supplied for ``server``.
        filters : SubscriptionFilter
            Value supplied for ``filters``.

        Returns
        -------
        None
            Complete the documented operation without returning a value.
        """
        self.server = server
        self.filters = filters
        self.pending: OrderedDict[Change, None] = OrderedDict()
        self.ready = asyncio.Event()
        self.closed = False

    def accepts(self, method: str, uri: str | None) -> bool:
        """
        Match only notification types explicitly requested by the client.

        Parameters
        ----------
        method : str
            Value supplied for ``method``.
        uri : str | None
            Value supplied for ``uri``.

        Returns
        -------
        bool
            Result of the operation described above.
        """
        match method:
            case "notifications/tools/list_changed":
                return self.filters.toolsListChanged
            case "notifications/prompts/list_changed":
                return self.filters.promptsListChanged
            case "notifications/resources/list_changed":
                return self.filters.resourcesListChanged
            case "notifications/resources/updated":
                return uri in self.filters.resourceSubscriptions
            case _:
                return False

class InMemoryMcpEventBus(IMcpEventBus):
    """Coalesce duplicate changes and close overloaded listeners gracefully."""

    __slots__ = ("_closed", "_listeners", "_max_listeners", "_size")

    def __init__(self, buffer_size: int = 64, max_listeners: int = 1024) -> None:
        """
        Set finite listener and per-listener buffer budgets.

        Parameters
        ----------
        buffer_size : int
            Value supplied for ``buffer_size``.
        max_listeners : int
            Value supplied for ``max_listeners``.

        Returns
        -------
        None
            Complete the documented operation without returning a value.
        """
        if type(buffer_size) is not int or type(max_listeners) is not int:
            error = "Subscription limits must be integers"
            raise TypeError(error)
        if buffer_size < 1 or max_listeners < 1:
            error = "Subscription limits must be positive"
            raise ValueError(error)
        self._size = buffer_size
        self._max_listeners = max_listeners
        self._listeners: set[_Listener] = set()
        self._closed = False

    @property
    def listener_count(self) -> int:
        """
        Expose aggregate lifecycle diagnostics, without subscriber identity.

        Returns
        -------
        int
            Result of the operation described above.
        """
        return len(self._listeners)

    def listen(
        self,
        server: type,
        filters: SubscriptionFilter,
    ) -> AsyncIterator[Change]:
        """
        Register synchronously so publication cannot race acknowledgment.

        Parameters
        ----------
        server : type
            Value supplied for ``server``.
        filters : SubscriptionFilter
            Value supplied for ``filters``.

        Returns
        -------
        AsyncIterator[Change]
            Result of the operation described above.
        """
        if self._closed or len(self._listeners) >= self._max_listeners:
            raise McpProtocolException(
                -32603, "Subscription capacity unavailable", status=503,
            )
        listener = _Listener(server, filters)
        self._listeners.add(listener)
        return _Subscription(self, listener)

    async def publish(self, server: type, method: str, uri: str | None = None) -> None:
        """
        Publish without awaiting a slow client or creating producer tasks.

        Parameters
        ----------
        server : type
            Value supplied for ``server``.
        method : str
            Value supplied for ``method``.
        uri : str | None
            Value supplied for ``uri``.

        Returns
        -------
        None
            Complete the documented operation without returning a value.
        """
        change = (method, uri)
        for listener in self._listeners:
            if (
                listener.closed
                or listener.server is not server
                or not listener.accepts(method, uri)
            ):
                continue
            if change in listener.pending:
                continue
            if len(listener.pending) >= self._size:
                listener.closed = True
                listener.pending.clear()
            else:
                listener.pending[change] = None
            listener.ready.set()

    def remove(self, listener: _Listener) -> None:
        """
        Release an iterator even if it was closed before its first read.

        Parameters
        ----------
        listener : _Listener
            Value supplied for ``listener``.

        Returns
        -------
        None
            Complete the documented operation without returning a value.
        """
        self._listeners.discard(listener)
        listener.pending.clear()
        listener.closed = True
        listener.ready.set()

    async def shutdown(self) -> None:
        """
        Stop admission and wake all consumers to send graceful completion.

        Returns
        -------
        None
            Complete the documented operation without returning a value.
        """
        self._closed = True
        for listener in self._listeners:
            listener.closed = True
            listener.pending.clear()
            listener.ready.set()

class _Subscription(AsyncClosable):
    """An explicitly closable iterator, including before first iteration."""

    __slots__ = ("_bus", "_listener")

    def __init__(self, bus: InMemoryMcpEventBus, listener: _Listener) -> None:
        """
        Own exactly one listener registration.

        Parameters
        ----------
        bus : InMemoryMcpEventBus
            Value supplied for ``bus``.
        listener : _Listener
            Value supplied for ``listener``.

        Returns
        -------
        None
            Complete the documented operation without returning a value.
        """
        self._bus = bus
        self._listener = listener

    def __aiter__(self) -> AsyncIterator[Change]:
        """
        Return the subscription iterator.

        Returns
        -------
        AsyncIterator[Change]
            The subscription iterator.
        """
        return self

    async def __anext__(self) -> Change:
        """
        Wait without losing wakeups; propagate cancellation after cleanup.

        Returns
        -------
        Change
            Result of the operation described above.
        """
        listener = self._listener
        try:
            while not listener.closed:
                if listener.pending:
                    return listener.pending.popitem(last=False)[0]
                listener.ready.clear()
                await listener.ready.wait()
            self._bus.remove(listener)
            raise StopAsyncIteration
        except asyncio.CancelledError:
            self._bus.remove(listener)
            raise

    async def aclose(self) -> None:
        """
        Release request-owned resources immediately.

        Returns
        -------
        None
            Complete the documented operation without returning a value.
        """
        self._bus.remove(self._listener)
