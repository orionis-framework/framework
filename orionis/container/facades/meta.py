# ruff: noqa: TC003
# Keep deferred-dispatch protocol annotations available at runtime.
"""Dispatch facade attributes while preserving Python introspection protocols."""

import inspect
from collections.abc import Callable, Generator
from functools import lru_cache
from types import TracebackType


class _FacadeDispatch:
    """Deferred facade call, awaitable and usable as an async context manager.

    Building this object never touches the container; the underlying
    service is only resolved once the caller either awaits the instance
    directly (``await Facade.method(...)``) or enters it with
    ``async with Facade.method(...) as value:``.
    """

    __slots__ = ("_args", "_cls", "_context", "_kwargs", "_name")
    """Declare the instance attribute slots reserved by this class."""

    def __init__(
        self,
        cls: type,
        name: str,
        args: tuple[object, ...],
        kwargs: dict[str, object],
    ) -> None:
        """
        Store the pending call until it is awaited or entered.

        Parameters
        ----------
        cls : type
            Facade class the attribute was requested on.
        name : str
            Name of the attribute requested on the resolved service.
        args : tuple of object
            Positional arguments to forward to the resolved attribute.
        kwargs : dict of str ``to`` object
            Keyword arguments to forward to the resolved attribute.

        Returns
        -------
        None
            This method does not return a value.
        """
        self._cls = cls
        """Facade class the attribute was requested on."""
        self._name = name
        """Name of the attribute requested on the resolved service."""
        self._args = args
        """Positional arguments to forward to the resolved attribute."""
        self._kwargs = kwargs
        """Keyword arguments to forward to the resolved attribute."""
        self._context: object = None
        """Runtime context made available to the operation and its callbacks."""

    async def __resolve(self) -> object:
        """
        Resolve the service and evaluate the requested attribute.

        Returns
        -------
        object
            The call result when the attribute is callable, otherwise
            the plain attribute value.
        """
        # A fresh service instance is resolved on every call, honoring
        # transient bindings exactly as a direct container.make() would.
        service = await self._cls.resolve()
        attr = getattr(service, self._name)
        if callable(attr):
            return attr(*self._args, **self._kwargs)
        return attr

    def __await__(self) -> Generator[object, None, object]:
        """
        Drive the deferred call to completion when awaited directly.

        Returns
        -------
        collections.abc.Generator
            Iterator driving the underlying resolution coroutine.
        """
        return self.__awaitImpl().__await__()

    async def __awaitImpl(self) -> object:
        """
        Resolve the call and transparently await an awaitable result.

        Returns
        -------
        object
            The awaited value for async results, the direct value for
            sync results, or the raw attribute value.
        """
        result = await self.__resolve()
        if inspect.isawaitable(result):
            return await result
        return result

    async def __aenter__(self) -> object:
        """
        Resolve the call and enter the resulting async context manager.

        Returns
        -------
        object
            The value yielded by the resolved context manager.
        """
        self._context = await self.__resolve()
        return await self._context.__aenter__()

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool | None:
        """
        Exit the async context manager entered by ``__aenter__``.

        Parameters
        ----------
        exc_type : type[BaseException] or None
            The exception type raised inside the block, if any.
        exc : BaseException or None
            The exception instance raised inside the block, if any.
        traceback : types.TracebackType or None
            The traceback for the raised exception, if any.

        Returns
        -------
        bool or None
            Whatever the resolved context manager returns from its own
            ``__aexit__``.
        """
        return await self._context.__aexit__(exc_type, exc, traceback)


@lru_cache(maxsize=1024)
def _dispatcher_for(cls: type, name: str) -> Callable[..., _FacadeDispatch]:
    """Reuse a dispatcher within a bounded cache of facade attributes.

    Parameters
    ----------
    cls : type
        Facade class requesting the attribute.
    name : str
        Service attribute dispatched after resolution.

    Returns
    -------
    collections.abc.Callable
        Function creating a deferred call without resolving a service.
    """

    def dispatcher(*args: object, **kwargs: object) -> _FacadeDispatch:
        """Build the deferred call for this attribute access.

        Parameters
        ----------
        *args : object
            Positional arguments forwarded to the target callable.
        **kwargs : object
            Keyword arguments forwarded to the target callable.

        Returns
        -------
        orionis.container.facades.meta._FacadeDispatch
            Awaitable call supporting asynchronous context management.
        """
        return _FacadeDispatch(cls, name, args, kwargs)

    return dispatcher


class FacadeMeta(type):
    """Resolve the facade meta service through the application facade."""

    def __getattr__(cls, name: str) -> object:
        """
        Return a proxy for a facade attribute.

        Parameters
        ----------
        cls : type
            Class on which the operation is performed.
        name : str
            Specify the requested attribute name.

        Returns
        -------
        object
            Return the pinned attribute when an instance is pinned;
            otherwise return a dispatcher that defers resolution until
            the call is awaited or entered as an async context manager.

        Raises
        ------
        AttributeError
            If an undefined Python protocol attribute is requested.
        """
        if name.startswith("__") and name.endswith("__"):
            raise AttributeError(name)
        # Use pinned instances for direct, zero-resolution access.
        if cls._pinned_instance is not None:
            return getattr(cls._pinned_instance, name)

        return _dispatcher_for(cls, name)


class ScopedFacadeMeta(FacadeMeta):
    """Dispatch attributes exclusively to the active scope's service."""

    def __getattr__(cls, name: str) -> object:
        """Return an attribute from the current scoped service.

        Parameters
        ----------
        cls : type
            Class on which the operation is performed.
        name : str
            Service attribute requested by the caller.

        Returns
        -------
        object
            Attribute of the service bound to the active scope.

        Raises
        ------
        AttributeError
            If an undefined Python protocol attribute is requested.
        RuntimeError
            If the scope is closed or the service has not been bound.
        """
        if name.startswith("__") and name.endswith("__"):
            raise AttributeError(name)
        return getattr(cls.scopedInstance(), name)
