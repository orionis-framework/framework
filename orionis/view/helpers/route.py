from __future__ import annotations
import re
from typing import TYPE_CHECKING, Any
from urllib.parse import quote
from orionis.view.exceptions import ViewRouteException
from orionis.view.helpers.url import _absolute_url

if TYPE_CHECKING:
    from orionis.foundation.contracts.application import IApplication

# ruff: noqa: ANN401, PLC0415

# Matches route path placeholders such as ``{id}`` or ``{id:int}``.
_ROUTE_PARAM_RE: re.Pattern = re.compile(r"\{(\w+)(?::\w+)?\}")

def _build_route_path(
    template: str,
    params: dict[str, Any],
) -> tuple[str, dict[str, Any]]:
    """
    Replace path placeholders with their values.

    Parameters
    ----------
    template : str
        Route path containing ``{name}`` or ``{name:type}`` segments.
    params : dict[str, Any]
        Values available to fill the placeholders.

    Returns
    -------
    tuple[str, dict[str, Any]]
        The interpolated path and the parameters left unused, which the
        caller appends as a query string.

    Raises
    ------
    ViewRouteException
        If a placeholder has no matching value in *params*.
    """
    pieces: list[str] = []
    used: set[str] = set()
    cursor = 0

    for match in _ROUTE_PARAM_RE.finditer(template):
        key = match.group(1)
        if key not in params:
            error_msg = (
                f"Missing value for route parameter '{key}' "
                f"while building '{template}'."
            )
            raise ViewRouteException(error_msg)
        pieces.append(template[cursor:match.start()])
        pieces.append(quote(str(params[key]), safe=""))
        cursor = match.end()
        used.add(key)

    pieces.append(template[cursor:])
    extra = {key: value for key, value in params.items() if key not in used}
    return "".join(pieces), extra

async def _load_named_routes(app: IApplication) -> dict[str, str]:
    """
    Collect every named route as a mapping of name to path template.

    Parameters
    ----------
    app : IApplication
        Application container used to build the route loader.

    Returns
    -------
    dict[str, str]
        Route name mapped to its raw path, e.g. ``'/users/{id:int}'``.
    """
    from orionis.http.routes.loader import RouteLoader

    loader = await app.build(RouteLoader)
    named: dict[str, str] = {}

    for bucket in loader.load().values():
        for compiled in bucket["static"].values():
            if compiled.name:
                named.setdefault(compiled.name, compiled.path)
        for compiled in bucket["dynamic"]:
            if compiled.name:
                named.setdefault(compiled.name, compiled.path)

    return named

def _global_route(app: IApplication) -> Any:
    """
    Build the async ``route`` template global bound to the application.

    Parameters
    ----------
    app : IApplication
        Application container used for service resolution.

    Returns
    -------
    Any
        Async callable that builds the URL of a named route.
    """
    named: dict[str, str] = {}
    loaded = False

    async def route(name: str, **params: Any) -> str:
        """
        Build the URL of a route registered with ``.name()``.

        Parameters
        ----------
        name : str
            Registered route name.
        **params : Any
            Values for the path placeholders; leftover values are
            appended as the query string.

        Returns
        -------
        str
            Absolute URL when a request is in scope, otherwise the
            interpolated path.

        Raises
        ------
        ViewRouteException
            If no route is registered under *name*.
        """
        nonlocal loaded
        if not loaded:
            named.update(await _load_named_routes(app))
            loaded = True

        template = named.get(name)
        if template is None:
            error_msg = f"No route is registered under the name '{name}'."
            raise ViewRouteException(error_msg)

        path, query = _build_route_path(template, params)
        return await _absolute_url(app, path, query)

    return route
