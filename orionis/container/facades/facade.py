# ruff: noqa: PLC0415, TC001
# Load Application lazily to avoid bootstrap cycles; retain its public contract.
"""Resolve global or scoped services through class-level facades."""

from orionis.container.context.manager import ScopeManager
from orionis.container.context.scope import ScopedContext
from orionis.container.facades.meta import FacadeMeta, ScopedFacadeMeta
from orionis.foundation.contracts.application import IApplication


class Facade(metaclass=FacadeMeta):
    """Resolve container services through a shared class-level interface."""

    _application: IApplication | None = None
    """Cached application instance shared across all facade subclasses."""
    _pinned_instance: object | None = None
    """Resolved service retained while the facade is pinned."""

    @classmethod
    def getFacadeAccessor(cls) -> str | type:
        """
        Return the container accessor key for this facade.

        Returns
        -------
        str | type
            Return the alias or contract class used to resolve the binding.

        Raises
        ------
        NotImplementedError
            Raise when the subclass does not implement this method.
        """
        # Enforce subclass implementation for the accessor key.
        error_msg = f"Class {cls.__name__} must define getFacadeAccessor()"
        raise NotImplementedError(error_msg)

    @classmethod
    async def resolve(cls, *args: object, **kwargs: object) -> object:
        """
        Resolve the service instance bound to this facade.

        Parameters
        ----------
        *args : object
            Forward positional arguments to the container make call.
        **kwargs : object
            Forward keyword arguments to the container make call.

        Returns
        -------
        object
            Return the resolved service instance from the application.

        Raises
        ------
        RuntimeError
            Raise when the application has not been booted.
        """
        # Lazily initialize the shared application instance.
        if cls._application is None:
            from orionis.foundation.application import Application

            cls._application = Application()

        # Guard against resolution before application boot.
        if not cls._application.isBooted:
            error_msg = "Application not booted. Boot your app first."
            raise RuntimeError(error_msg)

        # Delegate service construction to the application container.
        return await cls._application.make(
            cls.getFacadeAccessor(),
            *args,
            **kwargs,
        )

    @classmethod
    async def pin(cls) -> None:
        """
        Pin the resolved instance on this facade class.

        Returns
        -------
        None
            This method does not return a value.
        """
        # Cache the currently resolved instance for direct reuse.
        cls._pinned_instance = await cls.resolve()

    @classmethod
    def unpin(cls) -> None:
        """
        Clear the pinned instance from this facade class.

        Returns
        -------
        None
            This method does not return a value.
        """
        # Remove the cached pinned instance to restore normal resolution.
        cls._pinned_instance = None


class ScopedFacade(Facade, metaclass=ScopedFacadeMeta):
    """Expose a service already bound to the caller's active scope.

    Scoped services never enter the process-wide facade cache. Closing a
    scope also prevents access from child tasks that inherited that scope.
    """

    @classmethod
    def scopedInstance(cls) -> object:
        """Return the service bound to the active scope.

        Returns
        -------
        object
            Request-local service instance.

        Raises
        ------
        RuntimeError
            If no active scope contains the service.
        """
        scope = ScopedContext.getCurrentScope()
        if isinstance(scope, ScopeManager) and scope.isActive:
            instance = scope[cls.getFacadeAccessor()]
            if instance is not None:
                return instance
        error_msg = f"{cls.__name__} requires an active scope with a bound service."
        raise RuntimeError(error_msg)

    @classmethod
    async def resolve(cls, *_args: object, **_kwargs: object) -> object:
        """Resolve the current instance without constructing a global service.

        Parameters
        ----------
        *_args : object
            Unused; scoped instances are bound by their lifecycle owner.
        **_kwargs : object
            Unused; scoped instances are bound by their lifecycle owner.

        Returns
        -------
        object
            Service belonging to the active scope.
        """
        return cls.scopedInstance()

    @classmethod
    async def pin(cls) -> None:
        """Validate scope availability without retaining the service globally.

        Returns
        -------
        None
            This method does not return a value.
        """
        cls.scopedInstance()

    @classmethod
    def unpin(cls) -> None:
        """Leave lifetime management to the owning scope.

        Returns
        -------
        None
            This method does not return a value.
        """
