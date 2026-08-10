from __future__ import annotations
from collections.abc import Callable
import re
from typing import TYPE_CHECKING
from orionis.http.routes.contracts.route_resolver import IRouteResolver
from orionis.http.routes.entities.resolved_route import ResolvedRoute
from orionis.http.routes.exceptions.method_not_allowed import MethodNotAllowed
from orionis.http.routes.exceptions.route_not_found import RouteNotFound
from orionis.http.routes.functions import normalize_request_path, strip_regex_anchors

if TYPE_CHECKING:
    from orionis.http.routes.entities.compiled_route import CompiledRoute

_GROUP_NAME_RE: re.Pattern = re.compile(r"\(\?P<(\w+)>")

# Canonical dispatch method per incoming method string; HEAD is served
# by the GET table.
_METHOD_MAP: dict[str, str] = {
    "GET": "GET",
    "HEAD": "GET",
    "POST": "POST",
    "PUT": "PUT",
    "DELETE": "DELETE",
    "PATCH": "PATCH",
    "QUERY": "QUERY",
    "OPTIONS": "OPTIONS",
}

ParamConverter = Callable[[str], object]
Extractor = tuple[str, int, ParamConverter]
BucketEntry = tuple[list[Extractor], "CompiledRoute"]

class _DepthBucket:

    __slots__ = ("entries", "marker_to_entry", "pattern")

    def __init__(
        self,
        pattern: re.Pattern[str],
        entries: list[BucketEntry],
        marker_to_entry: dict[int, int] | None = None,
    ) -> None:
        """Initialize bucket data used to resolve dynamic routes.

        Parameters
        ----------
        pattern : re.Pattern[str]
            Compiled regex that matches all dynamic routes at one depth.
        entries : list[BucketEntry]
            Extraction metadata and route pairs aligned with regex alternatives.
        marker_to_entry : dict[int, int] | None, optional
            Map of marker group IDs to ``entries`` indices for fast lookup.

        Returns
        -------
        None
            Store the provided matching structures on the instance.
        """
        self.pattern = pattern
        self.entries = entries
        self.marker_to_entry = marker_to_entry

def _path_allowed_for_method(
    static_table: dict[str, ResolvedRoute] | None,
    dynamic_table: dict[int, _DepthBucket] | None,
    path: str,
    depth: int,
) -> bool:
    """
    Check whether a method table can serve a path.

    Parameters
    ----------
    static_table : dict[str, ResolvedRoute] | None
        Static routes for one method.
    dynamic_table : dict[int, _DepthBucket] | None
        Dynamic routes indexed by segment count.
    path : str
        Normalized request path.
    depth : int
        Precomputed slash count for ``path``.

    Returns
    -------
    bool
        Return ``True`` when at least one route matches ``path``.
    """
    if static_table is None and dynamic_table is None:
        return False

    if static_table is not None and path in static_table:
        return True

    if dynamic_table is None:
        return False

    # Fast depth lookup only.
    bucket = dynamic_table.get(depth)
    return bucket is not None and bucket.pattern.match(path) is not None

def _path_allowed_for_method_cross_depth(
    static_table: dict[str, ResolvedRoute] | None,
    dynamic_table: dict[int, _DepthBucket] | None,
    path: str,
    depth: int,
) -> bool:
    """
    Check whether a method table can serve a path, allowing cross-depth scan.

    Parameters
    ----------
    static_table : dict[str, ResolvedRoute] | None
        Static routes for one method.
    dynamic_table : dict[int, _DepthBucket] | None
        Dynamic routes indexed by segment count.
    path : str
        Normalized request path.
    depth : int
        Precomputed slash count for ``path``.

    Returns
    -------
    bool
        Return ``True`` when at least one route matches ``path``.
    """
    if _path_allowed_for_method(static_table, dynamic_table, path, depth):
        return True

    if dynamic_table is None:
        return False

    for bucket in dynamic_table.values():
        if bucket.pattern.match(path) is not None:
            return True
    return False

def _build_extractors(
    converters: dict[str, ParamConverter],
    prefix: str,
    groupindex: dict[str, int],
) -> list[Extractor]:
    """
    Build extraction tuples from route converters.

    Parameters
    ----------
    converters : dict[str, ParamConverter]
        Converter mapping from parameter name to converter callable.
    prefix : str
        Prefix applied to regex group names.
    groupindex : dict[str, int]
        Map of named groups to their numeric group indices.

    Returns
    -------
    list[Extractor]
        Ordered list of ``(param_name, group_index, converter)`` tuples.
    """
    return [
        (name, groupindex[prefix + name], conv)
        for name, conv in converters.items()
    ]

def _build_depth_bucket(routes: list[CompiledRoute]) -> _DepthBucket:
    """
    Build a matching bucket for dynamic routes at one depth.

    Parameters
    ----------
    routes : list[CompiledRoute]
        Depth-grouped routes sorted by compiler priority.

    Returns
    -------
    _DepthBucket
        Bucket with compiled regex and extraction metadata.
    """
    if len(routes) == 1:
        route = routes[0]
        extractors = _build_extractors(
            route.converters,
            "",
            route.regex.groupindex,
        )
        entries: list[BucketEntry] = [(extractors, route)]
        return _DepthBucket(pattern=route.regex, entries=entries)

    parts: list[str] = []
    marker_to_entry: dict[int, int] = {}
    group_offset = 0

    for index, route in enumerate(routes):
        raw_pattern = strip_regex_anchors(route.regex.pattern)
        prefix = f"_r{index}_"
        prefixed_pattern = _GROUP_NAME_RE.sub(
            lambda match, _prefix=prefix: f"(?P<{_prefix}{match.group(1)}>",
            raw_pattern,
        )
        # Append an empty capture-group marker per alternative so the
        # matched route can be selected in O(1) via ``match.lastindex``.
        parts.append(f"(?:{prefixed_pattern})()")

        marker_group_index = group_offset + route.regex.groups + 1
        marker_to_entry[marker_group_index] = index
        group_offset = marker_group_index

    combined_pattern = re.compile(
        "^(?:" + "|".join(f"(?:{part})" for part in parts) + ")$",
    )
    # Resolve named groups to numeric indices once so extraction at
    # request time uses integer group access.
    groupindex = combined_pattern.groupindex
    entries = [
        (
            _build_extractors(route.converters, f"_r{index}_", groupindex),
            route,
        )
        for index, route in enumerate(routes)
    ]
    return _DepthBucket(
        pattern=combined_pattern,
        entries=entries,
        marker_to_entry=marker_to_entry,
    )

def _extract_result(match: re.Match[str], bucket: _DepthBucket) -> ResolvedRoute:
    """
    Extract a resolved route from a combined-regex match.

    Parameters
    ----------
    match : re.Match[str]
        Successful regex match.
    bucket : _DepthBucket
        Bucket used for the match.

    Returns
    -------
    ResolvedRoute
        Resolved route with converted path parameters.
    """
    marker_to_entry = bucket.marker_to_entry
    if marker_to_entry is None:
        extractors, route = bucket.entries[0]
        group = match.group
        return ResolvedRoute(
            route=route,
            params={
                name: converter(group(group_index))
                for name, group_index, converter in extractors
            },
        )

    marker_index = match.lastindex
    if marker_index is None:
        error_msg = "internal: combined regex matched but marker was not found"
        raise RouteNotFound(error_msg)

    entry_index = marker_to_entry.get(marker_index)
    if entry_index is None:
        error_msg = (
            "internal: combined regex matched but marker index "
            f"{marker_index} was not registered"
        )
        raise RouteNotFound(error_msg)

    extractors, route = bucket.entries[entry_index]
    group = match.group
    return ResolvedRoute(
        route=route,
        params={
            name: converter(group(group_index))
            for name, group_index, converter in extractors
        },
    )

class RouteResolver(IRouteResolver):

    # ruff: noqa: C901

    __slots__ = (
        "_all_methods",
        "_cache",
        "_cache_max",
        "_dynamic",
        "_fallback",
        "_global_dynamic",
        "_global_static",
        "_method_cross_depth",
        "_static",
        "_tables",
    )

    def __init__(
        self,
        routes: dict[str, dict],
        hot_cache_size: int = 512,
        fallback: tuple | None = None,
    ) -> None:
        """
        Build all route lookup structures.

        Parameters
        ----------
        routes : dict[str, dict]
            Compiled route tables grouped by HTTP method.
        hot_cache_size : int, optional
            Maximum size of the hot-path cache.
        fallback : tuple | None, optional
            Registered fallback handler.

        Returns
        -------
        None
            Store precomputed state on the resolver.
        """
        static: dict[str, dict[str, ResolvedRoute]] = {}
        dynamic: dict[str, dict[int, _DepthBucket]] = {}
        method_cross_depth: dict[str, bool] = {}
        all_static_paths: set[str] = set()
        global_patterns: dict[int, set[str]] = {}

        for method, bucket in routes.items():
            method_static: dict[str, CompiledRoute] = bucket["static"]
            # Precompute the final resolution result for every static path
            # so a static hit returns a ready ResolvedRoute instance.
            static[method] = {
                path: ResolvedRoute(route=compiled, params={})
                for path, compiled in method_static.items()
            }
            all_static_paths.update(method_static)

            grouped_routes: dict[int, list[CompiledRoute]] = {}
            has_cross_depth = False
            for route in bucket["dynamic"]:
                depth = route.segment_count
                grouped_routes.setdefault(depth, []).append(route)
                # Strip capture-group names: the global pattern is only
                # used for existence checks, and duplicate names across
                # routes would make the combined regex invalid.
                global_patterns.setdefault(depth, set()).add(
                    _GROUP_NAME_RE.sub(
                        "(?:",
                        strip_regex_anchors(route.regex.pattern),
                    ),
                )
                # ``.+`` inside a param group can consume extra segments.
                if ".+" in route.regex.pattern:
                    has_cross_depth = True

            method_cross_depth[method] = has_cross_depth

            dynamic[method] = {
                depth: _build_depth_bucket(depth_routes)
                for depth, depth_routes in grouped_routes.items()
            }

        self._static = static
        self._dynamic = dynamic
        self._all_methods: tuple[str, ...] = tuple(
            sorted(set(static) | set(dynamic)),
        )

        # Pair each method with its static and dynamic tables so the
        # resolver reaches both with a single dictionary lookup.
        self._tables: dict[
            str,
            tuple[dict[str, ResolvedRoute], dict[int, _DepthBucket]],
        ] = {
            method: (static[method], dynamic[method])
            for method in static
        }

        self._global_static: frozenset[str] = frozenset(all_static_paths)
        self._global_dynamic: dict[int, re.Pattern[str]] = {
            depth: re.compile(
                "^(?:" + "|".join(f"(?:{part})" for part in sorted(parts)) + ")$",
            )
            for depth, parts in global_patterns.items()
        }

        self._cache: dict[tuple[str, str], ResolvedRoute] = {}
        self._cache_max = hot_cache_size
        self._fallback = fallback
        self._method_cross_depth = method_cross_depth

    def resolve(  # NOSONAR
        self,
        method: str,
        path: str,
    ) -> ResolvedRoute:
        """
        Resolve a method and path into a compiled route.

        Parameters
        ----------
        method : str
            HTTP method string.
        path : str
            Raw request path.

        Returns
        -------
        ResolvedRoute
            Matched route and converted path parameters.

        Raises
        ------
        RouteNotFound
            Raise when no route matches the path.
        MethodNotAllowed
            Raise when the path exists under a different method.
        """
        # Normalise the method with a single table lookup; HEAD folds
        # onto GET and unknown spellings fall back to uppercasing.
        canonical = _METHOD_MAP.get(method)
        if canonical is None:
            upper = method.upper()
            canonical = _METHOD_MAP.get(upper, upper)
        method = canonical
        path = normalize_request_path(path)

        tables = self._tables.get(method)
        if tables is not None:
            resolved = tables[0].get(path)
            if resolved is not None:
                return resolved

        depth = path.count("/") if path != "/" else 0

        if tables is not None:
            dynamic_buckets = tables[1]
            if dynamic_buckets:
                cache_key: tuple[str, str] | None = None
                if self._cache_max:
                    cache_key = (method, path)
                    cached = self._cache.get(cache_key)
                    if cached is not None:
                        return cached
                bucket = dynamic_buckets.get(depth)
                if bucket is not None:
                    match = bucket.pattern.match(path)
                    if match is not None:
                        result = _extract_result(match, bucket)
                        if cache_key is not None:
                            self.__storeCache(cache_key, result)
                        return result

        if path in self._global_static:
            raise MethodNotAllowed(path)

        global_bucket = self._global_dynamic.get(depth)
        if global_bucket is not None and global_bucket.match(path) is not None:
            raise MethodNotAllowed(path)

        raise RouteNotFound(path)

    def options(self, path: str) -> list[str]:
        """
        Resolve all allowed methods for a path.

        Parameters
        ----------
        path : str
            Raw request path.

        Returns
        -------
        list[str]
            Sorted list of methods valid for the path.
        """
        path = normalize_request_path(path)
        depth = path.count("/") if path != "/" else 0

        static_tables = self._static
        dynamic_tables = self._dynamic
        method_cross_depth = self._method_cross_depth
        allowed = [
            method
            for method in self._all_methods
            if (
                _path_allowed_for_method_cross_depth(
                    static_tables.get(method),
                    dynamic_tables.get(method),
                    path,
                    depth,
                )
                if method_cross_depth.get(method, False)
                else _path_allowed_for_method(
                    static_tables.get(method),
                    dynamic_tables.get(method),
                    path,
                    depth,
                )
            )
        ]

        if "GET" in allowed and "HEAD" not in allowed:
            allowed.append("HEAD")

        if allowed:
            if "OPTIONS" not in allowed:
                allowed.append("OPTIONS")
        elif self._fallback is not None:
            allowed = ["GET", "HEAD", "OPTIONS"]

        allowed.sort()
        return allowed

    def fallback(self) -> tuple | None:
        """
        Return the registered fallback handler.

        Parameters
        ----------
        None
            This method does not accept parameters.

        Returns
        -------
        tuple | None
            Fallback descriptor or ``None`` if not registered.
        """
        return self._fallback

    def allRoutes(self) -> list:
        """
        Return all compiled routes across all HTTP methods.

        Parameters
        ----------
        None
            This method does not accept parameters.

        Returns
        -------
        list[CompiledRoute]
            Deduplicated list of every registered compiled route.
        """
        seen: set[int] = set()
        result: list = []

        for method_table in self._static.values():
            for resolved in method_table.values():
                route = resolved.route
                route_id = id(route)
                if route_id not in seen:
                    seen.add(route_id)
                    result.append(route)

        for depth_table in self._dynamic.values():
            self.__collectDynamic(depth_table, seen, result)

        return result

    def invalidateCache(self) -> None:
        """
        Clear the hot-path cache.

        Parameters
        ----------
        None
            This method does not accept parameters.

        Returns
        -------
        None
            Remove all cached entries.
        """
        self._cache.clear()

    def __storeCache(
        self,
        key: tuple[str, str],
        result: ResolvedRoute,
    ) -> None:
        """
        Store one hot-path cache entry.

        Parameters
        ----------
        key : tuple[str, str]
            Cache key ``(method, normalized_path)``.
        result : ResolvedRoute
            Resolved route value.

        Returns
        -------
        None
            Mutate the cache in place.
        """
        cache = self._cache
        # Evict the oldest entry only when the cache is full and the key is new.
        if len(cache) >= self._cache_max and key not in cache:
            del cache[next(iter(cache))]
        cache[key] = result

    def __collectDynamic(
        self,
        depth_table: dict,
        seen: set[int],
        result: list,
    ) -> None:
        """Collect unique dynamic routes from a method depth table.

        Parameters
        ----------
        depth_table : dict
            Method-specific depth table containing route buckets.
        seen : set[int]
            Set of route object identifiers already collected.
        result : list
            Output list populated with unique dynamic route objects.

        Returns
        -------
        None
            Mutate ``seen`` and ``result`` in place.
        """
        for bucket in depth_table.values():
            for _, route in bucket.entries:
                route_id = id(route)
                if route_id not in seen:
                    seen.add(route_id)
                    result.append(route)
