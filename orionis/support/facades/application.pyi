from collections.abc import Awaitable, Callable, Mapping
from contextlib import AbstractAsyncContextManager
from pathlib import Path
from typing import Any, Protocol, overload, Unpack
from orionis.console.base.contracts.scheduler import IBaseScheduler
from orionis.container.context.manager import ScopeManager
from orionis.container.contracts.service_provider import IServiceProvider
from orionis.container.facades.facade import Facade
from orionis.failure.contracts.handler import IBaseExceptionHandler
from orionis.foundation.config import options
from orionis.foundation.contracts.application import IApplication
from orionis.foundation.enums.lifespan import Lifespan
from orionis.foundation.enums.runtimes import Runtime
from orionis.http.layer.contracts.middleware import IBaseMiddleware

class _ScopeDispatch(
    Awaitable[ScopeManager],
    AbstractAsyncContextManager[ScopeManager, None],
    Protocol,
): ...

# The unpinned facade defers service reads and calls. Await resolve() for direct access.
class Application(Facade):

    @classmethod
    def getFacadeAccessor(cls) -> str: ...

    @classmethod
    async def resolve(cls, *args: object, **kwargs: object) -> IApplication: ...

    @classmethod
    def isBooted(cls) -> Awaitable[bool]: ...

    @classmethod
    def isCreated(cls) -> Awaitable[bool]: ...

    @classmethod
    def areProvidersBooted(cls) -> Awaitable[bool]: ...

    @classmethod
    def isHttpReady(cls) -> Awaitable[bool]: ...

    @classmethod
    def startAt(cls) -> Awaitable[int]: ...

    @classmethod
    def routeHealthCheck(cls) -> Awaitable[str]: ...

    @classmethod
    def entryPoint(cls) -> Awaitable[str | None]: ...

    @classmethod
    def basePath(cls) -> Awaitable[Path]: ...

    @classmethod
    def compiled(cls) -> Awaitable[bool]: ...

    @classmethod
    def compiledPath(cls) -> Awaitable[Path | None]: ...

    @classmethod
    def compiledInvalidationPathsDirs(cls) -> Awaitable[list[Path]]: ...

    @classmethod
    def compiledInvalidationPathsFiles(cls) -> Awaitable[list[Path]]: ...

    @classmethod
    def handleCommand(cls, args: list[str] | None = None) -> Awaitable[int]: ...

    @classmethod
    def current(cls) -> Awaitable[IApplication | None]: ...

    @classmethod
    def compile(
        cls,
        path: str | None = None,
        invalidation_paths: list[str] | None = None,
    ) -> Awaitable[None]: ...

    @classmethod
    def on(
        cls,
        lifespan: Lifespan,
        *callbacks: Callable[..., Any] | Callable[..., Awaitable[Any]],
        runtime: Runtime | None = None,
    ) -> Awaitable[IApplication]: ...

    @classmethod
    def withMiddleware(
        cls,
        *middleware: type[IBaseMiddleware],
    ) -> Awaitable[IApplication]: ...

    @classmethod
    def getMiddleware(cls) -> Awaitable[list[type[IBaseMiddleware]]]: ...

    @classmethod
    def withProviders(
        cls,
        *providers: type[IServiceProvider],
    ) -> Awaitable[IApplication]: ...

    @classmethod
    def withRouting(
        cls,
        api: str | list[str] | None = None,
        web: str | list[str] | None = None,
        console: str | list[str] | None = None,
        health: str | None = None,
        ai: str | list[str] | None = None,
        *,
        websocket: str | list[str] | None = None,
    ) -> Awaitable[IApplication]: ...

    @classmethod
    def withExceptionHandler(
        cls,
        handler: type[IBaseExceptionHandler],
    ) -> Awaitable[IApplication]: ...

    @classmethod
    def getExceptionHandler(cls) -> Awaitable[IBaseExceptionHandler]: ...

    @classmethod
    def withScheduler(
        cls,
        scheduler: type[IBaseScheduler],
    ) -> Awaitable[IApplication]: ...

    @classmethod
    def getScheduler(cls) -> Awaitable[IBaseScheduler]: ...

    @classmethod
    def withConfigApp(
        cls,
        **app_config: Unpack[options.AppOptions],
    ) -> Awaitable[IApplication]: ...

    @classmethod
    def withConfigAuth(
        cls,
        **auth_config: Unpack[options.AuthOptions],
    ) -> Awaitable[IApplication]: ...

    @classmethod
    def withConfigMcp(
        cls,
        **mcp_config: Unpack[options.McpOptions],
    ) -> Awaitable[IApplication]: ...

    @classmethod
    def withConfigCache(
        cls,
        **cache_config: Unpack[options.CacheOptions],
    ) -> Awaitable[IApplication]: ...

    @classmethod
    def withConfigHttp(
        cls,
        **http_config: Unpack[options.HttpOptions],
    ) -> Awaitable[IApplication]: ...

    @classmethod
    def withConfigDatabase(
        cls,
        **database_config: Unpack[options.DatabaseOptions],
    ) -> Awaitable[IApplication]: ...

    @classmethod
    def withConfigFilesystems(
        cls,
        **filesystems_config: Unpack[options.FilesystemsOptions],
    ) -> Awaitable[IApplication]: ...

    @classmethod
    def withConfigLogging(
        cls,
        **logging_config: Unpack[options.LoggingOptions],
    ) -> Awaitable[IApplication]: ...

    @classmethod
    def withConfigMail(
        cls,
        **mail_config: Unpack[options.MailOptions],
    ) -> Awaitable[IApplication]: ...

    @classmethod
    def withConfigQueue(
        cls,
        **queue_config: Unpack[options.QueueOptions],
    ) -> Awaitable[IApplication]: ...

    @classmethod
    def withConfigSession(
        cls,
        **session_config: Unpack[options.SessionOptions],
    ) -> Awaitable[IApplication]: ...

    @classmethod
    def withConfigTesting(
        cls,
        **testing_config: Unpack[options.TestingOptions],
    ) -> Awaitable[IApplication]: ...

    @classmethod
    def withConfigPaths(
        cls,
        **paths: Unpack[options.PathsOptions],
    ) -> Awaitable[IApplication]: ...

    @classmethod
    def create(cls) -> Awaitable[IApplication]: ...

    @classmethod
    def boot(cls) -> Awaitable[IApplication]: ...

    @classmethod
    def aclose(cls) -> Awaitable[None]: ...

    @overload
    @classmethod
    def config(cls, key: None = None) -> Awaitable[dict[str, object]]: ...

    @overload
    @classmethod
    def config(cls, key: str) -> Awaitable[object]: ...

    @overload
    @classmethod
    def config[T](cls, key: str, value: T) -> Awaitable[T]: ...

    @classmethod
    def resetRuntimeConfig(cls) -> Awaitable[bool]: ...

    @overload
    @classmethod
    def path(cls, key: None = None) -> Awaitable[Mapping[str, Path]]: ...

    @overload
    @classmethod
    def path(cls, key: options.CorePathName) -> Awaitable[Path]: ...

    @overload
    @classmethod
    def path(cls, key: str) -> Awaitable[Path | None]: ...

    @overload
    @classmethod
    def routingPaths(cls, key: None = None) -> Awaitable[options.RoutingPaths]: ...

    @overload
    @classmethod
    def routingPaths(cls, key: str) -> Awaitable[list[Path] | None]: ...

    @classmethod
    def isProduction(cls) -> Awaitable[bool]: ...

    @classmethod
    def isDebug(cls) -> Awaitable[bool]: ...

    @classmethod
    def underMaintenance(cls) -> Awaitable[bool]: ...

    @classmethod
    def instance(
        cls,
        abstract: type[Any] | None,
        instance: object,
        *,
        alias: str | None = None,
        override: bool = False,
    ) -> Awaitable[bool]: ...

    @classmethod
    def transient(
        cls,
        abstract: type[Any] | None,
        concrete: type[Any],
        *,
        alias: str | None = None,
        override: bool = False,
    ) -> Awaitable[bool]: ...

    @classmethod
    def singleton(
        cls,
        abstract: type[Any] | None,
        concrete: type[Any],
        *,
        alias: str | None = None,
        override: bool = False,
    ) -> Awaitable[bool]: ...

    @classmethod
    def scoped(
        cls,
        abstract: type[Any] | None,
        concrete: type[Any],
        *,
        alias: str | None = None,
        override: bool = False,
    ) -> Awaitable[bool]: ...

    @classmethod
    def bound(cls, key: type[Any] | str) -> Awaitable[bool]: ...

    @classmethod
    def beginScope(cls) -> _ScopeDispatch: ...

    @classmethod
    def getCurrentScope(cls) -> Awaitable[ScopeManager | None]: ...

    @overload
    @classmethod
    def make[T](
        cls,
        key: type[T],
        *args: object,
        **kwargs: object,
    ) -> Awaitable[T]: ...

    @overload
    @classmethod
    def make(
        cls,
        key: str,
        *args: object,
        **kwargs: object,
    ) -> Awaitable[Any]: ...

    @classmethod
    def build[T](
        cls,
        type_: type[T],
        *args: object,
        **kwargs: object,
    ) -> Awaitable[T]: ...

    @classmethod
    def invoke(
        cls,
        fn: Callable[..., Any],
        *args: object,
        **kwargs: object,
    ) -> Awaitable[Any]: ...

    @classmethod
    def call(
        cls,
        instance: object,
        method_name: str,
        *args: object,
        **kwargs: object,
    ) -> Awaitable[Any]: ...
