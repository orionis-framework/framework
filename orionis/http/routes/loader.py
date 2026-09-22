import importlib
from typing import TYPE_CHECKING

from orionis.cache.file_based_cache import FileBasedCache
from orionis.foundation.contracts.application import IApplication
from orionis.http.routes.contracts.loader import IRouteLoader
from orionis.http.routes.contracts.router import IRouter
from orionis.http.routes.route_cache import RouteCache
from orionis.http.routes.route_compiler import RouteCompiler

if TYPE_CHECKING:
    from pathlib import Path

    from orionis.cache.contracts.file_based_cache import IFileBasedCache
    from orionis.http.layer.contracts.middleware import IBaseMiddleware

class RouteLoader(IRouteLoader):

    # ruff: noqa: TC001, SLF001

    # Keep a deterministic import order so route registration is stable.
    _KINDS: tuple[str, ...] = ("web", "api")

    def __init__(
        self,
        app: IApplication,
        router: IRouter,
        compiler: RouteCompiler,
        cache: RouteCache,
    ) -> None:
        """
        Initialise the RouteLoader with its required collaborators.

        Parameters
        ----------
        app : IApplication
            Application instance used to resolve paths and settings.
        router : IRouter
            Router that holds the raw registered routes.
        compiler : RouteCompiler
            Compiler that converts raw routes to ``CompiledRoute`` objects.
        cache : RouteCache
            Serialiser/deserialiser for the compiled route cache.

        Returns
        -------
        None
            The instance is initialised; no value is returned.
        """
        self.__router = router
        self.__app = app
        self.__app_middleware: list[type[IBaseMiddleware]] = app.getMiddleware()
        self.__routes: dict[str, dict] = {}
        self.__loaded = False
        self.__fallback: tuple | None = None
        self.__use_cache = False
        self.__persistence: IFileBasedCache | None = self.__getCachePersistence()
        self.__compiler = compiler
        self.__cache = cache

    def load(self) -> dict[str, dict]:
        """
        Return all compiled routes, loading them first if necessary.

        Returns
        -------
        dict[str, dict]
            Mapping of HTTP method to a dict with keys ``'static'``
            (``{path: CompiledRoute}``) and ``'dynamic'``
            (``[CompiledRoute, ...]``).
        """
        self.__loadRoutes()
        return self.__routes

    @property
    def fallback(self) -> tuple | None:
        """
        Return the registered fallback handler, if any.

        The fallback is used when no route matches the incoming request.
        Accessing this property triggers route loading if it has not
        already occurred.

        Returns
        -------
        tuple | None
            ``(class, method_name)`` for controller-based fallbacks,
            ``(None, callable)`` for callable-based fallbacks, or
            ``None`` if no fallback has been registered.
        """
        self.__loadRoutes()
        return self.__fallback

    def __getCachePersistence(self) -> IFileBasedCache | None:
        """
        Build the cache persistence handle for compiled routes.

        Returns
        -------
        IFileBasedCache | None
            A ``FileBasedCache`` instance when the application has a
            compiled cache directory configured, ``None`` otherwise.
        """
        compiled = self.__app.compiled
        if not compiled:
            return None
        self.__use_cache = True
        return FileBasedCache(
            path=self.__app.compiledPath,
            filename="routes",
            monitored_dirs=self.__app.compiledInvalidationPathsDirs,
            monitored_files=self.__app.compiledInvalidationPathsFiles,
        )

    def __importFluentRoutes(self, kind: str) -> None:
        """
        Import a route file by kind so its fluent registrations run.

        Parameters
        ----------
        kind : str
            Route group kind, e.g. ``'web'`` or ``'api'``.

        Returns
        -------
        None
            Imports the module as a side-effect; no value is returned.
        """
        routes_path: list[Path] | Path = self.__app.routingPaths(kind)
        if not routes_path:
            return
        routes_path = (
            routes_path if isinstance(routes_path, list) else [routes_path]
        )
        app_root: Path = self.__app.path("root")
        for route_file in routes_path:
            relative_path = route_file.relative_to(app_root)
            full_module_path = ".".join(relative_path.with_suffix("").parts)
            importlib.import_module(full_module_path)

    def __loadRoutes(self) -> None:
        """
        Load compiled routes, using the persistent cache when available.

        On a cache hit the routes and fallback are deserialised directly.
        On a cache miss all route files are imported (which registers
        routes in the router), the compiler builds ``CompiledRoute``
        objects, and the result is persisted for subsequent requests.

        Returns
        -------
        None
            Populates ``self.__routes`` and ``self.__fallback`` in place;
            no value is returned.
        """
        if self.__loaded:
            return

        # ── Cache hit ────────────────────────────────────────────────────────
        if self.__use_cache and self.__persistence:
            cached = self.__persistence.get()
            if cached and cached.get("version") == RouteCache.VERSION:
                self.__routes, self.__fallback = self.__cache.fromCache(cached)
                self.__loaded = True
                return

        # ── Cache miss: import → compile → persist ───────────────────────────
        try:
            for kind in self._KINDS:
                self.__router._setKind(kind)
                self.__importFluentRoutes(kind)
        finally:
            self.__router._setKind("web")

        exported = self.__router.export()
        self.__routes, self.__fallback = self.__compiler.compile(
            exported.get("routes", []),
            exported.get("fallback", None),
            self.__app_middleware,
        )

        if self.__use_cache and self.__persistence:
            self.__persistence.save(
                self.__cache.toCache(self.__routes, self.__fallback),
            )
        self.__loaded = True
