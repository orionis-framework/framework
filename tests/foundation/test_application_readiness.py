import asyncio
from collections import deque
from pathlib import Path
from orionis.foundation.application import Application
from orionis.test import TestCase

class _HeadlessApplication(Application):
    def create(self) -> Application:
        """Register a controlled configuration stage without global services.

        Returns
        -------
        Application
            Isolated application marked as created.
        """
        self._Application__booted = True
        return self

class _BootProvider:
    __slots__ = ("calls", "entered", "failure", "release")

    def __init__(self) -> None:
        """Initialize the provider startup barriers.

        Returns
        -------
        None
            Initialize counters, events and optional startup failure.
        """
        self.calls = 0
        self.entered = asyncio.Event()
        self.release = asyncio.Event()
        self.failure = None

    async def boot(self) -> None:
        """Wait at a controllable startup barrier.

        Returns
        -------
        None
            Finish startup after the barrier opens.

        Raises
        ------
        RuntimeError
            Propagate the configured startup failure.
        """
        self.calls += 1
        self.entered.set()
        await self.release.wait()
        if self.failure is not None:
            raise self.failure

def make_application() -> _HeadlessApplication:
    """Build an isolated application without replacing the running singleton.

    Returns
    -------
    _HeadlessApplication
        Application with its real startup locks and readiness flags.
    """
    app = object.__new__(_HeadlessApplication)
    app.__init__(Path.cwd())
    return app

class TestApplicationReadiness(TestCase):
    async def testHeadlessBootCreatesAndAwaitsProviders(self) -> None:
        """Publish provider readiness only after asynchronous startup finishes.

        Returns
        -------
        None
            Validate all three readiness stages while startup is suspended.
        """
        app = make_application()
        provider = _BootProvider()
        app._Application__pending_boot_providers = deque((provider,))
        self.assertFalse(app.isCreated)
        self.assertFalse(app.areProvidersBooted)
        async with asyncio.TaskGroup() as group:
            task = group.create_task(app.boot())
            await provider.entered.wait()
            self.assertTrue(app.isCreated)
            self.assertTrue(app.isBooted)
            self.assertFalse(app.areProvidersBooted)
            self.assertFalse(app.isHttpReady)
            provider.release.set()
        self.assertIs(task.result(), app)
        self.assertTrue(app.areProvidersBooted)
        self.assertFalse(app.isHttpReady)

    async def testConcurrentBootRunsProviderOnce(self) -> None:
        """Share asynchronous provider startup across headless callers.

        Returns
        -------
        None
            Verify concurrent and repeated calls do not boot a provider twice.
        """
        app = make_application()
        provider = _BootProvider()
        app._Application__pending_boot_providers.append(provider)
        async with asyncio.TaskGroup() as group:
            first = group.create_task(app.boot())
            await provider.entered.wait()
            second = group.create_task(app.boot())
            provider.release.set()
        self.assertIs(first.result(), app)
        self.assertIs(second.result(), app)
        self.assertIs(await app.boot(), app)
        self.assertEqual(provider.calls, 1)

    async def testFailedBootRemainsRetryableAndNotReady(self) -> None:
        """Retain failed provider startup without advertising readiness.

        Returns
        -------
        None
            Verify a later public boot call can retry the provider.
        """
        app = make_application()
        provider = _BootProvider()
        provider.release.set()
        message = "headless boot failed"
        provider.failure = RuntimeError(message)
        app._Application__pending_boot_providers.append(provider)
        with self.assertRaisesRegex(RuntimeError, message):
            await app.boot()
        self.assertTrue(app.isCreated)
        self.assertFalse(app.areProvidersBooted)
        provider.failure = None
        await app.boot()
        self.assertTrue(app.areProvidersBooted)
        self.assertEqual(provider.calls, 2)

    async def testHeadlessBootDoesNotExecuteRuntimeHooks(self) -> None:
        """Leave server and command lifecycle hooks with their entry points.

        Returns
        -------
        None
            Verify provider-only startup leaves both kernels uninitialized.
        """
        app = make_application()
        await app.boot()
        self.assertIsNone(app._Application__kernel_cli)
        self.assertIsNone(app._Application__kernel_http_asgi)
        self.assertIsNone(app._Application__kernel_http_rsgi)
        self.assertTrue(app.areProvidersBooted)

    def testHttpReadinessRequiresBothHandlersAndProviders(self) -> None:
        """Require successful provider and kernel stages for HTTP readiness.

        Returns
        -------
        None
            Verify partial publication cannot indicate HTTP readiness.
        """
        app = make_application()
        app.create()
        app._Application__kernel_http_asgi = app.boot
        self.assertFalse(app.isHttpReady)
        app._Application__kernel_http_rsgi = app.boot
        self.assertTrue(app.isHttpReady)
        app._Application__pending_boot_providers.append(_BootProvider())
        self.assertFalse(app.isHttpReady)
