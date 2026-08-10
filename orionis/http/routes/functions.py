from __future__ import annotations
import inspect
import re
from typing import TYPE_CHECKING
from orionis.http.middleware import BaseMiddleware

if TYPE_CHECKING:
    from collections.abc import Callable

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
    *middleware: type[BaseMiddleware] | list | tuple | set | frozenset,
) -> list[type[BaseMiddleware]]:
    """
    Flatten and validate middleware arguments into a plain list.

    Accepts middleware classes passed either individually or wrapped
    in a ``list``, ``tuple``, ``set`` or ``frozenset`` (one level of
    nesting), so all of these are equivalent::

        flattenMiddleware(A, B)
        flattenMiddleware([A, B])
        flattenMiddleware((A,), B)

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
            if isinstance(entry, (list, tuple, set, frozenset))
            else (entry,)
        )
        for m in items:
            if not isinstance(m, type) or not issubclass(m, BaseMiddleware):
                error_msg = (
                    "All middleware must be subclasses of BaseMiddleware"
                )
                raise TypeError(error_msg)
            flat.append(m)
    return flat

def is_valid_handler(action: Callable) -> bool:
    """
    Validate whether an action qualifies as a valid route handler.

    Parameters
    ----------
    action : Callable
        The action to validate.

    Returns
    -------
    bool
        ``True`` if the action is a valid handler; ``False`` otherwise.
    """
    # Reject coroutine functions; they cannot be used as route handlers.
    if inspect.iscoroutine(action):
        return False

    # Reject non-callables
    # only plain functions and invokable classes are valid handlers.
    if not callable(action):
        return False

    # Reject plain lambdas; they cannot be used as route handlers.
    return not (inspect.isfunction(action) and action.__name__ == "<lambda>")

def parse_action(
    action: Callable | list | type,
) -> tuple[Callable, None] | tuple[type, str]:
    """
    Parse and validate a route action into a normalised tuple.

    Supports three forms:

    1. **Invokable controller** — bare class that defines ``__call__``.
    2. **Controller + method** — two-element list
       ``[ControllerClass, 'method_name']``.
    3. **Callable** — any plain function or coroutine function.

    Parameters
    ----------
    action : Callable | list | type
        One of the three forms described above.

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
        have wrong types, or if *action* is none of the accepted forms.
    ValueError
        If the list does not have exactly two elements, or if the
        controller class does not expose the requested method.
    """
    # 1. Invokable controller: bare class passed directly
    if inspect.isclass(action):
        if "__call__" not in action.__dict__:
            error_msg = (
                f"Class '{action.__name__}' cannot be used as an invokable "
                "controller because it does not define __call__. "
                "Either add __call__ or use [Controller, 'method_name']."
            )
            raise TypeError(error_msg)
        return action, None

    # 2. Plain callable (function, coroutine function, …)
    if is_valid_handler(action):
        return action, None

    # 3. [ControllerClass, 'method_name'] list
    if isinstance(action, list):
        if len(action) != _ACTION_LIST_LENGTH:
            error_msg = (
                "Action list must have exactly two elements: "
                "[Controller, 'method_name']"
            )
            raise ValueError(error_msg)

        _callable, _handle = action

        if not isinstance(_callable, type):
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
        "Action must be a callable, a bare invokable class (defining __call__), "
        "or a list [Controller, 'method_name']"
    )
    raise TypeError(error_msg)
