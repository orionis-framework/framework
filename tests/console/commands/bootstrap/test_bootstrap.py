from __future__ import annotations
import ast
import os
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, Mock, patch
from orionis.console.commands.bootstrap._service import Bootstrapper
from orionis.console.commands.bootstrap.config import BootstrapConfigCommand
from orionis.console.commands.bootstrap.lifespan import BootstrapLifespanCommand
from orionis.console.commands.bootstrap.routes import (
    BootstrapAiCommand,
    BootstrapApiCommand,
    BootstrapConsoleCommand,
    BootstrapWebCommand,
    BootstrapWebsocketCommand,
)
from orionis.console.core.commands import CORE_COMMANDS
from orionis.container.context.scope import ScopedContext
from orionis.foundation.application import Application
from orionis.foundation.core_paths import CORE_APP_PATHS
from orionis.foundation.enums.lifespan import Lifespan
from orionis.foundation.enums.runtimes import Runtime
from orionis.test import TestCase

if TYPE_CHECKING:
    from typing import IO

_COMMANDS = {
    "api": BootstrapApiCommand,
    "ai": BootstrapAiCommand,
    "console": BootstrapConsoleCommand,
    "web": BootstrapWebCommand,
    "websocket": BootstrapWebsocketCommand,
}
_HTTP_KEYS = (
    "app_http_controllers", "app_http_middleware", "app_http_schemas",
    "app_http_schemas_rules",
)
_MCP_KEYS = (
    "app_mcp_servers", "app_mcp_tools", "app_mcp_resources", "app_mcp_prompts",
)
_CONSOLE_KEYS = ("app_console_commands", "app_console_listeners")
_ROOT = Path(__file__).resolve().parents[4]

class _Application:
    """Expose the effective paths and routing registrations of a project."""

    def __init__(self, root: Path) -> None:
        """
        Initialize independently customizable core paths and registrations.

        Parameters
        ----------
        root : Path
            Project directory containing the effective paths.

        Returns
        -------
        None
            Store effective paths and empty route registrations.
        """
        # Keep each test project independent of the real application singleton.
        self.basePath = root
        self.entryPoint = None
        self.paths = {key: root / value for key, value in CORE_APP_PATHS.items()}
        self.paths["root"] = root
        self.routing: dict[str, list[Path]] = {}

    def path(
        self, key: str | None = None,
    ) -> dict[str, Path] | Path | None:
        """
        Return effective paths through the public application interface.

        Parameters
        ----------
        key : str | None, optional
            Path key to resolve, or None for all paths.

        Returns
        -------
        dict[str, Path] | Path | None
            All paths, the selected path, or None when absent.
        """
        # Mirror the public path lookup used by the bootstrap service.
        return self.paths if key is None else self.paths.get(key)

    def routingPaths(
        self, key: str | None = None,
    ) -> dict[str, list[Path]] | list[Path] | None:
        """
        Return configured routing files without inventing defaults.

        Parameters
        ----------
        key : str | None, optional
            Routing context to resolve, or None for all contexts.

        Returns
        -------
        dict[str, list[Path]] | list[Path] | None
            All routes, the selected route list, or None when absent.
        """
        # Expose only route registrations explicitly loaded by the test.
        return self.routing if key is None else self.routing.get(key)

def _project(root: Path, configuration: str = "") -> tuple[_Application, Path]:
    """
    Write an executable slim bootstrap in a fresh project directory.

    Parameters
    ----------
    root : Path
        Project directory to initialize.
    configuration : str, optional
        Application configuration inserted before creation.

    Returns
    -------
    tuple[_Application, Path]
        Application test double and generated bootstrap path.
    """
    # Place custom configuration between application construction and creation.
    bootstrap = root / "bootstrap" / "app.py"
    bootstrap.parent.mkdir(parents=True, exist_ok=True)
    bootstrap.write_text(
        "from pathlib import Path\n"
        "from orionis import Application\n\n"
        "# Keep the application's construction and customization.\n"
        "app = Application(base_path=Path(__file__).parent.parent)\n\n"
        f"{configuration}"
        "# Boot only after all configuration is registered.\n"
        "app.create()\n",
        encoding="utf-8",
    )
    return _Application(root), bootstrap

def _routing_calls(source: str) -> list[ast.Call]:
    """
    Find route registration calls without relying on textual formatting.

    Parameters
    ----------
    source : str
        Python bootstrap source to inspect.

    Returns
    -------
    list[ast.Call]
        Route registration calls found in the parsed source.
    """
    # Match calls structurally so whitespace cannot affect the assertion.
    return [
        node for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "withRouting"
    ]

def _snapshot(root: Path) -> dict[str, tuple[bytes, int]]:
    """
    Capture file bytes and modification times to detect needless writes.

    Parameters
    ----------
    root : Path
        Project directory to inspect recursively.

    Returns
    -------
    dict[str, tuple[bytes, int]]
        Relative filenames mapped to their bytes and modification times.
    """
    # Include timestamps to detect rewrites that preserve file contents.
    return {
        path.relative_to(root).as_posix(): (
            path.read_bytes(), path.stat().st_mtime_ns,
        )
        for path in root.rglob("*") if path.is_file()
    }

def _execute_bootstrap(path: Path) -> Application:
    """
    Execute real Application configuration while isolating its singleton.

    Parameters
    ----------
    path : Path
        Bootstrap module to execute in an isolated environment.

    Returns
    -------
    Application
        Application instance configured by the bootstrap module.
    """
    # Isolate the singleton and import cache before executing project code.
    application = object.__new__(Application)
    Application.__init__(application, path.parent.parent)
    namespace = {"__file__": str(path), "__name__": "bootstrap.app"}
    with (
        patch.dict(Application._instances, {Application: application}),
        patch.dict(sys.modules),
        patch.object(sys, "path", [str(path.parent.parent), *sys.path]),
    ):
        for name in tuple(sys.modules):
            if name == "bootstrap" or name.startswith("bootstrap."):
                del sys.modules[name]
        exec(compile(path.read_bytes(), str(path), "exec"), namespace)  # noqa: S102
    return namespace["app"]

class TestBootstrapCommands(TestCase):
    """Exercise native commands and persistent application integration."""

    def setUp(self) -> None:
        """
        Keep isolated application registrations outside the runner's scope.

        Returns
        -------
        None
            Register cleanup for the isolated application scope.
        """
        # Restore the previous scope when the test finishes.
        token = ScopedContext.setCurrentScope(None)
        self.addCleanup(ScopedContext.reset, token)

    def testAllSevenCommandsAreRegisteredNatively(self) -> None:
        """
        Expose all signatures in the same registry as existing commands.

        Returns
        -------
        None
            Complete the assertions without returning a value.
        """
        # Check the same native registry used by Reactor discovery.
        commands = [
            *_COMMANDS.values(), BootstrapConfigCommand, BootstrapLifespanCommand,
        ]
        for command in commands:
            with self.subTest(command=command.__name__):
                self.assertIn(command, CORE_COMMANDS)
                self.assertTrue(command.description)
        self.assertEqual(
            {command.signature for command in commands},
            {f"bootstrap:{name}" for name in (*_COMMANDS, "config", "lifespan")},
        )

    async def testEachRoutingCommandCreatesOnlyItsOwnContext(self) -> None:
        """
        Generate valid route files and scoped application directories.

        Returns
        -------
        None
            Complete the assertions without returning a value.
        """
        # Exercise every command against a fresh slim project.
        for context, command_type in _COMMANDS.items():
            with self.subTest(context=context), TemporaryDirectory() as temporary:
                root = Path(temporary)
                app, bootstrap = _project(root)
                command = command_type()
                command.error = Mock()
                command.success = Mock()
                command.info = Mock()
                command.newLine = Mock()
                self.assertEqual(await command.handle(app), 0)
                command.error.assert_not_called()
                route = root / "routes" / f"{context}.py"
                self.assertTrue(route.is_file())
                ast.parse(route.read_text(encoding="utf-8"))
                self.assertEqual(
                    {path.name for path in (root / "routes").glob("*.py")},
                    {f"{context}.py"},
                )
                for keys, applicable in (
                    (_HTTP_KEYS, context in {"api", "web", "websocket"}),
                    (_MCP_KEYS, context == "ai"),
                    (_CONSOLE_KEYS, context == "console"),
                ):
                    for key in keys:
                        self.assertEqual(app.path(key).is_dir(), applicable)
                self.assertFalse((root / "config").exists())
                self.assertFalse((root / "database").exists())
                calls = _routing_calls(bootstrap.read_text(encoding="utf-8"))
                self.assertEqual(len(calls), 1)
                self.assertEqual(
                    [keyword.arg for keyword in calls[0].keywords], [context],
                )
                self.assertEqual(
                    ast.literal_eval(calls[0].keywords[0].value),
                    f"routes/{context}.py",
                )

    def testExistingRouteFilesArePreservedForEveryContext(self) -> None:
        """
        Register preexisting routes while preserving every original byte.

        Returns
        -------
        None
            Complete the assertions without returning a value.
        """
        # Use custom bytes and timestamps to detect accidental overwrites.
        for context in _COMMANDS:
            with self.subTest(context=context), TemporaryDirectory() as temporary:
                root = Path(temporary)
                app, bootstrap = _project(root)
                route = root / "routes" / f"{context}.py"
                route.parent.mkdir(parents=True)
                original = (
                    b"# Custom developer routes.\r\n"
                    b"from orionis.support.facades import Route\r\n"
                    b"CUSTOM = {'enabled': True}\r\n"
                )
                route.write_bytes(original)
                before = route.stat().st_mtime_ns
                Bootstrapper(app).routing(context)
                self.assertEqual(route.read_bytes(), original)
                self.assertEqual(route.stat().st_mtime_ns, before)
                ast.parse(bootstrap.read_text(encoding="utf-8"))

    async def testInvalidExistingRouteFilesFailWithoutAnyWrites(self) -> None:
        """
        Reject invalid Python or nonrouting files before updating bootstrap.

        Returns
        -------
        None
            Complete the assertions without returning a value.
        """
        # Check malformed Python and valid modules without route imports.
        for source in (
            "from orionis.support.facades import Route\ndef incomplete(\n",
            "# This module does not contain native routing imports.\nVALUE = 1\n",
        ):
            with self.subTest(source=source), TemporaryDirectory() as temporary:
                root = Path(temporary)
                app, _ = _project(root)
                route = root / "routes" / "api.py"
                route.parent.mkdir(parents=True)
                route.write_text(source, encoding="utf-8")
                before = _snapshot(root)
                command = BootstrapApiCommand()
                command.error = Mock()
                command.newLine = Mock()
                self.assertEqual(await command.handle(app), 1)
                command.error.assert_called()
                self.assertEqual(_snapshot(root), before)

    def testEmptyExistingRouteRemainsValidAndUnmodified(self) -> None:
        """
        Honor the native validator's explicit acceptance of empty files.

        Returns
        -------
        None
            Complete the assertions without returning a value.
        """
        # Verify the empty-file exception supported by the route validator.
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            app, bootstrap = _project(root)
            route = root / "routes" / "api.py"
            route.parent.mkdir(parents=True)
            route.write_bytes(b"")
            before = route.stat().st_mtime_ns
            Bootstrapper(app).routing("api")
            self.assertEqual(route.read_bytes(), b"")
            self.assertEqual(route.stat().st_mtime_ns, before)
            self.assertEqual(
                _execute_bootstrap(bootstrap).routingPaths("api"), [route.resolve()],
            )

    async def testHelperConfiguredRoutesFailBeforeReplacingOtherContexts(
        self,
    ) -> None:
        """
        Protect effective registrations configured through helper functions.

        Returns
        -------
        None
            Complete the assertions without returning a value.
        """
        # Load helper-based registration before checking safe rejection.
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            _, bootstrap = _project(
                root,
                "def configure(app):\n"
                "    app.withRouting(web='routes/web.py', health='/ready')\n\n"
                "configure(app)\n\n",
            )
            route = root / "routes" / "web.py"
            route.parent.mkdir(parents=True)
            route.write_text(
                "from orionis.support.facades import Route\n", encoding="utf-8",
            )
            app = _execute_bootstrap(bootstrap)
            self.assertEqual(app.routingPaths("web"), [route.resolve()])
            self.assertEqual(app.routeHealthCheck, "/ready")
            before = _snapshot(root)
            command = BootstrapApiCommand()
            command.error = Mock()
            command.newLine = Mock()
            self.assertEqual(await command.handle(app), 1)
            command.error.assert_called()
            self.assertEqual(_snapshot(root), before)
            restored = _execute_bootstrap(bootstrap)
            self.assertEqual(restored.routingPaths("web"), [route.resolve()])
            self.assertEqual(restored.routeHealthCheck, "/ready")

    async def testSourceAndEffectiveRouteMismatchFailsWithoutAnyWrites(
        self,
    ) -> None:
        """
        Reject conflicting runtime paths instead of registering another file.

        Returns
        -------
        None
            Complete the assertions without returning a value.
        """
        # Deliberately disagree with the bootstrap route registration.
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            app, _ = _project(root, "app.withRouting(api='routes/static.py')\n\n")
            app.routing["api"] = [root / "routes" / "effective.py"]
            before = _snapshot(root)
            command = BootstrapApiCommand()
            command.error = Mock()
            command.newLine = Mock()
            self.assertEqual(await command.handle(app), 1)
            command.error.assert_called()
            self.assertEqual(_snapshot(root), before)

    def testDeletedRegisteredRouteIsRecreatedWithoutChangingBootstrap(self) -> None:
        """
        Restore a route deleted after the application loaded its paths.

        Returns
        -------
        None
            Complete the assertions without returning a value.
        """
        # Delete a loaded custom route to exercise recovery in place.
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            _, bootstrap = _project(
                root, "app.withRouting(api='endpoints/public.py', health='/ready')\n",
            )
            route = root / "endpoints" / "public.py"
            route.parent.mkdir(parents=True)
            route.write_text(
                "from orionis.support.facades import Route\n", encoding="utf-8",
            )
            app = _execute_bootstrap(bootstrap)
            source = bootstrap.read_bytes()
            modified_at = bootstrap.stat().st_mtime_ns
            route.unlink()
            Bootstrapper(app).routing("api")
            self.assertTrue(route.is_file())
            ast.parse(route.read_text(encoding="utf-8"))
            self.assertEqual(bootstrap.read_bytes(), source)
            self.assertEqual(bootstrap.stat().st_mtime_ns, modified_at)
            restored = _execute_bootstrap(bootstrap)
            self.assertEqual(restored.routingPaths("api"), [route.resolve()])
            self.assertEqual(restored.routeHealthCheck, "/ready")

    async def testExpandedRoutingPreservesCustomPathsAndRestoresDeletedRoute(
        self,
    ) -> None:
        """
        Honor runtime-confirmed routing passed through expanded keywords.

        Returns
        -------
        None
            Complete the assertions without returning a value.
        """
        # Preserve expanded keywords across creation and recovery runs.
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            _, bootstrap = _project(
                root,
                "ROUTES = {'api': 'custom/api.py', 'health': '/ready'}\n"
                "app.withRouting(**ROUTES)\n\n",
            )
            route = root / "custom" / "api.py"
            route.parent.mkdir(parents=True)
            original_route = b"from orionis.support.facades import Route\n"
            route.write_bytes(original_route)
            route_modified_at = route.stat().st_mtime_ns
            app = _execute_bootstrap(bootstrap)
            original_source = bootstrap.read_bytes()
            source_modified_at = bootstrap.stat().st_mtime_ns
            command = BootstrapApiCommand()
            command.error = Mock()
            command.success = Mock()
            command.info = Mock()
            command.newLine = Mock()

            self.assertEqual(await command.handle(app), 0)
            command.error.assert_not_called()
            self.assertEqual(route.read_bytes(), original_route)
            self.assertEqual(route.stat().st_mtime_ns, route_modified_at)
            self.assertEqual(bootstrap.read_bytes(), original_source)
            self.assertEqual(bootstrap.stat().st_mtime_ns, source_modified_at)
            for key in _HTTP_KEYS:
                self.assertTrue(app.path(key).is_dir())
            for key in (*_MCP_KEYS, *_CONSOLE_KEYS, "config", "routes"):
                self.assertFalse(app.path(key).exists())

            route.unlink()
            self.assertEqual(await command.handle(app), 0)
            self.assertTrue(route.is_file())
            self.assertEqual(bootstrap.read_bytes(), original_source)
            self.assertEqual(bootstrap.stat().st_mtime_ns, source_modified_at)
            restored = _execute_bootstrap(bootstrap)
            self.assertEqual(restored.routingPaths("api"), [route.resolve()])
            self.assertEqual(restored.routeHealthCheck, "/ready")
            before = _snapshot(root)
            self.assertEqual(await command.handle(restored), 0)
            command.error.assert_not_called()
            self.assertEqual(_snapshot(root), before)

    def testRepeatedRoutingCommandsDoNotRewriteAnyFile(self) -> None:
        """
        Keep the bytes and modification times stable after initialization.

        Returns
        -------
        None
            Complete the assertions without returning a value.
        """
        # Snapshot only after every routing context has been initialized.
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            app, _ = _project(root)
            for context in _COMMANDS:
                Bootstrapper(app).routing(context)
            before = _snapshot(root)
            for _ in range(3):
                for context in _COMMANDS:
                    Bootstrapper(app).routing(context)
            self.assertEqual(_snapshot(root), before)

    def testEffectiveCustomPathsCreateAllMissingParents(self) -> None:
        """
        Use loaded paths for both routes and each context's directories.

        Returns
        -------
        None
            Complete the assertions without returning a value.
        """
        # Override each context path before creating missing directories.
        for context in _COMMANDS:
            with self.subTest(context=context), TemporaryDirectory() as temporary:
                root = Path(temporary)
                app, bootstrap = _project(root)
                app.paths["routes"] = root / "project" / "routing" / "definitions"
                keys = (
                    _MCP_KEYS if context == "ai" else _CONSOLE_KEYS
                    if context == "console" else _HTTP_KEYS
                )
                for key in keys:
                    app.paths[key] = root / "components" / "custom" / key
                Bootstrapper(app).routing(context)
                self.assertTrue((app.path("routes") / f"{context}.py").is_file())
                self.assertFalse((root / "routes").exists())
                for key in keys:
                    self.assertTrue(app.path(key).is_dir())
                    self.assertFalse((root / CORE_APP_PATHS[key]).exists())
                keyword = _routing_calls(
                    bootstrap.read_text(encoding="utf-8"),
                )[0].keywords[0]
                self.assertEqual(
                    ast.literal_eval(keyword.value),
                    f"project/routing/definitions/{context}.py",
                )

    def testLoadedCustomRouteListPreservesRegistrationAndFilenames(self) -> None:
        """
        Honor effective route lists instead of generating default files.

        Returns
        -------
        None
            Complete the assertions without returning a value.
        """
        # Retain custom filenames and a multiroute registration.
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            app, bootstrap = _project(
                root,
                "app.withRouting(api=['endpoints/public.v1.py', "
                "'endpoints/internal.py'], health='/ready')\n\n",
            )
            app.routing["api"] = [
                root / "endpoints" / "public.v1.py",
                root / "endpoints" / "internal.py",
            ]
            before = bootstrap.read_bytes()
            Bootstrapper(app).routing("api")
            for route in app.routing["api"]:
                self.assertTrue(route.is_file())
                ast.parse(route.read_text(encoding="utf-8"))
            self.assertFalse((root / "routes" / "api.py").exists())
            self.assertEqual(bootstrap.read_bytes(), before)

    def testPartialRegistrationPreservesHealthCommentsAndOtherContexts(self) -> None:
        """
        Append only the requested context to an existing routing call.

        Returns
        -------
        None
            Complete the assertions without returning a value.
        """
        # Keep unrelated keyword values and comments in the source fixture.
        configuration = (
            "# Keep this project's routing options.\n"
            "app.withRouting(\n"
            "    web='custom/web.py',  # Existing custom route.\n"
            "    health='/health/custom',  # Preserve the health endpoint.\n"
            ")\n\n"
        )
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            app, bootstrap = _project(root, configuration)
            Bootstrapper(app).routing("ai")
            source = bootstrap.read_text(encoding="utf-8")
            for line in configuration.splitlines():
                if line.strip() and line.strip() != ")":
                    self.assertIn(line, source)
            calls = _routing_calls(source)
            self.assertEqual(len(calls), 1)
            values = {
                keyword.arg: ast.literal_eval(keyword.value)
                for keyword in calls[0].keywords
            }
            self.assertEqual(values, {
                "web": "custom/web.py", "health": "/health/custom",
                "ai": "routes/ai.py",
            })

    def testCustomBootstrapEntryPointIsUpdated(self) -> None:
        """
        Use the application's real bootstrap module instead of app.py.

        Returns
        -------
        None
            Complete the assertions without returning a value.
        """
        # Move the bootstrap to the module named by the entry point.
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            app, original = _project(root)
            custom = root / "bootstrap" / "runtime.py"
            original.rename(custom)
            app.entryPoint = "bootstrap.runtime:app"
            Bootstrapper(app).routing("console")
            self.assertFalse(original.exists())
            calls = _routing_calls(custom.read_text(encoding="utf-8"))
            self.assertEqual(len(calls), 1)
            self.assertEqual(calls[0].keywords[0].arg, "console")

    def testRealSlimApplicationBootsBeforeAndAfterEveryContext(self) -> None:
        """
        Load generated registrations through Application's own validator.

        Returns
        -------
        None
            Complete the assertions without returning a value.
        """
        # Reload real application configuration after each context is added.
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            _, bootstrap = _project(root)
            app = _execute_bootstrap(bootstrap)
            self.assertEqual(app.path("routes"), root / "routes")
            for context in _COMMANDS:
                Bootstrapper(app).routing(context)
                app = _execute_bootstrap(bootstrap)
                self.assertEqual(
                    app.routingPaths(context),
                    [(root / "routes" / f"{context}.py").resolve()],
                )

    def testCompleteApplicationRemainsUnchangedAndBootable(self) -> None:
        """
        Leave fully initialized projects unchanged after all route commands.

        Returns
        -------
        None
            Complete the assertions without returning a value.
        """
        # Initialize every context before checking the complete project.
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            app, bootstrap = _project(root)
            for context in _COMMANDS:
                Bootstrapper(app).routing(context)
            app = _execute_bootstrap(bootstrap)
            before = _snapshot(root)
            for context in _COMMANDS:
                Bootstrapper(app).routing(context)
            self.assertEqual(_snapshot(root), before)
            self.assertIsInstance(_execute_bootstrap(bootstrap), Application)

    def testLifespanCreatesRegistersAndRemainsIdempotent(self) -> None:
        """
        Generate valid lifecycle callbacks with one import and registration.

        Returns
        -------
        None
            Complete the assertions without returning a value.
        """
        # Check generated syntax, unique registration, and actual lifecycle hooks.
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            app, bootstrap = _project(root)
            Bootstrapper(app).lifespan()
            lifespan = root / "bootstrap" / "lifespan.py"
            self.assertTrue(lifespan.is_file())
            ast.parse(lifespan.read_text(encoding="utf-8"))
            tree = ast.parse(bootstrap.read_text(encoding="utf-8"))
            registrations = [
                node for node in ast.walk(tree)
                if isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == "register_lifespan_callbacks"
            ]
            self.assertEqual(len(registrations), 1)
            imports = [
                alias for node in ast.walk(tree)
                if isinstance(node, ast.ImportFrom)
                for alias in node.names
                if alias.name == "register_lifespan_callbacks"
            ]
            self.assertEqual(len(imports), 1)
            before = _snapshot(root)
            Bootstrapper(app).lifespan()
            self.assertEqual(_snapshot(root), before)
            real_app = _execute_bootstrap(bootstrap)
            hooks = real_app._Application__hook_events
            self.assertTrue(hooks[None][Lifespan.STARTUP])
            self.assertTrue(hooks[None][Lifespan.SHUTDOWN])

    async def testExistingLifespanCallbacksArePreservedAndExecuted(self) -> None:
        """
        Preserve custom callbacks and register them before application create.

        Returns
        -------
        None
            Complete the assertions without returning a value.
        """
        # Execute a custom callback after preserving its original source.
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            app, bootstrap = _project(root)
            lifespan = root / "bootstrap" / "lifespan.py"
            original = (
                b"from orionis.foundation.enums.lifespan import Lifespan\n"
                b"events = []\n\n"
                b"async def custom_startup():\n"
                b"    events.append('started')\n\n"
                b"def register_lifespan_callbacks(app):\n"
                b"    app.on(Lifespan.STARTUP, custom_startup)\n"
            )
            lifespan.write_bytes(original)
            before = lifespan.stat().st_mtime_ns
            command = BootstrapLifespanCommand()
            command.success = Mock()
            command.info = Mock()
            command.newLine = Mock()
            self.assertEqual(await command.handle(app), 0)
            self.assertEqual(lifespan.read_bytes(), original)
            self.assertEqual(lifespan.stat().st_mtime_ns, before)
            real_app = _execute_bootstrap(bootstrap)
            with patch.object(
                real_app, "_Application__bootEagerProviders", AsyncMock(),
            ):
                await real_app._Application__onStartup(Runtime.CLI)
            callback = next(iter(
                real_app._Application__hook_events[None][Lifespan.STARTUP],
            ))
            self.assertEqual(callback.__globals__["events"], ["started"])

    async def testUnsafeLifespanBootstrapReportsFailureWithoutChangingIt(self) -> None:
        """
        Reject structures that cannot receive callbacks before creation safely.

        Returns
        -------
        None
            Complete the assertions without returning a value.
        """
        # Hide construction inside a factory to exercise unsafe insertion.
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            app, bootstrap = _project(root)
            bootstrap.write_text(
                "from orionis import Application\n"
                "def build():\n"
                "    return Application().create()\n"
                "app = build()\n",
                encoding="utf-8",
            )
            original = bootstrap.read_bytes()
            command = BootstrapLifespanCommand()
            command.error = Mock()
            self.assertEqual(await command.handle(app), 1)
            command.error.assert_called()
            self.assertEqual(bootstrap.read_bytes(), original)

    async def testAsyncLifespanRegistrarFailsWithoutInsertingAnUnawaitedCall(
        self,
    ) -> None:
        """
        Preserve asynchronous registrars when synchronous insertion is unsafe.

        Returns
        -------
        None
            Complete the assertions without returning a value.
        """
        # Keep an asynchronous registrar unchanged when insertion is unsafe.
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            app, _ = _project(root)
            lifespan = root / "bootstrap" / "lifespan.py"
            lifespan.write_text(
                "async def register_lifespan_callbacks(app):\n"
                "    pass\n",
                encoding="utf-8",
            )
            before = _snapshot(root)
            command = BootstrapLifespanCommand()
            command.error = Mock()
            command.success = Mock()
            command.newLine = Mock()
            self.assertEqual(await command.handle(app), 1)
            command.error.assert_called()
            command.success.assert_not_called()
            self.assertEqual(_snapshot(root), before)

    async def testUncompilableLifespanFailsWithoutChangingAnyFile(self) -> None:
        """
        Reject module-level return statements that AST parsing alone permits.

        Returns
        -------
        None
            Complete the assertions without returning a value.
        """
        # Use source that parses but cannot compile as a Python module.
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            app, _ = _project(root)
            lifespan = root / "bootstrap" / "lifespan.py"
            lifespan.write_text(
                "return None\n\n"
                "def register_lifespan_callbacks(app):\n"
                "    pass\n",
                encoding="utf-8",
            )
            ast.parse(lifespan.read_text(encoding="utf-8"))
            before = _snapshot(root)
            command = BootstrapLifespanCommand()
            command.error = Mock()
            command.success = Mock()
            command.newLine = Mock()
            self.assertEqual(await command.handle(app), 1)
            command.error.assert_called()
            command.success.assert_not_called()
            self.assertEqual(_snapshot(root), before)

    async def testFailedResourceWriteRemovesOnlyTheNewPartialFile(self) -> None:
        """
        Clean up an interrupted exclusive write and preserve project files.

        Returns
        -------
        None
            Complete the assertions without returning a value.
        """
        # Simulate failure after an exclusive write has created a partial file.
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            app, bootstrap = _project(root)
            route = root / "routes" / "api.py"
            route.parent.mkdir(parents=True)
            preserved = route.parent / "custom.py"
            preserved.write_bytes(b"# Preserve this existing file.\n")
            before = _snapshot(root)
            original_open = Path.open

            def failing_open(
                path: Path, mode: str = "r",
                *args: object, **kwargs: object,
            ) -> IO[str] | IO[bytes] | MagicMock:
                """
                Fail only writes to the new route after persisting some bytes.

                Parameters
                ----------
                path : Path
                    Filesystem path passed to the patched opener.
                mode : str, optional
                    File mode passed to the original opener.
                *args : object
                    Additional positional arguments for the original opener.
                **kwargs : object
                    Additional keyword arguments for the original opener.

                Returns
                -------
                IO[str] | IO[bytes] | MagicMock
                    Original stream or a wrapper that simulates a partial write.
                """
                # Intercept only exclusive creation of the target route.
                stream = original_open(path, mode, *args, **kwargs)
                if path != route or mode != "x":
                    return stream

                def write_partial(content: str) -> None:
                    """
                    Persist a prefix before simulating an exhausted filesystem.

                    Parameters
                    ----------
                    content : str
                        Generated route source to partially persist.

                    Returns
                    -------
                    None
                        Raise the simulated failure after persisting a prefix.
                    """
                    # Persist enough data to verify cleanup after a real partial write.
                    stream.write(content[:12])
                    stream.flush()
                    self.assertGreater(route.stat().st_size, 0)
                    error_msg = "Simulated route write failure"
                    raise OSError(error_msg)

                target = MagicMock(wraps=stream)
                target.__enter__.return_value = target
                target.__exit__.side_effect = stream.__exit__
                target.write.side_effect = write_partial
                return target

            command = BootstrapApiCommand()
            command.error = Mock()
            command.success = Mock()
            command.newLine = Mock()
            with patch.object(Path, "open", failing_open):
                self.assertEqual(await command.handle(app), 1)
            command.error.assert_called()
            command.success.assert_not_called()
            self.assertFalse(route.exists())
            self.assertTrue(preserved.is_file())
            self.assertTrue(bootstrap.is_file())
            self.assertEqual(_snapshot(root), before)

    async def testUnresolvedDynamicRoutingFailsBeforeCreatingResources(self) -> None:
        """
        Require effective app paths when a source expression is dynamic.

        Returns
        -------
        None
            Complete the assertions without returning a value.
        """
        # Leave the dynamic routing expression unresolved by effective paths.
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            app, bootstrap = _project(root, "app.withRouting(api=select_routes())\n")
            before = _snapshot(root)
            command = BootstrapApiCommand()
            command.error = Mock()
            command.newLine = Mock()
            self.assertEqual(await command.handle(app), 1)
            command.error.assert_called()
            self.assertEqual(_snapshot(root), before)
            ast.parse(bootstrap.read_text(encoding="utf-8"))

    def testEffectivePathsResolveDynamicRoutingWithoutChangingItsExpression(
        self,
    ) -> None:
        """
        Use loaded routing paths while preserving custom Python expressions.

        Returns
        -------
        None
            Complete the assertions without returning a value.
        """
        # Supply loaded routes for an expression that must remain unchanged.
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            app, bootstrap = _project(root, "app.withRouting(ai=load_ai_routes())\n")
            app.routing["ai"] = [
                root / "dynamic" / "tools.py", root / "dynamic" / "resources.py",
            ]
            source = bootstrap.read_bytes()
            Bootstrapper(app).routing("ai")
            self.assertEqual(bootstrap.read_bytes(), source)
            for route in app.routing["ai"]:
                self.assertTrue(route.is_file())
                ast.parse(route.read_text(encoding="utf-8"))
            self.assertFalse((root / "routes").exists())

    def testReactorExecutesBootstrapAndListsAllSevenCommands(self) -> None:
        """
        Run the unmodified Reactor entry point against an actual slim project.

        Returns
        -------
        None
            Complete the assertions without returning a value.
        """
        # Run Reactor in a separate process with the temporary project root.
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            _, bootstrap = _project(root)
            reactor = root / "reactor"
            reactor.write_bytes((_ROOT / "reactor").read_bytes())
            environment = {
                **os.environ,
                "PYTHONPATH": str(_ROOT),
                "PYTHONDONTWRITEBYTECODE": "1",
                "PYTHONUTF8": "1",
                "NO_COLOR": "1",
            }
            for command in ("bootstrap:console", "bootstrap:console", "list"):
                result = subprocess.run(  # noqa: S603
                    [sys.executable, "-B", str(reactor), command],
                    cwd=root, env=environment, capture_output=True, text=True,
                    encoding="utf-8", timeout=45, check=False,
                )
                self.assertEqual(
                    result.returncode, 0,
                    f"{command}: {result.stdout}\n{result.stderr}",
                )
                if command == "list":
                    for context in (*_COMMANDS, "config", "lifespan"):
                        self.assertIn(f"bootstrap:{context}", result.stdout)
            self.assertTrue((root / "routes" / "console.py").is_file())
            self.assertEqual(len(_routing_calls(
                bootstrap.read_text(encoding="utf-8"),
            )), 1)
