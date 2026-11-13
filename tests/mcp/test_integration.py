# ruff: noqa: ANN001, ANN201, ANN202, PT009, PT027, S603
# Preserve native TestCase assertions, boundary probes, and fixture signatures.
# Run fixed import probes and CLI fixtures using the active interpreter.
import asyncio
import inspect
import subprocess
import sys
import tempfile
from contextlib import ExitStack, redirect_stdout
from io import BytesIO, StringIO, TextIOWrapper
from importlib import import_module
from pathlib import Path
from types import FunctionType
from typing import get_type_hints
from unittest.mock import patch
from orionis.console.commands.make.mcp import (
    MakeMcpPrompt,
    MakeMcpResource,
    MakeMcpServer,
    MakeMcpTool,
)
from orionis.console.core.commands import get_core_commands_mapping
from orionis.console.stdio import protocol_stdio, protocol_stdout
from orionis.container.context.scope import reset_scope, set_current_scope
from orionis.foundation.application import Application
from orionis.foundation.contracts.application import IApplication
from orionis.foundation.core_config import get_core_config_mapping
from orionis.foundation.core_paths import CORE_APP_PATHS
from orionis.foundation.core_providers import get_core_providers_mapping
from orionis.http.routes.contracts.router import IRouter
from orionis.http.routes.provider import RouterProvider
from orionis.http.routes.route_cache import RouteCache
from orionis.http.routes.route_compiler import RouteCompiler
from orionis.mcp.contracts.event_bus import IMcpEventBus
from orionis.mcp.contracts.manager import IMcpManager
from orionis.mcp.protocol.requests import SubscriptionFilter
from orionis.mcp.provider import McpProvider
from orionis.mcp.server.primitives import Server
from orionis.support.facades.mcp import Mcp
from orionis.support.facades.router import Route
from orionis.test import TestCase

_RUNTIME_MODULES = (
    "orionis.mcp.context",
    "orionis.mcp.contracts.event_bus",
    "orionis.mcp.contracts.manager",
    "orionis.mcp.dispatcher",
    "orionis.mcp.invoker",
    "orionis.mcp.manager",
    "orionis.mcp.normalization",
    "orionis.mcp.reporting",
    "orionis.mcp.responses",
    "orionis.mcp.protocol.mrtr",
    "orionis.mcp.server.catalog",
    "orionis.mcp.server.compiler",
    "orionis.mcp.server.extension",
    "orionis.mcp.server.primitives",
    "orionis.mcp.server.templates",
    "orionis.mcp.subscriptions.event_bus",
    "orionis.mcp.transport.headers",
    "orionis.mcp.transport.http",
    "orionis.mcp.transport.policy",
    "orionis.mcp.transport.standard_io",
    "orionis.mcp.transport.stdio",
)


def _runtime_targets() -> list[type | FunctionType]:
    """Collect actual public declarations without supplying artificial namespaces.

    Returns
    -------
    list[type | types.FunctionType]
        Public classes, functions and their directly declared methods.
    """
    targets: list[type | FunctionType] = []
    for module_name in _RUNTIME_MODULES:
        module = import_module(module_name)
        for name, value in tuple(vars(module).items()):
            if (
                name.startswith("_")
                or getattr(value, "__module__", None) != module_name
            ):
                continue
            if isinstance(value, FunctionType):
                targets.append(value)
            elif inspect.isclass(value):
                targets.append(value)
                for member in vars(value).values():
                    if isinstance(member, (classmethod, staticmethod)):
                        function = member.__func__
                    elif isinstance(member, property):
                        function = member.fget
                    else:
                        function = member
                    if inspect.isfunction(function):
                        targets.append(function)
    return targets


class ExampleServer(Server):
    """Supply importable metadata for native route-cache reconstruction."""

    name = "Integration server"
    version = "1.0.0"


class _Consumer:
    """Request the same manager through ordinary constructor injection."""

    def __init__(self, manager: IMcpManager) -> None:
        """Initialize the test double.

        Parameters
        ----------
        manager : IMcpManager
            Value supplied for ``manager``.

        Returns
        -------
        None
            Complete the documented checks or setup without a return value.
        """
        self.manager = manager


def _application(root: Path, ai: str | None = None):
    # A native Reactor test command already owns a scope. A separate test app
    # must register in its own container, never in the runner's active scope.
    """Build a configured application for the integration tests.

    Parameters
    ----------
    root : Path
        Value supplied for ``root``.
    ai : str | None
        Value supplied for ``ai``.

    Returns
    -------
    object
        Return the result produced by ``_application``.
    """
    token = set_current_scope(None)
    try:
        app = object.__new__(Application)
        Application.__init__(app, base_path=root)
        app.withRouting(ai=ai, health="/up")
        app._Application__bootstrap["config"] = {"mcp": {}}
        app._Application__bootstrap["paths"] = {
            key: root / value for key, value in CORE_APP_PATHS.items()
        }
        app._Application__commitConfig()
        app._Application__booted = True
        app.instance(IApplication, app)
        RouterProvider(app).register()
        provider = McpProvider(app)
        provider.register()
        return app, provider
    finally:
        reset_scope(token)


def _facades(app):
    """Resolve facades from the configured application.

    Parameters
    ----------
    app : object
        Value supplied for ``app``.

    Returns
    -------
    object
        Return the result produced by ``_facades``.
    """
    stack = ExitStack()
    stack.callback(reset_scope, set_current_scope(None))
    for facade in (Route, Mcp):
        stack.enter_context(patch.object(facade, "_application", app))
        stack.enter_context(patch.object(facade, "_pinned_instance", None))
    return stack


class TestMcpIntegration(TestCase):
    """Connect public registrations to real containers, router and event bus."""

    def testPublicRuntimeAnnotationsResolveWithoutInjectedNamespaces(self) -> None:
        """Allow native DI and reflection to resolve every declared MCP type.

        Returns
        -------
        None
            No return value.
        """
        for target in _runtime_targets():
            with self.subTest(target=f"{target.__module__}.{target.__qualname__}"):
                get_type_hints(target)

    def testRuntimeTypesPreserveColdImportsAndNativeRequestIdentity(self) -> None:
        """Resolve public types after independent imports without eager HTTP parsing.

        Returns
        -------
        None
            No return value.
        """
        script = """
import importlib
import sys
from typing import get_type_hints

entry = sys.argv[1]
importlib.import_module(entry)
if entry in {
    "orionis.mcp.context", "orionis.mcp.invoker",
    "orionis.mcp.server.compiler", "orionis.mcp.transport.stdio",
}:
    assert "orionis.http.request" not in sys.modules

from tests.mcp.test_integration import _runtime_targets
for target in _runtime_targets():
    get_type_hints(target)
from orionis.mcp.context import McpContext, McpRequest
from orionis.mcp.contracts.manager import IMcpManager
from orionis.http.request import Request
from orionis.http.responses import Response
assert McpContext is McpRequest
assert get_type_hints(McpRequest)["native_request"] == Request | None
assert get_type_hints(IMcpManager.dispatchHttp)["return"] is Response
print("MCP runtime annotations resolved")
"""
        for entry in (
            "orionis.mcp.context",
            "orionis.mcp.invoker",
            "orionis.mcp.server.compiler",
            "orionis.mcp.contracts.manager",
            "orionis.mcp.manager",
            "orionis.mcp.transport.stdio",
            "orionis.mcp.transport.http",
            "orionis.mcp",
        ):
            with self.subTest(entry=entry):
                result = subprocess.run(
                    [sys.executable, "-B", "-c", script, entry],
                    cwd=Path(__file__).resolve().parents[2],
                    capture_output=True,
                    check=False,
                    text=True,
                    encoding="utf-8",
                    timeout=30,
                )
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertIn("MCP runtime annotations resolved", result.stdout)

    async def testFluentAndGroupPrefixesResolveAfterRegistration(self):
        """Respect native path mutations without searching every incoming request.

        Returns
        -------
        None
            Complete the documented checks or setup without a return value.
        """
        with tempfile.TemporaryDirectory() as directory:
            app, provider = _application(Path(directory))
            with _facades(app):
                await provider.boot()
                manager = await app.make(IMcpManager)
                first = manager.web("/mcp", ExampleServer).prefix("/one")
                second = manager.web("/mcp", ExampleServer)
                router = await app.make(IRouter)
                router.group(prefix="/two", routes=[second])
                manager.finalizeRoutes()
                self.assertIs(
                    manager.getWebServer("/one/mcp"),
                    manager.getWebServer("/two/mcp"),
                )
                self.assertEqual(
                    [row[1] for row in manager.servers()],
                    ["/one/mcp", "/two/mcp"],
                )
                first.prefix("/nested")
                manager.finalizeRoutes()
                with self.assertRaises(KeyError):
                    manager.getWebServer("/one/mcp")
                self.assertIsNotNone(manager.getWebServer("/nested/one/mcp"))

    async def testFacadeDiTransportsAndCacheShareCompiledMetadata(self):
        """Preserve native API routes and one compiled object in both modes.

        Returns
        -------
        None
            Complete the documented checks or setup without a return value.
        """
        with tempfile.TemporaryDirectory() as directory:
            app, provider = _application(Path(directory))
            with _facades(app):
                await provider.boot()
                manager = await app.make(IMcpManager)
                consumer = await app.build(_Consumer)
                self.assertIs(manager, consumer.manager)
                self.assertIs(manager, await Mcp.resolve())
                Mcp.web("/mcp/example", ExampleServer)
                Mcp.local("example", ExampleServer)
                self.assertIs(
                    manager.getWebServer("/mcp/example/"),
                    manager.getLocalServer("example"),
                )
                router = await app.make(IRouter)
                exported = router.export()
                native = [
                    route
                    for route in exported["routes"]
                    if route["path"] == "/mcp/example"
                ]
                self.assertEqual(len(native), 1)
                self.assertEqual(native[0]["method"], "POST")
                self.assertEqual(native[0]["kind"], "api")
                routes, fallback = RouteCompiler().compile(
                    exported["routes"],
                    exported["fallback"],
                    [],
                )
                restored, _ = RouteCache().fromCache(
                    RouteCache().toCache(routes, fallback),
                )
                restored_route = restored["POST"]["static"]["/mcp/example"]
                self.assertEqual(restored_route.kind, "api")
                self.assertEqual(restored_route.action["class"], "McpController")
                self.assertIs(manager, await app.make(IMcpManager))
                await manager.shutdown()

    async def testAiRegistrationsLoadOncePerAppIndependentOfImportCache(
        self,
    ) -> None:
        """Load registrations for each application even when Python cached imports.

        Returns
        -------
        None
            Verify independent registrations and resolved AI routing paths.
        """
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "ai.py").write_text(
                "from orionis.support.facades import Mcp\n"
                "from tests.mcp.test_integration import ExampleServer\n"
                "Mcp.web('/mcp/ai', ExampleServer)\n"
                "Mcp.local('ai', ExampleServer)\n",
                encoding="utf-8",
            )
            for _ in range(2):
                app, provider = _application(root, "ai.py")
                with _facades(app):
                    await provider.boot()
                    await provider.boot()
                    manager = await app.make(IMcpManager)
                    self.assertEqual(len(manager.servers()), 2)
                    self.assertIs(
                        manager.getLocalServer("ai"),
                        manager.getWebServer("/mcp/ai"),
                    )
                    paths = app.routingPaths("ai")
                    paths.clear()
                    self.assertEqual(
                        app.routingPaths("ai"),
                        [(root / "ai.py").resolve()],
                    )

    async def testDuplicateRegistrationAndUnregisteredEventsFailAtBoot(self):
        """Reject duplicate handles, ambiguous paths and unknown server events.

        Returns
        -------
        None
            Complete the documented checks or setup without a return value.
        """
        with tempfile.TemporaryDirectory() as directory:
            app, provider = _application(Path(directory))
            with _facades(app):
                await provider.boot()
                manager = await app.make(IMcpManager)
                with self.assertRaises(ValueError):
                    await manager.toolsChanged(ExampleServer)
                manager.web("mcp/example/", ExampleServer)
                manager.local("example", ExampleServer)
                with self.assertRaises(ValueError):
                    manager.web("/mcp/example", ExampleServer)
                with self.assertRaises(ValueError):
                    manager.local("example", ExampleServer)
                with self.assertRaises(ValueError):
                    manager.local("../../app.tools", ExampleServer)
                with self.assertRaises(ValueError):
                    manager.web("/mcp/{dynamic}", ExampleServer)

    async def testNotificationsUseTheInjectedBusAndShutdownUnblocks(self):
        """Use one event bus and release consumers when the application shuts down.

        Returns
        -------
        None
            Complete the documented checks or setup without a return value.
        """
        with tempfile.TemporaryDirectory() as directory:
            app, provider = _application(Path(directory))
            with _facades(app):
                await provider.boot()
                manager = await app.make(IMcpManager)
                manager.local("example", ExampleServer)
                bus = await app.make(IMcpEventBus)
                listener = bus.listen(
                    ExampleServer,
                    SubscriptionFilter(toolsListChanged=True),
                )
                await Mcp.toolsChanged(ExampleServer)
                self.assertEqual(
                    await anext(listener),
                    ("notifications/tools/list_changed", None),
                )
                waiter = asyncio.create_task(anext(listener))
                await manager.shutdown()
                with self.assertRaises(StopAsyncIteration):
                    await asyncio.wait_for(waiter, timeout=1)
                self.assertEqual(bus.listenerCount, 0)


class TestMcpCli(TestCase):
    """Protect the protocol stream and generate usable native declarations."""

    def testCoreWiringAndGenerators(self):
        """Generate compilable declarations and retain existing file safety guards.

        Returns
        -------
        None
            Complete the documented checks or setup without a return value.
        """
        self.assertIn(McpProvider, get_core_providers_mapping())
        self.assertEqual(
            get_core_config_mapping()["mcp"]["max_request_size"],
            1024 * 1024,
        )
        commands = {command.signature for command in get_core_commands_mapping()}
        self.assertTrue({"mcp:list", "mcp:start", "make:mcp-tool"}.issubset(commands))
        with tempfile.TemporaryDirectory() as directory:
            app, _ = _application(Path(directory))
            for command in (MakeMcpServer, MakeMcpTool, MakeMcpResource, MakeMcpPrompt):
                generated = command().createFile(app, "example")
                source = (app.basePath / generated).read_text(encoding="utf-8")
                compile(source, generated, "exec")
                self.assertIn("class Example", source)
                with self.assertRaises(FileExistsError):  # NOSONAR
                    command().createFile(app, "example")
                with self.assertRaises(ValueError):  # NOSONAR
                    command().createFile(app, "../../escape")

    def testEarlyStdoutBoundaryIsNestedAndRestored(self):
        """Separate diagnostics from protocol bytes throughout nested bootstrap.

        Returns
        -------
        None
            Complete the documented checks or setup without a return value.
        """
        binary = BytesIO()
        output = TextIOWrapper(binary, encoding="utf-8")
        diagnostics = StringIO()
        with (
            patch.object(sys, "stdout", output),
            patch.object(sys, "stderr", diagnostics),
        ):
            with protocol_stdio(["reactor", "mcp:start", "example"]):
                self.assertIs(protocol_stdout(), binary)
                sys.stdout.write("bootstrap diagnostic\n")
                with protocol_stdio(["mcp:start", "example"]):
                    protocol_stdout().write(b'{"jsonrpc":"2.0"}\n')
                self.assertIs(sys.stdout, diagnostics)
            self.assertIsNone(protocol_stdout())
            self.assertIs(sys.stdout, output)
        self.assertEqual(binary.getvalue(), b'{"jsonrpc":"2.0"}\n')
        self.assertIn("bootstrap diagnostic", diagnostics.getvalue())

    def testNormalCommandsKeepStdout(self):
        """Leave ordinary console output available to users and pipelines.

        Returns
        -------
        None
            Complete the documented checks or setup without a return value.
        """
        output = StringIO()
        with redirect_stdout(output), protocol_stdio(["reactor", "mcp:list"]):
            sys.stdout.write("ordinary command")
        self.assertEqual(output.getvalue(), "ordinary command")

    def testUnknownLocalHandleNeverWritesProtocolStdout(self):
        """Reject an invalid handle from the actual CLI without corrupting stdout.

        Returns
        -------
        None
            Complete the documented checks or setup without a return value.
        """
        root = Path(__file__).resolve().parents[2]
        result = subprocess.run(
            [sys.executable, "-B", "reactor", "mcp:start", "missing-fixture"],
            cwd=root,
            capture_output=True,
            check=False,
            timeout=30,
        )
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout, b"")
        self.assertIn(b"not registered", result.stderr)
