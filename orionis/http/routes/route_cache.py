from __future__ import annotations

import importlib
from pkgutil import resolve_name

from orionis.http.routes.contracts.route_cache import IRouteCache
from orionis.http.routes.entities.compiled_route import CompiledRoute
from orionis.http.routes.enums.route_types import RouteType
from orionis.http.routes.route_compiler import RouteCompiler


class RouteCache(IRouteCache):

    VERSION = 2

    def toCache(
        self,
        routes: dict[str, dict],
        fallback: tuple | None,
    ) -> dict:
        """
        Serialise compiled routes and the fallback handler to a cache dict.

        Parameters
        ----------
        routes : dict[str, dict]
            Compiled routes mapping produced by ``RouteCompiler.compile``.
        fallback : tuple | None
            Raw fallback tuple stored by the loader.

        Returns
        -------
        dict
            JSON-safe representation suitable for
            ``FileBasedCache.save()``.
        """
        return {
            "version": self.VERSION,
            "fallback": self.__serializeFallback(fallback),
            "routes": {
                method: {
                    "static": {
                        path: self.__serializeCompiledRoute(cr)
                        for path, cr in bucket["static"].items()
                    },
                    "dynamic": [
                        self.__serializeCompiledRoute(cr)
                        for cr in bucket["dynamic"]
                    ],
                }
                for method, bucket in routes.items()
            },
        }

    def fromCache(
        self,
        cached: dict,
    ) -> tuple[dict[str, dict], tuple | None]:
        """
        Rebuild compiled routes and the fallback handler from a cache dict.

        Parameters
        ----------
        cached : dict
            Dict previously produced by :meth:`toCache`.

        Returns
        -------
        tuple[dict[str, dict], tuple | None]
            ``(routes, fallback)`` ready to be stored on the loader.
        """
        fallback = self.__deserializeFallback(cached.get("fallback"))
        routes: dict[str, dict] = {}
        resolved_classes: dict[str, type] = {}

        for method, bucket in cached.get("routes", {}).items():
            routes[method] = {"static": {}, "dynamic": []}
            for path, route_data in bucket["static"].items():
                routes[method]["static"][path] = (
                    self.__deserializeCompiledRoute(route_data, resolved_classes)
                )
            for route_data in bucket["dynamic"]:
                routes[method]["dynamic"].append(
                    self.__deserializeCompiledRoute(route_data, resolved_classes),
                )

        return routes, fallback

    # ── Compiled-route helpers ────────────────────────────────────────────────

    @staticmethod
    def __serializeCompiledRoute(cr: CompiledRoute) -> dict:
        """Convert a ``CompiledRoute`` to a JSON-safe dict.

        ``regex`` and ``converters`` are omitted — they are fully
        deterministic from ``path`` and recomputed on deserialisation.
        Middleware class references are stored as dotted import paths.

        Parameters
        ----------
        cr : CompiledRoute
            The compiled route to serialise.

        Returns
        -------
        dict
            JSON-safe representation of the compiled route.
        """
        return {
            "path": cr.path,
            "method": cr.method,
            "type": cr.type.value,
            "action": cr.action,
            "name": cr.name,
            "segment_count": cr.segment_count,
            "priority_score": cr.priority_score,
            "kind": cr.kind,
            "middleware": [
                f"{m.__module__}.{m.__qualname__}"
                for m in cr.middleware
            ],
            "without_middleware": [
                f"{m.__module__}.{m.__qualname__}"
                for m in cr.without_middleware
            ],
            "compiled_middlewares": [
                f"{m.__module__}.{m.__qualname__}"
                for m in cr.compiled_middlewares
            ],
        }

    @staticmethod
    def __deserializeCompiledRoute(
        route_data: dict,
        resolved_classes: dict[str, type],
    ) -> CompiledRoute:
        """Rebuild a ``CompiledRoute`` from a cache dict.

        ``regex`` and ``converters`` are recomputed via
        :meth:`RouteCompiler.compilePath` so that callable converters
        (including lambdas) never need to be serialised.

        Parameters
        ----------
        route_data : dict
            Dict produced by :meth:`__serializeCompiledRoute`.
        resolved_classes : dict[str, type]
            Class references shared across this cache load.

        Returns
        -------
        CompiledRoute
            Fully initialised compiled route.
        """
        _, regex, converters = RouteCompiler.compilePath(route_data["path"])
        return CompiledRoute(
            path=route_data["path"],
            method=route_data["method"],
            type=RouteType(route_data["type"]),
            action=route_data["action"],
            name=route_data["name"],
            regex=regex,
            segment_count=route_data["segment_count"],
            priority_score=route_data["priority_score"],
            kind=route_data.get("kind", "web"),
            converters=converters,
            middleware=[
                RouteCache.__resolveClass(s, resolved_classes)
                for s in route_data["middleware"]
            ],
            without_middleware={
                RouteCache.__resolveClass(s, resolved_classes)
                for s in route_data["without_middleware"]
            },
            compiled_middlewares=tuple(
                RouteCache.__resolveClass(s, resolved_classes)
                for s in route_data["compiled_middlewares"]
            ),
        )

    # ── Fallback helpers ──────────────────────────────────────────────────────

    @staticmethod
    def __serializeFallback(fallback: tuple | None) -> dict | None:
        """Serialise the fallback tuple to a JSON-safe descriptor dict.

        Parameters
        ----------
        fallback : tuple | None
            Raw fallback tuple from the router.

        Returns
        -------
        dict | None
            Descriptor dict, or ``None`` if no fallback is registered.
        """
        if not fallback or fallback == (None, None):
            return None
        cls_ref, handler = fallback
        if cls_ref is None and callable(handler):
            return {
                "type": RouteType.FUNCTION,
                "module": handler.__module__,
                "function": handler.__qualname__,
            }
        if cls_ref is not None and handler is None:
            return {
                "type": RouteType.INVOKABLE,
                "class": f"{cls_ref.__module__}.{cls_ref.__qualname__}",
            }
        return {
            "type": RouteType.CONTROLLER,
            "class": f"{cls_ref.__module__}.{cls_ref.__qualname__}",
            "method": handler,
        }

    @staticmethod
    def __deserializeFallback(data: dict | None) -> tuple | None:
        """Rebuild the fallback tuple from a cache descriptor dict.

        Parameters
        ----------
        data : dict | None
            Descriptor produced by :meth:`__serializeFallback`.

        Returns
        -------
        tuple | None
            Fallback tuple for the dispatch engine, or ``None``.
        """
        if not data:
            return None
        route_type = RouteType(data["type"])
        if route_type == RouteType.FUNCTION:
            # Resolve the callable from its stored module and qualname
            func = RouteCache.__resolveQualname(
                module_path=data["module"],
                qualname=data["function"],
            )
            return (None, func)
        if route_type == RouteType.INVOKABLE:
            cls_ref = RouteCache.__resolveClass(data["class"])
            return (cls_ref, "__call__")
        cls_ref = RouteCache.__resolveClass(data["class"])
        return (cls_ref, data["method"])

    # ── Shared utility ────────────────────────────────────────────────────────

    @staticmethod
    def __resolveClass(
        dotted_path: str,
        resolved_classes: dict[str, type] | None = None,
    ) -> type:
        """Import and return a class given its fully-qualified dotted path.

        Parameters
        ----------
        dotted_path : str
            Fully-qualified class path,
            e.g. ``'app.http.middleware.Auth'``.
        resolved_classes : dict[str, type] | None, optional
            Memoized class references for one cache load.

        Returns
        -------
        type
            The imported class object.
        """
        if resolved_classes is None:
            return resolve_name(dotted_path)
        resolved = resolved_classes.get(dotted_path)
        if resolved is None:
            resolved = resolve_name(dotted_path)
            resolved_classes[dotted_path] = resolved
        return resolved

    @staticmethod
    def __resolveQualname(
        module_path: str,
        qualname: str,
    ) -> object:
        """Resolve a module-level qualname into its target object.

        Parameters
        ----------
        module_path : str
            Import path of the module containing the object.
        qualname : str
            Qualname to resolve, potentially with dotted nesting.

        Returns
        -------
        object
            Resolved target object.

        Raises
        ------
        ValueError
            If the qualname contains ``<locals>``, which cannot be
            safely restored from cache.
        """
        if "<locals>" in qualname:
            error_msg = (
                "Cannot restore cached fallback callable with <locals> "
                f"qualname: {module_path}.{qualname}"
            )
            raise ValueError(error_msg)

        target: object = importlib.import_module(module_path)
        for part in qualname.split("."):
            target = getattr(target, part)
        return target
