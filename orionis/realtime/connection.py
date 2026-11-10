"""Own tasks and pending client results for exactly one connection."""

import asyncio
from functools import partial
from math import isfinite
from typing import TYPE_CHECKING
import msgspec
from orionis.failure.runtime import (
    capture, capture_nowait, current_operation, get_runtime, handoff, operation,
)
from orionis.http.adapters.response.streams import await_cleanup
from orionis.http.exceptions.websocket import WebSocketDisconnected
from orionis.realtime.errors import ClientInvocationError

if TYPE_CHECKING:
    from orionis.failure.runtime import FailureRuntime
    from orionis.foundation.config.realtime.entities.realtime import RealtimeConfig
    from orionis.http import WebSocket
    from orionis.realtime.hub import Hub, HubContext
    from orionis.realtime.protocol import Completion, HubProtocol

_TARGET_LIMIT = 128
"""Target limit value used by ``connection``."""
_ARGUMENT_LIMIT = 64
"""Argument limit value used by ``connection``."""

class RealtimeConnection:
    """Own tasks and pending client results for exactly one connection."""

    __slots__ = (
        "__weakref__", "_cancel_requested", "_counter", "_failure_operation",
        "_failure_runtime",
        "_reports", "_write_lock",
        "_write_task", "active",
        "closing", "config", "context", "failure", "finishing", "hub", "owner",
        "pending", "protocol",
        "ready", "socket",
    )
    """Declare the instance attribute slots reserved by this class."""

    def __init__(
        self, context: HubContext, hub: type[Hub], protocol: HubProtocol,
        config: RealtimeConfig,
        *, runtime: FailureRuntime | None = None,
    ) -> None:
        """
        Bind connection state and initialize task, result, and write ownership.

        Parameters
        ----------
        context : orionis.realtime.HubContext
            Connection identity and public socket to retain.
        hub : type[orionis.realtime.Hub]
            Hub class defining this connection's namespace.
        protocol : orionis.realtime.HubProtocol
            Route-selected codec used for connection messages.
        config : orionis.foundation.config.realtime.entities.realtime.RealtimeConfig
            Invocation, client-result, and delivery limits.
        runtime : orionis.failure.runtime.FailureRuntime or None, optional
            Runtime for failure delivery; ``None`` retains the current runtime.

        Returns
        -------
        None
            Initialize owned tasks, pending results, and serialized write state.

        Raises
        ------
        RuntimeError
            If no event loop is running while identifying the owner task.
        """
        self.context = context
        """Connection identity and public socket."""
        self.socket: WebSocket = context.socket
        """WebSocket associated with the current realtime invocation."""
        self.hub = hub
        """Application-owned Hub type."""
        self.protocol = protocol
        """Route-selected codec."""
        self.config = config
        """Invocation and broadcast limits."""
        self.active: dict[str, asyncio.Task[None]] = {}
        """Operations currently running for this connection or transport."""
        self.finishing: set[asyncio.Task[None]] = set()
        """Finishing produced by ``set``."""
        self._cancel_requested: set[str] = set()
        """Cancel requested produced by ``set``."""
        self.pending: dict[str, asyncio.Future[object]] = {}
        """Work that has been admitted and is awaiting completion."""
        self.owner: asyncio.Task | None = asyncio.current_task()
        """Owner produced by ``asyncio.current_task``."""
        self.ready = False
        """Ready flag used by ``RealtimeConnection``."""
        self.closing = False
        """Closing flag used by ``RealtimeConnection``."""
        self.failure: BaseException | None = None
        """Failure retained for propagation or reporting."""
        self._counter = 0
        """Counter value used by ``RealtimeConnection``."""
        self._write_lock = asyncio.Lock()
        """Synchronization primitive controlling access to write lock."""
        self._write_task: asyncio.Task[None] | None = None
        """Background task sending queued messages to the connection."""
        self._failure_runtime = runtime if runtime is not None else get_runtime()
        """Application runtime retained through connection cleanup."""
        self._failure_operation = current_operation()
        """Connection boundary receiving fatal child-task incident identity."""
        self._reports: set[asyncio.Future] = set()
        """Failure delivery tasks owned by this connection."""

    def _observe(self, error: BaseException, phase: str) -> None:
        """
        Observe a connection failure and retain ownership of pending reports.

        Parameters
        ----------
        error : BaseException
            Connection, invocation-cleanup, or transport failure to observe.
        phase : str
            Realtime lifecycle phase identifying the failure.

        Returns
        -------
        None
            Preserve incident correlation across callbacks and track any pending
            failure delivery until completion.
        """
        original = (
            error.__cause__ if isinstance(error, WebSocketDisconnected)
            and isinstance(error.__cause__, Exception) else error
        )
        # A shielded write may finish after its invocation context has closed.
        # Claim a live receipt before notifying the still-active connection owner.
        with operation(runtime=self._failure_runtime, flow="realtime"):
            boundary = current_operation()
            owner = self._failure_operation
            previous = None if owner is None else owner.lookup(original)
            if previous is not None:
                handoff(original, target=boundary, receipt=previous)
            pending = capture_nowait(
                original, runtime=self._failure_runtime, flow="realtime", phase=phase,
                correlation_id=self.context.connection_id,
                expected=isinstance(original, WebSocketDisconnected),
            )
            receipt = None if boundary is None else boundary.lookup(original)
            if receipt is not None:
                handoff(error, target=boundary, receipt=receipt)
                handoff(error, target=self._failure_operation, receipt=receipt)
                handoff(original, target=self._failure_operation, receipt=receipt)
        if pending is not None:
            self._reports.add(pending)
            pending.add_done_callback(self._reports.discard)

    @property
    def failureRuntime(self) -> FailureRuntime | None:
        """
        Return the retained runtime used for connection failure delivery.

        Returns
        -------
        orionis.failure.runtime.FailureRuntime or None
            Runtime captured at construction, or ``None`` if none was available.
        """
        return self._failure_runtime

    def bindFailureOperation(self) -> None:
        """
        Bind the current failure operation as the connection's incident boundary.

        Returns
        -------
        None
            Retain the current operation for later incident handoff, or clear the
            saved boundary when none is active.
        """
        self._failure_operation = current_operation()

    def _writeDone(
        self, task: asyncio.Task[None], *, ready: asyncio.Future | None = None,
    ) -> None:
        """
        Retire a completed write and notify its waiter without losing failures.

        Parameters
        ----------
        task : asyncio.Task[None]
            Completed task owning the sole in-flight transport write.
        ready : asyncio.Future or None, optional
            Completion notification for the task's original waiter, if supplied.

        Returns
        -------
        None
            Release write ownership, observe failures, and notify an unfinished
            waiter; begin shutdown after a failed or cancelled write.
        """
        self._write_task = None
        self._write_lock.release()
        failure = None if task.cancelled() else task.exception()
        if failure is not None:
            self._observe(failure, "send")
        failed = task.cancelled() or failure is not None
        if failed and not self.closing:
            self.closing = True
            self.failure = failure
            if self.owner is not None and not self.owner.cancelling():
                self.owner.cancel()
        if ready is not None and not ready.done():
            ready.set_result(None)

    def invocationDone(self, invocation_id: str, task: asyncio.Task[None]) -> None:
        """
        Retire a completed invocation and observe unhandled task failures.

        Parameters
        ----------
        invocation_id : str
            Identifier originally owned by this invocation task.
        task : asyncio.Task[None]
            Completed invocation whose local cleanup has already run.

        Returns
        -------
        None
            Retire ownership without disturbing a reused ID and observe task failures,
            requesting shutdown only for a new unhandled failure.
        """
        if self.active.get(invocation_id) is task:
            self.active.pop(invocation_id)
            self._cancel_requested.discard(invocation_id)
        self.finishing.discard(task)
        failure = None if task.cancelled() else task.exception()
        if failure is not None:
            self._observe(failure, "invocation_cleanup")
        if failure is not None and not self.closing:
            self.failure = failure
            self.closing = True
            if self.owner is not None and not self.owner.cancelling():
                self.owner.cancel()

    def cancel(self, invocation_id: str) -> None:
        """
        Schedule cancellation once for an active invocation identifier.

        Parameters
        ----------
        invocation_id : str
            Active invocation identifier; ignore unknown or already requested IDs.

        Returns
        -------
        None
            Defer cancellation to the event loop so admitted work can enter cleanup.

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
        Cancel unfinished invocation work without interrupting cleanup twice.

        Parameters
        ----------
        task : asyncio.Task[None]
            Admitted invocation targeted by a deferred cancellation callback.

        Returns
        -------
        None
            Cancel only tasks that are not finishing, done, or already cancelling.
        """
        if task not in self.finishing and not task.done() and not task.cancelling():
            task.cancel()

    def finish(self, invocation_id: str) -> None:
        """
        Release an invocation ID while retaining ownership of terminal delivery.

        Parameters
        ----------
        invocation_id : str
            Identifier owned by the current task; ignore attempts from other tasks.

        Returns
        -------
        None
            Move the current ID owner from active work to terminal-delivery tracking.

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
        Serialize an encoded message while retaining ownership of its write task.

        An admitted write outlives caller cancellation until it finishes or
        connection cleanup cancels it.

        Parameters
        ----------
        data : str | bytes
            Immutable envelope already encoded for this connection's codec.

        Returns
        -------
        None
            Complete this message's ordered transport write.

        Raises
        ------
        ConnectionError
            If connection shutdown begins before write admission.
        asyncio.CancelledError
            If the caller or owned write is cancelled; caller cancellation does
            not itself cancel an admitted write.
        BaseException
            If the owned transport write fails.
        """
        await self._write_lock.acquire()
        if self.closing:
            self._write_lock.release()
            message = "Realtime connection is closed"
            raise ConnectionError(message)
        ready = asyncio.get_running_loop().create_future()
        task = asyncio.create_task(self._sendOwned(data))
        self._write_task = task
        task.add_done_callback(partial(self._writeDone, ready=ready))
        # Cancellation only cancels the notification. The connection retains and
        # inspects the write, including failures after its original caller leaves.
        await ready
        task.result()

    async def _sendOwned(self, data: str | bytes) -> None:
        """
        Send within an owned incident context that survives caller cancellation.

        Parameters
        ----------
        data : str | bytes
            Encoded message passed unchanged to the socket.

        Returns
        -------
        None
            Complete the socket send under connection-level failure ownership.

        Raises
        ------
        BaseException
            If the send fails or is cancelled. Observe non-cancellation failures
            before propagating them.
        """
        with operation(
            runtime=self._failure_runtime, flow="realtime",
            operation="send", correlation_id=self.context.connection_id,
            isolated=True,
        ):
            try:
                await self.socket.send(data)
            except asyncio.CancelledError:
                raise
            except BaseException as exc:
                self._observe(exc, "send")
                raise

    async def send(self, envelope: object) -> None:
        """
        Encode a protocol envelope and await its serialized transport write.

        Parameters
        ----------
        envelope : object
            Protocol message accepted by the selected connection codec.

        Returns
        -------
        None
            Encode the message and complete its ordered transport write.

        Raises
        ------
        TypeError, ValueError
            If the codec cannot encode the envelope.
        ConnectionError
            If connection shutdown begins before write admission.
        asyncio.CancelledError
            If delivery is cancelled; an admitted write remains connection-owned.
        """
        await self.sendEncoded(self.protocol.encode(envelope))

    async def invoke(
        self, target: str, *args: object,
        timeout: float | None = None,  # noqa: ASYNC109 # NOSONAR
    ) -> object:
        """
        Invoke a client method and release its pending result on every exit.

        Parameters
        ----------
        target : str
            Public client method identifier, at most 128 characters.
        *args : object
            Up to 64 positional arguments accepted by the selected codec.
        timeout : float or None, optional
            Total send-and-result deadline in seconds; ``None`` uses the
            configured client-result timeout.

        Returns
        -------
        object
            Value carried by a successful client completion, which may be ``None``.

        Raises
        ------
        ConnectionError
            If the connection is not ready, is closing, or disconnects.
        RuntimeError
            If the configured pending-result budget is exhausted.
        ValueError
            If the target, argument count, deadline, or encoded payload is invalid.
        TypeError
            If the selected codec cannot encode an argument value.
        TimeoutError
            If sending or awaiting the completion exceeds the total deadline.
        orionis.realtime.errors.ClientInvocationError
            If the client returns an error, represented by a sanitized exception.
        asyncio.CancelledError
            If the invocation is cancelled; release its pending-result entry.
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
                failure = future.exception()
                if failure is not None:
                    await capture(
                        failure, runtime=self._failure_runtime, flow="realtime",
                        phase="client_result", operation=target,
                        correlation_id=invocation_id,
                        expected=isinstance(
                            failure, (ClientInvocationError, ConnectionError),
                        ),
                    )

    def complete(self, completion: Completion) -> None:
        """
        Settle a pending client invocation and ignore late or duplicate completions.

        Parameters
        ----------
        completion : orionis.realtime.protocol.Completion
            Validated completion identifying a pending client invocation.

        Returns
        -------
        None
            Remove the pending ID and store its result or a sanitized client error;
            ignore absent or already settled futures.
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
        Cancel owned work, join cleanup, and release connection task registries.

        Returns
        -------
        None
            Drain owned tasks and pending failure reports before clearing registries
            and owner references.

        Raises
        ------
        BaseException
            If joining or failure observation fails, including cancellation; clear
            registries and owner references before propagating it.
        """
        self.closing = True
        self.ready = False
        tasks = self._cancelWork()
        try:
            if tasks:
                results = await await_cleanup(asyncio.gather(
                    *tasks, return_exceptions=True,
                ))
                for failure in results:
                    if isinstance(failure, BaseException):
                        await capture(
                            failure, runtime=self._failure_runtime,
                            flow="realtime", phase="cleanup",
                            correlation_id=self.context.connection_id,
                        )
            if self._reports:
                await await_cleanup(asyncio.gather(*self._reports))
        finally:
            self.active.clear()
            self.finishing.clear()
            self._cancel_requested.clear()
            self._reports.clear()
            self._failure_operation = None
            self.owner = None

    def _cancelWork(self) -> tuple[asyncio.Task, ...]:
        """
        Reject pending client results and request cancellation of owned tasks.

        Returns
        -------
        tuple[asyncio.Task, ``...``]
            Invocation tasks and any retained write task for the caller to join;
            do not await them here.
        """
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
        return (*tasks, write) if write is not None else tasks
