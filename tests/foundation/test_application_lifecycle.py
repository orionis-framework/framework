import asyncio
from collections import deque
from pathlib import Path
from types import SimpleNamespace
from orionis.foundation.application import Application
from orionis.foundation.enums.lifespan import Lifespan
from orionis.foundation.enums.runtimes import Runtime
from orionis.test import TestCase

def make_application() -> Application:
    """
    Construct an application without publishing a container singleton.

    Returns
    -------
    Application
        Isolated application with initialized lifecycle state.
    """
    app = object.__new__(Application)
    app.__init__(Path.cwd())
    return app

class _Provider:
    __slots__ = ("calls", "entered", "error", "release")

    def __init__(self) -> None:
        """
        Initialize a provider controlled by event barriers.

        Returns
        -------
        None
            Create the events and boot counter.
        """
        self.calls = 0
        self.entered = asyncio.Event()
        self.release = asyncio.Event()
        self.error = None

    async def boot(self) -> None:
        """Record startup and wait until the test releases the provider.

        Returns
        -------
        None
            Complete after the barrier unless an error is configured.

        Raises
        ------
        self.error
            Raised by this helper to exercise the failure path.
        """
        self.calls += 1
        self.entered.set()
        await self.release.wait()
        if self.error is not None:
            raise self.error

class _CliKernel:
    __slots__ = ("args", "provider")

    def __init__(self, provider: _Provider) -> None:
        """Store the boot barrier and received command arguments.

        Parameters
        ----------
        provider : _Provider
            Barrier used to control kernel initialization.

        Returns
        -------
        None
            Completes the operation described above.
        """
        self.provider = provider
        self.args = []

    def boot(self, _application: Application) -> object:
        """
        Return an awaitable from a synchronous boot method.

        Parameters
        ----------
        _application : Application
            Application supplied by the command dispatcher.

        Returns
        -------
        object
            Coroutine that boots the provider.
        """
        return self.provider.boot()

    async def handle(self, args: list[str]) -> int:
        """
        Record command arguments and return a successful status.

        Parameters
        ----------
        args : list[str]
            Arguments supplied to the command handler.

        Returns
        -------
        int
            Successful process exit code.
        """
        self.args.append(args)
        return 0

class TestApplicationLifecycle(TestCase):
    async def testConcurrentProviderBootWaitsForTheSameProvider(self) -> None:
        """
        Serialize startup and retain provider registration order.

        Returns
        -------
        None
            Assert both callers wait for each provider to finish.
        """
        app = make_application()
        first, second = _Provider(), _Provider()
        app._Application__pending_boot_providers = deque((first, second))
        async with asyncio.TaskGroup() as group:
            one = group.create_task(app._Application__bootEagerProviders())
            await first.entered.wait()
            two = group.create_task(app._Application__bootEagerProviders())
            await asyncio.sleep(0)
            self.assertFalse(two.done())
            self.assertFalse(second.entered.is_set())
            first.release.set()
            await second.entered.wait()
            self.assertFalse(one.done())
            second.release.set()
        self.assertEqual((first.calls, second.calls), (1, 1))
        self.assertFalse(app._Application__pending_boot_providers)

    async def testProviderFailureRetainsPendingStartupForRetry(self) -> None:
        """
        Keep a failed provider at the front of the startup queue.

        Returns
        -------
        None
            Assert retry completes the same provider before its successor.
        """
        app = make_application()
        first, second = _Provider(), _Provider()
        first.release.set()
        second.release.set()
        message = "provider failed"
        first.error = RuntimeError(message)
        app._Application__pending_boot_providers = deque((first, second))
        with self.assertRaisesRegex(RuntimeError, message):
            await app._Application__bootEagerProviders()
        self.assertEqual(second.calls, 0)
        self.assertIs(app._Application__pending_boot_providers[0], first)
        first.error = None
        await app._Application__bootEagerProviders()
        self.assertEqual((first.calls, second.calls), (2, 1))

    async def testProviderCancellationAllowsRetry(self) -> None:
        """
        Release startup coordination after cancellation without losing work.

        Returns
        -------
        None
            Assert a subsequent startup boots the retained provider.
        """
        app = make_application()
        provider = _Provider()
        app._Application__pending_boot_providers.append(provider)
        task = asyncio.create_task(app._Application__bootEagerProviders())
        await provider.entered.wait()
        task.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await task
        provider.release.set()
        await app._Application__bootEagerProviders()
        self.assertEqual(provider.calls, 2)
        self.assertFalse(app._Application__pending_boot_providers)

    async def testConcurrentCommandsShareAwaitableKernelBoot(self) -> None:
        """
        Await synchronous boot wrappers once before handling commands.

        Returns
        -------
        None
            Assert both commands use the fully initialized CLI kernel.
        """
        app = make_application()
        provider = _Provider()
        kernel = _CliKernel(provider)
        loads = []

        async def load_kernel() -> _CliKernel:
            """
            Return the controlled CLI kernel.

            Returns
            -------
            _CliKernel
                Kernel recorded in the load log.
            """
            loads.append(kernel)
            return kernel

        app._Application__loadCLIKernel = load_kernel
        async with asyncio.TaskGroup() as group:
            first = group.create_task(app.handleCommand(["first"]))
            await provider.entered.wait()
            second = group.create_task(app.handleCommand(["second"]))
            await asyncio.sleep(0)
            self.assertEqual(kernel.args, [])
            provider.release.set()
        self.assertEqual((first.result(), second.result()), (0, 0))
        self.assertEqual(kernel.args, [["first"], ["second"]])
        self.assertEqual(provider.calls, 1)
        self.assertEqual(loads, [kernel])

    async def testCommandFailureStillRunsShutdownHooks(self) -> None:
        """
        Pair command startup with shutdown when the handler raises.

        Returns
        -------
        None
            Assert lifecycle callbacks surround the failed command.
        """
        app = make_application()
        events = []

        async def on_startup() -> None:
            """
            Record command startup.

            Returns
            -------
            None
                Append the startup event.
            """
            events.append("startup")

        async def on_shutdown() -> None:
            """
            Record command shutdown.

            Returns
            -------
            None
                Append the shutdown event.
            """
            events.append("shutdown")

        async def handle_command(_args: list[str]) -> int:
            """Fail after recording command execution.

            Parameters
            ----------
            _args : list[str]
                Command arguments.

            Returns
            -------
            int
                No result is returned because execution fails.

            Raises
            ------
            RuntimeError
                Raised by this helper to exercise the failure path.
            """
            events.append("command")
            message = "command failed"
            raise RuntimeError(message)

        app.on(Lifespan.STARTUP, on_startup, runtime=Runtime.CLI)
        app.on(Lifespan.SHUTDOWN, on_shutdown, runtime=Runtime.CLI)
        app._Application__kernel_cli = handle_command
        with self.assertRaisesRegex(RuntimeError, "command failed"):
            await app.handleCommand()
        self.assertEqual(events, ["startup", "command", "shutdown"])

    async def testFailedCliBootDoesNotPublishItsHandler(self) -> None:
        """
        Retry a CLI kernel after an unsuccessful boot attempt.

        Returns
        -------
        None
            Assert the cached handler appears only after successful boot.
        """
        app = make_application()
        provider = _Provider()
        provider.release.set()
        message = "boot failed"
        provider.error = RuntimeError(message)
        kernel = _CliKernel(provider)

        async def load_kernel() -> _CliKernel:
            """
            Return a kernel whose boot behavior is controlled by the test.

            Returns
            -------
            _CliKernel
                Controlled kernel instance.
            """
            return kernel

        app._Application__loadCLIKernel = load_kernel
        with self.assertRaisesRegex(RuntimeError, message):
            await app.handleCommand()
        self.assertIsNone(app._Application__kernel_cli)
        provider.error = None
        self.assertEqual(await app.handleCommand(), 0)
        self.assertEqual(provider.calls, 2)

    async def testSynchronousCliBootRemainsSupported(self) -> None:
        """
        Accept a synchronous kernel boot that returns no awaitable.

        Returns
        -------
        None
            Assert the command executes after synchronous initialization.
        """
        app = make_application()
        provider = _Provider()
        kernel = _CliKernel(provider)
        synchronous_kernel = SimpleNamespace(
            boot=kernel.args.append, handle=kernel.handle,
        )

        async def load_kernel() -> SimpleNamespace:
            """
            Return the synchronous kernel double.

            Returns
            -------
            SimpleNamespace
                Kernel recording its boot argument.
            """
            return synchronous_kernel

        app._Application__loadCLIKernel = load_kernel
        self.assertEqual(await app.handleCommand(["run"]), 0)
        self.assertEqual(kernel.args, [app, ["run"]])
