from __future__ import annotations
import asyncio
from contextlib import suppress
from types import SimpleNamespace
from unittest import IsolatedAsyncioTestCase
from orionis.foundation.application import _ASGI_BODY_QUEUE_SIZE, Application
from orionis.foundation.enums.runtimes import Runtime
from orionis.http.contracts.kernel import IKernelHTTP

class _AsyncCall:
    """Record asynchronous calls and return explicit results or failures."""

    __slots__ = ("awaitCount", "calls", "returnValue", "sideEffect")

    def __init__(self, return_value=None, side_effect=None) -> None:
        """
        Initialize the recording callable.

        Parameters
        ----------
        return_value : object, optional
            Result returned by calls without a side effect.
        side_effect : object, optional
            Exception, asynchronous callable, or ordered results to consume.

        Returns
        -------
        None
            Initializes result and call tracking.
        """
        self.returnValue = return_value
        self.sideEffect = side_effect
        self.calls = []
        self.awaitCount = 0

    async def __call__(self, *args: object, **kwargs: object) -> object:
        """
        Record arguments and execute the configured result.

        Parameters
        ----------
        *args : object
            Positional arguments received from the application.
        **kwargs : object
            Keyword arguments received from the application.

        Returns
        -------
        object
            Configured result or the result of the asynchronous side effect.

        Raises
        ------
        BaseException
            If the configured result is an exception.
        """
        self.calls.append((args, kwargs))
        self.awaitCount += 1
        effect = self.sideEffect
        if isinstance(effect, list):
            effect = effect[self.awaitCount - 1]
        if isinstance(effect, BaseException):
            raise effect
        if callable(effect):
            return await effect(*args, **kwargs)
        return self.returnValue if self.sideEffect is None else effect

class _StubKernel(IKernelHTTP):
    """Implement the HTTP kernel contract with recording entry points."""

    __slots__ = ("asgiAction", "bootAction", "rsgiAction")

    def __init__(self) -> None:
        """
        Initialize the recording kernel operations.

        Returns
        -------
        None
            Initializes separate boot and protocol handlers.
        """
        self.bootAction = _AsyncCall()
        self.asgiAction = _AsyncCall()
        self.rsgiAction = _AsyncCall()

    async def boot(self) -> None:
        """
        Execute the configured kernel boot action.

        Returns
        -------
        None
            Completes after the configured boot action.
        """
        await self.bootAction()

    async def handleASGI(self, scope, receive, send) -> object:
        """
        Forward an ASGI request to the recording handler.

        Parameters
        ----------
        scope : dict
            HTTP request scope.
        receive : Callable
            Request body receiver.
        send : Callable
            Response sender.

        Returns
        -------
        object
            Configured ASGI result.
        """
        return await self.asgiAction(scope, receive, send)

    async def handleRSGI(self, scope, protocol) -> object:
        """
        Forward an RSGI request to the recording handler.

        Parameters
        ----------
        scope : object
            HTTP request scope.
        protocol : object
            Server protocol instance.

        Returns
        -------
        object
            Configured RSGI result.
        """
        return await self.rsgiAction(scope, protocol)

def _new_application() -> Application:
    """
    Construct an application without registering a container singleton.

    Returns
    -------
    Application
        Isolated application with a minimal runtime configuration.
    """
    application = object.__new__(Application)
    application.__init__()
    application._Application__http_disconnect_monitoring = True
    application._Application__configured = True
    application._Application__bootstrap = {
        "config": {"app": {}},
        "kernels": {
            "KernelHTTP": {"module": __name__, "class": "_StubKernel"},
        },
    }
    return application

async def _cancel_task(task: asyncio.Task) -> None:
    """
    Cancel and join a pending task during test cleanup.

    Parameters
    ----------
    task : asyncio.Task
        Request task that may still be running after an assertion fails.

    Returns
    -------
    None
        Returns after pending work has stopped.
    """
    if not task.done():
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task

class _AsyncGate:
    """Expose synchronization points around a cancellable coroutine."""

    __slots__ = ("cleaned", "entered", "release")

    def __init__(self) -> None:
        """
        Initialize entry, release, and cleanup events.

        Returns
        -------
        None
            Initializes the gate state.
        """
        self.entered = asyncio.Event()
        self.release = asyncio.Event()
        self.cleaned = asyncio.Event()

    async def run(self, *_args: object) -> str:
        """
        Wait for release and finish asynchronous cleanup before returning.

        Parameters
        ----------
        *_args : object
            Ignored arguments supplied by the application handler.

        Returns
        -------
        str
            Response marker after the gate is released.
        """
        self.entered.set()
        try:
            await self.release.wait()
            return "response"
        finally:
            await asyncio.sleep(0)
            self.cleaned.set()

class _ReceiveChannel:
    """Provide queued ASGI messages and observable receive cleanup."""

    __slots__ = ("calls", "cleaned", "entered", "messages")

    def __init__(self, messages: tuple[dict, ...] = ()) -> None:
        """
        Populate the server receive queue.

        Parameters
        ----------
        messages : tuple of dict, optional
            Messages immediately available to the application dispatcher.

        Returns
        -------
        None
            Initializes queue and tracking events.
        """
        self.messages = asyncio.Queue()
        self.calls = 0
        self.entered = asyncio.Event()
        self.cleaned = asyncio.Event()
        for message in messages:
            self.messages.put_nowait(message)

    async def receive(self) -> dict:
        """Read one message and record cancellation cleanup.

        Returns
        -------
        dict
            Next message supplied by the server.

        Raises
        ------
        Exception
            Raised by this helper to exercise the failure path.
        """
        self.calls += 1
        self.entered.set()
        try:
            return await self.messages.get()
        except asyncio.CancelledError:
            await asyncio.sleep(0)
            self.cleaned.set()
            raise

class _CleanupChannel:
    """Suspend receive cleanup until released or cancelled again."""

    __slots__ = ("cleaned", "cleaning", "entered", "release", "task")

    def __init__(self) -> None:
        """
        Initialize receive and cleanup synchronization events.

        Returns
        -------
        None
            Initializes observable monitor state.
        """
        self.entered = asyncio.Event()
        self.cleaning = asyncio.Event()
        self.cleaned = asyncio.Event()
        self.release = asyncio.Event()
        self.task = None

    async def receive(self) -> dict:
        """
        Block the receive operation and expose its asynchronous cleanup.

        Returns
        -------
        dict
            No message is returned because the receive operation is cancelled.
        """
        self.task = asyncio.current_task()
        self.entered.set()
        try:
            return await asyncio.get_running_loop().create_future()
        finally:
            self.cleaning.set()
            try:
                await self.release.wait()
            finally:
                self.cleaned.set()

class TestApplicationAsync(IsolatedAsyncioTestCase):
    """Verify HTTP transport lifetime, backpressure, and kernel initialization."""

    def _requestTask(self, application, channel) -> asyncio.Task:
        """
        Start an ASGI request with guaranteed test cleanup.

        Parameters
        ----------
        application : Application
            Application under test.
        channel : _ReceiveChannel
            Server message source.

        Returns
        -------
        asyncio.Task
            Running request task.
        """
        task = asyncio.create_task(
            application({"type": "http"}, channel.receive, _AsyncCall()),
        )
        self.addAsyncCleanup(_cancel_task, task)
        return task

    def _rsgiTask(self, application, disconnect) -> asyncio.Task:
        """
        Start an RSGI request with guaranteed test cleanup.

        Parameters
        ----------
        application : Application
            Application under test.
        disconnect : Callable
            Protocol method returning a disconnect awaitable.

        Returns
        -------
        asyncio.Task
            Running request task.
        """
        task = asyncio.create_task(
            application.__rsgi__(
                SimpleNamespace(proto="http"),
                SimpleNamespace(client_disconnect=disconnect),
            ),
        )
        self.addAsyncCleanup(_cancel_task, task)
        return task

    async def testAsgiPreservesBodyChunkOrder(self) -> None:
        """
        Deliver body chunks to the kernel in the original server order.

        Returns
        -------
        None
            Raises AssertionError if messages change or tasks remain pending.
        """
        application = _new_application()
        messages = tuple(
            {"type": "http.request", "body": body, "more_body": index < 2}
            for index, body in enumerate((b"first", b"second", b"third"))
        )
        channel = _ReceiveChannel(messages)
        observed = []

        async def handle(_scope, receive, _send) -> bytes:
            """
            Collect all request chunks through the kernel receive callable.

            Parameters
            ----------
            _scope : dict
                Unused HTTP scope.
            receive : Callable
                Kernel receive callable.
            _send : Callable
                Unused response sender.

            Returns
            -------
            bytes
                Joined request body.
            """
            observed.extend([await receive() for _ in messages])
            return b"".join(message["body"] for message in observed)

        application._Application__kernel_http_asgi = handle
        async with asyncio.timeout(2):
            result = await self._requestTask(application, channel)
        self.assertEqual(result, b"firstsecondthird")
        self.assertEqual(observed, list(messages))
        self.assertTrue(channel.cleaned.is_set())

    async def testAsgiLimitsReadAheadForUnreadBodies(self) -> None:
        """
        Bound unread body buffering to the queue capacity and a pending message.

        Returns
        -------
        None
            Raises AssertionError if the dispatcher drains the request body.
        """
        application = _new_application()
        channel = _ReceiveChannel(
            tuple({"type": "http.request", "body": b"chunk"} for _ in range(1000)),
        )
        handler = _AsyncGate()
        application._Application__kernel_http_asgi = handler.run
        task = self._requestTask(application, channel)
        async with asyncio.timeout(2):
            await handler.entered.wait()
            for _ in range(5):
                await asyncio.sleep(0)
            maximum_read_ahead = _ASGI_BODY_QUEUE_SIZE + 1
            self.assertLessEqual(channel.calls, maximum_read_ahead)
            self.assertGreaterEqual(
                channel.messages.qsize(), 1000 - maximum_read_ahead,
            )
            handler.release.set()
            self.assertEqual(await task, "response")

    async def testAsgiDisconnectCancelsHandlerAndJoinsCleanup(self) -> None:
        """
        Stop a running kernel when the server reports a client disconnect.

        Returns
        -------
        None
            Raises AssertionError if cancellation cleanup is not awaited.
        """
        application = _new_application()
        channel = _ReceiveChannel()
        handler = _AsyncGate()
        application._Application__kernel_http_asgi = handler.run
        task = self._requestTask(application, channel)
        async with asyncio.timeout(2):
            await handler.entered.wait()
            channel.messages.put_nowait({"type": "http.disconnect"})
            self.assertIsNone(await task)
        self.assertTrue(handler.cleaned.is_set())

    async def testAsgiDisconnectRemainsAvailableDuringKernelCleanup(self) -> None:
        """
        Forward the terminal message to kernels that receive during cancellation.

        Returns
        -------
        None
            Raises AssertionError if a cooperating kernel waits forever on receive.
        """
        application = _new_application()
        channel = _ReceiveChannel()
        entered = asyncio.Event()

        async def handle(_scope, receive, _send) -> dict:
            """
            Read the disconnect message after request cancellation starts.

            Parameters
            ----------
            _scope : dict
                Unused HTTP request scope.
            receive : Callable
                Request body and disconnect receiver.
            _send : Callable
                Unused response sender.

            Returns
            -------
            dict
                Terminal message received during kernel cleanup.
            """
            entered.set()
            try:
                return await asyncio.get_running_loop().create_future()
            except asyncio.CancelledError:
                return await receive()

        application._Application__kernel_http_asgi = handle
        task = self._requestTask(application, channel)
        await asyncio.wait_for(entered.wait(), timeout=2)
        terminal = {"type": "http.disconnect"}
        channel.messages.put_nowait(terminal)
        self.assertIs(await asyncio.wait_for(task, timeout=2), terminal)

    async def testAsgiExternalCancellationPropagates(self) -> None:
        """
        Preserve cancellation requested by the server or request owner.

        Returns
        -------
        None
            Raises AssertionError if cancellation is swallowed or cleanup leaks.
        """
        application = _new_application()
        channel = _ReceiveChannel()
        handler = _AsyncGate()
        application._Application__kernel_http_asgi = handler.run
        task = self._requestTask(application, channel)
        async with asyncio.timeout(2):
            await handler.entered.wait()
            await channel.entered.wait()
            task.cancel()
            with self.assertRaises(asyncio.CancelledError):
                await task
        self.assertTrue(handler.cleaned.is_set())
        self.assertTrue(channel.cleaned.is_set())

    async def testAsgiReceiveFailurePropagatesWithoutHanging(self) -> None:
        """
        Surface server receive errors and cancel the pending kernel.

        Returns
        -------
        None
            Raises AssertionError if a receive failure is lost.
        """
        application = _new_application()
        handler = _AsyncGate()
        application._Application__kernel_http_asgi = handler.run

        async def receive() -> dict:
            """
            Fail after the HTTP kernel starts processing.

            Returns
            -------
            dict
                No message is returned.

            Raises
            ------
            RuntimeError
                Signals a simulated transport failure.
            """
            await handler.entered.wait()
            message = "receive failed"
            raise RuntimeError(message)

        async with asyncio.timeout(2):
            with self.assertRaisesRegex(RuntimeError, "receive failed"): # NOSONAR
                await application({"type": "http"}, receive, _AsyncCall())
        self.assertTrue(handler.cleaned.is_set())

    async def testAsgiKernelFailureCleansDispatcher(self) -> None:
        """
        Preserve kernel errors and await receive dispatcher cancellation.

        Returns
        -------
        None
            Raises AssertionError if the dispatcher outlives the failed request.
        """
        application = _new_application()
        channel = _ReceiveChannel()

        async def fail_after_receive(*_args: object) -> None:
            """
            Fail after the receive monitor begins waiting for server messages.

            Parameters
            ----------
            *_args : object
                Ignored ASGI kernel arguments.

            Returns
            -------
            None
                No result is returned.

            Raises
            ------
            ValueError
                Signals a kernel failure with an active receive monitor.
            """
            await channel.entered.wait()
            message = "kernel failed"
            raise ValueError(message)

        application._Application__kernel_http_asgi = fail_after_receive
        async with asyncio.timeout(2):
            with self.assertRaisesRegex(ValueError, "kernel failed"):
                await self._requestTask(application, channel)
        self.assertTrue(channel.cleaned.is_set())

    async def testAsgiCancelledReceiveDoesNotLeaveHandlerPending(self) -> None:
        """
        Stop the kernel when the receive channel itself raises cancellation.

        Returns
        -------
        None
            Raises AssertionError if transport cancellation leaves the kernel alive.
        """
        application = _new_application()
        handler = _AsyncGate()
        application._Application__kernel_http_asgi = handler.run
        with self.assertRaises(asyncio.CancelledError): # NOSONAR
            await asyncio.wait_for(
                application(
                    {"type": "http"},
                    _AsyncCall(side_effect=asyncio.CancelledError()),
                    _AsyncCall(),
                ),
                timeout=2,
            )
        self.assertTrue(handler.cleaned.is_set())

    async def testAsgiHandlesEagerTaskFactory(self) -> None:
        """
        Support handlers that complete during eager task construction.

        Returns
        -------
        None
            Raises AssertionError if eager execution changes request results.
        """
        application = _new_application()
        application._Application__kernel_http_asgi = _AsyncCall(return_value="done")
        channel = _ReceiveChannel()
        loop = asyncio.get_running_loop()
        previous_factory = loop.get_task_factory()
        loop.set_task_factory(asyncio.eager_task_factory)
        try:
            self.assertEqual(
                await application({"type": "http"}, channel.receive, _AsyncCall()),
                "done",
            )
        finally:
            loop.set_task_factory(previous_factory)
        self.assertEqual(channel.calls, 0)

    async def testAsgiEagerDisconnectCancelsPendingHandler(self) -> None:
        """
        Handle disconnects delivered during eager dispatcher construction.

        Returns
        -------
        None
            Raises AssertionError if an immediate disconnect races task setup.
        """
        application = _new_application()
        handler = _AsyncGate()
        application._Application__kernel_http_asgi = handler.run
        channel = _ReceiveChannel(({"type": "http.disconnect"},))
        loop = asyncio.get_running_loop()
        previous_factory = loop.get_task_factory()
        loop.set_task_factory(asyncio.eager_task_factory)
        try:
            async with asyncio.timeout(2):
                self.assertIsNone(
                    await application(
                        {"type": "http"}, channel.receive, _AsyncCall(),
                    ),
                )
        finally:
            loop.set_task_factory(previous_factory)
        self.assertTrue(handler.cleaned.is_set())

    async def testRsgiAcceptsFutureDisconnectWatcher(self) -> None:
        """
        Accept a native protocol Future and cancel it after a normal response.

        Returns
        -------
        None
            Raises AssertionError if the protocol Future is rejected or leaked.
        """
        application = _new_application()
        handler = _AsyncGate()
        application._Application__kernel_http_rsgi = handler.run
        disconnect = asyncio.get_running_loop().create_future()
        task = self._rsgiTask(application, lambda: disconnect)
        async with asyncio.timeout(2):
            await handler.entered.wait()
            handler.release.set()
            self.assertEqual(await task, "response")
        self.assertTrue(disconnect.cancelled())

    async def testImmediateResponseDoesNotOpenTransportMonitor(self) -> None:
        """
        Avoid calling receive or disconnect channels after a completed response.

        Returns
        -------
        None
            Raises AssertionError if completed requests open transport monitors.
        """
        for interface in ("asgi", "rsgi"):
            with self.subTest(interface=interface):
                application = _new_application()
                handler = _AsyncCall(return_value="complete")
                channel = _ReceiveChannel()
                if interface == "asgi":
                    application._Application__kernel_http_asgi = handler
                    task = self._requestTask(application, channel)
                else:
                    application._Application__kernel_http_rsgi = handler
                    task = self._rsgiTask(application, channel.receive)
                self.assertEqual(await asyncio.wait_for(task, timeout=2), "complete")
                self.assertEqual(channel.calls, 0)
                self.assertFalse(channel.entered.is_set())

    async def testRsgiDisconnectCancelsHandler(self) -> None:
        """
        Stop the RSGI handler when the client disconnect Future resolves.

        Returns
        -------
        None
            Raises AssertionError if the handler survives the disconnect.
        """
        application = _new_application()
        handler = _AsyncGate()
        application._Application__kernel_http_rsgi = handler.run
        disconnect = asyncio.get_running_loop().create_future()
        task = self._rsgiTask(application, lambda: disconnect)
        async with asyncio.timeout(2):
            await handler.entered.wait()
            disconnect.set_result(None)
            self.assertIsNone(await task)
        self.assertTrue(handler.cleaned.is_set())

    async def testRsgiExternalCancellationJoinsBothTasks(self) -> None:
        """
        Propagate owner cancellation after handler and watcher cleanup.

        Returns
        -------
        None
            Raises AssertionError if cancellation or asynchronous cleanup is lost.
        """
        application = _new_application()
        handler = _AsyncGate()
        watcher = _AsyncGate()
        application._Application__kernel_http_rsgi = handler.run
        task = self._rsgiTask(application, watcher.run)
        async with asyncio.timeout(2):
            await handler.entered.wait()
            await watcher.entered.wait()
            task.cancel()
            with self.assertRaises(asyncio.CancelledError):
                await task
        self.assertTrue(handler.cleaned.is_set())
        self.assertTrue(watcher.cleaned.is_set())

    async def testRsgiWatcherFailurePropagates(self) -> None:
        """
        Surface disconnect watcher failures and finish handler cleanup.

        Returns
        -------
        None
            Raises AssertionError if a watcher exception is silently discarded.
        """
        application = _new_application()
        handler = _AsyncGate()
        application._Application__kernel_http_rsgi = handler.run
        disconnect = asyncio.get_running_loop().create_future()
        task = self._rsgiTask(application, lambda: disconnect)
        async with asyncio.timeout(2):
            await handler.entered.wait()
            disconnect.set_exception(RuntimeError("watcher failed"))
            with self.assertRaisesRegex(RuntimeError, "watcher failed"):
                await task
        self.assertTrue(handler.cleaned.is_set())

    async def testRsgiSynchronousWatcherFailureCleansHandler(self) -> None:
        """
        Clean up the handler when requesting the disconnect awaitable fails.

        Returns
        -------
        None
            Raises AssertionError if a protocol setup error leaks its handler.
        """
        application = _new_application()
        handler = _AsyncGate()
        application._Application__kernel_http_rsgi = handler.run

        def disconnect() -> None:
            """
            Raise a protocol error before returning an awaitable.

            Returns
            -------
            None
                No awaitable is returned.

            Raises
            ------
            RuntimeError
                Signals an invalid protocol state.
            """
            message = "protocol unavailable"
            raise RuntimeError(message)

        async with asyncio.timeout(2):
            with self.assertRaisesRegex(RuntimeError, "protocol unavailable"):
                await self._rsgiTask(application, disconnect)
        self.assertTrue(handler.cleaned.is_set())

    async def testRsgiKernelCancellationPropagates(self) -> None:
        """
        Preserve a cancellation raised directly by the HTTP kernel.

        Returns
        -------
        None
            Raises AssertionError if kernel cancellation appears as disconnect.
        """
        application = _new_application()
        application._Application__kernel_http_rsgi = _AsyncCall(
            side_effect=asyncio.CancelledError(),
        )
        disconnect = _AsyncCall()
        async with asyncio.timeout(2):
            with self.assertRaises(asyncio.CancelledError):
                await self._rsgiTask(application, disconnect)
        self.assertEqual(disconnect.awaitCount, 0)

    async def testRsgiCancelledWatcherDoesNotLeaveHandlerPending(self) -> None:
        """
        Stop the kernel when the native disconnect Future is cancelled.

        Returns
        -------
        None
            Raises AssertionError if protocol cancellation leaves the kernel alive.
        """
        application = _new_application()
        handler = _AsyncGate()
        application._Application__kernel_http_rsgi = handler.run
        disconnect = asyncio.get_running_loop().create_future()
        task = self._rsgiTask(application, lambda: disconnect)
        await handler.entered.wait()
        disconnect.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await asyncio.wait_for(task, timeout=2)
        self.assertTrue(handler.cleaned.is_set())

    async def testRsgiExternalCancellationWinsDisconnectRace(self) -> None:
        """
        Preserve request owner cancellation concurrent with a disconnect event.

        Returns
        -------
        None
            Raises AssertionError if a disconnect suppresses owner cancellation.
        """
        application = _new_application()
        handler = _AsyncGate()
        application._Application__kernel_http_rsgi = handler.run
        disconnect = asyncio.get_running_loop().create_future()
        task = self._rsgiTask(application, lambda: disconnect)
        async with asyncio.timeout(2):
            await handler.entered.wait()
            disconnect.set_result(None)
            task.cancel()
            with self.assertRaises(asyncio.CancelledError):
                await task
        self.assertTrue(handler.cleaned.is_set())

    async def testExternalCancellationDuringMonitorCleanupPropagates(self) -> None:
        """
        Cancel both transport requests while their monitors await cleanup.

        Returns
        -------
        None
            Raises AssertionError if cancellation is lost or a child task survives.
        """
        for interface in ("asgi", "rsgi"):
            with self.subTest(interface=interface):
                application = _new_application()
                handler = _AsyncGate()
                monitor = _CleanupChannel()
                if interface == "asgi":
                    application._Application__kernel_http_asgi = handler.run
                    task = self._requestTask(application, monitor)
                else:
                    application._Application__kernel_http_rsgi = handler.run
                    task = self._rsgiTask(application, monitor.receive)
                await asyncio.wait_for(monitor.entered.wait(), timeout=2)
                handler.release.set()
                await asyncio.wait_for(monitor.cleaning.wait(), timeout=2)
                self.assertFalse(task.done())
                task.cancel()
                with self.assertRaises(asyncio.CancelledError):
                    await asyncio.wait_for(task, timeout=2)
                self.assertTrue(handler.cleaned.is_set())
                self.assertTrue(monitor.cleaned.is_set())
                self.assertTrue(monitor.task.done())

    async def testKernelSelfCancellationPropagatesForBothProtocols(self) -> None:
        """
        Preserve cancellation requested by a running kernel task itself.

        Returns
        -------
        None
            Raises AssertionError if kernel cancellation becomes a normal response.
        """

        async def cancel_self(*_args: object) -> None:
            """
            Cancel the currently executing kernel task.

            Parameters
            ----------
            *_args : object
                Ignored protocol handler arguments.

            Returns
            -------
            None
                Cancellation interrupts the next suspension point.
            """
            asyncio.current_task().cancel()
            await asyncio.sleep(0)

        for interface in ("asgi", "rsgi"):
            with self.subTest(interface=interface):
                application = _new_application()
                channel = _ReceiveChannel()
                if interface == "asgi":
                    application._Application__kernel_http_asgi = cancel_self
                    task = self._requestTask(application, channel)
                else:
                    application._Application__kernel_http_rsgi = cancel_self
                    task = self._rsgiTask(application, channel.receive)
                with self.assertRaises(asyncio.CancelledError):
                    await asyncio.wait_for(task, timeout=2)
                self.assertTrue(channel.cleaned.is_set())

    async def testRsgiResponseAwaitsWatcherCleanup(self) -> None:
        """
        Join asynchronous watcher cleanup before returning a completed response.

        Returns
        -------
        None
            Raises AssertionError if watcher cleanup runs after the response.
        """
        application = _new_application()
        handler = _AsyncGate()
        watcher = _AsyncGate()
        application._Application__kernel_http_rsgi = handler.run
        task = self._rsgiTask(application, watcher.run)
        async with asyncio.timeout(2):
            await handler.entered.wait()
            await watcher.entered.wait()
            handler.release.set()
            self.assertEqual(await task, "response")
        self.assertTrue(watcher.cleaned.is_set())

    async def testConcurrentRequestsBootKernelOnce(self) -> None:
        """
        Share one completed kernel boot across concurrent HTTP transports.

        Returns
        -------
        None
            Raises AssertionError if requests duplicate kernel construction.
        """
        application = _new_application()
        kernel = _StubKernel()
        boot = _AsyncGate()
        kernel.bootAction = _AsyncCall(side_effect=boot.run)
        kernel.asgiAction = _AsyncCall(return_value="asgi")
        kernel.rsgiAction = _AsyncCall(return_value="rsgi")
        application.build = _AsyncCall(return_value=kernel)
        async with asyncio.timeout(2):
            first = self._requestTask(application, _ReceiveChannel())
            await boot.entered.wait()
            requests = [
                self._requestTask(application, _ReceiveChannel())
                for _ in range(8)
            ]
            requests.append(self._rsgiTask(application, _AsyncGate().run))
            await asyncio.sleep(0)
            self.assertEqual(kernel.bootAction.awaitCount, 1)
            boot.release.set()
            results = await asyncio.gather(first, *requests)
        self.assertEqual(results, ["asgi"] * 9 + ["rsgi"])
        self.assertEqual(application.build.awaitCount, 1)
        self.assertEqual(kernel.bootAction.awaitCount, 1)

    async def testFailedKernelBootCanRetry(self) -> None:
        """
        Leave handler caches unpublished after boot failure and allow retry.

        Returns
        -------
        None
            Raises AssertionError if failed initialization poisons future requests.
        """
        application = _new_application()
        kernel = _StubKernel()
        kernel.bootAction = _AsyncCall(side_effect=[RuntimeError("boot failed"), None])
        kernel.asgiAction = _AsyncCall(return_value="ready")
        kernel.rsgiAction = _AsyncCall(return_value="ready")
        application.build = _AsyncCall(return_value=kernel)
        async with asyncio.timeout(2):
            with self.assertRaisesRegex(RuntimeError, "boot failed"): # NOSONAR
                await self._requestTask(application, _ReceiveChannel())
            self.assertIsNone(application._Application__kernel_http_asgi)
            self.assertIsNone(application._Application__kernel_http_rsgi)
            self.assertEqual(
                await self._requestTask(application, _ReceiveChannel()),
                "ready",
            )
        self.assertEqual(kernel.bootAction.awaitCount, 2)

    async def testCancelledKernelBootCanRetry(self) -> None:
        """
        Release initialization ownership when the first request is cancelled.

        Returns
        -------
        None
            Raises AssertionError if cancellation leaves an unusable kernel lock.
        """
        application = _new_application()
        kernel = _StubKernel()
        boot = _AsyncGate()
        kernel.bootAction = _AsyncCall(side_effect=boot.run)
        kernel.asgiAction = _AsyncCall(return_value="ready")
        kernel.rsgiAction = _AsyncCall(return_value="ready")
        application.build = _AsyncCall(return_value=kernel)
        async with asyncio.timeout(2):
            first = self._requestTask(application, _ReceiveChannel())
            await boot.entered.wait()
            first.cancel()
            with self.assertRaises(asyncio.CancelledError):
                await first
            self.assertIsNone(application._Application__kernel_http_asgi)
            self.assertIsNone(application._Application__kernel_http_rsgi)
            boot.release.set()
            self.assertEqual(
                await self._requestTask(application, _ReceiveChannel()),
                "ready",
            )
        self.assertEqual(kernel.bootAction.awaitCount, 2)

    async def testLifespanHandlesDuplicateStartupAndShutdown(self) -> None:
        """
        Run startup once, acknowledge duplicates, and end after first shutdown.

        Returns
        -------
        None
            Raises AssertionError if lifecycle callbacks execute repeatedly.
        """
        application = _new_application()
        application._Application__onStartup = _AsyncCall()
        application._Application__onShutdown = _AsyncCall()
        receive = _AsyncCall(side_effect=[
            {"type": "unknown.event"},
            {"type": "lifespan.startup"},
            {"type": "lifespan.startup"},
            {"type": "lifespan.shutdown"},
            {"type": "lifespan.shutdown"},
        ])
        send = _AsyncCall()
        await application({"type": "lifespan"}, receive, send)
        self.assertEqual(
            application._Application__onStartup.calls,
            [((), {"runtime": Runtime.HTTP})],
        )
        self.assertEqual(
            application._Application__onShutdown.calls,
            [((), {"runtime": Runtime.HTTP})],
        )
        self.assertEqual(receive.awaitCount, 4)
        self.assertEqual(
            [args[0] for args, _kwargs in send.calls],
            [
                {"type": "lifespan.startup.complete"},
                {"type": "lifespan.startup.complete"},
                {"type": "lifespan.shutdown.complete"},
            ],
        )

    async def testLifespanReportsStartupFailure(self) -> None:
        """
        Report a lifecycle failure and stop consuming further events.

        Returns
        -------
        None
            Raises AssertionError if startup failure is acknowledged as success.
        """
        application = _new_application()
        application._Application__onStartup = _AsyncCall(
            side_effect=RuntimeError("startup failed"),
        )
        receive = _AsyncCall(return_value={"type": "lifespan.startup"})
        send = _AsyncCall()
        await application({"type": "lifespan"}, receive, send)
        self.assertEqual(receive.awaitCount, 1)
        self.assertEqual(send.calls, [(({
            "type": "lifespan.startup.failed",
            "message": "startup failed",
        },), {})])

    async def testUnsupportedScopesDoNotInitializeKernel(self) -> None:
        """
        Ignore unsupported ASGI and RSGI protocols without loading a kernel.

        Returns
        -------
        None
            Raises AssertionError if unsupported scopes trigger request work.
        """
        application = _new_application()
        application.build = _AsyncCall()
        self.assertIsNone(
            await application({"type": "websocket"}, _AsyncCall(), _AsyncCall()),
        )
        self.assertIsNone(
            await application.__rsgi__(SimpleNamespace(proto="websocket"), None),
        )
        self.assertEqual(application.build.awaitCount, 0)
