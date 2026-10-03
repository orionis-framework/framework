import asyncio
from math import isfinite
from typing import TYPE_CHECKING
import msgspec
from orionis.realtime.errors import ClientInvocationError

if TYPE_CHECKING:
    from orionis.foundation.config.realtime.entities.realtime import RealtimeConfig
    from orionis.http import WebSocket
    from orionis.realtime.hub import Hub, HubContext
    from orionis.realtime.protocol import Completion, HubProtocol

_TARGET_LIMIT = 128
_ARGUMENT_LIMIT = 64

class RealtimeConnection:
    """Own tasks and pending client results for exactly one connection."""

    __slots__ = (
        "__weakref__", "_cancel_requested", "_counter", "_write_lock",
        "_write_task", "active",
        "closing", "config", "context", "failure", "finishing", "hub", "owner",
        "pending", "protocol",
        "ready", "socket",
    )

    def __init__(
        self, context: HubContext, hub: type[Hub], protocol: HubProtocol,
        config: RealtimeConfig,
    ) -> None:
        """
        Bind immutable context and initialize finite connection registries.

        Parameters
        ----------
        context : HubContext
            Connection identity and public socket.
        hub : type[Hub]
            Application-owned Hub type.
        protocol : HubProtocol
            Route-selected codec.
        config : RealtimeConfig
            Invocation and broadcast limits.

        Returns
        -------
        None
            Initialize owned tasks, pending results and serialized write state.

        Raises
        ------
        RuntimeError
            If no event loop is running to identify the connection owner.
        """
        self.context = context
        self.socket: WebSocket = context.socket
        self.hub = hub
        self.protocol = protocol
        self.config = config
        self.active: dict[str, asyncio.Task[None]] = {}
        self.finishing: set[asyncio.Task[None]] = set()
        self._cancel_requested: set[str] = set()
        self.pending: dict[str, asyncio.Future[object]] = {}
        self.owner: asyncio.Task | None = asyncio.current_task()
        self.ready = False
        self.closing = False
        self.failure: BaseException | None = None
        self._counter = 0
        self._write_lock = asyncio.Lock()
        self._write_task: asyncio.Task[None] | None = None

    def _writeDone(self, task: asyncio.Task[None]) -> None:
        """
        Release write ownership even when its original caller was cancelled.

        Parameters
        ----------
        task : asyncio.Task[None]
            Completed task for the sole in-flight transport write.

        Returns
        -------
        None
            Release the write lock and cancel the owner after a failed write.
        """
        self._write_task = None
        self._write_lock.release()
        failure = None if task.cancelled() else task.exception()
        failed = task.cancelled() or failure is not None
        if failed and not self.closing:
            self.closing = True
            self.failure = failure
            if self.owner is not None and not self.owner.cancelling():
                self.owner.cancel()

    def invocationDone(self, invocation_id: str, task: asyncio.Task[None]) -> None:
        """
        Retrieve invocation failures and wake a reader after fatal delivery.

        Parameters
        ----------
        invocation_id : str
            Identifier owned by this task, including cancellation before entry.
        task : asyncio.Task[None]
            Invocation whose local cleanup has already run.

        Returns
        -------
        None
            Release task ownership and cancel the connection owner on failure.
        """
        if self.active.get(invocation_id) is task:
            self.active.pop(invocation_id)
            self._cancel_requested.discard(invocation_id)
        self.finishing.discard(task)
        failure = None if task.cancelled() else task.exception()
        if failure is not None and not self.closing:
            self.failure = failure
            self.closing = True
            if self.owner is not None and not self.owner.cancelling():
                self.owner.cancel()

    def cancel(self, invocation_id: str) -> None:
        """
        Schedule one cancellation after an admitted task can enter its finally.

        Parameters
        ----------
        invocation_id : str
            Active invocation to cancel; unknown IDs are ignored.

        Returns
        -------
        None
            Schedule cancellation once for the selected active invocation.

        Raises
        ------
        RuntimeError
            If cancellation needs scheduling but no event loop is running.
        """
        task = self.active.get(invocation_id)
        if task is not None and invocation_id not in self._cancel_requested:
            self._cancel_requested.add(invocation_id)
            asyncio.get_running_loop().call_soon(self._cancelTask, task)

    def _cancelTask(self, task: asyncio.Task[None]) -> None:
        """
        Deliver at most one cancellation without interrupting cleanup again.

        Parameters
        ----------
        task : asyncio.Task[None]
            Invocation admitted before this event-loop callback was scheduled.

        Returns
        -------
        None
            Cancel the task unless it is finishing, done or already cancelling.
        """
        if task not in self.finishing and not task.done() and not task.cancelling():
            task.cancel()

    def finish(self, invocation_id: str) -> None:
        """
        Release a completed ID while retaining its terminal delivery task.

        Parameters
        ----------
        invocation_id : str
            ID belonging to the current invocation task. Admission errors from
            the connection reader cannot release another invocation's ownership.

        Returns
        -------
        None
            Move the current owned invocation from active to finishing tasks.

        Raises
        ------
        RuntimeError
            If no event loop is running to identify the current task.
        """
        task = asyncio.current_task()
        if task is not None and self.active.get(invocation_id) is task:
            self.active.pop(invocation_id)
            self._cancel_requested.discard(invocation_id)
            self.finishing.add(task)

    async def sendEncoded(self, data: str | bytes) -> None:
        """
        Await one serialized write without letting RPC cancellation tear it.

        Parameters
        ----------
        data : str | bytes
            Immutable, already encoded envelope.

        Returns
        -------
        None
            Complete the ordered transport write while preserving backpressure.

        Raises
        ------
        ConnectionError
            If cleanup has started.
        asyncio.CancelledError
            If the caller is cancelled; an already started write stays shielded
            until it finishes or connection cleanup cancels it.
        """
        await self._write_lock.acquire()
        if self.closing:
            self._write_lock.release()
            message = "Realtime connection is closed"
            raise ConnectionError(message)
        task = asyncio.create_task(self.socket.send(data))
        self._write_task = task
        task.add_done_callback(self._writeDone)
        await asyncio.shield(task)

    async def send(self, envelope: object) -> None:
        """
        Encode and await delivery of a protocol envelope.

        Parameters
        ----------
        envelope : object
            Serializable Orionis protocol message.

        Returns
        -------
        None
            Encode the envelope and complete its ordered transport write.

        Raises
        ------
        TypeError, ValueError
            If the selected codec cannot encode the envelope.
        ConnectionError
            If connection cleanup has started.
        asyncio.CancelledError
            If delivery is cancelled; an already started write stays shielded.
        """
        await self.sendEncoded(self.protocol.encode(envelope))

    async def invoke(
        self, target: str, *args: object,
        timeout: float | None = None,  # noqa: ASYNC109 # NOSONAR
    ) -> object:
        """
        Invoke one client and release its Future on every exit path.

        Parameters
        ----------
        target : str
            Explicit client method name.
        *args : object
            Up to 64 serializable positional arguments.
        timeout : float | None, optional
            Total send/result deadline in seconds. None uses the configured
            client-result timeout.

        Returns
        -------
        object
            Client completion result, including ``None``.

        Raises
        ------
        ConnectionError
            If the target is not ready or disconnects.
        RuntimeError
            If the pending-result budget is exhausted.
        ValueError
            If the target, argument count, deadline or encoded payload is invalid.
        TypeError
            If the selected codec cannot encode an argument value.
        TimeoutError
            If sending or receiving the completion exceeds the deadline.
        ClientInvocationError
            If the client returns a completion error.
        asyncio.CancelledError
            If the invocation is cancelled; its pending result is released.
        """
        if not self.ready or self.closing:
            message = "Realtime connection is not ready"
            raise ConnectionError(message)
        if (
            not isinstance(target, str) or not target.isidentifier()
            or target.startswith("_") or len(target) > _TARGET_LIMIT
            or len(args) > _ARGUMENT_LIMIT
        ):
            message = "Invalid client invocation target"
            raise ValueError(message)
        deadline = self.config.client_result_timeout if timeout is None else timeout
        if (
            isinstance(deadline, bool) or not isinstance(deadline, (int, float))
            or not isfinite(deadline) or deadline <= 0
        ):
            message = "Client invocation timeout must be finite and positive"
            raise ValueError(message)
        if len(self.pending) >= self.config.max_pending_client_invocations:
            message = "Pending client invocation limit exceeded"
            raise RuntimeError(message)
        self._counter += 1
        invocation_id = f"s{self._counter:x}"
        future = asyncio.get_running_loop().create_future()
        self.pending[invocation_id] = future
        try:
            async with asyncio.timeout(deadline):
                await self.send({
                    "type": "invoke", "id": invocation_id,
                    "target": target, "args": args,
                })
                return await future
        finally:
            self.pending.pop(invocation_id, None)
            if not future.done():
                future.cancel()
            elif not future.cancelled():
                # Disconnect may finish the Future while sending is still blocked.
                future.exception()

    def complete(self, completion: Completion) -> None:
        """
        Correlate a completion without retaining duplicate or late messages.

        Parameters
        ----------
        completion : Completion
            Validated client completion.

        Returns
        -------
        None
            Resolve the pending result or record a sanitized client error;
            ignore unknown, duplicate and already completed identifiers.
        """
        future = self.pending.pop(completion.id, None)
        if future is None or future.done():
            return
        if completion.error is not msgspec.UNSET:
            # The untrusted message is not propagated into server diagnostics.
            future.set_exception(ClientInvocationError(
                "client_error", "Client invocation failed",
            ))
        else:
            future.set_result(completion.result)

    async def cleanup(self) -> None:
        """
        Cancel owned work and release every retained task and Future.

        Returns
        -------
        None
            Finish cooperative cancellation before the connection scope exits.

        Raises
        ------
        asyncio.CancelledError
            If cleanup is cancelled while joining tasks; task registries and
            owner references are still cleared.
        """
        self.closing = True
        self.ready = False
        for future in self.pending.values():
            if not future.done():
                message = "Realtime connection disconnected"
                future.set_exception(ConnectionError(message))
        self.pending.clear()
        tasks = (*self.active.values(), *self.finishing)
        for task in tasks:
            if not task.done() and not task.cancelling():
                task.cancel()
        write = self._write_task
        if write is not None and not write.done():
            write.cancel()
        try:
            if tasks or write is not None:
                await asyncio.gather(
                    *tasks, *((write,) if write is not None else ()),
                    return_exceptions=True,
                )
        finally:
            self.active.clear()
            self.finishing.clear()
            self._cancel_requested.clear()
            self.owner = None
