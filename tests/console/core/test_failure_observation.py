# ruff: noqa: PT009
# Preserve native TestCase assertions, boundary probes, and fixture signatures.
"""Verify console dispatch uses one original failure and preserves exit codes."""

from unittest.mock import AsyncMock, MagicMock, patch
from orionis.console.core.reactor import Reactor
from orionis.console.entities.command import Command
from orionis.failure.catch import Catch
from orionis.test import TestCase
from tests.support.failure_runtime import activate_runtime


class _Command:
    """Expose a controllable command without external dependencies."""

    error: Exception | None = None
    result = 0

    async def handle(self) -> int:
        """Verify handle."""
        if self.error is not None:
            raise self.error
        return self.result


class TestConsoleFailureObservation(TestCase):
    """Use actual container invocation, Catch and the configured handler."""

    async def asyncSetUp(self) -> None:
        """Prepare an isolated runtime and collaborators."""
        self.app, self.runtime, self.handler = activate_runtime()
        self.app.getExceptionHandler = AsyncMock(return_value=self.handler)
        loader = MagicMock()
        loader.get = AsyncMock(
            return_value=Command(
                obj=_Command,
                signature="test:failure",
                description="Test",
                timestamps=False,
            ),
        )
        performance = MagicMock()
        performance.astart = AsyncMock()
        performance.astop = AsyncMock()
        performance.agetSeconds = AsyncMock(return_value=0.1)
        self.logger = MagicMock()
        self.reactor = Reactor(
            self.app,
            loader,
            MagicMock(),
            self.logger,
            Catch(self.app),
            performance,
        )

    async def testExceptionArgsAndIdentityRemainUnmodified(self) -> None:
        """Verify exception args and identity remain unmodified."""
        error = ValueError("original", 42)
        with patch.object(_Command, "error", error):
            result = await self.reactor.call("test:failure")
        self.assertEqual(result, 1)
        self.assertEqual(error.args, ("original", 42))
        self.assertEqual(self.handler.reports, [error])
        self.assertEqual(self.handler.rendered, [error])
        self.logger.error.assert_not_called()

    async def testNonzeroResultReachesResultHookWithoutSyntheticException(self) -> None:
        """Verify nonzero result reaches result hook without synthetic exception."""
        with patch.object(_Command, "result", 7):
            result = await self.reactor.call("test:failure")
        self.assertEqual(result, 7)
        self.assertEqual(self.handler.failures, [])
        self.assertEqual([value for value, _ in self.handler.results], [7])

    async def testReporterFailureDoesNotChangeCommandFailureExitCode(self) -> None:
        """Verify reporter failure does not change command failure exit code."""
        error = ValueError("command")
        with (
            patch.object(_Command, "error", error),
            patch.object(self.handler, "log", side_effect=OSError("logger")),
            patch("sys.stderr.write"),
        ):
            result = await self.reactor.call("test:failure")
        self.assertEqual(result, 1)
        self.assertEqual(self.handler.failures[0][0], error)
        self.assertEqual(self.handler.rendered, [error])

    async def testSuccessDoesNotInvokeFailureOrResultHooks(self) -> None:
        """Verify success does not invoke failure or result hooks."""
        self.assertEqual(await self.reactor.call("test:failure"), 0)
        self.assertEqual(self.handler.failures, [])
        self.assertEqual(self.handler.results, [])
