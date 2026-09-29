import asyncio
from unittest import IsolatedAsyncioTestCase
from unittest.mock import patch
from orionis.foundation.config.http.entitites.http import HTTP
from orionis.foundation.enums.lifespan import Lifespan
from orionis.foundation.enums.runtimes import Runtime
from tests.foundation.test_application_async import (
    _AsyncCall,
    _AsyncGate,
    _new_application,
    _StubKernel,
)

def lifecycle_events(application):
    """Record startup generator boundaries without writing server output.

    Parameters
    ----------
    application : Application
        Application with an event list attached by the test.

    Yields
    ------
    None
        Boundary enclosing startup callbacks and kernel readiness.
    """
    application.events.append("start")
    yield
    application.events.append("ready")

class TestApplicationDispatch(IsolatedAsyncioTestCase):
    """Exercise direct requests without server-created helper tasks."""

    async def testDirectDispatchKeepsServerTaskAndTransport(self) -> None:
        """Forward both protocols in the caller's task with no transport reads.

        Returns
        -------
        None
            Assert handler identity and zero child-task creation.
        """
        application = _new_application()
        application._Application__http_disconnect_monitoring = False
        kernel = _StubKernel()
        application._Application__kernel_http_asgi = kernel.handleASGI
        application._Application__kernel_http_rsgi = kernel.handleRSGI
        caller = asyncio.current_task()
        received = []

        async def record(*arguments: object):
            """Record transport arguments and executing task.

            Parameters
            ----------
            *arguments : object
                Original request transport objects.

            Returns
            -------
            str
                Response marker forwarded to the caller.
            """
            received.append((asyncio.current_task(), arguments))
            return "response"

        kernel.asgiAction.sideEffect = record
        kernel.rsgiAction.sideEffect = record
        scope, protocol = object(), object()
        receive, send = _AsyncCall(), _AsyncCall()
        loop = asyncio.get_running_loop()
        with patch.object(loop, "create_task") as create_task:
            asgi_result = await application._Application__handleHttpAsgi(
                scope, receive, send,
            )
            rsgi_result = await application._Application__handleHttpRsgi(
                scope, protocol,
            )
        create_task.assert_not_called()
        self.assertEqual((asgi_result, rsgi_result), ("response", "response"))
        self.assertEqual(received, [
            (caller, (scope, receive, send)), (caller, (scope, protocol)),
        ])
        self.assertEqual(receive.awaitCount, 0)

    async def testDirectCancellationRunsHandlerCleanup(self) -> None:
        """Propagate server cancellation through the inline handler.

        Returns
        -------
        None
            Assert cleanup completes and cancellation reaches the caller.
        """
        for interface in ("asgi", "rsgi"):
            with self.subTest(interface=interface):
                application = _new_application()
                application._Application__http_disconnect_monitoring = False
                gate = _AsyncGate()
                setattr(application, f"_Application__kernel_http_{interface}", gate.run)
                callback = getattr(
                    application, f"_Application__handleHttp{interface.capitalize()}",
                )
                arguments = (
                    ({}, _AsyncCall(), _AsyncCall())
                    if interface == "asgi" else ({}, object())
                )
                task = asyncio.create_task(callback(*arguments))
                await asyncio.wait_for(gate.entered.wait(), timeout=2)
                task.cancel()
                with self.assertRaises(asyncio.CancelledError):
                    await task
                self.assertTrue(gate.cleaned.is_set())

    async def testDirectReceiveFailurePropagates(self) -> None:
        """Forward body receiver errors to the server without wrapping them.

        Returns
        -------
        None
            Assert the exact transport exception is propagated.
        """
        application = _new_application()
        application._Application__http_disconnect_monitoring = False

        async def read_body(_scope, receive, _send):
            """Read one transport event.

            Parameters
            ----------
            _scope, receive, _send : object
                ASGI transport arguments.

            Returns
            -------
            dict
                Received body message.
            """
            return await receive()

        application._Application__kernel_http_asgi = read_body
        failure = OSError("transport failed")
        with self.assertRaises(OSError) as error: # NOSONAR
            await application._Application__handleHttpAsgi(
                {}, _AsyncCall(side_effect=failure), _AsyncCall(),
            )
        self.assertIs(error.exception, failure)

    async def testStartupWarmsKernelAfterHooksBeforeReady(self) -> None:
        """Publish handlers after hooks and before readiness for either interface.

        Returns
        -------
        None
            Assert one boot, interface selection, and no first-request rebuild.
        """
        for interface in ("asgi", "rsgi"):
            with self.subTest(interface=interface):
                application = _new_application()
                application._Application__http_disconnect_monitoring = False
                application.events = []
                kernel = _StubKernel()
                application.build = _AsyncCall(return_value=kernel)

                async def hook(app=application):
                    """Record the startup callback.

                    Parameters
                    ----------
                    app : Application, optional
                        Application receiving the event.

                    Returns
                    -------
                    None
                        Append the callback event.
                    """
                    app.events.append("hook")

                async def boot(app=application):
                    """Record HTTP kernel readiness.

                    Parameters
                    ----------
                    app : Application, optional
                        Application receiving the event.

                    Returns
                    -------
                    None
                        Append the kernel boot event.
                    """
                    app.events.append("kernel")

                application._Application__hook_events[Runtime.HTTP][Lifespan.STARTUP].add(hook)
                kernel.bootAction.sideEffect = boot
                with patch(
                    "orionis.foundation.lifespan.startup.startup_orionis_generator",
                    lifecycle_events,
                ):
                    await application._Application__onStartup(Runtime.HTTP, interface)
                self.assertEqual(
                    application.events, ["start", "hook", "kernel", "ready"],
                )
                self.assertEqual(application.config("app.interface"), interface)
                await application._Application__handleHttpAsgi(
                    {}, _AsyncCall(), _AsyncCall(),
                )
                await application._Application__handleHttpRsgi({}, object())
                self.assertEqual(kernel.bootAction.awaitCount, 1)
                self.assertEqual(application.build.awaitCount, 1)

    def testDisconnectConfigurationRequiresBoolean(self) -> None:
        """Validate direct dispatch defaults and explicit monitoring configuration.

        Returns
        -------
        None
            Assert only boolean monitoring values are accepted.
        """
        self.assertFalse(HTTP().monitor_disconnects)
        self.assertTrue(HTTP(monitor_disconnects=True).monitor_disconnects)
        for invalid in (None, 0, 1, "false", []):
            with self.subTest(value=invalid), self.assertRaises(TypeError):
                HTTP(monitor_disconnects=invalid)
