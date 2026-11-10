"""Define application configuration, lifecycle and runtime entry points."""

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Self
from orionis.container.contracts.container import IContainer

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable, Mapping
    from pathlib import Path
    from orionis.console.base.contracts.scheduler import IBaseScheduler
    from orionis.container.contracts.service_provider import IServiceProvider
    from orionis.failure.contracts.handler import IBaseExceptionHandler
    from orionis.foundation.enums.lifespan import Lifespan
    from orionis.foundation.enums.runtimes import Runtime
    from orionis.http.layer.contracts.middleware import IBaseMiddleware

_SENTINEL = object()
"""Sentinel distinguishing sentinel from ordinary values."""

class IApplication(IContainer, ABC):
    """Define application configuration, lifecycle and runtime entry points."""

    __slots__ = ()
    """Declare that this class introduces no additional instance slots."""

    @property
    @abstractmethod
    def isBooted(self: Self) -> bool:
        """
        Report whether configuration and eager registration are complete.

        Returns
        -------
        bool
            ``True`` after ``create()`` completes, independently of asynchronous
            provider startup and HTTP kernel readiness.
        """

    @property
    @abstractmethod
    def isCreated(self: Self) -> bool:
        """
        Report the configuration-stage state exposed by ``isBooted``.

        Returns
        -------
        bool
            Legacy creation flag, identical to ``isBooted``.
        """

    @property
    @abstractmethod
    def areProvidersBooted(self: Self) -> bool:
        """
        Check whether all eager providers have finished booting.

        Returns
        -------
        bool
            ``True`` after creation and eager startup. Deferred providers
            still boot on first resolution.
        """

    @property
    @abstractmethod
    def isHttpReady(self: Self) -> bool:
        """
        Check whether eager providers and both HTTP handlers are ready.

        Returns
        -------
        bool
            ``True`` after eager startup and handler publication; this does not
            indicate listening sockets or deployment health.
        """

    @property
    @abstractmethod
    def startAt(self: Self) -> int:
        """
        Return the instance initialization timestamp in Unix nanoseconds.

        Returns
        -------
        int
            Time recorded when this singleton was first initialized.
        """

    @property
    @abstractmethod
    def routeHealthCheck(self: Self) -> str:
        """
        Return the configured health-check URL path.

        Returns
        -------
        str
            Health-check path, or ``"/up"`` when no nonempty path is configured.
        """

    @property
    @abstractmethod
    def entryPoint(self: Self) -> str | None:
        """
        Return the creation entry point as a module path with an app suffix.

        Returns
        -------
        str | None
            Inferred ``module:app`` path, or ``None`` before creation records
            the caller's filename.
        """

    @property
    @abstractmethod
    def basePath(self: Self) -> Path:
        """
        Return the resolved application root directory.

        Returns
        -------
        pathlib.Path
            Absolute root selected when this singleton was first initialized.
        """

    @property
    @abstractmethod
    def compiled(self: Self) -> bool:
        """
        Check whether compiled bootstrap caching is enabled.

        Returns
        -------
        bool
            ``True`` when compiled caching is enabled, even before a cache hit.
        """

    @property
    @abstractmethod
    def compiledPath(self: Self) -> Path | None:
        """
        Return the configured bootstrap cache directory.

        Returns
        -------
        pathlib.Path or None
            Resolved cache directory, or ``None`` before caching is configured.
        """

    @property
    @abstractmethod
    def compiledInvalidationPathsDirs(self: Self) -> list[Path]:
        """
        Return configured directories used for bootstrap cache invalidation.

        Returns
        -------
        list of pathlib.Path
            Configured directory invalidation paths as a new list.
        """

    @property
    @abstractmethod
    def compiledInvalidationPathsFiles(self: Self) -> list[Path]:
        """
        Return configured files used for bootstrap cache invalidation.

        Returns
        -------
        list of pathlib.Path
            Configured file invalidation paths as a new list.
        """

    @abstractmethod
    def compile(
        self: Self,
        path: str | None = None,
        invalidation_paths: list[str] | None = None,
    ) -> None:
        """
        Configure bootstrap caching and restore any valid compiled state.

        Parameters
        ----------
        path : str | None, optional
            Cache directory, defaulting to the application's framework cache path.
        invalidation_paths : list[str] | None, optional
            Existing files or directories monitored relative to the application
            root, or ``None`` for no additional invalidation paths.

        Returns
        -------
        None
            Configure the cache and commit a valid restored snapshot, if present.

        Notes
        -----
        Core application path definitions are always monitored so framework
        updates invalidate outdated snapshots. Configuration setters leave
        restored snapshots unchanged.
        """

    @abstractmethod
    def on(
        self: Self,
        lifespan: Lifespan,
        *callbacks: Callable[..., Any] | Callable[..., Awaitable[Any]],
        runtime: Runtime | None = None,
    ) -> Self:
        """
        Register unique callbacks for a runtime's startup or shutdown event.

        Parameters
        ----------
        lifespan : orionis.foundation.enums.lifespan.Lifespan
            Lifecycle event that triggers the callbacks.
        *callbacks : collections.abc.Callable
            Synchronous or asynchronous callbacks invoked through the container.
        runtime : orionis.foundation.enums.runtimes.Runtime or None, optional
            Target runtime, or ``None`` for callbacks shared by HTTP and CLI.

        Returns
        -------
        typing.Self
            This application for method chaining.

        Raises
        ------
        TypeError
            If ``lifespan`` is not a ``Lifespan`` or a callback is not callable.
        ValueError
            If no callbacks are provided.

        Notes
        -----
        Callbacks are deduplicated in sets; execution order is unspecified.
        """

    @abstractmethod
    def withMiddleware(
        self: Self,
        *middleware: type[IBaseMiddleware],
    ) -> Self:
        """
        Register unique middleware classes in application execution order.

        Parameters
        ----------
        *middleware : type[IBaseMiddleware]
            Middleware classes implementing ``IBaseMiddleware``.

        Returns
        -------
        typing.Self
            This application for method chaining.

        Raises
        ------
        TypeError
            If an argument is not a middleware class.
        RuntimeError
            If bootstrap configuration is locked.
        """

    @abstractmethod
    def getMiddleware(self: Self) -> list[type[IBaseMiddleware]]:
        """
        Resolve registered middleware classes in application execution order.

        Returns
        -------
        list[type[orionis.http.layer.contracts.middleware.IBaseMiddleware]]
            Registered classes in order, or an empty list when none are stored.
        """

    @abstractmethod
    def withProviders(
        self: Self,
        *providers: type[IServiceProvider],
    ) -> Self:
        """
        Register eager or deferred service provider classes for bootstrap.

        Parameters
        ----------
        *providers : type[IServiceProvider]
            Provider classes implementing ``IServiceProvider``.

        Returns
        -------
        typing.Self
            This application for method chaining.

        Raises
        ------
        TypeError
            If a provider class or deferred service identifier is invalid.
        RuntimeError
            If bootstrap configuration is locked.
        """

    @abstractmethod
    def withRouting(  # noqa: PLR0913
        self: Self,
        api: str | list[str] | None = None,
        web: str | list[str] | None = None,
        console: str | list[str] | None = None,
        health: str | None = None,
        ai: str | list[str] | None = None,
        *,
        websocket: str | list[str] | None = None,
    ) -> Self:
        """
        Configure route files and the health-check path for each protocol.

        Parameters
        ----------
        api : str | list[str] | None, optional
            API route files relative to the application root, or ``None``.
        web : str | list[str] | None, optional
            Web route files relative to the application root, or ``None``.
        console : str | list[str] | None, optional
            CLI route files relative to the application root, or ``None``.
        health : str | None, optional
            Health-check URL path, or ``None`` to use ``"/up"``.
        ai : str | list[str] | None, optional
            MCP registration files loaded before HTTP or CLI startup.
        websocket : str | list[str] | None, optional
            WebSocket and Hub route files using the web middleware profile.

        Returns
        -------
        typing.Self
            This application for method chaining.

        Raises
        ------
        TypeError
            If an argument has an invalid type or a route file lacks valid imports.
        FileNotFoundError
            If a route file is missing outside an active recovery context.
        RuntimeError
            If bootstrap configuration is locked.
        """

    @abstractmethod
    def withExceptionHandler(
        self: Self,
        handler: type[IBaseExceptionHandler],
    ) -> Self:
        """
        Set the exception handler class used for lazy singleton resolution.

        Parameters
        ----------
        handler : type[orionis.failure.contracts.handler.IBaseExceptionHandler]
            Handler class implementing ``IBaseExceptionHandler``.

        Returns
        -------
        typing.Self
            This application for method chaining.

        Raises
        ------
        TypeError
            If ``handler`` is not a class implementing the handler contract.
        RuntimeError
            If bootstrap configuration is locked.
        """

    @abstractmethod
    async def getExceptionHandler(
        self: Self,
    ) -> IBaseExceptionHandler:
        """
        Resolve and cache the configured exception handler instance.

        Construct shared dependencies outside request and operation scopes.

        Returns
        -------
        orionis.failure.contracts.handler.IBaseExceptionHandler
            Shared handler instance, using the core default when not overridden.

        Raises
        ------
        RuntimeError
            If application creation has not completed.
        """

    @abstractmethod
    def withScheduler(
        self: Self,
        scheduler: type[IBaseScheduler],
    ) -> Self:
        """
        Set the scheduler class built by ``getScheduler``.

        Parameters
        ----------
        scheduler : type[orionis.console.base.contracts.scheduler.IBaseScheduler]
            Scheduler class implementing ``IBaseScheduler``.

        Returns
        -------
        typing.Self
            This application for method chaining.

        Raises
        ------
        RuntimeError
            If bootstrap configuration is locked.
        TypeError
            If ``scheduler`` is not a class implementing ``IBaseScheduler``.
        """

    @abstractmethod
    async def getScheduler(
        self: Self,
    ) -> IBaseScheduler:
        """
        Resolve the scheduler class and build its instance.

        Returns
        -------
        orionis.console.base.contracts.scheduler.IBaseScheduler
            Instance built from the cached configured scheduler class.

        Raises
        ------
        RuntimeError
            If application creation has not completed.
        """

    @abstractmethod
    def withConfigApp(
        self: Self,
        **app_config: object,
    ) -> Self:
        """
        Set application configuration overrides for bootstrap.

        Parameters
        ----------
        **app_config : object
            Field values for the ``app`` configuration section.

        Returns
        -------
        typing.Self
            This application for method chaining.

        Raises
        ------
        RuntimeError
            If bootstrap configuration is locked.
        """

    @abstractmethod
    def withConfigMcp(self: Self, **mcp_config: object) -> Self:
        """
        Set MCP protocol limits and allowed origins for bootstrap.

        Parameters
        ----------
        **mcp_config : object
            MCP configuration fields, including limits and the Origin allowlist.

        Returns
        -------
        typing.Self
            This application for method chaining.

        Raises
        ------
        RuntimeError
            If bootstrap configuration is locked.
        """

    @abstractmethod
    def withConfigAuth(
        self: Self,
        **auth_config: object,
    ) -> Self:
        """
        Set authentication configuration overrides for bootstrap.

        Parameters
        ----------
        **auth_config : object
            Field values for the ``auth`` configuration section.

        Returns
        -------
        typing.Self
            This application for method chaining.

        Raises
        ------
        RuntimeError
            If bootstrap configuration is locked.
        """

    @abstractmethod
    def withConfigCache(
        self: Self,
        **cache_config: object,
    ) -> Self:
        """
        Set cache configuration overrides for bootstrap.

        Parameters
        ----------
        **cache_config : object
            Field values for the ``cache`` configuration section.

        Returns
        -------
        typing.Self
            This application for method chaining.

        Raises
        ------
        RuntimeError
            If bootstrap configuration is locked.
        """

    @abstractmethod
    def withConfigHttp(
        self: Self,
        **http_config: object,
    ) -> Self:
        """
        Set HTTP configuration overrides for bootstrap.

        Parameters
        ----------
        **http_config : object
            Field values for the ``http`` configuration section.

        Returns
        -------
        typing.Self
            This application for method chaining.

        Raises
        ------
        RuntimeError
            If bootstrap configuration is locked.
        """

    @abstractmethod
    def withConfigDatabase(
        self: Self,
        **database_config: object,
    ) -> Self:
        """
        Set database configuration overrides for bootstrap.

        Parameters
        ----------
        **database_config : object
            Field values for the ``database`` configuration section.

        Returns
        -------
        typing.Self
            This application for method chaining.

        Raises
        ------
        RuntimeError
            If bootstrap configuration is locked.
        """

    @abstractmethod
    def withConfigFilesystems(
        self: Self,
        **filesystems_config: object,
    ) -> Self:
        """
        Set filesystem configuration overrides for bootstrap.

        Parameters
        ----------
        **filesystems_config : object
            Field values for the ``filesystems`` configuration section.

        Returns
        -------
        typing.Self
            This application for method chaining.

        Raises
        ------
        RuntimeError
            If bootstrap configuration is locked.
        """

    @abstractmethod
    def withConfigLogging(
        self: Self,
        **logging_config: object,
    ) -> Self:
        """
        Set logging configuration overrides for bootstrap.

        Parameters
        ----------
        **logging_config : object
            Field values for the ``logging`` configuration section.

        Returns
        -------
        typing.Self
            This application for method chaining.

        Raises
        ------
        RuntimeError
            If bootstrap configuration is locked.
        """

    @abstractmethod
    def withConfigMail(
        self: Self,
        **mail_config: object,
    ) -> Self:
        """
        Set mail configuration overrides for bootstrap.

        Parameters
        ----------
        **mail_config : object
            Field values for the ``mail`` configuration section.

        Returns
        -------
        typing.Self
            This application for method chaining.

        Raises
        ------
        RuntimeError
            If bootstrap configuration is locked.
        """

    @abstractmethod
    def withConfigQueue(
        self: Self,
        **queue_config: object,
    ) -> Self:
        """
        Set queue configuration overrides for bootstrap.

        Parameters
        ----------
        **queue_config : object
            Field values for the ``queue`` configuration section.

        Returns
        -------
        typing.Self
            This application for method chaining.

        Raises
        ------
        RuntimeError
            If bootstrap configuration is locked.
        """

    @abstractmethod
    def withConfigSession(
        self: Self,
        **session_config: object,
    ) -> Self:
        """
        Set session configuration overrides for bootstrap.

        Parameters
        ----------
        **session_config : object
            Field values for the ``session`` configuration section.

        Returns
        -------
        typing.Self
            This application for method chaining.

        Raises
        ------
        RuntimeError
            If bootstrap configuration is locked.
        """

    @abstractmethod
    def withConfigTesting(
        self: Self,
        **testing_config: object,
    ) -> Self:
        """
        Set testing configuration overrides for bootstrap.

        Parameters
        ----------
        **testing_config : object
            Field values for the ``testing`` configuration section.

        Returns
        -------
        typing.Self
            This application for method chaining.

        Raises
        ------
        RuntimeError
            If bootstrap configuration is locked.
        """

    @abstractmethod
    def withConfigPaths(
        self: Self,
        **paths: str | Path | None,
    ) -> Self:
        """
        Configure resolved application directories with core path overrides.

        Parameters
        ----------
        **paths : str | pathlib.Path | None
            Overrides keyed by core path names such as ``app_providers``,
            ``config``, and ``storage_framework``. Relative strings use the root;
            path objects use the working directory. ``None`` uses defaults.
            Unknown keys are ignored, and ``root`` remains ``basePath``.

        Returns
        -------
        typing.Self
            This application for method chaining.

        Raises
        ------
        RuntimeError
            If bootstrap configuration is locked.
        """

    @abstractmethod
    def create(self: Self) -> Self:
        """
        Create application configuration and register eager services once.

        Apply locale settings and cache runtime flags without awaiting
        asynchronous provider boots or preparing HTTP handlers.

        Returns
        -------
        typing.Self
            This application after configuration and registration complete.

        Raises
        ------
        TypeError
            If ``http.monitor_disconnects`` is neither a boolean nor ``None``.
        """

    @abstractmethod
    async def boot(self: Self) -> Self:
        """
        Create the application and start eager providers for headless use.

        Coordinate repeated calls and acquire headless reporting ownership.
        Leave HTTP and CLI kernels and lifecycle callbacks to their runtimes.

        Returns
        -------
        typing.Self
            This application after all eager providers finish booting.

        Raises
        ------
        Exception
            If creation, provider boot, or reporting startup fails. Unfinished
            providers remain pending for a later retry.
        """

    async def aclose(self: Self) -> None:
        """
        Close a headless lifetime when the implementation owns one.

        Keep the default implementation as a no-op for custom applications
        that do not manage headless reporting ownership.

        Returns
        -------
        None
            Release owned resources in overrides; do nothing in the default method.
        """

    @abstractmethod
    async def handleCommand(
        self: Self,
        args: list[str] | None = None,
    ) -> int:
        """
        Run a CLI command within its startup and shutdown lifecycle.

        Parameters
        ----------
        args : list of str or None, optional
            Command arguments, or ``None`` to pass an empty argument list.

        Returns
        -------
        int
            Exit code returned by the CLI kernel.

        Raises
        ------
        RuntimeError
            If no CLI kernel is configured.
        TypeError
            If the configured kernel does not implement the CLI interface.
        """

    @abstractmethod
    def config(
        self: Self,
        key: str | None = None,
        value: object = _SENTINEL,
    ) -> object:
        """
        Read or update the mutable runtime configuration.

        Parameters
        ----------
        key : str or None, optional
            Dot-separated key, or ``None`` with no value to return all settings.
        value : object, optional
            Replacement value; omit to read the key. Explicit ``None`` is stored.

        Returns
        -------
        object
            Requested value, assigned value, or the full mutable mapping.
            Missing keys and non-dictionary parents return ``None`` on reads.

        Raises
        ------
        RuntimeError
            If the application configuration is not initialized.
        TypeError
            If a keyed read or write uses a non-string key.
        """

    @abstractmethod
    def resetRuntimeConfig(self: Self) -> bool:
        """
        Restore mutable runtime settings from the bootstrap configuration.

        Replace runtime containers with an isolated copy without changing
        creation or readiness flags.

        Returns
        -------
        bool
            ``True`` after the runtime mapping has been replaced.
        """

    @abstractmethod
    def path(
        self: Self,
        key: str | None = None,
    ) -> Path | Mapping[str, Path] | None:
        """
        Return one configured application path or the read-only path mapping.

        Parameters
        ----------
        key : str | None, optional
            Core path name, or ``None`` to return the complete path mapping.

        Returns
        -------
        pathlib.Path | collections.abc.Mapping[str, pathlib.Path] | None
            Resolved path, read-only mapping when omitted, or ``None`` for an
            unknown key.

        Raises
        ------
        RuntimeError
            If the application configuration is not initialized.
        TypeError
            If a supplied key is not a string.
        """

    @abstractmethod
    def routingPaths(
        self: Self,
        key: str | None = None,
    ) -> list[Path] | dict | None:
        """
        Return mutable copies of configured routing paths.

        Parameters
        ----------
        key : str | None, optional
            Routing type: ``api``, ``web``, ``console``, ``ai``, or ``websocket``.
            Use ``None`` to return the complete routing dictionary.

        Returns
        -------
        list[pathlib.Path] | dict | None
            Copied route list, full mutable routing dictionary, or ``None`` for
            an unsupported or unconfigured type. The full dictionary may also
            contain the health-check setting.

        Raises
        ------
        RuntimeError
            If the application configuration is not initialized.
        TypeError
            If a supplied key is neither a string nor ``None``.
        """

    @abstractmethod
    def isProduction(self: Self) -> bool:
        """
        Check the production flag cached during application creation.

        Returns
        -------
        bool
            ``True`` when the creation-time ``app.env`` string contains ``"prod"``.

        Raises
        ------
        RuntimeError
            If application creation has not completed.
        """

    @abstractmethod
    def isDebug(self: Self) -> bool:
        """
        Check the debug flag cached during application creation.

        Returns
        -------
        bool
            ``True`` only when the creation-time ``app.debug`` value is ``True``.

        Raises
        ------
        RuntimeError
            If application creation has not completed.
        """

    @abstractmethod
    def underMaintenance(self: Self) -> bool:
        """
        Check effective maintenance mode using a short-lived worker cache.

        Refresh the shared marker at most every 100 ms. Treat unreadable markers
        as maintenance mode; use configuration for missing or unrecognized values.

        Returns
        -------
        bool
            ``True`` when maintenance is enabled. Marker values ``"down"`` and
            ``"up"`` override ``app.maintenance``.

        Raises
        ------
        RuntimeError
            If application creation has not completed.
        """
