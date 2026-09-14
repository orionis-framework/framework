import inspect
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Generator
    from types import TracebackType

# Cache for dispatcher functions to avoid recreating them on every access.
_dispatcher_cache: dict[tuple[type, str], object] = {}

class _FacadeDispatch:
    """Deferred facade call, awaitable and usable as an async context manager.

    Building this object never touches the container; the underlying
    service is only resolved once the caller either awaits the instance
    directly (``await Facade.method(...)``) or enters it with
    ``async with Facade.method(...) as value:``.
    """

    __slots__ = ("_args", "_cls", "_context", "_kwargs", "_name")

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
        kwargs : dict of str to object
            Keyword arguments to forward to the resolved attribute.

        Returns
        -------
        None
            This method does not return a value.
        """
        self._cls = cls
        self._name = name
        self._args = args
        self._kwargs = kwargs
        self._context: object = None

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
        Generator
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
    ) -> bool:
        """
        Exit the async context manager entered by ``__aenter__``.

        Parameters
        ----------
        exc_type : type[BaseException] or None
            The exception type raised inside the block, if any.
        exc : BaseException or None
            The exception instance raised inside the block, if any.
        traceback : TracebackType or None
            The traceback for the raised exception, if any.

        Returns
        -------
        bool
            Whatever the resolved context manager returns from its own
            ``__aexit__``.
        """
        return await self._context.__aexit__(exc_type, exc, traceback)

class FacadeMeta(type):

    def __getattr__(cls, name: str) -> object:
        """
        Return a proxy for a facade attribute.

        Parameters
        ----------
        name : str
            Specify the requested attribute name.

        Returns
        -------
        object
            Return the pinned attribute when an instance is pinned;
            otherwise return a dispatcher that defers resolution until
            the call is awaited or entered as an async context manager.
        """
        # Use pinned instances for direct, zero-resolution access.
        if cls._pinned_instance is not None:
            return getattr(cls._pinned_instance, name)

        # Return a cached dispatcher when one already exists for this (class, attr).
        # This avoids creating a new function object and closure on every access.
        cache_key = (cls, name)
        cached = _dispatcher_cache.get(cache_key)
        if cached is not None:
            return cached

        # Build the dispatcher once and store it for subsequent calls.
        def dispatcher(*args: object, **kwargs: object) -> _FacadeDispatch:
            """
            Build the deferred call for this attribute access.

            Parameters
            ----------
            *args : object
                Pass positional arguments to the target callable.
            **kwargs : object
                Pass keyword arguments to the target callable.

            Returns
            -------
            _FacadeDispatch
                Deferred call, awaitable directly or usable as an async
                context manager.
            """
            return _FacadeDispatch(cls, name, args, kwargs)

        # Cache the dispatcher for future accesses to avoid recreating it.
        _dispatcher_cache[cache_key] = dispatcher

        # Return the newly created dispatcher for this attribute access.
        return dispatcher

class ScopedFacadeMeta(FacadeMeta):
    """Dispatch attributes exclusively to the active scope's service."""

    def __getattr__(cls, name: str) -> object:
        """Return an attribute from the current scoped service.

        Parameters
        ----------
        name : str
            Service attribute requested by the caller.

        Returns
        -------
        object
            Attribute of the service bound to the active scope.

        Raises
        ------
        RuntimeError
            If the scope is closed or the service has not been bound.
        """
        return getattr(cls.scopedInstance(), name)
