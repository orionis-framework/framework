from __future__ import annotations
import json
from pathlib import Path
from types import SimpleNamespace
from typing import TYPE_CHECKING
from orionis.http.adapters.request.asgi import ASGITransportAdapter
from orionis.http.enums.interfaces import Interface
from orionis.http.kernel import _MiddlewarePipeline
from orionis.http.middleware import BaseMiddleware
from orionis.http.request import Request
from orionis.http.responses import Response
from orionis.http.routes import loader as loader_module
from orionis.http.routes import route_cache as cache_module
from orionis.http.routes.loader import RouteLoader
from orionis.http.routes.route_cache import RouteCache
from orionis.http.routes.route_compiler import RouteCompiler
from orionis.http.routes.route_resolver import RouteResolver
from orionis.test import TestCase
from tests.http.routes.test_nested_routing import (
    Namespace,
    OneMiddleware,
    TwoMiddleware,
    compile_router,
    make_router,
    route_handler,
)
from tests.http.test_kernel import boot_kernel, dispatch, make_asgi_scope
from tests.http.test_support import replace_attribute

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

class LoaderApplicationDouble:
    """Supply route-loading configuration and optional import failures."""

    def __init__(
        self,
        *,
        compiled: bool = False,
        import_error: Exception | None = None,
    ) -> None:
        """Store cache configuration and the requested import outcome.

        Parameters
        ----------
        compiled : bool
            Value supplied for ``compiled``.
        import_error : Exception | None
            Value supplied for ``import_error``.

        Returns
        -------
        None
            Completes the operation described above.
        """
        self.compiled = compiled
        self.import_error = import_error
        self.compiledPath = Path("compiled")
        self.compiledInvalidationPathsDirs: list[Path] = []
        self.compiledInvalidationPathsFiles: list[Path] = []

    def getMiddleware(self) -> list[type[BaseMiddleware]]:
        """Return the empty application middleware stack.

        Returns
        -------
        list[type[BaseMiddleware]]
            No globally registered middleware.
        """
        return []

    def routingPaths(self, _kind: str) -> None:
        """Report no route modules or raise the configured import error.

        Parameters
        ----------
        _kind : str
            Value supplied for ``_kind``.

        Returns
        -------
        None
            Completes the operation described above.

        Raises
        ------
        Exception
            The import failure supplied by the test.
        """
        if self.import_error is not None:
            raise self.import_error

class LoaderRouterDouble:
    """Record route exports and changes to the registration kind."""

    def __init__(self, fallback: tuple | None = None) -> None:
        """Store the fallback and initialize call records.

        Parameters
        ----------
        fallback : tuple | None
            Value supplied for ``fallback``.

        Returns
        -------
        None
            Completes the operation described above.
        """
        self.fallback = fallback
        self.exports = 0
        self.kinds: list[str] = []

    def _setKind(self, kind: str) -> None:
        """Record the registration kind selected by the loader.

        Parameters
        ----------
        kind : str
            Value supplied for ``kind``.

        Returns
        -------
        None
            Completes the operation described above.
        """
        self.kinds.append(kind)

    def export(self) -> dict[str, object]:
        """Return an empty route table and count each export.

        Returns
        -------
        dict[str, object]
            Raw router output consumed by the production compiler.
        """
        self.exports += 1
        return {"routes": [], "fallback": self.fallback}

class RoutePersistenceDouble:
    """Record cache reads and saved compiled route snapshots."""

    def __init__(self, cached: dict[str, object]) -> None:
        """Store the cache snapshot and initialize read and write records.

        Parameters
        ----------
        cached : dict[str, object]
            Value supplied for ``cached``.

        Returns
        -------
        None
            Completes the operation described above.
        """
        self.cached = cached
        self.reads = 0
        self.saved: list[dict[str, object]] = []

    def get(self) -> dict[str, object]:
        """Return the configured cached snapshot and record the read.

        Returns
        -------
        dict[str, object]
            Route snapshot read by the loader.
        """
        self.reads += 1
        return self.cached

    def save(self, value: dict[str, object]) -> None:
        """Record a compiled route snapshot written by the loader.

        Parameters
        ----------
        value : dict[str, object]
            Value supplied for ``value``.

        Returns
        -------
        None
            Completes the operation described above.
        """
        self.saved.append(value)

class DoubleNextMiddleware(BaseMiddleware):
    """Exercise the continuation guard at the final middleware layer."""

    async def handle(
        self,
        _request: Request,
        call_next: Callable[[], Awaitable[Response]],
    ) -> Response:
        """Try advancing the same continuation twice.

        Parameters
        ----------
        _request : Request
            Value supplied for ``_request``.
        call_next : Callable[[], Awaitable[Response]]
            Value supplied for ``call_next``.

        Returns
        -------
        Response
            Value produced by the helper.
        """
        await call_next()
        return await call_next()

def item_handler(item: int) -> Response:
    """Expose the parameter ultimately passed to the handler.

    Parameters
    ----------
    item : int
        Value supplied for ``item``.

    Returns
    -------
    Response
        Value produced by the helper.
    """
    return Response(content=str(item))

class RewriteParamMiddleware(BaseMiddleware):
    """Adjust one parameter using the mutable request API."""

    async def handle(
        self,
        request: Request,
        call_next: Callable[[], Awaitable[Response]],
    ) -> Response:
        """Increment the parameter only for the current request.

        Parameters
        ----------
        request : Request
            Value supplied for ``request``.
        call_next : Callable[[], Awaitable[Response]]
            Value supplied for ``call_next``.

        Returns
        -------
        Response
            Value produced by the helper.
        """
        request.routeParams()["item"] += 1
        return await call_next()

class TestRoutingRuntime(TestCase):
    """Check request isolation and middleware continuation correctness."""

    async def testLastMiddlewareCannotExecuteTheHandlerTwice(self) -> None:
        """Count terminal invocations when the final layer calls next twice.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        calls = []

        async def terminal() -> Response:
            """Record and return the first terminal response.

            Returns
            -------
            Response
                Response produced before repeated continuation is rejected.
            """
            calls.append("called")
            return Response()

        pipeline = _MiddlewarePipeline((DoubleNextMiddleware(),), None, terminal)
        with self.assertRaises(RuntimeError):
            await pipeline()
        self.assertEqual(calls, ["called"])

    async def testContinuationRemainsConsumedAfterHandlerFailure(self) -> None:
        """Restore pipeline depth while preserving the at-most-once guard.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        calls = []

        async def terminal() -> Response:
            """Record the terminal invocation and raise its failure.

            Returns
            -------
            Response
                Value produced by the helper.

            Raises
            ------
            ValueError
                Always, to verify the consumed continuation remains guarded.
            """
            calls.append("called")
            error_msg = "failure"
            raise ValueError(error_msg)

        pipeline = _MiddlewarePipeline((DoubleNextMiddleware(),), None, terminal)
        with self.assertRaises(ValueError):
            await pipeline()
        with self.assertRaises(RuntimeError):
            await pipeline()
        self.assertEqual(calls, ["called"])

    def testRequestParamsRemainMutableAndIsolated(self) -> None:
        """Copy resolved params at the request boundary, preserving the public API.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        router = make_router()
        router.get("/items/{id:int}", route_handler)
        resolver = RouteResolver(compile_router(router))
        resolved = resolver.resolve("GET", "/items/1")
        request = Request(
            interface=Interface.ASGI,
            adapter=ASGITransportAdapter(make_asgi_scope("/items/1")),
            body_stream=SimpleNamespace(),
            params=resolved.params,
        )
        request.routeParams()["id"] = 99
        self.assertEqual(request.routeParam("id"), 99)
        self.assertEqual(resolver.resolve("GET", "/items/1").params["id"], 1)

    async def testMiddlewareParamChangesReachOnlyTheCurrentHandler(self) -> None:
        """Preserve middleware rewriting without leaking writes through the cache.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        router = make_router()
        router._setKind("api")
        router.get("/items/{item:int}", item_handler).middleware(RewriteParamMiddleware)
        kernel, _, _, catch = await boot_kernel(routes=compile_router(router))
        for _ in range(3):
            response = await dispatch(kernel, "/items/1")
            self.assertEqual(response.getBody(), b"2")
        self.assertEqual(catch.handled, [])

class TestRoutingCache(TestCase):
    """Exercise the real cache serializer and loader bootstrap boundaries."""

    def testJsonRoundTripPreservesNestedGroupsAndMiddleware(self) -> None:
        """Round-trip paths, exclusions, names, converters and nested classes.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        router = make_router()
        router._setKind("api")
        router.group(
            prefix="api",
            middleware=[OneMiddleware, TwoMiddleware],
            routes=[
                router.group(
                    prefix="v1",
                    middleware=Namespace.Middleware,
                    routes=[
                        router.get(
                            "/items/{id:int}",
                            [Namespace.Controller, "index"],
                        ).name("items.show"),
                    ],
                    without_middleware=TwoMiddleware,
                ),
            ],
        )
        cache = RouteCache()
        data = json.loads(json.dumps(cache.toCache(compile_router(router), None)))
        restored, fallback = cache.fromCache(data)
        result = RouteResolver(restored, fallback=fallback).resolve(
            "GET",
            "/api/v1/items/4",
        )
        self.assertEqual(result.params, {"id": 4})
        self.assertEqual(result.kind, "api")
        self.assertEqual(result.route.name, "items.show")
        self.assertEqual(
            result.route.compiled_middlewares,
            (
                OneMiddleware,
                Namespace.Middleware,
            ),
        )
        self.assertEqual(result.route.without_middleware, {TwoMiddleware})

    def testMiddlewareImportsAreSharedWithinOneCacheLoad(self) -> None:
        """Resolve a shared class once while restoring many compiled routes.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        router = make_router()
        router.group(
            middleware=Namespace.Middleware,
            routes=[
                router.get("/first", route_handler),
                router.get("/second", route_handler),
            ],
        )
        cache = RouteCache()
        data = cache.toCache(compile_router(router), None)
        imports: list[str] = []
        original_import = cache_module.resolve_name

        def record_import(path: str) -> object:
            """Record a class import and delegate to the real resolver.

            Parameters
            ----------
            path : str
                Value supplied for ``path``.

            Returns
            -------
            object
                Imported middleware class.
            """
            imports.append(path)
            return original_import(path)

        with replace_attribute(cache_module, "resolve_name", record_import):
            restored, _ = cache.fromCache(data)
        self.assertEqual(
            imports,
            [f"{Namespace.Middleware.__module__}.{Namespace.Middleware.__qualname__}"],
        )
        resolver = RouteResolver(restored)
        for path in ("/first", "/second"):
            self.assertEqual(
                resolver.resolve("GET", path).route.compiled_middlewares,
                (Namespace.Middleware,),
            )

    def testEmptyRouteTablesAreLoadedOnlyOnce(self) -> None:
        """Track completion independently from the truthiness of compiled routes.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        app = LoaderApplicationDouble()
        router = LoaderRouterDouble((None, None))
        loader = RouteLoader(app, router, RouteCompiler(), RouteCache())
        self.assertEqual(loader.load(), {})
        self.assertEqual(loader.load(), {})
        self.assertIsNone(loader.fallback)
        self.assertEqual(router.exports, 1)
        self.assertEqual(
            router.kinds,
            [
                "web",
                "api",
                "web",
            ],
        )

    def testCacheVersionInvalidatesOlderCompositionRules(self) -> None:
        """Recompile stale snapshots while accepting the current format.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        for version in (None, RouteCache.VERSION):
            with self.subTest(version=version):
                app = LoaderApplicationDouble(compiled=True)
                router = LoaderRouterDouble()
                persistence = RoutePersistenceDouble({
                    "version": version,
                    "routes": {},
                    "fallback": None,
                })

                def create_persistence(
                    backend: RoutePersistenceDouble = persistence,
                    **_options: object,
                ) -> RoutePersistenceDouble:
                    """Return the cache backend configured for this load.

                    Parameters
                    ----------
                    backend : RoutePersistenceDouble
                        Value supplied for ``backend``.
                    **_options : object
                        Arguments passed to the wrapped callable.

                    Returns
                    -------
                    RoutePersistenceDouble
                        Backend recording reads and writes.
                    """
                    return backend

                with replace_attribute(
                    loader_module, "FileBasedCache", create_persistence,
                ):
                    loader = RouteLoader(app, router, RouteCompiler(), RouteCache())
                self.assertEqual(loader.load(), {})
                self.assertEqual(loader.load(), {})
                self.assertEqual(persistence.reads, 1)
                if version is None:
                    self.assertEqual(router.exports, 1)
                    self.assertEqual(len(persistence.saved), 1)
                    self.assertEqual(
                        persistence.saved[0]["version"], RouteCache.VERSION,
                    )
                else:
                    self.assertEqual(router.exports, 0)
                    self.assertEqual(persistence.saved, [])

    def testLoaderRestoresKindAfterAnImportError(self) -> None:
        """Do not leave subsequent route registrations in an API import context.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        app = LoaderApplicationDouble(import_error=RuntimeError("import failed"))
        router = LoaderRouterDouble()
        loader = RouteLoader(app, router, RouteCompiler(), RouteCache())
        with self.assertRaises(RuntimeError):
            loader.load()
        self.assertEqual(router.kinds, ["web", "web"])
        self.assertEqual(router.exports, 0)
