from __future__ import annotations
import inspect
import re
from collections.abc import Sequence
from collections.abc import Set as AbstractSet
from typing import TYPE_CHECKING
from orionis.http.middleware import BaseMiddleware

if TYPE_CHECKING:
    from collections.abc import Callable
    from orionis.http.routes.types import MiddlewareInput

# Expected number of elements in a [Controller, method_name] action list.
_ACTION_LIST_LENGTH: int = 2

# Matches one or more consecutive forward slashes anywhere in a path.
_MULTI_SLASH_RE: re.Pattern = re.compile(r"/{2,}")

def normalize_path(path: str) -> str:
    """
    Normalise an HTTP route path to a canonical form.

    Rules applied in order:

    1. Strip leading/trailing whitespace.
    2. Collapse consecutive slashes (``//``, ``///``, …) into one.
    3. Ensure the path starts with exactly one ``/``.
    4. Remove any trailing ``/`` (except for the root path ``/``).

    Parameters
    ----------
    path : str
        Raw route path supplied by the developer.

    Returns
    -------
    str
        Normalised path, e.g. ``'//users//me/'`` → ``'/users/me'``.
    """
    path = path.strip()
    path = _MULTI_SLASH_RE.sub("/", path)
    if not path.startswith("/"):
        path = "/" + path
    if path != "/":
        path = path.rstrip("/")
    return path

def normalize_request_path(path: str) -> str:
    """
    Normalise a request path for route resolution.

    Parameters
    ----------
    path : str
        Raw request path from the HTTP layer.

    Returns
    -------
    str
        Path with a leading ``/`` and without trailing slashes
        on non-root paths.
    """
    if not path:
        return "/"
    if path[0] != "/":
        path = "/" + path
    if len(path) > 1 and path[-1] == "/":
        path = path.rstrip("/") or "/"
    return path

def strip_regex_anchors(pattern: str) -> str:
    """
    Remove start and end anchors from a regex pattern.

    Parameters
    ----------
    pattern : str
        Regex pattern that may start with ``^`` and end with ``$``.

    Returns
    -------
    str
        Pattern without a leading ``^`` and trailing ``$``.
    """
    if pattern and pattern[0] == "^":
        pattern = pattern[1:]
    if pattern and pattern[-1] == "$":
        pattern = pattern[:-1]
    return pattern

def flatten_middleware(
    *middleware: MiddlewareInput,
) -> list[type[BaseMiddleware]]:
    """
    Flatten and validate middleware arguments into a plain list.

    Accepts middleware classes passed either individually or wrapped
    in a ``list``, ``tuple``, ``set`` or ``frozenset`` (one level of
    nesting), so all of these are equivalent::

        flatten_middleware(A, B)
        flatten_middleware([A, B])
        flatten_middleware((A,), B)

    Parameters
    ----------
    *middleware : type[BaseMiddleware] | list | tuple | set | frozenset
        Middleware classes or containers of middleware classes.

    Returns
    -------
    list[type[BaseMiddleware]]
        Flat list of validated middleware classes, in the order
        they were provided.

    Raises
    ------
    TypeError
        If any entry is not a ``BaseMiddleware`` subclass.
    """
    flat: list[type[BaseMiddleware]] = []
    for entry in middleware:
        items = (
            entry
            if isinstance(entry, (Sequence, AbstractSet))
            else (entry,)
        )
        validated = []
        for m in items:
            if not isinstance(m, type) or not issubclass(m, BaseMiddleware):
                error_msg = (
                    "All middleware must be subclasses of BaseMiddleware"
                )
                raise TypeError(error_msg)
            validated.append(m)
        # Unordered containers use import names for a repeatable execution order.
        if isinstance(entry, AbstractSet):
            validated.sort(key=_middleware_key)
        flat.extend(validated)
    return flat


def _middleware_key(middleware: type[BaseMiddleware]) -> tuple[str, str]:
    """
    Return a stable ordering key for middleware supplied in sets.

    Parameters
    ----------
    middleware : type[BaseMiddleware]
        Middleware class to order consistently when using unordered containers.

    Returns
    -------
    tuple[str, str]
        The module name and qualified class name used as the sort key.
    """
    return middleware.__module__, middleware.__qualname__

def is_valid_handler(action: object) -> bool:
    """
    Check whether the route action parser accepts a candidate.

    Parameters
    ----------
    action : object
        Candidate function, invokable controller class, or controller/method
        pair to validate using the same rules as parse_action.

    Returns
    -------
    bool
        True if parse_action accepts the candidate; False if it raises
        TypeError or ValueError for an unsupported or malformed action.

    Notes
    -----
    Does not instantiate controllers or invoke handlers. Controller attribute
    lookup may execute descriptors; exceptions other than TypeError and
    ValueError propagate. Importability and dependency resolution are checked
    later in the routing lifecycle.
    """
    try:
        parse_action(action)
    except (TypeError, ValueError):
        return False
    return True

def parse_action( # NOSONAR
    action: object,
) -> tuple[Callable, None] | tuple[type, str]:
    """
    Parse and validate a route action into a normalised tuple.

    Supports three forms:

    1. **Invokable controller** — concrete class that defines ``__call__``.
    2. **Controller + method** — two-element list or tuple with a concrete class
       ``[ControllerClass, 'method_name']``.
    3. **Python function** — plain function or coroutine function, excluding
       lambdas. Callable instances, bound methods and builtins are unsupported.

    Parameters
    ----------
    action : object
        Candidate action to validate against the three forms described above.

    Returns
    -------
    tuple[type, None]
        When *action* is an invokable controller class.
    tuple[Callable, None]
        When *action* is a standalone callable.
    tuple[type, str]
        When *action* is a ``[ControllerClass, 'method_name']`` list.

    Raises
    ------
    TypeError
        If a bare class does not define ``__call__``, if list elements
        have wrong types, if a controller class is abstract in either form,
        or if *action* is none of the accepted forms.
    ValueError
        If the list does not have exactly two elements, or if the
        controller class does not expose the requested method.
    """
    # 1. Invokable controller: bare class passed directly
    if inspect.isclass(action):
        handler = next((
            base.__dict__["__call__"] for base in action.__mro__
            if "__call__" in base.__dict__
        ), None)
        if isinstance(handler, (staticmethod, classmethod)):
            handler = handler.__func__
        if not callable(handler) or inspect.isabstract(action):
            error_msg = (
                f"Class '{action.__name__}' cannot be used as an invokable "
                "controller: it must be concrete and define a callable __call__. "
                "Use a concrete invokable class or "
                "[ConcreteController, 'method_name']."
            )
            raise TypeError(error_msg)
        return action, None

    # 2. Plain callable (function, coroutine function, …)
    # Only functions can be restored from a function import descriptor.
    if (
        inspect.isfunction(action)
        and callable(action)
        and not inspect.iscoroutine(action)
        and action.__name__ != "<lambda>"
    ):
        return action, None

    # 3. [ControllerClass, 'method_name'] list
    if isinstance(action, (list, tuple)):
        if len(action) != _ACTION_LIST_LENGTH:
            error_msg = (
                "Action list must have exactly two elements: "
                "[Controller, 'method_name']"
            )
            raise ValueError(error_msg)

        _callable, _handle = action

        if not isinstance(_callable, type) or inspect.isabstract(_callable):
            error_msg = (
                "First element of action list must be a concrete class"
            )
            raise TypeError(error_msg)

        if not isinstance(_handle, str):
            error_msg = "Second element of action list must be a string"
            raise TypeError(error_msg)

        # Verify the method exists on the class (including inherited ones)
        # and is callable before accepting the action.
        handler_attr = getattr(_callable, _handle, None)
        if not callable(handler_attr):
            error_msg = (
                f"Class {_callable} does not have method {_handle}"
            )
            # ValueError is part of the documented public contract.
            raise ValueError(error_msg)  # noqa: TRY004

        return _callable, _handle

    error_msg = (
        "Action must be a non-lambda Python function (sync or async), "
        "a bare invokable class (defining __call__), or a two-element "
        "list/tuple [Controller, 'method_name']. "
        "Callable instances and bound methods are not supported."
    )
    raise TypeError(error_msg)
