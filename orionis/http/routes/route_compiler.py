from __future__ import annotations

import re
from operator import attrgetter
from typing import TYPE_CHECKING

from orionis.http.routes.contracts.route_compiler import IRouteCompiler
from orionis.http.routes.entities.compiled_route import CompiledRoute
from orionis.http.routes.enums.route_types import RouteType
from orionis.http.routes.functions import parse_action
from orionis.http.routes.params_types import PARAM_TYPES

if TYPE_CHECKING:
    from collections.abc import Callable

    from orionis.http.middleware import BaseMiddleware

# Precompiled pattern for path parameter placeholders like {name} or {name:type}.
_PARAM_RE: re.Pattern = re.compile(r"\{(\w+)(?::(\w+))?\}")

# Precompiled pattern to normalise named capture groups for collision detection.
_NAMED_GROUP_RE: re.Pattern = re.compile(r"\(\?P<\w+>")


def _validate_literal(fragment: str, path: str) -> None:
    """Reject unmatched braces and malformed parameter declarations.

    Raises
    ------
    ValueError
        If a literal fragment contains a parameter delimiter.
    """
    if "{" in fragment or "}" in fragment:
        error_msg = f"Malformed route parameter in path '{path}'"
        raise ValueError(error_msg)


def _action_name(handler: Callable | type) -> str:
    """Return an importable handler name for boot-time dispatch and caching.

    Raises
    ------
    ValueError
        If the handler is local to a function and cannot be imported at boot.
    """
    name = handler.__qualname__
    if "<locals>" in name:
        error_msg = f"Route handlers must be importable: {name}"
        raise ValueError(error_msg)
    return name


def _register_name(names: dict[str, str], route: dict) -> None:
    """Require one unambiguous URL template per route name.

    Raises
    ------
    ValueError
        If the same name refers to different path templates.
    """
    name = route.get("name")
    if name:
        previous = names.setdefault(name, route["path"])
        if previous != route["path"]:
            error_msg = f"Route name '{name}' refers to multiple paths."
            raise ValueError(error_msg)

class RouteCompiler(IRouteCompiler):

    def compile(
        self,
        routes: list[dict],
        fallback: tuple | None,
        app_middleware: list[type] | None = None,
    ) -> tuple[dict[str, dict], tuple | None]:
        """
        Compile a list of raw route dicts into a ready-to-dispatch structure.

        Parameters
        ----------
        routes : list[dict]
            Raw route dicts as returned by ``Router.export()["routes"]``.
        fallback : tuple | None
            Raw fallback tuple from ``Router.export()["fallback"]``.
        app_middleware : list[type] | None, optional
            Global middleware classes to prepend to every route's middleware
            stack before route-specific middleware is applied.

        Returns
        -------
        tuple[dict[str, dict], tuple | None]
            A pair ``(compiled_routes, fallback)`` where
            ``compiled_routes`` maps each HTTP method to
            ``{"static": {path: CompiledRoute},
            "dynamic": [CompiledRoute, ...]}``. Dynamic lists are
            sorted descending by ``priority_score`` so more-specific
            patterns are matched first.

        Raises
        ------
        ValueError
            If two dynamic routes produce the same structural URL
            pattern (collision).
        TypeError
            If an invokable class does not define ``__call__``.
        """
        compiled_routes: dict[str, dict] = {}
        seen_signatures: dict[str, str] = {}
        names: dict[str, str] = {}

        for route in routes:
            _register_name(names, route)
            method = route["method"]
            path = route["path"]
            is_static, compiled = self.__compileRoute(
                route,
                app_middleware,
            )

            method_bucket = compiled_routes.get(method)
            if method_bucket is None:
                method_bucket = {"static": {}, "dynamic": []}
                compiled_routes[method] = method_bucket

            if is_static:
                static_bucket = method_bucket["static"]
                if path in static_bucket:
                    error_msg = (
                        f"Route conflict detected for {method} "
                        f"'{path}':\n"
                        "  A static route with the same method and path "
                        "is already registered."
                    )
                    raise ValueError(error_msg)

                static_bucket[path] = compiled
            else:
                # Collision detection: two dynamic routes whose regex patterns
                # are structurally identical would match identical URLs,
                # making one unreachable.
                signature = self.__routeSignature(method, compiled.regex)
                if signature in seen_signatures:
                    error_msg = (
                        f"Route conflict detected for {method} "
                        f"'{path}':\n"
                        f"  '{path}' and "
                        f"'{seen_signatures[signature]}' produce the same "
                        "URL pattern and would collide at dispatch.\n"
                        f"  Signature: {signature}"
                    )
                    raise ValueError(error_msg)
                seen_signatures[signature] = path
                method_bucket["dynamic"].append(compiled)

        # Sort each method's dynamic routes by specificity (descending).
        # More static segments → higher score → matched first.
        priority_key = attrgetter("priority_score")
        for bucket in compiled_routes.values():
            bucket["dynamic"].sort(
                key=priority_key,
                reverse=True,
            )

        return compiled_routes, fallback

    @staticmethod
    def compilePath(
        path: str,
    ) -> tuple[bool, re.Pattern | None, dict[str, Callable]]:
        """
        Determine whether a path is static or dynamic and compile its regex.

        This method is intentionally public so that :class:`RouteCache`
        can call it during cache deserialisation to reconstruct ``regex``
        and ``converters`` without ever persisting callable objects.

        Parameters
        ----------
        path : str
            The route path, e.g. ``'/users/{id:int}'``.

        Returns
        -------
        tuple[bool, re.Pattern | None, dict[str, Callable]]
            ``(is_static, regex, converters)`` — ``regex`` and
            ``converters`` are ``None`` / empty for static paths.
        """
        if "{" not in path and "}" not in path:
            return True, None, {}

        regex, converters = RouteCompiler.__buildPathRegex(path)
        return False, regex, converters

    # ── Private helpers ───────────────────────────────────────────────────────

    def __compileRoute(
        self,
        route: dict,
        app_middleware: list[type] | None = None,
    ) -> tuple[bool, CompiledRoute]:
        """
        Compile a single raw route dict into a ``CompiledRoute``.

        Parameters
        ----------
        route : dict
            Raw route dictionary from the router export.

        Returns
        -------
        tuple[bool, CompiledRoute]
            ``(is_static, compiled_route)``.
        """
        # Determine the final middleware stack for this route, respecting
        # global and route-specific middleware and exclusions.
        without_middleware = set(route.get("without_middleware", ()))
        middleware = list(route.get("middleware", ()))
        seen: set[type[BaseMiddleware]] = set()
        stack: list[type[BaseMiddleware]] = []

        # Global middleware first
        for mw in app_middleware or ():
            if mw in without_middleware or mw in seen:
                continue
            seen.add(mw)
            stack.append(mw)

        # Route middleware second
        for mw in middleware:
            if mw in without_middleware or mw in seen:
                continue
            seen.add(mw)
            stack.append(mw)

        # Store the middleware execution order as a tuple.
        compiled_middlewares = tuple(stack)

        # Resolve the action type and build the action descriptor for dispatch.
        path = route["path"]
        route_type, action = self.__buildAction(route)
        is_static, regex, converters = self.compilePath(path)
        segment_count, priority_score = self.__routeMetrics(path)

        # Build the CompiledRoute with all the resolved information.
        compiled = CompiledRoute(
            path=path,
            method=route["method"],
            type=route_type,
            action=action,
            name=route.get("name"),
            regex=regex,
            segment_count=segment_count,
            priority_score=priority_score,
            kind=route.get("kind", "web"),
            converters=converters,
            middleware=middleware,
            without_middleware=without_middleware,
            compiled_middlewares=compiled_middlewares,
        )
        return is_static, compiled

    @staticmethod
    def __buildAction(route: dict) -> tuple[RouteType, dict]:
        """
        Resolve the handler type and build the action descriptor for a route.

        Parameters
        ----------
        route : dict
            Raw route dictionary from the router export.

        Returns
        -------
        tuple[RouteType, dict]
            A tuple of the resolved ``RouteType`` and an action
            descriptor dict containing the information needed to
            dispatch the request.

        Raises
        ------
        TypeError
            If an invokable class does not define ``__call__``.
        """
        # View routes carry only a template name, so they stay JSON-safe and
        # survive the compiled route cache without importing any module.
        view_name = route.get("view")
        if view_name is not None:
            return RouteType.VIEW, {"view": view_name}

        callable_handler = route.get("callable_handler")

        if callable_handler is not None:
            parse_action(callable_handler)
            if isinstance(callable_handler, type):
                return RouteType.INVOKABLE, {
                    "class": _action_name(callable_handler),
                    "module": callable_handler.__module__,
                    "method": "__call__",
                }
            return RouteType.FUNCTION, {
                "function": _action_name(callable_handler),
                "module": callable_handler.__module__,
            }

        # Controller-based route: [ControllerClass, 'method_name']
        _class = route.get("class")
        parse_action([_class, route.get("handler")])
        return RouteType.CONTROLLER, {
            "class": _action_name(_class),
            "module": _class.__module__,
            "method": route.get("handler"),
        }

    @staticmethod
    def __buildPathRegex(
        path: str,
    ) -> tuple[re.Pattern, dict[str, Callable]]:
        """
        Compile a route path with placeholders into a regex and converters.

        Parameters
        ----------
        path : str
            Route path containing placeholders,
            e.g. ``'/user/{id:int}'``.

        Returns
        -------
        tuple[re.Pattern, dict[str, Callable]]
            Compiled regex pattern and a dict mapping parameter names
            to their converter callables.

        Raises
        ------
        ValueError
            If an unknown parameter type is encountered in the path.
        """
        param_types = PARAM_TYPES
        converters: dict[str, Callable] = {}
        parts: list[str] = []
        last_end = 0

        # Iterate over placeholders and build the regex incrementally.
        # Static segments are escaped so characters like '.' are literals.
        for match in _PARAM_RE.finditer(path):
            fragment = path[last_end : match.start()]
            _validate_literal(fragment, path)
            parts.append(re.escape(fragment))
            name, type_name = match.groups()
            if not name.isidentifier() or name in converters:
                error_msg = f"Invalid or duplicate parameter '{name}' in path '{path}'"
                raise ValueError(error_msg)
            if type_name is None:
                type_name = "str"
            if type_name not in param_types:
                error_msg = (
                    f"Unknown parameter type: '{type_name}' in path '{path}'"
                )
                raise ValueError(error_msg)
            type_info = param_types[type_name]
            parts.append(f"(?P<{name}>{type_info['pattern']})")
            converters[name] = type_info["converter"]
            last_end = match.end()

        # Escape any remaining static tail after the last placeholder.
        tail = path[last_end:]
        _validate_literal(tail, path)
        parts.append(re.escape(tail))

        regex = re.compile(f"^{''.join(parts)}$")
        return regex, converters

    @staticmethod
    def __routeSignature(method: str, regex: re.Pattern) -> str:
        """
        Build a collision-detection key for a dynamic route.

        Two routes collide when they match the same set of URLs regardless
        of parameter names, e.g. ``/users/{id}`` and ``/users/{name}``
        both produce ``^/users/(?P<param>[^/]+)$``.

        The key normalises every named capture group to the fixed
        placeholder ``param`` and prefixes with the HTTP method::

            GET:^/users/(?P<param>[^/]+)$

        Parameters
        ----------
        method : str
            HTTP method in uppercase.
        regex : re.Pattern
            Compiled route regex.

        Returns
        -------
        str
            Normalised signature string.
        """
        normalised = _NAMED_GROUP_RE.sub("(?P<param>", regex.pattern)
        return f"{method}:{normalised}"

    @staticmethod
    def __routeMetrics(path: str) -> tuple[int, int]:
        """
        Compute the segment count and specificity score for a route path.

        Higher scores are more specific and should be matched first.
        The formula weights static segments heavily so that
        ``/users/me`` (score 20) always beats ``/users/{id}``
        (score 9).

        Parameters
        ----------
        path : str
            The route path, e.g. ``'/users/{id}/settings'``.

        Returns
        -------
        tuple[int, int]
            ``(segment_count, priority_score)`` where the score is
            ``static_segments * 10 - dynamic_segments``.
        """
        # Count static and dynamic segments in a single pass.
        static = 0
        dynamic = 0
        for s in path.split("/"):
            if not s:
                continue
            if "{" in s:
                dynamic += 1
            else:
                static += 1
        return static + dynamic, static * 10 - dynamic
