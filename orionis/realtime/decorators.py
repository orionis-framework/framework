from types import FunctionType
from typing import TYPE_CHECKING, cast, overload

if TYPE_CHECKING:
    from collections.abc import Callable

MAX_TARGET_LENGTH = 128
REMOTE_ATTRIBUTE = "__orionis_remote_name__"

def validate_remote_name(name: str) -> None:
    """
    Validate a public method name or alias without evaluating it.

    Parameters
    ----------
    name : str
        Explicit developer-owned remote name.

    Returns
    -------
    None
        Accept a bounded public Python identifier.

    Raises
    ------
    ValueError
        If the name is not a string or a public Python identifier of at most
        128 characters.
    """
    if (
        not isinstance(name, str) or not name.isidentifier()
        or name.startswith("_") or len(name) > MAX_TARGET_LENGTH
    ):
        message = "Remote names must be public identifiers of at most 128 characters"
        raise ValueError(message)

@overload
def remote[F: Callable](function: F, *, name: str | None = None) -> F:  # noqa: D418
    """
    Mark a supplied instance method for remote dispatch.

    Parameters
    ----------
    function : F
        Original instance-method function.
    name : str | None, optional
        Public alias, or None to use the Python method name.

    Returns
    -------
    F
        Original function with validated remote metadata attached.

    Raises
    ------
    TypeError
        If the supplied object is not a Python function.
    ValueError
        If the method name or alias is invalid, or metadata is already attached.
    """

@overload
def remote[F: Callable](  # noqa: D418
    function: None = None, *, name: str | None = None,
) -> Callable[[F], F]:
    """
    Create a decorator for remote dispatch with an optional alias.

    Parameters
    ----------
    function : None, optional
        Omit the function to return a decorator.
    name : str | None, optional
        Public alias, or None to use the decorated method's Python name.

    Returns
    -------
    Callable[[F], F]
        Decorator attaching metadata without wrapping the original function.

    Raises
    ------
    ValueError
        If the supplied alias is invalid.
    """

def remote[F: Callable](
    function: F | None = None, *, name: str | None = None,
) -> F | Callable[[F], F]:
    """
    Mark an instance method for remote dispatch without wrapping it.

    Parameters
    ----------
    function : F | None, optional
        Method supplied by bare decorator syntax.
    name : str | None, optional
        Explicit public alias, otherwise the Python method name.

    Returns
    -------
    F | Callable[[F], F]
        Original function, or a decorator returning the original function.

    Raises
    ------
    TypeError
        If the decorated object is not a Python function.
    ValueError
        If the method name or alias is invalid, or the method is already marked.
    """
    if name is not None:
        validate_remote_name(name)

    def decorate(target: F) -> F:
        """
        Attach validated metadata to the original callable.

        Parameters
        ----------
        target : F
            Developer-owned instance method.

        Returns
        -------
        F
            The exact input callable.

        Raises
        ------
        TypeError
            If the object is not an instance-method function.
        ValueError
            If the method name is invalid or remote metadata is already attached.
        """
        if not isinstance(target, FunctionType):
            message = "@remote requires an ordinary instance method"
            raise TypeError(message)
        validate_remote_name(target.__name__)
        if hasattr(target, REMOTE_ATTRIBUTE):
            message = "A remote method may only be decorated once"
            raise ValueError(message)
        setattr(target, REMOTE_ATTRIBUTE, name or target.__name__)
        return cast("F", target)

    return decorate if function is None else decorate(function)
