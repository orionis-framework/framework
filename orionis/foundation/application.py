from __future__ import annotations
import asyncio
import inspect
import locale
import os
from collections import OrderedDict, deque
from contextlib import suppress
from copy import deepcopy
from dataclasses import asdict
from importlib import import_module
from pathlib import Path
import sys
import time
from typing import TYPE_CHECKING, Any, Self
from orionis.console.base.contracts.scheduler import IBaseScheduler
from orionis.container.container import Container
from orionis.container.contracts.service_provider import IServiceProvider
from orionis.container.providers.deferrable_provider import DeferrableProvider
from orionis.container.providers.service_provider import ServiceProvider
from orionis.failure.contracts.handler import IBaseExceptionHandler
from orionis.foundation.contracts.application import IApplication
from orionis.foundation.core_config import get_core_config_mapping
from orionis.foundation.core_exception_handler import CORE_EXCEPTION_HANDLER
from orionis.foundation.core_kernels import CORE_KERNELS
from orionis.foundation.core_paths import CORE_APP_PATHS
from orionis.foundation.core_providers import get_core_providers_mapping
from orionis.foundation.core_scheduler import CORE_SCHEDULER
from orionis.foundation.enums.lifespan import Lifespan
from orionis.foundation.enums.runtimes import Runtime
from orionis.http.contracts.kernel import IKernelHTTP
from orionis.http.layer.contracts.middleware import IBaseMiddleware
from orionis.metadata.framework import PYTHON_REQUIRES
from orionis.cache import FileBasedCache
from orionis.introspection.modules.inspector import ModuleInspector
from orionis.support.structures.freezer import FreezeThaw
from orionis.support.facades.datetime import DateTime
from orionis.console.contracts.kernel import IKernelCLI

if TYPE_CHECKING:
    from collections.abc import Awaitable
    from collections.abc import Callable
    from collections.abc import Coroutine
    from collections.abc import Mapping
    from granian.rsgi import (
        Scope,
        HTTPProtocol,
        WebsocketProtocol,
        ProtocolError,
        ProtocolClosed,
    )
    from orionis.cache.contracts.file_based_cache import IFileBasedCache
    from orionis.container.contracts.deferrable_provider import IDeferrableProvider

_SENTINEL = object()
_ASGI_BODY_QUEUE_SIZE = 8
_CWD = Path.cwd()
_CONFIG_KEY_CACHE_SIZE = 256
_ERR_NOT_CONFIGURED: str = (
    "Application configuration is not initialized. Please call create() first."
)

def _create_http_handler_task(
    loop: asyncio.AbstractEventLoop,
    coroutine: Coroutine,
) -> asyncio.Task:
    """Start a monitored handler through the event loop's task factory.

    Parameters
    ----------
    loop : asyncio.AbstractEventLoop
        Running request event loop.
    coroutine : Coroutine
        Kernel handler coroutine to schedule.

    Returns
    -------
    asyncio.Task
        Handler task. The native loop without a custom factory starts it eagerly;
        other loops and factories receive their standard task-creation arguments.
    """
    if (
        type(loop).create_task is asyncio.BaseEventLoop.create_task
        and loop.get_task_factory() is None
    ):
        return loop.create_task(coroutine, eager_start=True)
    return loop.create_task(coroutine)

async def _asgi_receive_dispatcher(
    receive: Callable[[], Awaitable[dict[str, Any]]],
    request_queue: asyncio.Queue,
    handler_task: asyncio.Task,
) -> bool:
    """
    Consume ASGI receive messages and dispatch them concurrently.

    Forward body chunks through a bounded queue and cancel the handler when
    the receive channel reports a disconnect or fails. A full queue pauses
    receive calls until the handler consumes a buffered message.

    Parameters
    ----------
    receive : Callable[[], Awaitable[dict[str, Any]]]
        ASGI receive callable provided by the server.
    request_queue : asyncio.Queue
        Queue that buffers body messages for the handler.
    handler_task : asyncio.Task
        Kernel task to cancel when the receive channel closes.

    Returns
    -------
    bool
        Whether the disconnect requested cancellation of the handler.
    """
    if handler_task.done():
        return False
    try:
        while True:
            message = await receive()
            await request_queue.put(message)
            if message.get("type") == "http.disconnect":
                return handler_task.cancel("client_disconnect")
    except BaseException:
        # Stop the handler when the server receive channel fails.
        handler_task.cancel()
        raise

async def _rsgi_disconnect_watcher(
    protocol: HTTPProtocol,
    handler_task: asyncio.Task,
) -> bool:
    """
    Cancel the kernel task when the RSGI disconnect awaitable completes.

    Parameters
    ----------
    protocol : HTTPProtocol
        Protocol providing the client disconnect awaitable.
    handler_task : asyncio.Task
        Kernel task associated with the connection.

    Returns
    -------
    bool
        Whether the disconnect requested cancellation of the handler.
    """
    if handler_task.done():
        return False
    try:
        await protocol.client_disconnect()
    except BaseException:
        # Stop the handler when the disconnect channel fails.
        handler_task.cancel()
        raise
    return handler_task.cancel("client_disconnect")

async def _await_http_tasks(
    handler_task: asyncio.Task,
    disconnect_task: asyncio.Task[bool],
) -> Any:
    """
    Await the kernel and finish its disconnect monitor before returning.

    Parameters
    ----------
    handler_task : asyncio.Task
        Kernel task handling the request.
    disconnect_task : asyncio.Task[bool]
        Monitor returning whether it cancelled the kernel on disconnect.

    Returns
    -------
    Any
        Kernel result, or None after a client disconnect.

    Raises
    ------
    asyncio.CancelledError
        If the caller or kernel is cancelled independently of a disconnect.
    Exception
        If the kernel or disconnect monitor fails.
    """
    parent_task = asyncio.current_task()
    try:
        return await handler_task
    except asyncio.CancelledError: # NOSONAR
        if parent_task.cancelling() or not disconnect_task.done():
            raise
        if not disconnect_task.result():
            raise
        return None
    finally:
        if not disconnect_task.done():
            disconnect_task.cancel()
        try:
            await disconnect_task
        except asyncio.CancelledError:
            # Preserve cancellation of the request during monitor cleanup.
            if parent_task.cancelling():
                raise

class Application(Container, IApplication):
    """
    Configure the container and serve requests within one worker event loop.

    Notes
    -----
    Concurrent tasks share kernel initialization and provider startup locks.
    Mutable application state is not synchronized across threads or event loops.
    Python and RSGI special methods retain their protocol-defined names.
    """

    # ruff: noqa: SLF001, ANN401

    # --- ASGI Application Handling ---

    async def __call__(
        self,
        scope: dict,
        receive: Callable[[], Awaitable[dict[str, Any]]],
        send: Callable[[dict[str, Any]], Awaitable[None]],
    ) -> Any | None:
        """
        Dispatch ASGI requests to the appropriate handler by scope type.

        Parameters
        ----------
        scope : dict
            ASGI connection scope containing request metadata and type.
        receive : Callable[[], Awaitable[dict[str, Any]]]
            ASGI receive callable for message retrieval.
        send : Callable[[dict[str, Any]], Awaitable[None]]
            ASGI send callable for response transmission.

        Returns
        -------
        Any | None
            Result from the lifespan or HTTP handler, or ``None`` for
            unsupported scope types.
        """
        scope_type: str = scope["type"]

        # Route lifespan events to the dedicated handler
        if scope_type == "lifespan":
            return await self.__asgiLifespan(receive, send)

        # Route HTTP requests to the kernel handler.
        if scope_type == "http":
            return await self.__handleHttpAsgi(scope, receive, send)

        # Ignore unsupported scopes per ASGI specification
        return None

    async def __asgiLifespan(
        self,
        receive: Callable[[], Awaitable[dict]],
        send: Callable[[dict], Awaitable[None]],
    ) -> None:
        """
        Handle ASGI lifespan startup and shutdown events.

        Parameters
        ----------
        receive : Callable[[], Awaitable[dict]]
            ASGI receive callable for lifespan message retrieval.
        send : Callable[[dict], Awaitable[None]]
            ASGI send callable for lifespan response transmission.

        Returns
        -------
        None
            Returns after shutdown completes or a fatal error occurs.
        """
        # Map each lifespan event to its corresponding lifecycle method
        handler_map: dict[Lifespan, Callable[..., Any]] = {
            Lifespan.STARTUP: self.__onStartup,
            Lifespan.SHUTDOWN: self.__onShutdown,
        }

        # Guard against duplicate startup execution
        started: bool = False

        while True:
            message: dict = await receive()
            message_type: str | None = message.get("type")

            # Exit on client lifespan disconnect
            if message_type == "lifespan.disconnect":
                return

            # Validate and convert message type to Lifespan enum
            try:
                event: Lifespan = Lifespan(message_type)
            except ValueError:
                continue

            # Skip unrecognised events
            handler: Callable | None = handler_map.get(event)
            if handler is None:
                continue

            try:
                # Prevent duplicate startup if the server fires it twice
                if event is Lifespan.STARTUP and not started:
                    started = True
                elif event is Lifespan.STARTUP:
                    await send({"type": "lifespan.startup.complete"})
                    continue

                # Execute the corresponding lifecycle callback
                await handler(runtime=Runtime.HTTP)

                # Acknowledge the event to the server
                await send({"type": f"{message_type}.complete"})

                # Exit after shutdown is confirmed
                if event is Lifespan.SHUTDOWN:
                    return

            except Exception as exc:  # noqa: BLE001
                error_msg: str = str(exc)
                await send(
                    {
                        "type": f"{message_type}.failed",
                        "message": error_msg,
                    },
                )
                return

    async def __handleHttpAsgi(
        self,
        scope: dict,
        receive: Callable[[], Awaitable[dict[str, Any]]],
        send: Callable[[dict[str, Any]], Awaitable[None]],
    ) -> Any | None:
        """
        Handle an HTTP request using the configured disconnect policy.

        Direct dispatch uses the server task and receive callable. When
        ``http.monitor_disconnects`` is enabled, a receive dispatcher cancels
        the kernel on disconnect and buffers incoming body messages.
        At most nine body messages are retained outside the kernel: eight
        in the queue and one waiting to enter it. Disconnect detection
        pauses while the queue is full.

        Parameters
        ----------
        scope : dict
            ASGI connection scope containing request metadata.
        receive : Callable[[], Awaitable[dict[str, Any]]]
            ASGI receive callable provided by the server.
        send : Callable[[dict[str, Any]], Awaitable[None]]
            ASGI send callable for transmitting the response.

        Returns
        -------
        Any | None
            Result of the kernel handler, or ``None`` if the client
            disconnected before the response was sent.
        """
        handler = self.__kernel_http_asgi
        if handler is None:
            await self.__initializeHttpKernel("asgi")
            handler = self.__kernel_http_asgi

        if not self.__http_disconnect_monitoring:
            return await handler(scope, receive, send)

        loop = asyncio.get_running_loop()
        request_queue: asyncio.Queue = asyncio.Queue(maxsize=_ASGI_BODY_QUEUE_SIZE)
        handler_task = _create_http_handler_task(
            loop, handler(scope, request_queue.get, send),
        )
        if handler_task.done():
            return handler_task.result()
        dispatcher_task = loop.create_task(
            _asgi_receive_dispatcher(receive, request_queue, handler_task),
        )
        return await _await_http_tasks(handler_task, dispatcher_task)

    # --- RSGI Application Handling ---

    async def __rsgi__(
        self,
        scope: Scope,
        protocol: HTTPProtocol | WebsocketProtocol | ProtocolError | ProtocolClosed,
    ) -> object:
        """
        Handle the RSGI protocol for incoming requests.

        Parameters
        ----------
        scope : Scope
            The connection scope information.
        protocol : HTTPProtocol | WebsocketProtocol | ProtocolError | ProtocolClosed
            The RSGI protocol instance representing the connection.

        Returns
        -------
        object
            The result of handling the RSGI request.
        """
        # Delegate to the appropriate kernel handler based on protocol type.
        if scope.proto == "http":
            return await self.__handleHttpRsgi(scope, protocol)

        # Unsupported protocol; return None per RSGI specification.
        return None

    def __rsgi_init__(
        self,
        loop: asyncio.AbstractEventLoop,
    ) -> None:
        """
        Initialize the RSGI application lifecycle and execute startup callbacks.

        Parameters
        ----------
        loop : asyncio.AbstractEventLoop
            The event loop for asynchronous execution.

        Returns
        -------
        None
            This method executes startup callbacks and does not return a value.
        """
        # Trigger application startup lifecycle and run all startup callbacks.
        loop.run_until_complete(
            self.__onStartup(runtime=Runtime.HTTP, http_interface="rsgi"),
        )

    def __rsgi_del__(
        self,
        loop: asyncio.AbstractEventLoop,
    ) -> None:
        """
        Execute the RSGI application shutdown lifecycle.

        Parameters
        ----------
        loop : asyncio.AbstractEventLoop
            The event loop for asynchronous execution.

        Returns
        -------
        None
            This method executes shutdown callbacks and does not return a value.
        """
        # Trigger application shutdown lifecycle and run all shutdown callbacks.
        loop.run_until_complete(
            self.__onShutdown(runtime=Runtime.HTTP),
        )

    async def __handleHttpRsgi(
        self,
        scope: Scope,
        protocol: HTTPProtocol,
    ) -> object:
        """
        Handle HTTP requests using the KernelHTTP in RSGI mode.

        Direct dispatch executes in the server task. When
        ``http.monitor_disconnects`` is enabled, a watcher requests cancellation
        when the client disconnects. The watcher is joined before returning.

        Parameters
        ----------
        scope : Scope
            The connection scope information for the RSGI protocol.
        protocol : HTTPProtocol
            The RSGI protocol instance; must expose a ``client_disconnect``
            coroutine that resolves when the client closes the connection.

        Returns
        -------
        object
            The result returned by the HTTP kernel's handleRSGI method, or
            ``None`` when execution is cancelled due to client disconnect.

        Raises
        ------
        RuntimeError
            If KernelHTTP is not configured in the application.
        TypeError
            If the HTTP kernel does not have a handleRSGI method.
        """
        handler = self.__kernel_http_rsgi
        if handler is None:
            await self.__initializeHttpKernel("rsgi")
            handler = self.__kernel_http_rsgi

        if not self.__http_disconnect_monitoring:
            return await handler(scope, protocol)

        loop = asyncio.get_running_loop()
        handler_task = _create_http_handler_task(loop, handler(scope, protocol))
        if handler_task.done():
            return handler_task.result()
        disconnect_task = loop.create_task(
            _rsgi_disconnect_watcher(protocol, handler_task),
        )
        return await _await_http_tasks(handler_task, disconnect_task)

    # --- Kernel Handling Methods ---

    async def __initializeHttpKernel(self, interface: str) -> None:
        """
        Build and boot the HTTP kernel once for concurrent first requests.

        Parameters
        ----------
        interface : str
            Server interface recorded before the kernel is built.

        Returns
        -------
        None
            Both protocol handlers are published after a successful boot.
        """
        async with self.__kernel_http_lock:
            if self.__kernel_http_asgi is not None:
                return
            self.config("app.interface", interface)
            kernel = await self.__loadHTTPKernel()
            asgi_handler = kernel.handleASGI
            rsgi_handler = kernel.handleRSGI
            self.__kernel_http_asgi = asgi_handler
            self.__kernel_http_rsgi = rsgi_handler

    async def __loadHTTPKernel(
        self,
    ) -> IKernelHTTP:
        """
        Load and return the configured HTTP kernel instance.

        Returns
        -------
        IKernelHTTP
            An instance of the configured HTTP kernel.

        Raises
        ------
        TypeError
            If the loaded kernel does not implement IKernelHTTP.
        """
        # Retrieve HTTP kernel configuration from bootstrap
        kernel_metadata = self.__bootstrap["kernels"]["KernelHTTP"]

        # Load the configured HTTP kernel class.
        kernel_cls = ModuleInspector.loadClass(metadata=kernel_metadata)
        kernel_instance = await self.build(kernel_cls)

        # Validate that the loaded kernel implements the IKernelHTTP interface
        if not isinstance(kernel_instance, IKernelHTTP):
            error_msg = (
                f"Loaded HTTP kernel does not implement IKernelHTTP: {kernel_cls}"
            )
            raise TypeError(error_msg)

        # Boot the HTTP kernel before publishing its handlers.
        await kernel_instance.boot()

        # Return the loaded HTTP kernel instance
        return kernel_instance

    async def __loadCLIKernel(
        self,
    ) -> IKernelCLI:
        """
        Load and return the configured CLI kernel instance.

        Returns
        -------
        IKernelCLI
            An instance of the configured CLI kernel.

        Raises
        ------
        RuntimeError
            If KernelCLI is not configured in the application.
        TypeError
            If the loaded kernel does not implement IKernelCLI.
        """
        # Try to retrieve CLI kernel configuration from bootstrap
        try:
            kernel_metadata = self.__bootstrap["kernels"]["KernelCLI"]
        except KeyError:
            error_msg = "CLI Kernel is not configured in the application."
            raise RuntimeError(error_msg) from None

        # Load the configured CLI kernel class.
        kernel_cls = ModuleInspector.loadClass(metadata=kernel_metadata)
        kernel_instance = await self.build(kernel_cls)

        # Validate that the loaded kernel implements the IKernelCLI interface
        if not isinstance(kernel_instance, IKernelCLI):
            error_msg = f"Loaded CLI kernel does not implement IKernelCLI: {kernel_cls}"
            raise TypeError(error_msg)

        # Return the loaded CLI kernel instance
        return kernel_instance

    # --- CLI Application Handling ---

    async def handleCommand(
        self,
        args: list[str] | None = None,
    ) -> int:
        """
        Handle a CLI command using the configured KernelCLI.

        Parameters
        ----------
        args : list[str] | None, optional
            Arguments to pass to the kernel's handle method. Defaults to an
            empty list if not provided.

        Returns
        -------
        int
            The exit code returned by the CLI kernel's handle method.

        Raises
        ------
        RuntimeError
            If KernelCLI is not configured in the application.
        TypeError
            If the CLI kernel does not have a handle method.
        """
        # Initialize the CLI kernel before starting command lifecycle hooks.
        if self.__kernel_cli is None:
            await self.__initializeCliKernel()

        # Trigger startup lifecycle event before each command execution
        await self.__onStartup(runtime=Runtime.CLI)

        try:
            # Execute the kernel's handle method with provided arguments
            response = await self.__kernel_cli(args or [])
        finally:
            # Always trigger shutdown after each command, paired with the startup above
            await self.__onShutdown(runtime=Runtime.CLI)

        # Return the response code from the CLI kernel
        return response

    async def __initializeCliKernel(self) -> None:
        """
        Build and boot the CLI kernel once for concurrent commands.

        Returns
        -------
        None
            The command handler is published after the kernel boots.
        """
        async with self.__kernel_cli_lock:
            if self.__kernel_cli is not None:
                return
            kernel = await self.__loadCLIKernel()
            boot_result = kernel.boot(self)
            if inspect.isawaitable(boot_result):
                await boot_result
            self.__kernel_cli = kernel.handle

    # --- Application Properties ---

    @property
    def isBooted(self) -> bool:
        """
        Check whether configuration and provider registration have completed.

        Returns
        -------
        bool
            True after create() finishes. Asynchronous provider startup and HTTP
            kernel readiness are completed separately during lifespan startup.
        """
        return self.__booted

    @property
    def startAt(self) -> int:
        """
        Return the application startup timestamp in nanoseconds.

        Returns
        -------
        int
            Timestamp in nanoseconds since Unix epoch when the application
            instance was initialized.
        """
        return self.__start_at

    @property
    def routeHealthCheck(self) -> str:
        """
        Return the health check route for the application.

        Returns
        -------
        str
            The configured health check route path. Returns "/up" if not set.
        """
        # Get health check route from routing config, default to "/up"
        routing_config: dict = self.__bootstrap.get("routing", {})
        return routing_config.get("health") or "/up"

    @property
    def entryPoint(self) -> str | None:
        """
        Return the entry point module path where the application was created.

        Returns
        -------
        str | None
            The module path in the format 'folder.subfolder.file:app' where
            the application instance was created, or None if not available.
        """
        # Return None if the creation stack is not set
        if not self.__entry_point:
            return None

        # Get absolute path to the entry point file
        abs_path = Path(self.__entry_point).resolve()

        # Compute the relative path from the root to the entry point
        try:
            rel_path = abs_path.relative_to(self.basePath)
        except ValueError:
            rel_path = abs_path.name

        # Remove file extension and convert to module path notation
        if isinstance(rel_path, Path) and rel_path.suffix:
            rel_path = rel_path.with_suffix("")

        # Convert the relative path to module notation (dot-separated)
        module_path: str = (
            ".".join(rel_path.parts)
            if isinstance(rel_path, Path)
            else ".".join(Path(rel_path).parts)
        )

        # Return the module path in dot notation, or None if not available
        return f"{module_path}:app"

    @property
    def basePath(self) -> Path:
        """
        Return the base path of the application.

        Returns
        -------
        Path
            The base directory path of the application.
        """
        return self.__basePath

    @property
    def compiled(self) -> bool:
        """
        Indicate whether the application is running in compiled mode.

        Returns
        -------
        bool
            True if the application is configured to run in compiled mode,
            otherwise False.
        """
        return self.__compiled

    @property
    def compiledPath(self) -> Path | None:
        """
        Return the path where compiled cache files are stored.

        Returns
        -------
        Path or None
            The directory path for compiled cache storage, or None if not
            configured.
        """
        return self.__compiled_path

    @property
    def compiledInvalidationPathsDirs(self) -> list[Path]:
        """
        Return the list of directory paths monitored for cache invalidation.

        Returns
        -------
        list of Path
            List of directory paths monitored for cache invalidation.
        """
        return list(self.__compiled_invalidation_paths_dirs)

    @property
    def compiledInvalidationPathsFiles(self) -> list[Path]:
        """
        Return the list of file paths monitored for cache invalidation.

        Returns
        -------
        list of Path
            List of file paths monitored for cache invalidation.
        """
        return list(self.__compiled_invalidation_paths_files)

    # --- Application Initialization ---

    def __init__(
        self,
        base_path: Path = _CWD,
    ) -> None:
        """
        Initialize the Application instance.

        Parameters
        ----------
        base_path : Path
            The base directory path of the application.

        Returns
        -------
        None
            This method initializes the Application instance in place.
        """
        # Ensure the application is initialized only once (singleton pattern).
        if not hasattr(self, "_Application__initialized"):
            # Call the base Container constructor to initialize dependency injection.
            super().__init__()

            # Store the application startup timestamp in nanoseconds.
            self.__start_at = time.time_ns()

            # Ensure the minimum required Python version.
            self.__assertPythonVersion()

            # Validate and store the basePath as the application root.
            self.__basePath = self.__validateAndReturnPath(base_path)

            # Flag to determine if working with previously compiled state.
            self.__is_compiled: bool = False

            # Cache driver for storing compiled configuration.
            self.__compiled_state_store: IFileBasedCache | None = None

            # Lifecycle event callbacks for each runtime (HTTP/CLI/global).
            # These are not cached and execute on each lifecycle event.
            self.__hook_events: dict = {
                Runtime.HTTP: {Lifespan.STARTUP: set(), Lifespan.SHUTDOWN: set()},
                Runtime.CLI: {Lifespan.STARTUP: set(), Lifespan.SHUTDOWN: set()},
                None: {Lifespan.STARTUP: set(), Lifespan.SHUTDOWN: set()},
            }

            # Initialize references to resolved service classes.
            self.__scheduler_resolved: type[IBaseScheduler] | None = None
            self.__exception_handler_resolved: type[IBaseExceptionHandler] | None = None

            # Initialize application state flags.
            self.__booted: bool = False
            self.__configured: bool = False
            self.__runtime_config_initialized: bool = False
            self.__is_production_cache: bool = False
            self.__is_debug_cache: bool = False

            # Initialize configuration dictionaries.
            self.__bootstrap: dict[str, Any] = {}
            self.__runtime_config: dict[str, Any] = {}
            self.__config_key_parts: dict[str, tuple[str, ...]] = {}

            # Initialize kernel caches.
            self.__kernel_cli: Callable | None = None
            self.__kernel_http_rsgi: Callable | None = None
            self.__kernel_http_asgi: Callable | None = None
            self.__http_disconnect_monitoring: bool = False
            self.__kernel_http_lock = asyncio.Lock()
            self.__kernel_cli_lock = asyncio.Lock()

            # Initialize deferred providers cache.
            self.__cache_resolved_providers: set[str] = set()
            self.__pending_boot_providers: deque[IServiceProvider] = deque()
            self.__provider_boot_lock = asyncio.Lock()

            # Initialize providers registry sentinel.
            self.__providers_registry_initialized: bool = False

            # Store the file path where the application was started.
            self.__entry_point: str | None = None

            # Initialize deferred providers storage for tracking.
            self._deferred_providers: dict = {}

            # Compilation and configuration caching logic.
            self.__compiled: bool = False
            self.__compiled_path: Path | None = None
            self.__compiled_invalidation_paths_dirs: set[Path] = set()
            self.__compiled_invalidation_paths_files: set[Path] = set()

            # Mark the Application as initialized to enforce singleton behavior.
            self._Application__initialized = True

    def compile(
        self,
        path: str | None = None,
        invalidation_paths: list[str] | None = None,
    ) -> None:
        """
        Compile the application with the specified caching and invalidation settings.

        Parameters
        ----------
        path : str | None, optional
            The path where compiled files should be stored.
            Defaults to None.
        invalidation_paths : list[str] | None, optional
            List of paths that trigger cache invalidation when modified.
            Defaults to None.

        Returns
        -------
        None
            This method does not return a value.
        """
        self.__bootCompiledState(
            compiled_path=path,
            compiled_invalidation_paths=invalidation_paths,
        )

    def __assertPythonVersion(self) -> None:
        """
        Assert that the current Python version meets the minimum requirement.

        Raises
        ------
        RuntimeError
            If the current Python version is lower than the required version.

        Returns
        -------
        None
            This method does not return a value.
            It raises if the version is insufficient.
        """
        # Compare current Python version with the required minimum version.
        if sys.version_info < PYTHON_REQUIRES:
            error_msg = (
                f"Python {PYTHON_REQUIRES[0]}.{PYTHON_REQUIRES[1]} or higher is "
                f"required to run this application. Current version: "
                f"{sys.version_info.major}.{sys.version_info.minor}"
            )
            raise RuntimeError(error_msg)

    def __validateAndReturnPath(
        self,
        path: Path | str,
    ) -> Path:
        """
        Validate and return a resolved Path object.

        Parameters
        ----------
        path : Path or str
            The path to validate and resolve.

        Returns
        -------
        Path
            The validated and resolved Path object.

        Raises
        ------
        TypeError
            If `path` is not a Path or str.
        """
        # Convert string to Path. basePath may not be set yet (e.g. during __init__),
        # so fall back to the process working directory for relative strings.
        if isinstance(path, str):
            base = getattr(self, "_Application__basePath", _CWD)
            path = (base / path).resolve()
        elif isinstance(path, Path):
            path = path.resolve()
        else:
            error_msg = "Path must be a Path or str."
            raise TypeError(error_msg)

        # Return the path
        return path

    # --- Lifecycle Callbacks Registration Methods ---

    def on(
        self,
        lifespan: Lifespan,
        *callbacks: Callable[..., Any] | Callable[..., Awaitable[Any]],
        runtime: Runtime | None = None,
    ) -> Self:
        """
        Register callbacks for a specific application lifespan event.

        Parameters
        ----------
        lifespan : Lifespan
            The application lifespan event to register callbacks for.
        *callbacks : Callable[..., Any] | Callable[..., Awaitable[Any]]
            One or more callback functions to execute during the event.
        runtime : Runtime | None, optional
            The runtime environment for which to register the callbacks.
            If None, callbacks are registered for all runtimes.

        Returns
        -------
        Self
            The current Application instance for method chaining.

        Raises
        ------
        TypeError
            If `lifespan` is not a Lifespan enum or any callback is not callable.
        ValueError
            If no callbacks are provided.

        Notes
        -----
        Callbacks are stored as-is and executed during the specified lifespan
        event. Lambdas and dynamic callables are supported.
        """
        # Validate that lifespan is a Lifespan enum instance
        if not isinstance(lifespan, Lifespan):
            error_msg = (
                f"Expected lifespan to be an instance of Lifespan enum, got "
                f"{type(lifespan).__name__}"
            )
            raise TypeError(error_msg)

        # Ensure at least one callback is provided
        if not callbacks:
            error_msg = "At least one callback must be provided."
            raise ValueError(error_msg)

        # Validate that all callbacks are callable
        for cb in callbacks:
            if not callable(cb):
                error_msg = f"{cb!r} is not callable."
                raise TypeError(error_msg)

        # Use None as runtime if not provided or invalid
        rt: Runtime | None = runtime if runtime in self.__hook_events else None

        # Register callbacks in the appropriate set for the event and runtime
        self.__hook_events[rt][lifespan].update(callbacks)

        # Return self to allow method chaining
        return self

    async def __onStartup(
        self,
        runtime: Runtime,
        http_interface: str = "asgi",
    ) -> None:
        """
        Execute startup callbacks for the application lifecycle.

        Parameters
        ----------
        runtime : Runtime
            The runtime environment (HTTP or CLI) for which to
            execute startup callbacks.
        http_interface : str, optional
            HTTP transport recorded when the kernel is warmed during startup.

        Returns
        -------
        None
            This method executes startup callbacks and does not return a value.
        """
        # Ensure all pending eager providers are booted before startup hooks
        await self.__bootEagerProviders()

        # Collect startup callbacks for the given runtime and global scope
        callbacks = (
            self.__hook_events[None][Lifespan.STARTUP]
            | self.__hook_events[runtime][Lifespan.STARTUP]
        )

        # Trigger startup lifecycle events and execute registered startup callbacks
        if runtime == Runtime.HTTP:
            # Start the Orionis startup generator.
            startup_gen = import_module(
                "orionis.foundation.lifespan.startup",
            ).startup_orionis_generator(self)
            next(startup_gen)

            # Execute all registered startup callbacks (sync or async).
            for func in callbacks:
                await self.invoke(func)

            # Publish both HTTP handlers before the server acknowledges readiness.
            await self.__initializeHttpKernel(http_interface)

            # Finalize the startup generator.
            with suppress(StopIteration):
                next(startup_gen)

        elif runtime == Runtime.CLI:
            # Execute all registered startup callbacks (sync or async).
            for func in callbacks:
                await self.invoke(func)

    async def __onShutdown(
        self,
        runtime: Runtime,
    ) -> None:
        """
        Execute shutdown callbacks for the application lifecycle.

        Parameters
        ----------
        runtime : Runtime
            The runtime environment (HTTP or CLI) for which to
            execute shutdown callbacks.

        Returns
        -------
        None
            This method executes shutdown callbacks and does not return a value.
        """
        # Collect shutdown callbacks for the given runtime and global scope
        callbacks = (
            self.__hook_events[None][Lifespan.SHUTDOWN]
            | self.__hook_events[runtime][Lifespan.SHUTDOWN]
        )

        # Trigger shutdown lifecycle events and execute registered shutdown callbacks
        if runtime == Runtime.HTTP:
            # Start the Orionis shutdown generator.
            shutdown_gen = import_module(
                "orionis.foundation.lifespan.shutdown",
            ).shutdown_orionis_generator(self)
            next(shutdown_gen)

            # Execute all registered shutdown callbacks (sync or async).
            for func in callbacks:
                await self.invoke(func)

            # Finalize the shutdown generator.
            with suppress(StopIteration):
                next(shutdown_gen)

        elif runtime == Runtime.CLI:
            # Execute all registered shutdown callbacks (sync or async).
            for func in callbacks:
                await self.invoke(func)

    # --- Default Configuration Setup Methods ---

    def __defaultBootstrap(
        self,
    ) -> dict[str, Any]:
        """
        Return the default bootstrap configuration.

        Returns
        -------
        dict[str, Any]
            Default bootstrap configuration dictionary with all core sections
            initialized for application startup.
        """
        # Build and return the default bootstrap dictionary
        return {
            "commands": {},
            "config": {},
            "exception_handler": FreezeThaw.thaw(CORE_EXCEPTION_HANDLER),
            "kernels": FreezeThaw.thaw(CORE_KERNELS),
            "paths": {},
            "providers": {},
            "routing": {},
            "scheduler": FreezeThaw.thaw(CORE_SCHEDULER),
            "middleware": [],
        }

    def __ensureDefaultBootstrap(
        self,
    ) -> None:
        """
        Initialize the bootstrap configuration with default values.

        Initialize the internal bootstrap configuration dictionary with the default
        bootstrap configuration if it is currently empty. This ensures the
        application has a valid configuration structure before any customization.

        Returns
        -------
        None
            This method does not return a value. It modifies the internal bootstrap
            configuration state in place.
        """
        # If bootstrap is not empty, return immediately
        if self.__bootstrap:
            return

        # Initialize bootstrap configuration if not already set
        self.__bootstrap = self.__defaultBootstrap()

    def __ensureDefaultPaths(
        self,
    ) -> None:
        """
        Ensure default application paths are set in the bootstrap configuration.

        Initialize the 'paths' key in the bootstrap dictionary using default
        configuration paths if it is missing or empty.

        Returns
        -------
        None
            This method does not return a value. It modifies the internal
            bootstrap state to ensure paths are set.
        """
        # If paths exist and are not empty, return immediately
        if self.__bootstrap.get("paths"):
            return

        # Set default paths if not already present in bootstrap configuration
        self.withConfigPaths()

    # --- Utility Functions for Application Loading ---

    def __assertConfigMutable(
        self,
    ) -> None:
        """
        Assert that configuration is mutable before modification.

        Raises
        ------
        RuntimeError
            If attempting to modify configuration after application boot.

        Returns
        -------
        None
            This method does not return a value. Raises if configuration is locked.
        """
        # Prevent configuration changes after boot
        if self.__booted:
            error_msg = "Cannot modify configuration after application has been booted."
            raise RuntimeError(error_msg)

        # Initialize bootstrap configuration if not already set
        self.__ensureDefaultBootstrap()

    def __lockConfig(
        self,
    ) -> None:
        """
        Deeply freeze and lock the application configuration.

        Freezes the internal bootstrap configuration in-place to prevent
        further modifications. The booted flag is set separately in ``create()``.

        Returns
        -------
        None
            This method does not return a value. The configuration is locked
            in-place.
        """
        # Deep freeze the bootstrap configuration to make it immutable
        self.__bootstrap = FreezeThaw.freeze(self.__bootstrap)

    # --- Application Compilation Methods ---

    def __bootCompiledState(
        self,
        compiled_path: str | None = None,
        compiled_invalidation_paths: list[str] | None = None,
    ) -> None:
        """
        Initialize application compilation and configuration caching.

        Parameters
        ----------
        compiled_path : str | None, optional
            Path to the cache directory, or None.
        compiled_invalidation_paths : list[str] | None, optional
            List of paths to monitor for cache invalidation, or None.

        Returns
        -------
        None
            Configure the cache and load any valid stored bootstrap state.

        Notes
        -----
        This method sets up the cache driver and loads cached configuration
        if available. It also tracks directories and files for cache invalidation.
        """
        # Mark the application as compiled to activate caching logic.
        self.__compiled = True

        # Resolve and set the cache directory path if provided.
        if compiled_path is not None:
            self.__compiled_path = self.__validateAndReturnPath(compiled_path)

        # Monitor specified paths for cache invalidation.
        if compiled_invalidation_paths:
            for path_str in compiled_invalidation_paths:
                abs_path = (self.__basePath / path_str).resolve()
                if abs_path.is_dir():
                    self.__compiled_invalidation_paths_dirs.add(abs_path)
                elif abs_path.is_file():
                    self.__compiled_invalidation_paths_files.add(abs_path)

        # Fall back to a default cache path when none was provided.
        if self.__compiled_path is None:
            self.__compiled_path = (
                self.__basePath / "storage" / "framework" / "cache"
            ).resolve()

        # Initialize the cache driver for configuration caching.
        self.__compiled_state_store = FileBasedCache(
            path=self.__compiled_path,
            filename="config",
            monitored_dirs=self.compiledInvalidationPathsDirs,
            monitored_files=self.compiledInvalidationPathsFiles,
        )

        # Retrieve the current cache if available.
        bootstrapt_cache = self.__compiled_state_store.get()

        # Use the cache if it exists and mark as cached.
        if bootstrapt_cache is not None:
            self.__bootstrap = bootstrapt_cache
            self.__is_compiled = True
            self.__commitConfig()

    def __persistCompiledState(self) -> None:
        """
        Persist the compiled application state to cache.

        Save the current bootstrap configuration to the cache if the application
        is running in compiled mode and the cache driver is initialized.

        Returns
        -------
        None
            This method does not return a value. It persists the configuration
            state to cache if applicable.
        """
        # Skip if not running in compiled mode
        if not self.__compiled:
            return

        # Save the current bootstrap configuration to cache if cache driver exists
        if self.__compiled_state_store is not None:
            self.__compiled_state_store.save(self.__bootstrap)

    # --- Service Provider Bootstrapping Logic ---

    def withMiddleware(
        self,
        *middleware: type[IBaseMiddleware],
    ) -> Self:
        """
        Register middleware for the application.

        Parameters
        ----------
        middleware : tuple[type[IBaseMiddleware], ...]
            Middleware classes to register. Each must inherit from
            IBaseMiddleware.

        Returns
        -------
        Self
            The current Application instance for method chaining.
        """
        # Return early if configuration is already cached: middleware is
        # stored inside __bootstrap["middleware"], which is serialised to
        # the compiled cache, so it is already present on cache hit.
        if self.__is_compiled:
            return self

        # Ensure configuration is not locked before modification
        self.__assertConfigMutable()

        # Store unique middleware metadata in registration order.
        mw_list: list = self.__bootstrap["middleware"]
        for mw in middleware:
            if not isinstance(mw, type) or not issubclass(mw, IBaseMiddleware):
                error_msg = (
                    f"Expected middleware to be a class inheriting from "
                    f"IBaseMiddleware, got {type(mw).__name__}"
                )
                raise TypeError(error_msg)
            mw_entry = {"module": mw.__module__, "class": mw.__name__}
            if mw_entry not in mw_list:
                mw_list.append(mw_entry)

        # Return self instance for method chaining
        return self

    def getMiddleware(self) -> list[type[IBaseMiddleware]]:
        """
        Retrieve the list of registered middleware classes.

        Returns
        -------
        list[type[IBaseMiddleware]]
            A list of middleware classes registered in the application.
        """
        # Resolve and return middleware classes from bootstrap metadata.
        # Falls back to an empty list if the key is missing (e.g. old cache).
        middleware_classes = []
        for mw_metadata in self.__bootstrap.get("middleware", []):
            mw_cls = ModuleInspector.loadClass(metadata=mw_metadata)
            middleware_classes.append(mw_cls)
        return middleware_classes

    def withProviders(
        self,
        *providers: type[IServiceProvider],
    ) -> Self:
        """
        Register service providers for the application.

        Parameters
        ----------
        providers : tuple[type[IServiceProvider], ...]
            Service provider classes to register. Each must inherit from
            IServiceProvider.

        Returns
        -------
        Self
            The current Application instance for method chaining.

        Raises
        ------
        TypeError
            If any argument is not a class or does not inherit from
            IServiceProvider.
        """
        # Return early if configuration is already cached
        if self.__is_compiled:
            return self

        # Ensure configuration is not locked before modification
        self.__assertConfigMutable()

        # Register each provider using the internal storage method
        for provider in providers:
            self.__storeProviderClass(provider)

        # Return self instance for method chaining
        return self

    def __loadCoreProviders(self) -> None:
        """
        Load and register core framework service providers.

        Import and register essential service providers required for framework
        operation. Ensures core services are available before user-defined
        providers.

        Parameters
        ----------
        self : Application
            The current Application instance.

        Returns
        -------
        None
            This method modifies the internal providers registry in place.
        """
        # Register each core provider in the providers registry
        for provider in get_core_providers_mapping():
            self.__storeProviderClass(provider)

    def __ensureProvidersRegistryStructure(self) -> None:
        """
        Ensure the providers registry structure is properly initialized.

        Initialize the eager and deferred provider registries in the bootstrap
        configuration if they do not already exist. This method creates the
        necessary dictionary structure for storing service provider information
        and prevents duplicate initialization through a sentinel attribute.

        Returns
        -------
        None
            This method does not return a value. It modifies internal state.
        """
        # Ensure eager and deferred provider registries exist
        if not self.__providers_registry_initialized:
            if "eager" not in self.__bootstrap["providers"]:
                self.__bootstrap["providers"]["eager"] = OrderedDict()
            if "deferred" not in self.__bootstrap["providers"]:
                self.__bootstrap["providers"]["deferred"] = {}
            self.__providers_registry_initialized = True

    def __validateProviderClass(
        self,
        provider_class: type[IServiceProvider],
    ) -> None:
        """
        Validate that the provider class meets IServiceProvider requirements.

        Parameters
        ----------
        provider_class : type[IServiceProvider]
            The service provider class to validate.

        Returns
        -------
        None
            This method does not return a value. Raises exceptions if validation
            fails.

        Raises
        ------
        TypeError
            If the provider is not a class or not a subclass of IServiceProvider.
        """
        # Validate that the provider is a class
        if not isinstance(provider_class, type):
            error_msg = (
                f"Expected IServiceProvider class, got {type(provider_class).__name__}"
            )
            raise TypeError(error_msg)

        # Validate that the provider is a subclass of IServiceProvider
        if not issubclass(provider_class, IServiceProvider):
            error_msg = (
                f"Expected IServiceProvider subclass, got "
                f"{type(provider_class).__name__}"
            )
            raise TypeError(error_msg)

    def __storeEagerProviderClass(
        self,
        provider: type[IServiceProvider],
    ) -> None:
        """
        Store an eager service provider instance in the eager registry.

        Parameters
        ----------
        provider : type[IServiceProvider]
            The service provider class to register.

        Returns
        -------
        None
            This method does not return a value. It modifies the internal eager
            providers registry in-place.

        Raises
        ------
        TypeError
            If the provider is not a class or not a subclass of IServiceProvider.
        """
        # Direct reference to the registry for in-place mutation
        eager: OrderedDict = self.__bootstrap["providers"]["eager"]

        # Extract module and class name for storage
        module: str = provider.__module__
        class_name: str = provider.__name__
        provider_full_path: str = f"{module}.{class_name}"

        # Insert metadata and move to front to maintain priority ordering
        eager[provider_full_path] = {"module": module, "class": class_name}
        eager.move_to_end(provider_full_path, last=False)

    def __storeDeferredProviderClass(
        self,
        provider: type[IDeferrableProvider],
    ) -> None:
        """
        Store a deferred service provider instance in the deferred registry.

        Parameters
        ----------
        provider : type[IDeferrableProvider]
            The service provider class to register.

        Returns
        -------
        None
            This method does not return a value.

        Raises
        ------
        TypeError
            If the provider is not a class or not a subclass of IServiceProvider.
        """
        # Prepare deferred provider registry
        deferred: dict = self.__bootstrap["providers"]["deferred"]

        # Extract module and class name for storage
        module = provider.__module__
        class_name = provider.__name__

        # Register each service provided by the deferred provider
        provided_services = provider.provides()
        for service in provided_services:
            if isinstance(service, str):
                service_full_path = service
            elif isinstance(service, type):
                service_full_path = f"{service.__module__}.{service.__name__}"
            else:
                error_msg = (
                    f"Service provided by {provider.__name__} must be a string or "
                    f"class type, got {type(service).__name__}"
                )
                raise TypeError(error_msg)
            deferred.pop(service_full_path, None)
            deferred[service_full_path] = {
                "module": module,
                "class": class_name,
            }

    def __storeProviderClass(
        self,
        provider: type[IServiceProvider],
    ) -> None:
        """
        Store a service provider instance in the appropriate registry.

        Register the provider class in either the eager or deferred registry based
        on its inheritance hierarchy. Validates provider type and ensures proper
        registry structure before storage.

        Parameters
        ----------
        provider : type[IServiceProvider]
            The service provider class to register.

        Returns
        -------
        None
            This method does not return a value.

        Raises
        ------
        TypeError
            If the provider is not a class or not a subclass of IServiceProvider.
        """
        # Ensure providers registry structure is initialized
        self.__ensureProvidersRegistryStructure()

        # Validate the provider class meets requirements
        self.__validateProviderClass(provider)

        # Register as deferred or eager based on provider inheritance
        if issubclass(provider, DeferrableProvider):
            self.__storeDeferredProviderClass(provider)
        else:
            self.__storeEagerProviderClass(provider)

    def __discoverProviders(
        self,
        modules: set[str],
    ) -> None:
        """
        Discover and register service providers from the providers folder.

        Imports each discovered module, identifies classes that are
        subclasses of ServiceProvider, and registers them in the appropriate
        registry based on whether they are deferred or immediate providers.

        Parameters
        ----------
        modules : set[str]
            Dotted module names containing service provider classes.

        Returns
        -------
        None
            Modifies the internal providers registry in-place.
        """
        # Import each module and register its service providers
        for module_name in modules:
            module = __import__(module_name, fromlist=["*"])
            for attribute in vars(module).values():
                if (
                    isinstance(attribute, type)
                    and issubclass(attribute, ServiceProvider)
                    and attribute is not ServiceProvider
                    and attribute is not DeferrableProvider
                ):
                    self.__storeProviderClass(attribute)

    def __loadProviders(self) -> None:
        """
        Load and register all service providers.

        Discovers provider modules, registers provider classes, and loads core
        framework providers. Ensures all service providers are available for
        dependency injection and application bootstrapping.

        Parameters
        ----------
        self : Application
            The current application instance.

        Returns
        -------
        None
            This method updates the internal providers registry in place.
        """
        # Discover provider modules in the providers directory.
        config_paths: dict[str, Any] = self.__bootstrap["paths"]

        # Register discovered provider classes from modules.
        self.__discoverProviders(
            ModuleInspector.discoverModules(
                base_path=self.__basePath,
                target_path=config_paths["app_providers"],
            ),
        )

        # Load and register core framework providers.
        self.__loadCoreProviders()

    def __resolveEagerProvider(self) -> None:
        """
        Resolve and register all eager service providers.

        Resolves all eager service providers defined in the application's
        bootstrap configuration. Registers each provider and schedules its boot
        method if asynchronous.

        Returns
        -------
        None
            This method does not return a value. It registers and schedules
            eager providers for booting.
        """
        eager_providers: dict = self.__bootstrap.get("providers", {}).get("eager", {})

        # Iterate and resolve each eager provider class
        for full_path_provider, provider_metadata in eager_providers.items():
            # Skip if this provider has already been resolved to prevent duplicates
            if full_path_provider in self.__cache_resolved_providers:
                continue

            # Resolve the provider class using the module engine and register it
            provider = ModuleInspector.loadClass(metadata=provider_metadata)
            instance: IServiceProvider = provider(self)
            register = getattr(instance, "register", None)
            if callable(register):
                register()

            # Schedule boot for async providers, call directly for sync
            boot_fn = getattr(instance, "boot", None)
            if boot_fn is not None and callable(boot_fn):
                if inspect.iscoroutinefunction(boot_fn):
                    self.__pending_boot_providers.append(instance)
                else:
                    boot_fn()

            # Add to resolved providers cache to prevent duplicate resolution
            self.__cache_resolved_providers.add(full_path_provider)

    async def __bootEagerProviders(self) -> None:
        """
        Boot all pending eager service providers.

        Await providers in registration order and retain unfinished providers
        so a later startup can retry them.

        Returns
        -------
        None
            This method does not return a value.
        """
        # Skip startup coordination when every provider has finished booting.
        if not self.__pending_boot_providers:
            return

        # Keep each provider pending until its boot method completes.
        async with self.__provider_boot_lock:
            pending = self.__pending_boot_providers
            while pending:
                await pending[0].boot()
                pending.popleft()

    # --- Routing Configuration and Validation ---

    def withRouting(
        self,
        api: str | list[str] | None = None,
        web: str | list[str] | None = None,
        console: str | list[str] | None = None,
        health: str | None = None,
    ) -> Self:
        """
        Configure routing files for API, web, console, and health endpoints.

        Parameters
        ----------
        api : str | list[str] | None
            Path or list of paths to API routing files.
        web : str | list[str] | None
            Path or list of paths to web routing files.
        console : str | list[str] | None
            Path or list of paths to console routing files.
        health : str | None
            Path to the health check route.

        Returns
        -------
        Self
            The current Application instance for method chaining.

        Raises
        ------
        TypeError
            If routing arguments are of invalid types or do not contain valid
            routing definitions.
        FileNotFoundError
            If a specified routing file does not exist.
        """
        # Return early if configuration is already cached
        if self.__is_compiled:
            return self

        # Ensure configuration is not locked before modification
        self.__assertConfigMutable()

        # Resolve and validate API routing files
        api_routers = self.__resolveAndValidateRoutingFiles(
            api,
            {"orionis.support.facades.router"},
        )

        # Resolve and validate web routing files
        web_routers = self.__resolveAndValidateRoutingFiles(
            web,
            {"orionis.support.facades.router"},
        )

        # Resolve and validate console routing files
        console_routers = self.__resolveAndValidateRoutingFiles(
            console,
            {"orionis.support.facades.reactor"},
        )

        # Validate health route type
        if health is not None and not isinstance(health, str):
            error_msg = (
                f"Expected str for 'health' routing, got {type(health).__name__}."
            )
            raise TypeError(error_msg)

        # Store routing configuration in bootstrap
        self.__bootstrap["routing"] = {
            "api": api_routers,
            "web": web_routers,
            "console": console_routers,
            "health": health,
        }

        # Return self for method chaining
        return self

    def __resolveAndValidateRoutingFiles(
        self,
        paths: str | list[str] | None,
        required_imports: set[str],
    ) -> list[Path]:
        """
        Resolve and validate routing file paths.

        Parameters
        ----------
        paths : str | list[str] | None
            Routing file path(s) to validate and resolve.
        required_imports : set[str]
            Set of required module imports for validation.

        Returns
        -------
        list[Path]
            List of resolved Path objects for valid routing files.

        Raises
        ------
        TypeError
            If `paths` is not a str, list[str], or None, or if a file does not
            contain valid routing definitions.
        FileNotFoundError
            If a specified routing file does not exist.
        """
        # Ensure the routing argument is of the expected type
        if not isinstance(paths, (str, list, type(None))):
            error_msg = "Expected str, list[str], or None for routing paths"
            raise TypeError(error_msg)

        # Convert to list if a single string is provided
        if isinstance(paths, str):
            paths = [paths]

        # Final list to hold resolved Path objects for valid routing files
        final_paths: list[Path] = []

        # Iterate through each provided path, validate existence and required imports
        for path in paths or []:
            # Resolve the absolute path for the routing file
            file_path = (self.__basePath / path).resolve()

            # Check if the file exists before validating its contents
            if not file_path.exists():
                error_msg = f"Routing file does not exist: {file_path}"
                raise FileNotFoundError(error_msg)

            # Check if the file contains required routing imports
            if file_path.read_text(
                encoding="utf-8",
            ).strip() and not ModuleInspector.fileImportsAny(
                file_path,
                required_imports,
            ):
                error_msg = (
                    f"The file '{path}' does not contain valid routing definitions."
                )
                raise TypeError(error_msg)

            # Append the valid routing file path to the final list
            final_paths.append(file_path)

        # Return the list of resolved Path objects for valid routing files
        return final_paths

    # --- Exception Handler Configuration ---

    def withExceptionHandler(
        self,
        handler: type[IBaseExceptionHandler],
    ) -> Self:
        """
        Register a custom exception handler class for the application.

        Parameters
        ----------
        handler : type[IBaseExceptionHandler]
            Exception handler class to use. Must inherit from BaseExceptionHandler.

        Returns
        -------
        Self
            The current Application instance for method chaining.

        Raises
        ------
        TypeError
            If the handler is not a class or not a subclass of BaseExceptionHandler.
        RuntimeError
            If attempting to set handler after application has been booted.

        Notes
        -----
        Stores the handler class for later instantiation. Any previously
        registered handler is silently replaced.
        """
        # Return early if configuration is already cached
        if self.__is_compiled:
            return self

        # Ensure configuration is not locked before modification
        self.__assertConfigMutable()

        # Validate handler is a class
        if not isinstance(handler, type):
            error_msg = (
                f"Expected exception handler class, got {type(handler).__name__}"
            )
            raise TypeError(error_msg)

        # Validate handler is a subclass of BaseExceptionHandler
        if not issubclass(handler, IBaseExceptionHandler):
            error_msg = (
                f"Expected BaseExceptionHandler subclass, got {type(handler).__name__}"
            )
            raise TypeError(error_msg)

        # Store the exception handler class metadata
        self.__bootstrap["exception_handler"] = {
            "module": handler.__module__,
            "class": handler.__name__,
        }

        return self

    async def getExceptionHandler(
        self,
    ) -> IBaseExceptionHandler:
        """
        Retrieve the registered exception handler instance.

        Parameters
        ----------
        self : Application
            The current application instance.

        Returns
        -------
        IBaseExceptionHandler
            The registered exception handler instance. If none is set, returns
            the default BaseExceptionHandler instance.

        Raises
        ------
        RuntimeError
            If called before the application is booted.
        """
        # Ensure the application is booted before accessing the exception handler
        if not self.__booted:
            error_msg = (
                "Cannot retrieve exception handler before application is booted."
            )
            raise RuntimeError(error_msg)

        # Resolve and cache the exception handler class.
        if self.__exception_handler_resolved is None:
            exception_handler = self.__bootstrap.get("exception_handler")
            concrete_handler = ModuleInspector.loadClass(metadata=exception_handler)
            self.__exception_handler_resolved = concrete_handler

        # Return the exception handler instance
        return await self.build(self.__exception_handler_resolved)

    # --- Scheduler Configuration ---

    def withScheduler(
        self,
        scheduler: type[IBaseScheduler],
    ) -> Self:
        """
        Register a custom scheduler class for the application.

        Parameters
        ----------
        scheduler : type[IBaseScheduler]
            The scheduler class to be used. Must inherit from IBaseScheduler.

        Returns
        -------
        Self
            The current Application instance for method chaining.

        Raises
        ------
        RuntimeError
            If attempting to set scheduler after application has been booted.
        TypeError
            If the provided scheduler is not a subclass of IBaseScheduler.

        Notes
        -----
        Stores the scheduler class metadata for later instantiation. Any
        previously registered scheduler is silently replaced.
        """
        # Return early if configuration is already cached
        if self.__is_compiled:
            return self

        # Ensure configuration is not locked before modification
        self.__assertConfigMutable()

        # Validate that the scheduler is a class and a subclass of IBaseScheduler
        if not isinstance(scheduler, type) or not issubclass(scheduler, IBaseScheduler):
            error_msg = (
                f"Expected IBaseScheduler subclass, got {type(scheduler).__name__}"
            )
            raise TypeError(error_msg)

        # Store the scheduler class metadata for later instantiation
        self.__bootstrap["scheduler"] = {
            "module": scheduler.__module__,
            "class": scheduler.__name__,
        }

        # Return the application instance for method chaining
        return self

    async def getScheduler(
        self,
    ) -> IBaseScheduler:
        """
        Retrieve the currently registered scheduler instance.

        Returns
        -------
        IBaseScheduler
            The registered scheduler instance.

        Raises
        ------
        RuntimeError
            If the application is not booted.
        """
        # Ensure the application is booted before accessing the scheduler
        if not self.__booted:
            error_msg = "Cannot retrieve scheduler before application is booted."
            raise RuntimeError(error_msg)

        # Resolve and cache the scheduler class.
        if self.__scheduler_resolved is None:
            scheduler = self.__bootstrap.get("scheduler")
            concrete_scheduler = ModuleInspector.loadClass(metadata=scheduler)
            self.__scheduler_resolved = concrete_scheduler

        # Return the scheduler instance
        return await self.build(self.__scheduler_resolved)

    # --- Configuration Subsystem Setup Methods ---

    def withConfigApp(
        self,
        **app_config: object,
    ) -> Self:
        """
        Configure application settings using keyword arguments.

        Parameters
        ----------
        **app_config : object
            Configuration parameters for the application. Keys must match the
            field names and types expected by the App dataclass from
            orionis.foundation.config.app.entities.app.App.

        Returns
        -------
        Self
            The current Application instance for method chaining.
        """
        # Return early if configuration is already cached
        if self.__is_compiled:
            return self

        # Ensure configuration is not locked before modification
        self.__assertConfigMutable()

        # Store the provided application configuration
        self.__bootstrap["config"]["app"] = app_config

        # Return the application instance for method chaining
        return self

    def withConfigAuth(
        self,
        **auth_config: object,
    ) -> Self:
        """
        Configure authentication subsystem using keyword arguments.

        Parameters
        ----------
        **auth_config : object
            Keyword arguments for authentication configuration. Keys must match
            the fields of the `Auth` dataclass from
            `orionis.foundation.config.auth.entities.auth.Auth`.

        Returns
        -------
        Self
            The current Application instance for method chaining.
        """
        # Return early if configuration is already cached
        if self.__is_compiled:
            return self

        # Ensure configuration is not locked before modification
        self.__assertConfigMutable()

        # Store the provided authentication configuration
        self.__bootstrap["config"]["auth"] = auth_config

        # Return the application instance for method chaining
        return self

    def withConfigCache(
        self,
        **cache_config: object,
    ) -> Self:
        """
        Configure the cache subsystem using keyword arguments.

        Parameters
        ----------
        **cache_config : object
            Keyword arguments representing cache configuration options. Keys must
            match the field names and types expected by the `Cache` dataclass from
            `orionis.foundation.config.cache.entities.cache.Cache`.

        Returns
        -------
        Self
            The current Application instance to enable method chaining.
        """
        # Return early if configuration is already cached
        if self.__is_compiled:
            return self

        # Ensure configuration is not locked before modification
        self.__assertConfigMutable()

        # Store the provided cache configuration in the bootstrap config
        self.__bootstrap["config"]["cache"] = cache_config

        # Return the application instance for method chaining
        return self

    def withConfigHttp(
        self,
        **http_config: object,
    ) -> Self:
        """
        Configure the HTTP subsystem using keyword arguments.

        Parameters
        ----------
        **http_config : object
            Keyword arguments for HTTP configuration. Keys must match the field
            names and types expected by the `HTTP` dataclass from
            `orionis.foundation.config.http.entitites.http.HTTP`.

        Returns
        -------
        Self
            The current Application instance for method chaining.
        """
        # Return early if configuration is already cached
        if self.__is_compiled:
            return self

        # Ensure configuration is not locked before modification
        self.__assertConfigMutable()

        # Store the provided HTTP configuration in the bootstrap config
        self.__bootstrap["config"]["http"] = http_config

        # Return the application instance for method chaining
        return self

    def withConfigDatabase(
        self,
        **database_config: object,
    ) -> Self:
        """
        Configure the database subsystem using keyword arguments.

        Parameters
        ----------
        **database_config : object
            Keyword arguments for database configuration. Keys must match the
            fields of the `Database` dataclass from
            `orionis.foundation.config.database.entities.database.Database`.

        Returns
        -------
        Self
            The current Application instance for method chaining.
        """
        # Return early if configuration is already cached
        if self.__is_compiled:
            return self

        # Ensure configuration is not locked before modification
        self.__assertConfigMutable()

        # Store the provided database configuration in the bootstrap config
        self.__bootstrap["config"]["database"] = database_config

        # Return the application instance for method chaining
        return self

    def withConfigFilesystems(
        self,
        **filesystems_config: object,
    ) -> Self:
        """
        Configure the filesystems subsystem using keyword arguments.

        Parameters
        ----------
        **filesystems_config : object
            Keyword arguments for filesystems configuration. Keys must match the
            fields of the `Filesystems` dataclass from
            `orionis.foundation.config.filesystems.entitites.filesystems.Filesystems`.

        Returns
        -------
        Self
            The current Application instance for method chaining.
        """
        # Return early if already cached
        if self.__is_compiled:
            return self

        # Ensure configuration is not locked before modification
        self.__assertConfigMutable()

        # Store the provided filesystems configuration
        self.__bootstrap["config"]["filesystems"] = filesystems_config

        # Return the application instance for method chaining
        return self

    def withConfigLogging(
        self,
        **logging_config: object,
    ) -> Self:
        """
        Configure logging subsystem using keyword arguments.

        Parameters
        ----------
        **logging_config : object
            Keyword arguments for logging configuration. Keys must match the
            fields of the `Logging` dataclass from
            `orionis.foundation.config.logging.entities.logging.Logging`.

        Returns
        -------
        Self
            The current Application instance for method chaining.
        """
        # Return early if already cached
        if self.__is_compiled:
            return self

        # Ensure configuration is not locked before modification
        self.__assertConfigMutable()

        # Store the provided logging configuration in the bootstrap config
        self.__bootstrap["config"]["logging"] = logging_config

        # Return the application instance for method chaining
        return self

    def withConfigMail(
        self,
        **mail_config: object,
    ) -> Self:
        """
        Configure mail subsystem using keyword arguments.

        Parameters
        ----------
        **mail_config : object
            Keyword arguments for mail configuration. Keys must match the fields
            of the `Mail` dataclass from
            `orionis.foundation.config.mail.entities.mail.Mail`.

        Returns
        -------
        Self
            The current Application instance for method chaining.
        """
        # Return early if configuration is already cached
        if self.__is_compiled:
            return self

        # Ensure configuration is not locked before modification
        self.__assertConfigMutable()

        # Store the provided mail configuration in the bootstrap config
        self.__bootstrap["config"]["mail"] = mail_config

        # Return the application instance for method chaining
        return self

    def withConfigQueue(
        self,
        **queue_config: object,
    ) -> Self:
        """
        Configure the queue subsystem using keyword arguments.

        Parameters
        ----------
        **queue_config : object
            Keyword arguments representing queue configuration options. Keys must
            match the field names and types expected by the `Queue` dataclass from
            `orionis.foundation.config.queue.entities.queue.Queue`.

        Returns
        -------
        Self
            The current Application instance for method chaining.
        """
        # Return early if configuration is already cached
        if self.__is_compiled:
            return self

        # Ensure configuration is not locked before modification
        self.__assertConfigMutable()

        # Store the provided queue configuration in the bootstrap config
        self.__bootstrap["config"]["queue"] = queue_config

        # Return the application instance for method chaining
        return self

    def withConfigSession(
        self,
        **session_config: object,
    ) -> Self:
        """
        Configure session subsystem using keyword arguments.

        Parameters
        ----------
        **session_config : object
            Keyword arguments for session configuration. Keys must match the
            fields of the `Session` dataclass from
            `orionis.foundation.config.session.entities.session.Session`.

        Returns
        -------
        Self
            The current Application instance for method chaining.
        """
        # Return early if configuration is already cached
        if self.__is_compiled:
            return self

        # Ensure configuration is not locked before modification
        self.__assertConfigMutable()

        # Store the provided session configuration in the bootstrap config
        self.__bootstrap["config"]["session"] = session_config

        # Return the application instance for method chaining
        return self

    def withConfigTesting(
        self,
        **testing_config: object,
    ) -> Self:
        """
        Configure the testing subsystem using keyword arguments.

        Parameters
        ----------
        **testing_config : object
            Keyword arguments for testing configuration. Keys must match the
            fields of the `Testing` dataclass from
            `orionis.foundation.config.testing.entities.testing.Testing`.

        Returns
        -------
        Self
            The current Application instance for method chaining.
        """
        # Return early if configuration is already cached
        if self.__is_compiled:
            return self

        # Ensure configuration is not locked before modification
        self.__assertConfigMutable()

        # Store the provided testing configuration in the bootstrap config
        self.__bootstrap["config"]["testing"] = testing_config

        # Return the application instance for method chaining
        return self

    def withConfigPaths(
        self,
        **paths: str | Path | None,
    ) -> Self:
        """
        Set and resolve application directory paths.

        Parameters
        ----------
        **paths : str | Path | None
            Optional directory path overrides. Valid keys are 'app', 'console',
            'exceptions', 'http', 'models', 'providers', 'notifications',
            'services', 'jobs', 'bootstrap', 'config', 'database', 'resources',
            'routes', 'storage' and 'tests'. The root always comes from basePath.

        Returns
        -------
        Self
            The current Application instance for method chaining.
        """
        # Return early if configuration is already cached
        if self.__is_compiled:
            return self

        # Ensure configuration is not locked before modification
        self.__assertConfigMutable()

        # Initialize final paths with the root path
        base_path = self.__basePath
        final_paths: dict = {
            "root": base_path,
        }

        # Iterate over valid keys and resolve paths, using provided values or defaults
        for key, default in CORE_APP_PATHS.items():
            path = paths.get(key)
            if isinstance(path, Path):
                final_paths[key] = path.resolve()
            elif isinstance(path, str):
                final_paths[key] = (base_path / path).resolve()
            else:
                final_paths[key] = (base_path / default).resolve()

        # Store the resolved paths in the application configuration
        self.__bootstrap["paths"] = final_paths

        # Return the application instance for method chaining
        return self

    # --- Configuration Loading Methods ---

    def __loadCustomConfig(
        self,
        default_config: dict[str, Any],
        custom_config: dict[str, Any],
        dataclasses: set[tuple[str, str, str, type[Any]]] | None = None,
    ) -> dict[str, Any]:
        """
        Merge custom configuration and dataclass defaults into the base config.

        Parameters
        ----------
        default_config : dict[str, Any]
            The base configuration dictionary containing default values.
        custom_config : dict[str, Any]
            The custom configuration dictionary to merge into defaults.
        dataclasses : set[tuple[str, str, str, Type[Any]]] | None, optional
            Set of tuples containing dataclass info to merge, or None.

        Returns
        -------
        dict[str, Any]
            The merged configuration dictionary containing all sections.
        """

        # Helper function to update a config section
        def update_section(
            section: str,
            values: dict[str, Any],
            base: dict[str, Any],
        ) -> None:
            """
            Merge one configuration section into the destination mapping.

            Parameters
            ----------
            section : str
                Name of the configuration section.
            values : dict[str, Any]
                Values overriding existing keys within the section.
            base : dict[str, Any]
                Destination configuration modified in place.

            Returns
            -------
            None
                The destination mapping contains the merged section.
            """
            # Merge values into the base config section
            current = base.get(section)
            if isinstance(current, dict):
                current.update(values)
            else:
                base[section] = values

        # Merge custom config sections into defaults
        for section, values in custom_config.items():
            if isinstance(values, dict):
                update_section(section, values, default_config)

        # Merge dataclass config sections into defaults
        if dataclasses:
            for section, _, _, cls in dataclasses:
                try:
                    update_section(section, asdict(cls()), default_config)
                except Exception as e:
                    error_msg = str(e)
                    raise RuntimeError(error_msg) from e

        # Return merged configuration dictionary
        return default_config

    def __loadConfig(self) -> None:
        """
        Load and merge the final configuration from dataclasses and custom config.

        Discovers configuration modules and dataclasses, loads default configuration
        values, merges them with custom configuration, and updates the application's
        bootstrap dictionary with the final configuration and discovered providers.

        Returns
        -------
        None
            This method updates the internal bootstrap configuration in place.
        """
        # Use the core config as the default configuration
        default_config: dict = dict(get_core_config_mapping())

        # Discover configuration modules in the config directory
        config_paths: dict = self.__bootstrap["paths"]

        # Discover frozen dataclasses in the discovered modules
        config_dataclasses: set = ModuleInspector.discoverFrozenDataclasses(
            ModuleInspector.discoverModules(
                base_path=self.__basePath,
                target_path=config_paths["config"],
            ),
        )

        # Retrieve custom configuration values if provided
        custom_config: dict = {}
        if "config" in self.__bootstrap:
            custom_config = deepcopy(self.__bootstrap["config"])

        # Merge custom configuration and dataclass defaults into the base config
        final_config: dict = self.__loadCustomConfig(
            default_config=default_config,
            custom_config=custom_config,
            dataclasses=config_dataclasses,
        )

        # Update the bootstrap configuration with the final merged config
        self.__bootstrap["config"] = final_config

    def __commitConfig(
        self,
    ) -> None:
        """
        Lock configuration and mark application as initialized.

        Freeze the bootstrap configuration to prevent further modifications and
        set the configured flag to indicate the application is ready for use.

        Returns
        -------
        None
            This method does not return a value. It modifies internal state
            to lock configuration.
        """
        # Deep freeze the configuration to prevent further modifications
        self.__lockConfig()

        # Mark configuration as initialized
        self.__configured = True

    # --- Bootstrap Application Methods ---

    def __setTimezoneAndLocale(self) -> None:
        """
        Set system timezone and locale from application configuration.

        Uses the application's configuration to set the system timezone and
        locale. This method updates environment variables and system locale
        settings if the relevant configuration values are present.

        Returns
        -------
        None
            This method updates environment variables and system locale settings
            in place. It does not return a value.
        """
        # Retrieve timezone and locale from configuration
        tz: str | None = self.config("app.timezone")  # NOSONAR
        lc: str | None = self.config("app.locale")  # NOSONAR

        # Return early if neither timezone nor locale is configured
        if not tz and not lc:
            return

        # Load local date-time configuration for the application
        DateTime._loadConfig(timezone_name=tz, locale=lc)

        # Update environment variables only for values that are set
        if tz:
            os.environ["TZ"] = tz
        if lc:
            os.environ["LC_ALL"] = lc
            os.environ["LANG"] = lc

        # Set system timezone if supported by the platform
        if tz and hasattr(time, "tzset"):
            time.tzset()

        # Set system locale if configured and valid
        if lc:
            with suppress(locale.Error):
                locale.setlocale(locale.LC_ALL, lc)

    def __load(self) -> None:
        """
        Load and initialize application configuration and service providers.

        Ensures the bootstrap configuration is initialized, sets up default
        paths, loads the final application configuration, loads service
        providers, saves the configuration to cache, and locks the configuration.
        Registers and boots all service providers.

        Returns
        -------
        None
            This method modifies internal state and does not return a value.
        """
        # Skip loading if already cached
        if not self.__is_compiled:

            # Ensure bootstrap configuration is initialized
            self.__ensureDefaultBootstrap()

            # Ensure default application paths are set
            self.__ensureDefaultPaths()

            # Load the final application configuration
            self.__loadConfig()

            # Load all service providers
            self.__loadProviders()

            # Save configuration to cache if enabled
            self.__persistCompiledState()

            # Lock and commit the configuration
            self.__commitConfig()

        # Register and boot all service providers
        self.__resolveEagerProvider()

    def create(self) -> Self:
        """
        Bootstrap and initialize the application framework.

        Register the application instance, load all configurations, set timezone
        and locale, and mark the application as booted.

        Returns
        -------
        Self
            The current Application instance for method chaining.
        """
        # Prevent duplicate initialization if already booted
        if not self.__booted:

            # Store the file path where the application was started.
            try:
                self.__entry_point = sys._getframe(1).f_code.co_filename
            except AttributeError:
                self.__entry_point = inspect.stack(context=0)[1].filename

            # Register application instance in the container
            self.instance(IApplication, self, alias="x-orionis-IApplication")

            # Load and initialize all application components
            self.__load()

            # Set timezone and locale based on configuration
            self.__setTimezoneAndLocale()

            # Set deferred providers for resolution during provider booting
            providers: dict = self.__bootstrap.get("providers", {})
            self._deferred_providers = providers.get("deferred", {})

            # Pre-compute and cache frequently accessed environment flags
            self.__is_production_cache = "prod" in str(self.config("app.env") or "")
            self.__is_debug_cache = self.config("app.debug") is True

            # Store the HTTP policy used throughout this worker's lifetime.
            monitoring = self.config("http.monitor_disconnects")
            if monitoring is not None and not isinstance(monitoring, bool):
                error_msg = "http.monitor_disconnects must be a bool."
                raise TypeError(error_msg)
            self.__http_disconnect_monitoring = monitoring is True

            # Mark configuration and provider registration as complete.
            self.__booted = True

        # Return the application instance for method chaining
        return self

    # --- Runtime Configuration Access Methods ---

    def config(
        self,
        key: str | None = None,
        value: object = _SENTINEL,
    ) -> object:
        """
        Get or set an application configuration value.

        Parameters
        ----------
        key : str or None, optional
            Dot-notated key specifying the configuration value to get or set.
            If None and value is not provided, returns the entire configuration.
        value : object, optional
            Value to set at the specified key. If not provided, retrieves the value.

        Returns
        -------
        object
            The configuration value for the given key, or the entire configuration
            if no key is provided. If setting a value, returns the value set.

        Raises
        ------
        RuntimeError
            If the application configuration is not initialized.
        TypeError
            If the configuration key is not a string.
        """
        # Ensure configuration is initialized before accessing or modifying it
        if not self.__configured:
            raise RuntimeError(_ERR_NOT_CONFIGURED)

        # Initialize runtime configuration from bootstrap on first access
        if not self.__runtime_config_initialized:
            self.resetRuntimeConfig()

        # Return the entire configuration if no key or value is provided
        if key is None and value is _SENTINEL:
            return self.__runtime_config

        # Ensure the key is a string
        if not isinstance(key, str):
            error_msg = "Configuration key must be a string."
            raise TypeError(error_msg)

        # Store parsed paths for subsequent configuration lookups.
        key_cache = self.__config_key_parts
        key_parts = key_cache.get(key)
        if key_parts is None:
            key_parts = tuple(key.split("."))
            if len(key_cache) >= _CONFIG_KEY_CACHE_SIZE:
                key_cache.clear()
            key_cache[key] = key_parts

        # If value is not provided, retrieve the configuration value
        if value is _SENTINEL:
            return self.__getRuntimeConfigValue(key_parts)

        # Otherwise, set the configuration value and return it
        return self.__setRuntimeConfigValue(key_parts, value)

    def resetRuntimeConfig(self) -> bool:
        """
        Reset the runtime configuration to a mutable copy of the bootstrap config.

        Resets the application's runtime configuration to a mutable and isolated
        copy of the bootstrap configuration. The application remains booted
        and subsequent accesses use the restored runtime values.

        Returns
        -------
        bool
            True if the configuration was reset successfully.
        """
        # Obtain current bootstrap configuration for runtime use
        bootstrap_config: dict = self.__bootstrap.get("config", {})

        # Recreate mutable containers from the frozen bootstrap configuration.
        self.__runtime_config = FreezeThaw.thaw(bootstrap_config)

        # Mark runtime configuration as ready for access
        self.__runtime_config_initialized = True

        # Indicate successful reset
        return True

    def __getRuntimeConfigValue(
        self,
        key_parts: tuple[str, ...],
    ) -> object:
        """
        Retrieve a value from a nested dictionary using dot notation.

        Parameters
        ----------
        key_parts : tuple[str, ...]
            Keys representing the path in the nested dictionary.

        Returns
        -------
        object
            The value found at the nested key path, or None if not found.
        """
        cfg: object = self.__runtime_config
        for part in key_parts:
            # Traverse nested dictionaries using the provided key parts
            if not isinstance(cfg, dict):
                return None
            cfg = cfg.get(part)
        return cfg

    def __setRuntimeConfigValue(
        self,
        key_parts: tuple[str, ...],
        value: object,
    ) -> object:
        """
        Set a value in a nested dictionary using dot notation.

        Parameters
        ----------
        key_parts : tuple[str, ...]
            Keys representing the path in the nested dictionary.
        value : object
            The value to set at the specified nested key path.

        Returns
        -------
        object
            The value that was set.
        """
        # Traverse the nested dictionary structure, creating intermediate
        # dictionaries as needed, and set the value at the specified path.
        current = self.__runtime_config
        parts = iter(key_parts)
        part = next(parts)
        for next_part in parts:
            child = current.get(part)
            if not isinstance(child, dict):
                child = {}
                current[part] = child
            current = child
            part = next_part
        current[part] = value
        return value

    # --- Application Path Access Method ---

    def path(
        self,
        key: str | None = None,
    ) -> Path | Mapping[str, Path] | None:
        """
        Retrieve an application path by key or return all paths.

        Parameters
        ----------
        key : str | None, optional
            The key for the desired path. If None, returns all paths.

        Returns
        -------
        Path | Mapping[str, Path] | None
            The resolved path for the given key, all paths as a read-only
            mapping, or None if the key does not exist.

        Raises
        ------
        RuntimeError
            If the application configuration is not initialized.
        TypeError
            If the key is not a string.
        """
        # Ensure configuration is initialized before accessing paths
        if not self.__configured:
            raise RuntimeError(_ERR_NOT_CONFIGURED)

        # Retrieve the paths configuration from bootstrap
        paths: dict = self.__bootstrap.get("paths", {})

        # Return all paths if no key is provided
        if key is None:
            return paths

        # Validate key type
        if not isinstance(key, str):
            error_msg = (
                "Key must be a string. Use path() without arguments to get all paths."
            )
            raise TypeError(error_msg)

        # Return the requested path or None if not found
        return paths.get(key)

    def routingPaths(
        self,
        key: str | None = None,
    ) -> list[Path] | dict | None:
        """
        Retrieve routing file paths from configuration.

        Only 'api', 'web', and 'console' routing types are supported.
        The health-check route is exposed through the ``routeHealthCheck``
        property and is not accessible via this method.

        Parameters
        ----------
        key : str | None, optional
            Routing type to retrieve: 'api', 'web', or 'console'.
            If None, returns the complete routing configuration dictionary.

        Returns
        -------
        list[Path] | dict | None
            List of Path objects for the specified routing type, the complete
            routing configuration dictionary if no key is provided, or None
            if the key is not one of the valid routing types.

        Raises
        ------
        RuntimeError
            If the application configuration is not initialized.
        TypeError
            If the key is not a string or None.
        """
        # Ensure configuration is initialized before accessing routing
        if not self.__configured:
            error_msg = (
                "Application configuration is not initialized. "
                "Please call create() before accessing routing paths."
            )
            raise RuntimeError(error_msg)

        # Validate key type if provided
        if key is not None and not isinstance(key, str):
            error_msg = (
                f"Routing key must be a string or None. Got {type(key).__name__}"
            )
            raise TypeError(error_msg)

        # Retrieve the routing configuration from bootstrap
        routing: dict = self.__bootstrap.get("routing", {})

        # Return complete routing configuration if no key specified
        if key is None:
            return FreezeThaw.thaw(routing)

        # Validate key exists in valid routing types
        if key not in {"api", "web", "console"}:
            return None

        # Thaw before returning: freeze converts lists→tuples; callers expect list[Path]
        return FreezeThaw.thaw(routing.get(key))

    # --- Environment Check Methods ---

    def isProduction(self) -> bool:
        """
        Determine if the application is running in a production environment.

        Checks the 'app.env' configuration value to see if it contains 'prod'.
        This is useful for toggling production-specific features.

        Returns
        -------
        bool
            True if the application environment contains 'prod', otherwise False.

        Raises
        ------
        RuntimeError
            If the application configuration is not initialized.
        """
        # Guard against access before application bootstrap is complete
        if not self.__booted:
            raise RuntimeError(_ERR_NOT_CONFIGURED)
        # Return pre-computed production environment flag cached at boot time
        return self.__is_production_cache

    def isDebug(self) -> bool:
        """
        Determine if the application is running in debug mode.

        Returns
        -------
        bool
            True if debug mode is enabled in the configuration, otherwise False.

        Raises
        ------
        RuntimeError
            If the application configuration is not initialized.
        """
        # Guard against access before application bootstrap is complete
        if not self.__booted:
            raise RuntimeError(_ERR_NOT_CONFIGURED)
        # Return pre-computed debug mode flag cached at boot time
        return self.__is_debug_cache

    def underMaintenance(self) -> bool:
        """
        Determine if the application is currently in maintenance mode.

        Returns
        -------
        bool
            True if the application is in maintenance mode, otherwise False.

        Raises
        ------
        RuntimeError
            If the application configuration is not initialized.
        """
        # Guard against access before application bootstrap is complete
        if not self.__booted:
            raise RuntimeError(_ERR_NOT_CONFIGURED)

        # Return the maintenance mode flag from the configuration
        return self.config("app.maintenance") is True
