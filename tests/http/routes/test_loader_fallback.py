from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from orionis.cache.file_based_cache import FileBasedCache
from orionis.http.routes.exceptions.route_not_found import RouteNotFound
from orionis.http.routes.loader import RouteLoader
from orionis.http.routes.route_cache import RouteCache
from orionis.http.routes.route_compiler import RouteCompiler
from orionis.http.routes.router import Router
from orionis.support.facades.router import Route
from orionis.test import TestCase
from tests.http.routes.test_nested_routing import UserController, route_handler
from tests.http.test_kernel import boot_kernel, dispatch

class _LoaderApp:
    """Configure real route persistence and record route-import requests."""

    __slots__ = (
        "cache_only", "compiled", "compiledInvalidationPathsDirs",
        "compiledInvalidationPathsFiles", "compiledPath", "imports", "route_files",
    )

    @property
    def routeHealthCheck(self) -> str:
        """Return the default health route registered by the real router.

        Returns
        -------
        str
            Value produced by the helper.
        """
        return "/up"

    def __init__(
        self, path: Path, *, compiled: bool = True, cache_only: bool = False,
    ) -> None:
        """Configure an isolated directory and optional cache-hit guards.

        Parameters
        ----------
        path : Path
            Value supplied for ``path``.
        compiled : bool
            Value supplied for ``compiled``.
        cache_only : bool
            Value supplied for ``cache_only``.

        Returns
        -------
        None
            Completes the operation described above.
        """
        self.compiled = compiled
        self.compiledPath = path
        self.compiledInvalidationPathsDirs: list[Path] = []
        self.compiledInvalidationPathsFiles: list[Path] = []
        self.imports: list[str] = []
        self.cache_only = cache_only
        self.route_files: dict[str, list[Path]] = {}

    def getMiddleware(self) -> list[type]:
        """Return an empty application middleware stack.

        Returns
        -------
        list[type]
            Value produced by the helper.
        """
        return []

    def path(self, _key: str) -> Path:
        """Return the root containing this test's route modules.

        Parameters
        ----------
        _key : str
            Application directory requested by the loader.

        Returns
        -------
        Path
            Test-owned module root.
        """
        return self.compiledPath

    def routingPaths(self, kind: str) -> list[Path] | None:
        """Record cold imports and fail if a warm load requests route files.

        Parameters
        ----------
        kind : str
            Value supplied for ``kind``.

        Returns
        -------
        list[Path] | None
            Route files associated with the requested kind, when configured.

        Raises
        ------
        AssertionError
            Raised by this helper to exercise the failure path.
        """
        if self.cache_only:
            error_msg = "A cache hit must not import route files"
            raise AssertionError(error_msg)
        self.imports.append(kind)
        return self.route_files.get(kind)

class _CacheOnlyRouter(Router):
    """Use a real router while rejecting exports during a cache hit."""

    __slots__ = ()

    def export(self) -> dict:
        """Fail if cached routes are rebuilt from router registrations.

        Returns
        -------
        dict
            Value produced by the helper.

        Raises
        ------
        AssertionError
            Raised by this helper to exercise the failure path.
        """
        error_msg = "A cache hit must not export registered routes"
        raise AssertionError(error_msg)

class _IdentityOnlyMeta(type):
    """Reject equality checks against controller classes."""

    __hash__ = type.__hash__

    def __eq__(cls, _other: object) -> bool:
        """Fail if fallback normalization invokes controller equality.

        Parameters
        ----------
        _other : object
            Value supplied for ``_other``.

        Returns
        -------
        bool
            Value produced by the helper.

        Raises
        ------
        AssertionError
            Raised by this helper to exercise the failure path.
        """
        error_msg = "Fallback normalization must not compare controller classes"
        raise AssertionError(error_msg)

class _IdentityOnlyController(UserController, metaclass=_IdentityOnlyMeta):
    """Provide a valid invokable action with guarded metaclass equality."""

    __slots__ = ()

class TestLoaderFallbackPersistence(TestCase):
    """Keep fallback state consistent across real persistence boundaries."""

    async def testAbsentFallbackStaysNoneWithoutCacheAndAcrossColdWarmLoads(
        self,
    ) -> None:
        """Normalize absence once and preserve missing-route handling on reload.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        for compiled in (False, True):
            with TemporaryDirectory() as directory:
                path = Path(directory)
                app = _LoaderApp(path, compiled=compiled)
                router = Router(app)
                loader = RouteLoader(app, router, RouteCompiler(), RouteCache())
                routes = loader.load()
                self.assertEqual(router.export()["fallback"], (None, None))
                self.assertEqual(app.imports, ["web", "api", "websocket"])
                loaders = [loader]
                if compiled:
                    self.assertTrue((path / "routes").is_file())
                    saved = FileBasedCache(path, "routes").get()
                    self.assertIsNone(saved["fallback"])
                    warm_app = _LoaderApp(path, cache_only=True)
                    loaders.append(RouteLoader(
                        warm_app, _CacheOnlyRouter(warm_app),
                        RouteCompiler(), RouteCache(),
                    ))
                else:
                    self.assertFalse((path / "routes").exists())
                for current in loaders:
                    self.assertIsNone(current.fallback)
                    loaded = current.load()
                    self.assertIs(current.load(), loaded)
                    self.assertIsNone(current.fallback)
                    self.assertEqual(
                        loaded["GET"]["static"].keys(),
                        routes["GET"]["static"].keys(),
                    )
                    kernel, _, _, catch = await boot_kernel(
                        routes=loaded, fallback=current.fallback,
                    )
                    await dispatch(kernel, "/missing")
                    self.assertIsInstance(catch.handled[0], RouteNotFound)
                self.assertEqual(app.imports, ["web", "api", "websocket"])
                if compiled:
                    self.assertEqual(warm_app.imports, [])
                else:
                    guarded_app = _LoaderApp(path, compiled=False)
                    guarded_router = Router(guarded_app)
                    guarded_router.fallback(_IdentityOnlyController)
                    expected = guarded_router.export()["fallback"]
                    guarded = RouteLoader(
                        guarded_app, guarded_router, RouteCompiler(), RouteCache(),
                    )
                    self.assertIs(guarded.fallback, expected)
                    self.assertIs(guarded.fallback[0], _IdentityOnlyController)

    async def testRegisteredFallbackFormsKeepDescriptorsAndDispatchAfterReload(
        self,
    ) -> None:
        """Restore functions, invokable classes and controller pairs from disk.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        cases = (
            (route_handler, (None, route_handler)),
            (UserController, (UserController, "__call__")),
            ([UserController, "index"], (UserController, "index")),
            ((UserController, "index"), (UserController, "index")),
        )
        for action, expected in cases:
            with TemporaryDirectory() as directory:
                path = Path(directory)
                app = _LoaderApp(path)
                router = Router(app)
                router.fallback(action)
                cold = RouteLoader(app, router, RouteCompiler(), RouteCache())
                self.assertEqual(cold.fallback, expected)
                warm_app = _LoaderApp(path, cache_only=True)
                warm = RouteLoader(
                    warm_app, _CacheOnlyRouter(warm_app), RouteCompiler(), RouteCache(),
                )
                for loader in (cold, warm):
                    self.assertEqual(loader.fallback, expected)
                    routes = loader.load()
                    self.assertIs(loader.load(), routes)
                    self.assertEqual(loader.fallback, expected)
                    kernel, _, _, catch = await boot_kernel(
                        routes=routes, fallback=loader.fallback,
                    )
                    response = await dispatch(kernel, "/missing")
                    self.assertEqual(response.getStatusCode(), 200)
                    self.assertEqual(response.getBody(), b"routed")
                    self.assertEqual(catch.handled, [])
                self.assertEqual(app.imports, ["web", "api", "websocket"])
                self.assertEqual(warm_app.imports, [])

    def testStaleRouteCacheVersionRebuildsWithAnAbsentFallback(self) -> None:
        """Replace an old route snapshot and read the repaired file on a hit.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        with TemporaryDirectory() as directory:
            path = Path(directory)
            persistence = FileBasedCache(path, "routes")
            persistence.save({
                "version": RouteCache.VERSION - 1, "routes": {}, "fallback": None,
            })
            app = _LoaderApp(path)
            loader = RouteLoader(app, Router(app), RouteCompiler(), RouteCache())
            self.assertIsNone(loader.fallback)
            routes = loader.load()
            self.assertIs(loader.load(), routes)
            self.assertIn("/up", routes["GET"]["static"])
            self.assertEqual(app.imports, ["web", "api", "websocket"])
            saved = persistence.get()
            self.assertEqual(saved["version"], RouteCache.VERSION)
            self.assertIsNone(saved["fallback"])
            warm_app = _LoaderApp(path, cache_only=True)
            warm = RouteLoader(
                warm_app, _CacheOnlyRouter(warm_app), RouteCompiler(), RouteCache(),
            )
            self.assertIsNone(warm.fallback)
            self.assertIn("/up", warm.load()["GET"]["static"])
            self.assertEqual(warm_app.imports, [])

class TestDedicatedRouteFiles(TestCase):
    """Load protocol-specific route files through the real import path."""

    def setUp(self) -> None:
        """Install a test-owned route facade and importable temporary modules.

        Returns
        -------
        None
            Each route kind has its own module and registrations.
        """
        self._directory = TemporaryDirectory()
        root = Path(self._directory.name)
        self._app = _LoaderApp(root, compiled=False)
        self._router = Router(self._app)
        self._previous = Route._pinned_instance
        Route._pinned_instance = self._router
        self._module_names = []
        sys.path.insert(0, str(root))
        for kind in ("web", "api", "websocket"):
            module_name = "_orionis_audit_routes_" + kind
            self._module_names.append(module_name)
            route_file = root / (module_name + ".py")
            method = "websocket" if kind == "websocket" else "get"
            route_file.write_text(
                "from orionis.support.facades.router import Route\n"
                "from tests.http.routes.test_nested_routing import route_handler\n"
                f"Route.{method}('/{kind}', route_handler)\n",
                encoding="utf-8",
            )
            self._app.route_files[kind] = [route_file]

    def tearDown(self) -> None:
        """Restore facade and import state after discarding temporary modules.

        Returns
        -------
        None
            No route registrations or modules leak into other tests.
        """
        Route._pinned_instance = self._previous
        sys.path.remove(self._directory.name)
        for module_name in self._module_names:
            sys.modules.pop(module_name, None)
        self._directory.cleanup()

    def testDedicatedFilesPreserveProfilesAndLoadOnlyOnce(self) -> None:
        """Load WebSocket separately while retaining the web middleware profile.

        Returns
        -------
        None
            Three independent files register once in deterministic order.
        """
        loader = RouteLoader(self._app, self._router, RouteCompiler(), RouteCache())
        loaded = loader.load()
        self.assertIs(loader.load(), loaded)
        self.assertEqual(self._app.imports, ["web", "api", "websocket"])
        routes = {
            item["path"]: item for item in self._router.export()["routes"]
        }
        self.assertEqual(routes["/web"]["kind"], "web")
        self.assertEqual(routes["/api"]["kind"], "api")
        self.assertEqual(routes["/websocket"]["kind"], "web")
        self.assertEqual(routes["/websocket"]["protocol"], "websocket")
