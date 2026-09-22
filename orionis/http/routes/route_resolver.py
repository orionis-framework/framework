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
    """Select a depth and, when available, a literal first-segment bucket."""
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
    """Check a method's existing lookup structures without extracting params."""
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

def _build_matching_bucket(routes: list[CompiledRoute]) -> _DepthBucket:
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

def _build_depth_bucket(
    routes: list[CompiledRoute],
    start: int = 1,
) -> _DepthBucket | _PrefixIndex:
    """Partition literal segments while preserving overlapping route order."""
    minimum_partition_size = 16
    if len(routes) < minimum_partition_size:
        return _build_matching_bucket(routes)
    while True:
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
                return _build_matching_bucket(routes)
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
    """Include overlapping candidates in each literal branch in route order.

    At most eight wildcard alternatives are repeated per branch. Larger
    wildcard populations retain the shared ordered matcher to bound storage.
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

class RouteResolver(IRouteResolver):
    """Resolve compiled routes using static maps and ordered dynamic buckets."""

    __slots__ = (
        "_cache", "_cache_max", "_cache_order", "_fallback", "_global_static",
        "_routes", "_tables",
    )

    def __init__(
        self,
        routes: dict[str, dict],
        hot_cache_size: int = 512,
        fallback: tuple | None = None,
    ) -> None:
        """Build lookup tables and the bounded FIFO result cache.

        Parameters
        ----------
        routes : dict[str, dict]
            Compiler output grouped by method and static/dynamic paths.
        hot_cache_size : int, optional
            Maximum cached dynamic results; zero disables caching.
        fallback : tuple | None, optional
            Handler for unmatched paths.

        Raises
        ------
        TypeError
            If the cache capacity is not an integer.
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
            self._tables[method] = static, dynamic
            for route in bucket["static"].values():
                all_routes[id(route)] = route
            for route in bucket["dynamic"]:
                all_routes[id(route)] = route
        self._routes = tuple(all_routes.values())
        self._global_static = frozenset(static_paths)
        self._cache: dict[tuple[str, str], ResolvedRoute] = {}
        self._cache_order: deque[tuple[str, str]] = deque()
        self._cache_max = hot_cache_size
        self._fallback = None if fallback == (None, None) else fallback

    def resolve(self, method: str, path: str) -> ResolvedRoute:
        """Resolve the method/path pair using prebuilt dispatch metadata.

        Returns
        -------
        ResolvedRoute
            Matched route and immutable, converted parameters.

        Raises
        ------
        RouteNotFound
            If no route matches the path.
        MethodNotAllowed
            If the path exists only under another method.
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
        if tables is not None and tables[1]:
            cache_key = (method, path) if self._cache_max else None
            cached = self._cache.get(cache_key) if cache_key is not None else None
            if cached is not None:
                return cached
            depth = path.count("/") if path != "/" else 0
            resolved = self.__resolveDynamic(path, depth, tables[1], cache_key)
            if resolved is not None:
                return resolved
        else:
            depth = path.count("/") if path != "/" else 0
        if path in self._global_static or any(
            _path_allowed_for_method(static, dynamic, path, depth)
            for other, (static, dynamic) in self._tables.items() if other != method
        ):
            raise MethodNotAllowed(path)
        raise RouteNotFound(path)

    def __resolveDynamic(
        self,
        path: str,
        depth: int,
        table: DepthTable,
        cache_key: tuple[str, str] | None,
    ) -> ResolvedRoute | None:
        """Match a dynamic bucket, caching only successful immutable results."""
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
            return None
        if cache_key is not None:
            self.__storeCache(cache_key, result)
        return result

    def options(self, path: str) -> list[str]:
        """Return sorted allowed methods, including implicit HEAD and OPTIONS."""
        path = normalize_request_path(path)
        depth = path.count("/") if path != "/" else 0
        allowed = [
            method for method, (static, dynamic) in self._tables.items()
            if _path_allowed_for_method(static, dynamic, path, depth)
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
        """Return the fallback handler, or None when none is registered."""
        return self._fallback

    def allRoutes(self) -> list[CompiledRoute]:
        """Return every compiled route once in registration-table order."""
        return list(self._routes)

    def invalidateCache(self) -> None:
        """Clear cached dynamic lookup results."""
        self._cache.clear()
        self._cache_order.clear()

    def __storeCache(self, key: tuple[str, str], result: ResolvedRoute) -> None:
        """Evict the oldest result when adding to a full FIFO cache."""
        cache = self._cache
        if key not in cache:
            order = self._cache_order
            if len(cache) >= self._cache_max:
                del cache[order.popleft()]
            order.append(key)
        cache[key] = result
