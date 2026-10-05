from __future__ import annotations
import fnmatch
import functools
import re
import unittest
from contextvars import ContextVar
from typing import TYPE_CHECKING, cast
from orionis.support.facades.application import Application

if TYPE_CHECKING:
    from collections.abc import Callable
    from typing import Any
    from orionis.container.contracts.container import IContainer
    from orionis.mcp.config import McpConfig
    from orionis.mcp.server.compiler import CompiledMcpServer
    from orionis.mcp.server.primitives import Server
    from orionis.test.clients.mcp import McpTestClient

# Lifecycle hooks that must never be wrapped regardless of naming pattern.
_LIFECYCLE_HOOKS: frozenset[str] = frozenset({
    "setUp", "tearDown",
    "setUpClass", "tearDownClass",
    "asyncSetUp", "asyncTearDown",
})

# Precompiled regex for the default glob pattern avoids repeated fnmatch compilation.
_DEFAULT_PATTERN: re.Pattern[str] = re.compile(fnmatch.translate("test*"))

# unittest enables asyncio debug for every isolated test. Its 0.1-second
# default reports routine test work as a slow task; retain debug with a
# threshold that highlights substantial event-loop blocking.
_SLOW_CALLBACK_DURATION: float = 1.0

# Context-local pattern: a value set by one run is never seen by another run
# executing in a different task or thread.
_METHOD_PATTERN: ContextVar[re.Pattern[str]] = ContextVar(
    "orionis_test_method_pattern",
    default=_DEFAULT_PATTERN,
)

class TestCase(unittest.IsolatedAsyncioTestCase): # NOSONAR

    @classmethod
    def setMethodPattern(cls, pattern: str) -> None:
        """
        Set the method pattern for identifying test methods.

        Parameters
        ----------
        pattern : str
            The glob pattern to match test method names (e.g., "test*").

        Returns
        -------
        None
            This method stores the compiled pattern in the current context and
            returns None.
        """
        # Compile once and publish it to the current context only.
        _METHOD_PATTERN.set(re.compile(fnmatch.translate(pattern)))

    def __init__(self, method_name: str = "runTest") -> None:
        """
        Initialize the test case and eagerly wrap the designated test method.

        Parameters
        ----------
        method_name : str, optional
            Name of the test method to run, by default "runTest".

        Returns
        -------
        None
            Complete the documented operation without returning a value.
        """
        super().__init__(method_name)

        # Wrap the single test method once at construction instead of
        # intercepting every attribute access via __getattribute__.
        _regex: re.Pattern[str] = _METHOD_PATTERN.get()
        if (
            not method_name.startswith("_")
            and method_name not in _LIFECYCLE_HOOKS
            and _regex.match(method_name) is not None
        ):
            original = object.__getattribute__(self, method_name)
            if callable(original):
                object.__setattr__(self, method_name, self._resolveTest(original))

    async def mcp(
        self,
        server: type[Server] | CompiledMcpServer,
        config: McpConfig | None = None,
        *,
        app: IContainer | None = None,
    ) -> McpTestClient:
        """
        Create an MCP client using the test runner's application.

        Parameters
        ----------
        server : type[Server] | CompiledMcpServer
            Server declaration or compiled snapshot to exercise.
        config : McpConfig | None, optional
            Client limits; use MCP defaults when omitted.
        app : IContainer | None, optional
            Explicit container for isolated tests; otherwise use the application
            already booted by the Orionis test runner.

        Returns
        -------
        McpTestClient
            In-process client with independent request scopes and event state.

        Raises
        ------
        RuntimeError
            If no container is supplied and the application is not booted.
        """
        from orionis.test.clients.mcp import McpTestClient  # noqa: PLC0415

        container = app if app is not None else cast(
            "IContainer", await Application.resolve(),
        )
        return McpTestClient(container, server, config)

    def _setupAsyncioRunner(self) -> None:
        """
        Configure the event loop's slow-callback threshold.

        Keep asyncio debug checks enabled while reporting substantial event-loop
        blocking.

        Returns
        -------
        None
            Set the loop's ``slow_callback_duration`` to the configured threshold.
        """
        super()._setupAsyncioRunner()
        loop = self._asyncioRunner.get_loop()
        loop.slow_callback_duration = _SLOW_CALLBACK_DURATION

    def _resolveTest(self, method: Callable[..., Any]) -> Callable[..., Any]:
        """
        Wrap a test method to initialize the application context before execution.

        Parameters
        ----------
        method : Callable[..., Any]
            The test method to be wrapped.

        Returns
        -------
        Callable[..., Any]
            An asynchronous wrapper that invokes the test method within the
            application context.
        """
        @functools.wraps(method)
        async def wrapper(*args: object, **kwargs: object) -> object:
            """
            Invoke a test method within the application context.

            Parameters
            ----------
            *args : object
                Positional arguments passed to the test method.
            **kwargs : object
                Keyword arguments passed to the test method.

            Returns
            -------
            object
                Result returned by the test method.
            """
            # Execute the test method inside the application context.
            return await Application.invoke(method, *args, **kwargs)

        return wrapper
