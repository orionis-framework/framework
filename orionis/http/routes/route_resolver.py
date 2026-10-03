from __future__ import annotations
import re
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass
from heapq import merge
from typing import TYPE_CHECKING
from orionis.http.routes.contracts.route_resolver import IRouteResolver
from orionis.http.routes.entities.resolved_route import ResolvedRoute
from orionis.http.routes.exceptions.method_not_allowed import MethodNotAllowed
from orionis.http.routes.exceptions.route_not_found import RouteNotFound
from orionis.http.routes.functions import normalize_request_path, strip_regex_anchors

if TYPE_CHECKING:
    from typing import Never
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
        """
        Store matching and parameter extraction metadata for dynamic routes.

        Parameters
        ----------
        pattern : re.Pattern[str]
            Compiled regex for the bucket's dynamic route candidates.
        entries : list[BucketEntry]
            Extraction metadata and route pairs aligned with regex alternatives.
        marker_to_entry : dict[int, int] | None, optional
            Map of terminal capture group IDs to entry indices, or None for
            a single-route bucket. Defaults to None.

        Returns
        -------
        None
            Initialize the matcher, ordered entries, and optional marker lookup.
        """
        self.pattern = pattern
        self.entries = entries
        self.marker_to_entry = marker_to_entry

@dataclass(frozen=True, slots=True)
class _PrefixIndex:
    """Select the first distinct segment after a shared static path prefix."""

    start: int
    branches: dict[str, _DepthBucket | _PrefixIndex]
    fallback: _DepthBucket | None = None

type DepthTable = dict[int, _DepthBucket | _PrefixIndex]

def _select_bucket(
    table: DepthTable,
    path: str,
    depth: int,
) -> _DepthBucket | None:
    """
    Select a dynamic route bucket by path depth and literal segments.

    Parameters
    ----------
    table : DepthTable
        Dynamic candidates grouped by depth for one HTTP method.
    path : str
        Normalized request path used to traverse literal prefix branches.
    depth : int
        Number of path separators, or zero for the root path.

    Returns
    -------
    _DepthBucket | None
        Bucket selected by depth and prefix, or None if no branch or fallback
        applies. The bucket's regex is not evaluated.
    """
    bucket = table.get(depth)
    while isinstance(bucket, _PrefixIndex):
        start = bucket.start
        end = path.find("/", start)
        segment = path[start:end] if end != -1 else path[start:]
        bucket = bucket.branches.get(segment, bucket.fallback)
    return bucket

def _path_allowed_for_method(
    static_table: dict[str, ResolvedRoute],
    dynamic_table: DepthTable,
    path: str,
    depth: int,
) -> bool:
    """
    Check whether a method has a static or regex match for a path.

    Inspect lookup structures without extracting or converting parameters.

    Parameters
    ----------
    static_table : dict[str, ResolvedRoute]
        Static paths mapped to resolved routes for one HTTP method.
    dynamic_table : DepthTable
        Dynamic candidates grouped by depth for the same method.
    path : str
        Normalized request path to check.
    depth : int
        Number of path separators, or zero for the root path.

    Returns
    -------
    bool
        True if a static path or dynamic pattern matches; otherwise, False.
    """
    if path in static_table:
        return True
    bucket = _select_bucket(dynamic_table, path, depth)
    return bucket is not None and bucket.pattern.fullmatch(path) is not None

def _build_extractors(
    converters: dict[str, ParamConverter],
    prefix: str,
    groupindex: dict[str, int],
) -> list[Extractor]:
    """
    Build parameter extraction tuples from route converters.

    Parameters
    ----------
    converters : dict[str, ParamConverter]
        Parameter names mapped to converter callables, in extraction order.
    prefix : str
        Prefix prepended to parameter names in the regex capture groups.
    groupindex : dict[str, int]
        Named capture groups mapped to their numeric indices.

    Returns
    -------
    list[Extractor]
        Ordered list of ``(param_name, group_index, converter)`` tuples.

    Raises
    ------
    KeyError
        If a prefixed parameter name is absent from ``groupindex``.
    """
    return [
        (name, groupindex[prefix + name], conv)
        for name, conv in converters.items()
    ]

def _build_matching_bucket(routes: list[CompiledRoute]) -> _DepthBucket:
    """
    Build an ordered matcher and extractors for dynamic routes.

    Parameters
    ----------
    routes : list[CompiledRoute]
        Dynamic candidates at one depth, sorted by compiler priority.

    Returns
    -------
    _DepthBucket
        Regex matcher with per-route extractors and optional alternative markers.

    Raises
    ------
    re.PatternError
        If rewritten route patterns cannot form a valid combined regex.
    KeyError
        If a converter has no corresponding named capture group.
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
        # Append a marker group identifying each matched alternative.
        parts.append(f"(?:{prefixed_pattern})()")

        marker_group_index = group_offset + route.regex.groups + 1
        marker_to_entry[marker_group_index] = index
        group_offset = marker_group_index

    combined_pattern = re.compile(
        "^(?:" + "|".join(f"(?:{part})" for part in parts) + ")$",
    )
    # Associate parameter names with their numeric capture groups.
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

def _partition_route_segments(
    routes: list[CompiledRoute],
    start: int,
) -> tuple[
    dict[str, list[tuple[int, CompiledRoute]]],
    list[tuple[int, CompiledRoute]],
] | None:
    """
    Partition literal and wildcard path segments in candidate order.

    Parameters
    ----------
    routes : list[CompiledRoute]
        Candidates sorted by compiler priority.
    start : int
        Character offset of the path segment to partition.

    Returns
    -------
    tuple | None
        Literal branches and wildcard candidates as ``(index, route)`` pairs,
        or None if any selected segment is empty.
    """
    branches: dict[str, list[tuple[int, CompiledRoute]]] = {}
    wildcards: list[tuple[int, CompiledRoute]] = []
    for index, route in enumerate(routes):
        end = route.path.find("/", start)
        segment = route.path[start:end] if end != -1 else route.path[start:]
        if "{" in segment:
            wildcards.append((index, route))
        elif segment:
            branches.setdefault(segment, []).append((index, route))
        else:
            return None
    return branches, wildcards

def _build_depth_bucket(
    routes: list[CompiledRoute],
    start: int = 1,
) -> _DepthBucket | _PrefixIndex:
    """
    Build a depth matcher, splitting literal prefixes when useful.

    Parameters
    ----------
    routes : list[CompiledRoute]
        Dynamic candidates at one depth, sorted by compiler priority.
    start : int, optional
        Character offset of the next path segment to partition. Defaults to 1.

    Returns
    -------
    _DepthBucket | _PrefixIndex
        Shared matcher or prefix index preserving route priority and overlap.
    """
    minimum_partition_size = 16
    if len(routes) < minimum_partition_size:
        return _build_matching_bucket(routes)
    while True:
        partition = _partition_route_segments(routes, start)
        if partition is None:
            return _build_matching_bucket(routes)
        branches, wildcards = partition
        if wildcards:
            return _build_overlapping_index(routes, start, branches, wildcards)
        if len(branches) > 1:
            return _PrefixIndex(
                start,
                {
                    prefix: _build_depth_bucket(
                        [route for _, route in members],
                        start + len(prefix) + 1,
                    )
                    for prefix, members in branches.items()
                },
            )
        start += len(next(iter(branches))) + 1

def _build_overlapping_index(
    routes: list[CompiledRoute],
    start: int,
    branches: dict[str, list[tuple[int, CompiledRoute]]],
    wildcards: list[tuple[int, CompiledRoute]],
) -> _DepthBucket | _PrefixIndex:
    """
    Merge wildcard candidates into literal branches in route order.

    Reuse a shared matcher when fewer than two literal branches exist or more
    than eight wildcard candidates would be duplicated.

    Parameters
    ----------
    routes : list[CompiledRoute]
        Complete candidate list in priority order for the shared matcher.
    start : int
        Character offset of the segment used to select a literal branch.
    branches : dict[str, list[tuple[int, CompiledRoute]]]
        Literal segment values mapped to sorted ``(index, route)`` pairs.
    wildcards : list[tuple[int, CompiledRoute]]
        Wildcard candidates with original indices, in priority order.

    Returns
    -------
    _DepthBucket | _PrefixIndex
        Prefix index with a wildcard fallback, or the shared ordered matcher.
    """
    maximum_wildcards = 8
    minimum_branches = 2
    if len(branches) < minimum_branches or len(wildcards) > maximum_wildcards:
        return _build_matching_bucket(routes)
    return _PrefixIndex(
        start,
        {
            prefix: _build_matching_bucket([
                route for _, route in merge(members, wildcards)
            ])
            for prefix, members in branches.items()
        },
        _build_matching_bucket([route for _, route in wildcards]),
    )

def _extract_result(match: re.Match[str], bucket: _DepthBucket) -> ResolvedRoute:
    """
    Extract a resolved route and convert its matched parameters.

    Parameters
    ----------
    match : re.Match[str]
        Successful match against the bucket's regex.
    bucket : _DepthBucket
        Ordered route candidates and their parameter extraction metadata.

    Returns
    -------
    ResolvedRoute
        Compiled route with its extracted and converted parameter mapping.

    Raises
    ------
    RouteNotFound
        If a combined match lacks its identifying route marker.
    ValueError, OverflowError
        If a parameter converter rejects a captured value.
    """
    marker_to_entry = bucket.marker_to_entry
    entry_index = 0
    if marker_to_entry is not None:
        marker_index = match.lastindex
        if marker_index is None:
            error_msg = "Combined route regex matched without a route marker."
            raise RouteNotFound(error_msg)
        entry_index = marker_to_entry[marker_index]

    extractors, route = bucket.entries[entry_index]
    group = match.group
    return ResolvedRoute._fromOwnedParams(  # noqa: SLF001
        route,
        {
            name: converter(group(group_index))
            for name, group_index, converter in extractors
        },
    )

def _extract_converter_fallback(
    path: str,
    bucket: _DepthBucket,
    match: re.Match[str],
) -> ResolvedRoute | None:
    """
    Try later matching routes after a parameter conversion failure.

    Skip candidates whose converters raise ``ValueError`` or ``OverflowError``.

    Parameters
    ----------
    path : str
        Normalized request path to match against later routes.
    bucket : _DepthBucket
        Ordered routes in the selected dynamic bucket.
    match : re.Match[str]
        Match whose parameter converter failed.

    Returns
    -------
    ResolvedRoute | None
        First later route whose parameters convert successfully, or None.
    """
    marker_to_entry = bucket.marker_to_entry
    first_index = (
        marker_to_entry[match.lastindex]
        if marker_to_entry is not None else 0
    )
    for _, route in bucket.entries[first_index + 1:]:
        candidate = route.regex.fullmatch(path)
        if candidate is None:
            continue
        try:
            params = {
                name: converter(candidate.group(name))
                for name, converter in route.converters.items()
            }
        except (ValueError, OverflowError):
            continue
        return ResolvedRoute._fromOwnedParams(route, params)  # noqa: SLF001
    return None

class RouteResolver(IRouteResolver):
    """Resolve compiled routes using static maps and ordered dynamic buckets."""

    __slots__ = (
        "_cache_max", "_cache_order", "_fallback", "_global_static",
        "_routes", "_tables",
    )

    def __init__(
        self,
        routes: dict[str, dict],
        hot_cache_size: int = 512,
        fallback: tuple | None = None,
    ) -> None:
        """
        Build lookup tables and the bounded FIFO result cache.

        Parameters
        ----------
        routes : dict[str, dict]
            Compiler output grouped by method and static/dynamic paths.
        hot_cache_size : int, optional
            Maximum dynamic results cached across all methods; zero disables
            caching. Defaults to 512.
        fallback : tuple | None, optional
            Fallback handler metadata. None or ``(None, None)`` disables the
            fallback. Defaults to None.

        Returns
        -------
        None
            Initialize route tables, the route inventory, and the FIFO cache.

        Raises
        ------
        TypeError
            If the cache capacity is a boolean or not an integer.
        ValueError
            If the cache capacity is negative.
        """
        if isinstance(hot_cache_size, bool) or not isinstance(hot_cache_size, int):
            error_msg = "Hot cache size must be an integer."
            raise TypeError(error_msg)
        if hot_cache_size < 0:
            error_msg = "Hot cache size must not be negative."
            raise ValueError(error_msg)
        self._tables = {}
        all_routes: dict[int, CompiledRoute] = {}
        static_paths: set[str] = set()
        for method, bucket in routes.items():
            static = {
                path: ResolvedRoute(route=route, params={})
                for path, route in bucket["static"].items()
            }
            static_paths.update(static)
            grouped: dict[int, list[CompiledRoute]] = {}
            for route in bucket["dynamic"]:
                grouped.setdefault(route.segment_count, []).append(route)
            dynamic = {
                depth: _build_depth_bucket(members)
                for depth, members in grouped.items()
            }
            self._tables[method] = static, dynamic, {}
            for route in bucket["static"].values():
                all_routes[id(route)] = route
            for route in bucket["dynamic"]:
                all_routes[id(route)] = route
        self._routes = tuple(all_routes.values())
        self._global_static = frozenset(static_paths)
        self._cache_order: deque[tuple[str, str]] = deque()
        self._cache_max = hot_cache_size
        self._fallback = None if fallback == (None, None) else fallback

    def resolve(self, method: str, path: str) -> ResolvedRoute:
        """
        Resolve a request method and path using prebuilt dispatch metadata.

        Parameters
        ----------
        method : str
            HTTP method, matched case-insensitively; HEAD uses the GET table.
        path : str
            Request path to normalize before lookup.

        Returns
        -------
        ResolvedRoute
            Matched route and immutable, converted parameters. Cached results
            may be reused.

        Raises
        ------
        RouteNotFound
            If no route can be resolved and no other method matches the path.
        MethodNotAllowed
            If no route is resolved and another method has a matching path.
        """
        canonical = _METHOD_MAP.get(method)
        if canonical is None:
            method = method.upper()
            canonical = _METHOD_MAP.get(method, method)
        method = canonical
        path = normalize_request_path(path)
        tables = self._tables.get(method)
        if tables is not None:
            resolved = tables[0].get(path)
            if resolved is not None:
                return resolved
            method_cache = tables[2] if self._cache_max else None
            if method_cache and (cached := method_cache.get(path)) is not None:
                return cached
        depth = path.count("/") if path != "/" else 0
        if tables is not None and tables[1]:
            resolved = self.__resolveDynamic(
                path, depth, tables[1], method, method_cache,
            )
            if resolved is not None:
                return resolved
        return self.__raiseForUnmatchedPath(method, path, depth)

    def __raiseForUnmatchedPath(self, method: str, path: str, depth: int) -> Never:
        """
        Distinguish an unknown path from a path registered for another method.

        Parameters
        ----------
        method : str
            Canonical request method that did not match.
        path : str
            Normalized request path.
        depth : int
            Number of path separators, or zero for the root path.

        Returns
        -------
        Never
            Always raise a routing exception; never return a value.

        Raises
        ------
        MethodNotAllowed
            If another method has a static or regex match for the path.
        RouteNotFound
            If no method has a static or regex match for the path.
        """
        if path in self._global_static or any(
            _path_allowed_for_method(tables[0], tables[1], path, depth)
            for other, tables in self._tables.items() if other != method
        ):
            raise MethodNotAllowed(path)
        raise RouteNotFound(path)

    def __resolveDynamic(
        self,
        path: str,
        depth: int,
        table: DepthTable,
        method: str,
        method_cache: dict[str, ResolvedRoute] | None,
    ) -> ResolvedRoute | None:
        """
        Resolve dynamic candidates and cache a successful conversion.

        Parameters
        ----------
        path : str
            Normalized request path.
        depth : int
            Number of path separators, or zero for the root path.
        table : DepthTable
            Dynamic route buckets for the request method.
        method : str
            Canonical request method used as part of the cache key.
        method_cache : dict[str, ResolvedRoute] | None
            Per-method result cache, or None when caching is disabled.

        Returns
        -------
        ResolvedRoute | None
            First matching route with valid parameter conversions, or None if
            no candidate succeeds.

        Raises
        ------
        RouteNotFound
            If a combined match lacks its identifying route marker.
        """
        bucket = _select_bucket(table, path, depth)
        if bucket is None:
            return None
        match = bucket.pattern.fullmatch(path)
        if match is None:
            return None
        try:
            result = _extract_result(match, bucket)
        except (ValueError, OverflowError):
            # A converter can reject a regex match, such as an oversized integer.
            result = _extract_converter_fallback(path, bucket, match)
            if result is None:
                return None
        if method_cache is not None:
            self.__storeCache(method_cache, method, path, result)
        return result

    def options(self, path: str) -> list[str]:
        """
        Return the sorted HTTP methods whose routes match a path.

        Inspect path patterns without converting parameters.

        Parameters
        ----------
        path : str
            Request path to normalize before checking registered methods.

        Returns
        -------
        list[str]
            Matching methods, adding HEAD for GET and OPTIONS for any match.
            Return GET, HEAD, and OPTIONS for an unmatched path with a fallback,
            or an empty list when no fallback is configured.
        """
        path = normalize_request_path(path)
        depth = path.count("/") if path != "/" else 0
        allowed = [
            method for method, tables in self._tables.items()
            if _path_allowed_for_method(tables[0], tables[1], path, depth)
        ]
        if "GET" in allowed and "HEAD" not in allowed:
            allowed.append("HEAD")
        if allowed:
            if "OPTIONS" not in allowed:
                allowed.append("OPTIONS")
        elif self._fallback is not None:
            allowed = ["GET", "HEAD", "OPTIONS"]
        return sorted(allowed)

    def fallback(self) -> tuple | None:
        """
        Return the configured fallback handler metadata.

        Returns
        -------
        tuple | None
            Registered handler tuple, or None when no fallback is configured.
        """
        return self._fallback

    def allRoutes(self) -> list[CompiledRoute]:
        """
        Return a fresh list of all unique compiled routes.

        Returns
        -------
        list[CompiledRoute]
            Routes deduplicated by identity in their original table traversal
            order. The returned list shares the compiled route objects.
        """
        return list(self._routes)

    def invalidateCache(self) -> None:
        """
        Clear all dynamic route results and their FIFO eviction order.

        Returns
        -------
        None
            Empty per-method caches and the shared queue, preserving route tables.
        """
        for tables in self._tables.values():
            tables[2].clear()
        self._cache_order.clear()

    def __storeCache(
        self,
        cache: dict[str, ResolvedRoute],
        method: str,
        path: str,
        result: ResolvedRoute,
    ) -> None:
        """
        Cache a dynamic result, evicting the oldest entry at capacity.

        Parameters
        ----------
        cache : dict[str, ResolvedRoute]
            Cache belonging to the request method.
        method : str
            Canonical request method.
        path : str
            Normalized request path.
        result : ResolvedRoute
            Immutable route resolution to retain.

        Returns
        -------
        None
            Store the result and append its method/path key to the FIFO queue.
        """
        order = self._cache_order
        if len(order) >= self._cache_max:
            old_method, old_path = order.popleft()
            del self._tables[old_method][2][old_path]
        cache[path] = result
        order.append((method, path))
