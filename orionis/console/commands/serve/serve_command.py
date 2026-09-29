import asyncio
import os
import sys
from anyio import Path as AnyPath
from granian.constants import Interfaces, Loops
from granian.log import LogLevels
from pathlib import Path
from threading import RLock
from typing import ClassVar, Self, TYPE_CHECKING
from orionis.console.args.argument import Argument
from orionis.console.base.command import BaseCommand
from orionis.foundation.contracts.application import IApplication
from orionis.foundation.enums.runtimes import Runtime
from orionis.metadata.framework import PYTHON_REQUIRES, VERSION
from orionis.support.types.sentinel import MISSING

if TYPE_CHECKING:
    from collections.abc import Callable

# Characters additionally allowed in the sanitized process name, besides alphanumeric
_EXTRA_ALLOWED: frozenset[str] = frozenset({"_", "-"})

# Number of logical CPUs available; resolved once at import time
_CPU_COUNT: int = os.cpu_count() or 1

class ServerCommand(BaseCommand):

    # ruff: noqa: S606, S104, TC001, PLC0415, SLF001

    _instance = None
    _instance_lock = RLock()
    timestamps = False

    # Command signature and description
    signature = "serve"
    description = (
        "Initializes the Orionis server with Granian "
        "(The Rust HTTP server for Python)."
    )
    arguments: ClassVar[list[Argument]] = [
        Argument(
            name_or_flags=["--interface", "-i"],
            type_=str,
            help="Interface type to use (ASGI or RSGI).",
            choices=["rsgi", "asgi"],
            dest="interface",
            default=MISSING,
            required=False,
        ),
        Argument(
            name_or_flags=["--port", "-p"],
            type_=int,
            help="Port number to bind the server to.",
            dest="port",
            default=MISSING,
            required=False,
        ),
        Argument(
            name_or_flags=["--log"],
            help="Enable logging in production mode.",
            action="store_true",
            dest="log_enabled",
            default=False,
            required=False,
        ),
        Argument(
            name_or_flags=["--export"],
            help="Export the resolved Granian command in console.",
            action="store_true",
            dest="export",
            default=False,
            required=False,
        ),
    ]

    def __new__(cls) -> Self:
        """Create or return the singleton instance of ``ServerCommand``.

        Returns
        -------
        Self
            The single shared instance of this class.
        """
        with cls._instance_lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        """Initialize instance state on first construction.

        Returns
        -------
        None
            This method does not return a value.
        """
        if not hasattr(self, "_initialized"):
            self.__lock = RLock()
            self.__env = self.__initNewEnvironment()
            self.__cmd: list[str] = [sys.executable.replace("\\", "/")]
            self.__app_reload: bool = False
            self.__call_in_shutdown: Callable | None = None
            self._initialized = True

    # -------------------------------------------------------------------------
    # Environment
    # -------------------------------------------------------------------------

    def __initNewEnvironment(self) -> dict[str, str]:
        """Build a fresh environment dictionary with Orionis metadata.

        Returns
        -------
        dict[str, str]
            A copy of ``os.environ`` extended with framework-specific keys.
        """
        env = os.environ.copy()
        env["PYTHONUTF8"] = "1"
        env["PYTHONIOENCODING"] = "utf-8"
        env["ORIONIS_FRAMEWORK_VERSION"] = VERSION
        env["ORIONIS_PYTHON_VERSION_REQUIRED"] = (
            f"{PYTHON_REQUIRES[0]}.{PYTHON_REQUIRES[1]}"
        )
        return env

    # -------------------------------------------------------------------------
    # Command builder
    # -------------------------------------------------------------------------

    def __configureBytecodeWriting(self, app: IApplication) -> None:
        """Configure bytecode-writing flags based on the current environment.

        Parameters
        ----------
        app : IApplication
            The running application instance.

        Returns
        -------
        None
            This method does not return a value.
        """
        is_production: bool = app.isProduction()
        # Disable bytecode in development; allow it in production.
        self.__env["PYTHONDONTWRITEBYTECODE"] = "0" if is_production else "1"
        if not is_production:
            self.__cmd.append("-B")

    def __appendHostAndPortToCommand(self, app: IApplication) -> None:
        """Resolve and append host and port arguments to the command.

        Parameters
        ----------
        app : IApplication
            The running application instance.

        Returns
        -------
        None
            This method does not return a value.
        """
        is_production: bool = app.isProduction()
        # Default host differs between production and development.
        host: str = "0.0.0.0" if is_production else "127.0.0.1"
        cmd_port: int | None = self.getArgument("port")
        port: int = int(cmd_port) if cmd_port is not None else 8000
        self.__cmd.extend(
            ["-m", "granian", "--host", str(host), "--port", str(port)],
        )
        self.__env["GRANIAN_HOST"] = str(host)
        self.__env["GRANIAN_PORT"] = str(port)

    def __appendInterfaceToCommand(self) -> None:
        """Append the selected interface type to the command.

        Returns
        -------
        None
            This method does not return a value.
        """
        interface: str = (
            self.getArgument("interface") or Interfaces.RSGI.value
        )
        self.__cmd.extend(["--interface", interface])
        self.__env["GRANIAN_INTERFACE"] = interface

    def __appendWorkersToCommand(self) -> None:
        """Append the worker-process count to the command.

        Parameters
        ----------
        app : IApplication
            The running application instance.

        Returns
        -------
        None
            This method does not return a value.
        """
        workers: int = 1 if os.name == "nt" else max(1, _CPU_COUNT)
        self.__cmd.extend(["--workers", str(workers)])
        self.__env["GRANIAN_WORKERS"] = str(workers)

    def __appendLoopToCommand(self) -> None:
        """Append the event-loop backend to the command.

        Returns
        -------
        None
            This method does not return a value.
        """
        # Use uvloop on Unix for performance; fall back to auto on Windows.
        event_loop: str = (
            Loops.uvloop.value if os.name != "nt" else Loops.auto.value
        )
        self.__cmd.extend(["--loop", event_loop])
        self.__env["GRANIAN_LOOP"] = event_loop

    def __appendLoggingConfigurationToCommand(
        self, app: IApplication,
    ) -> None:
        """Append the logging-level flags to the command.

        Parameters
        ----------
        app : IApplication
            The running application instance.

        Returns
        -------
        None
            This method does not return a value.
        """
        if self.getArgument("log_enabled"):
            # Explicit --log flag: always log at info level.
            self.__cmd.extend(["--log-level", "info"])
            self.__env.update(
                {"GRANIAN_LOG_ENABLED": "1", "GRANIAN_LOG_LEVEL": "info"},
            )
            return
        if app.isProduction():
            # Production: log errors only to reduce noise.
            self.__cmd.extend(["--log-level", "error"])
            self.__env.update(
                {"GRANIAN_LOG_ENABLED": "1", "GRANIAN_LOG_LEVEL": "error"},
            )
        else:
            # Development: suppress all Granian output.
            self.__cmd.append("--no-log")
            self.__env["GRANIAN_LOG_ENABLED"] = "0"

    def __appendReloadOptionsToCommand(self, app: IApplication) -> None:
        """Append hot-reload flags and watched directories to the command.

        Parameters
        ----------
        app : IApplication
            The running application instance.

        Returns
        -------
        None
            This method does not return a value.
        """
        self.__app_reload = True
        # Prefer compiled invalidation paths when available.
        watch_dirs: list[Path] = (
            app.compiledInvalidationPathsDirs
            if app.compiled
            else [app.basePath]
        )
        if self.__app_reload and watch_dirs and not app.isProduction():
            # Exclude paths that contain spaces (Granian CLI limitation).
            target: list[str] = [
                p.resolve().as_posix()
                for p in watch_dirs
                if " " not in str(p) and p.is_dir()
            ]
            self.__cmd.append("--reload")
            self.__env["GRANIAN_RELOAD"] = "1"
            self.__env["GRANIAN_RELOAD_PATHS"] = ",".join(target)
            for path in target:
                self.__cmd.extend(["--reload-paths", path])
        else:
            self.__app_reload = False
            self.__env["GRANIAN_RELOAD"] = "0"

    def __appendStaticMountAndRouteToCommand(
        self, app: IApplication,
    ) -> None:
        """Append the static-file mount path and URL route to the command.

        Parameters
        ----------
        app : IApplication
            The running application instance.

        Returns
        -------
        None
            This method does not return a value.
        """
        public_disk: dict = (
            app.config("filesystems").get("disks", {}).get("public", {})
        )
        mount = Path(public_disk.get("path", "storage/app/public"))

        # Resolve relative paths against the application root.
        if not mount.is_absolute():
            mount = Path(app.basePath) / mount
        mount = mount.resolve()

        # Normalize the URL route by stripping trailing slashes and spaces,
        # and collapsing multiple slashes. Granian CLI
        # does not allow spaces in routes.
        route: str = public_disk.get("url", "/static")\
                                .strip()\
                                .rstrip("/")\
                                .replace(" ", "")\
                                .replace("//", "/")

        # Ensure the route starts with a slash for Granian CLI compatibility.
        if route and not route.startswith("/"):
            route = "/" + route

        self.__cmd.extend([
            "--static-path-mount", mount.as_posix(),
            "--static-path-route", route,
            "--static-path-dir-to-file", "index.html",
        ])
        self.__env["GRANIAN_STATIC_PATH_MOUNT"] = mount.as_posix()
        self.__env["GRANIAN_STATIC_PATH_ROUTE"] = route
        self.__env["GRANIAN_STATIC_PATH_DIR_TO_FILE"] = "index.html"

    def __appendProcessNameToCommand(self, name: str) -> None:
        """Append the process name to the command.

        Parameters
        ----------
        name : str
            Identifier shown in the OS process list.

        Returns
        -------
        None
            This method does not return a value.
        """
        self.__cmd.extend(["--process-name", name])
        self.__env["GRANIAN_PROCESS_NAME"] = name

    # -------------------------------------------------------------------------
    # Server strategies
    # -------------------------------------------------------------------------

    def __unixServe(self) -> None:
        """Replace the current process with the Granian server via execvpe.

        Returns
        -------
        None
            This method never returns; the process is replaced by execvpe.
        """
        sys.stdout.flush()
        sys.stderr.flush()
        os.execvpe(self.__cmd[0], self.__cmd, self.__env)

    @staticmethod
    def __isDebugMode() -> bool:
        """Detect whether a Python debugger is currently attached.

        Returns
        -------
        bool
            ``True`` if a debugger is attached, ``False`` otherwise.

        Notes
        -----
        Covers legacy trace-based debuggers (``sys.gettrace``) and
        debugpy >= 1.8 on Python >= 3.12, which uses ``sys.monitoring``
        and no longer sets a global trace function but always imports
        ``pydevd`` during its bootstrap.
        """
        if hasattr(sys, "gettrace") and sys.gettrace() is not None:
            return True
        return "pydevd" in sys.modules or "debugpy" in sys.modules

    async def __embeddedServe(self, app: IApplication) -> None:
        """Start the server in-process using Granian's embedded backend.

        Parameters
        ----------
        app : IApplication
            The running application instance.

        Returns
        -------
        None
            This method does not return a value.

        Notes
        -----
        Used on Windows when a debugger is attached. Workers run as
        asyncio tasks so debugpy breakpoints work without subprocess
        interception issues.

        Lifecycle is managed explicitly because
        ``Application.__rsgi_init__`` calls ``loop.run_until_complete()``,
        which raises ``RuntimeError`` when the loop is already running,
        and ``asyncio.ensure_future(loop=)`` was removed in Python 3.12+.
        """
        from granian.server.embed import Server as EmbedServer

        class _RSGIProxy:
            """Delegate RSGI calls and suppress framework lifecycle hooks."""

            def __init__(self, inner: IApplication) -> None:
                """Store a reference to the wrapped application.

                Parameters
                ----------
                inner : IApplication
                    The real application to delegate RSGI calls to.

                Returns
                -------
                None
                    This method does not return a value.
                """
                self._inner = inner

            async def __rsgi__(
                self, scope: object, protocol: object,
            ) -> object:
                """Forward the RSGI request to the real application.

                Parameters
                ----------
                scope : object
                    The RSGI connection scope.
                protocol : object
                    The RSGI protocol object.

                Returns
                -------
                object
                    The value returned by the inner application.
                """
                return await self._inner.__rsgi__(scope, protocol)

            def __rsgi_init__(
                self, loop: asyncio.AbstractEventLoop,
            ) -> None:
                """Accept the event-loop reference without side effects.

                Parameters
                ----------
                loop : asyncio.AbstractEventLoop
                    The running event loop (unused).

                Returns
                -------
                None
                    Startup is awaited explicitly before ``server.serve()``.
                """

            def __rsgi_del__(
                self, loop: asyncio.AbstractEventLoop,
            ) -> None:
                """Accept the event-loop reference without side effects.

                Parameters
                ----------
                loop : asyncio.AbstractEventLoop
                    The running event loop (unused).

                Returns
                -------
                None
                    Shutdown is awaited explicitly after ``server.serve()``.
                """

        host: str = app.config("app.host") or "127.0.0.1"
        cmd_port: int | None = self.getArgument("port")
        port: int = (
            int(cmd_port) if cmd_port is not None
            else (app.config("app.port") or 8000)
        )
        cmd_interface: str | None = self.getArgument("interface")
        interface: Interfaces = (
            Interfaces(cmd_interface) if cmd_interface else Interfaces.RSGI
        )

        # Resolve logging settings for the embedded server.
        if self.getArgument("log_enabled"):
            log_enabled, log_level = True, LogLevels.info
        elif app.isProduction():
            log_enabled, log_level = True, LogLevels.error
        else:
            log_enabled, log_level = False, LogLevels.warning

        # Resolve static-file configuration.
        public_disk: dict = (
            app.config("filesystems").get("disks", {}).get("public", {})
        )
        mount = Path(public_disk.get("path", "storage/app/public"))
        if not mount.is_absolute():
            mount = Path(app.basePath) / mount
        route: str = public_disk.get("url", "/static").lstrip("/")

        server = EmbedServer(
            target=_RSGIProxy(app),
            address=host,
            port=port,
            interface=interface,
            log_enabled=log_enabled,
            log_level=log_level,
            static_path_mount=[mount.resolve()],
            static_path_route=[route],
        )

        # Run startup before the embed server spawns its worker task.
        await app._Application__onStartup(runtime=Runtime.HTTP)
        try:
            await server.serve()
        except asyncio.CancelledError:
            await app._Application__onShutdown(runtime=Runtime.HTTP)
            raise
        await app._Application__onShutdown(runtime=Runtime.HTTP)

    async def __windowsServe(self) -> None:
        """Launch Granian as a managed subprocess on Windows.

        Returns
        -------
        None
            This method does not return a value.

        Notes
        -----
        Merges ``self.__env`` into ``os.environ`` so the subprocess
        inherits the active virtual environment without an explicit
        ``env=`` argument, which would break site-packages resolution.

        Uses ``asyncio.create_subprocess_exec`` so that ``await proc.wait()``
        is directly cancellable by the event loop.  On ``CancelledError``
        (Ctrl+C), ``taskkill /F /T`` terminates the entire process tree
        (main Granian process **and** all worker children) before the
        shutdown handler is called.
        """
        # Propagate configured vars into the live environment so the
        # child process picks them up via inheritance.
        os.environ.update(self.__env)

        proc = await asyncio.create_subprocess_exec(*self.__cmd)

        try:
            await proc.wait()
        except asyncio.CancelledError:
            # Ctrl+C: kill the whole process tree so Granian workers are
            # also terminated, invoke the shutdown handler, then re-raise.
            if proc.returncode is None:
                try:
                    _tk = await asyncio.create_subprocess_exec(
                        "C:\\Windows\\System32\\taskkill.exe",
                        "/F", "/T", "/PID", str(proc.pid),
                        stdout=asyncio.subprocess.DEVNULL,
                        stderr=asyncio.subprocess.DEVNULL,
                    )
                    await asyncio.wait_for(_tk.wait(), timeout=5)
                except OSError:
                    proc.kill()
            if self.__call_in_shutdown:
                await self.__call_in_shutdown(runtime=Runtime.HTTP)
            raise

        # Normal exit: run the shutdown handler.
        if self.__call_in_shutdown:
            await self.__call_in_shutdown(runtime=Runtime.HTTP)

    def __setShutdownHandler(self, app: IApplication) -> None:
        """Assign the application shutdown coroutine for later invocation.

        Parameters
        ----------
        app : IApplication
            The running application instance.

        Returns
        -------
        None
            This method does not return a value.
        """
        # Retrieve and store the application shutdown coroutine if available
        self.__call_in_shutdown = getattr(app, "_Application__onShutdown", None)

    # -------------------------------------------------------------------------
    # Entry point
    # -------------------------------------------------------------------------

    async def handle(self, app: IApplication) -> None:
        """Build the Granian command and start the HTTP server.

        Parameters
        ----------
        app : IApplication
            The running application instance.

        Returns
        -------
        None
            This method does not return a value.

        Notes
        -----
        Dispatches to the appropriate server strategy:

        - **Unix**: replaces the process via ``execvpe``.
        - **Windows + debugger**: uses the Granian embedded server
          (in-process asyncio tasks) for full breakpoint support.
        - **Windows**: launches Granian as a managed subprocess.
        """
        with self.__lock:

            self.__configureBytecodeWriting(app)
            self.__appendHostAndPortToCommand(app)
            self.__appendInterfaceToCommand()
            self.__appendWorkersToCommand()
            self.__appendLoopToCommand()
            self.__appendLoggingConfigurationToCommand(app)
            self.__appendReloadOptionsToCommand(app)
            self.__appendStaticMountAndRouteToCommand(app)
            self.__setShutdownHandler(app)

            app_name = str(app.config("app.name") or "orionis-app")
            process_name = "".join([
                char for char in app_name.replace(" ", "-").lower()
                if char.isalnum() or char in _EXTRA_ALLOWED
            ])
            process_name = process_name[:64].lstrip("_-")
            if not process_name:
                process_name = "orionis-app"

            self.__appendProcessNameToCommand(process_name)

            root_path: str = (await AnyPath(app.basePath).resolve()).as_posix()
            self.__env["ORIONIS_BUILD_TIMESTAMP_NS"] = str(app.startAt)
            self.__env["ORIONIS_APP_ROOT_PATH"] = root_path
            self.__env["PWD"] = root_path
            self.__cmd.append(app.entryPoint)

            # If --export is specified
            # Print the resolved command and exit instead of launching.
            if self.getArgument("export"):
                self.newLine()
                self.textInfoBold("🦀 Resolved Granian Command:")
                self.textInfo("Copy and paste this command to run the server manually.")
                self.newLine()
                self.textMuted(" ".join(self.__cmd))
                self.newLine()
                self.exitSuccess()

            # Dispatch to the strategy that matches the current environment.
            if os.name != "nt":
                self.__unixServe()
            elif self.__isDebugMode():
                await self.__embeddedServe(app)
            else:
                await self.__windowsServe()
