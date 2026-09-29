from __future__ import annotations
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING
from typing import Any

if TYPE_CHECKING:
    from collections.abc import Callable
    from orionis.container.context.manager import ScopeManager

class IContainer(ABC):

    # ruff: noqa: ANN401

    @abstractmethod
    def instance(
        self,
        abstract: type[Any] | None,
        instance: object,
        *,
        alias: str | None = None,
        override: bool = False,
    ) -> bool:
        """
        Register an object instance as a singleton in the container.

        Parameters
        ----------
        abstract : type[Any] | None
            The abstract contract class to associate with the instance, or None.
        instance : object
            The initialized object to register.
        alias : str | None, optional
            An optional alias for the registration.
        override : bool, optional
            If True, override any existing registration.

        Returns
        -------
        bool
            True if the instance was registered successfully.

        Raises
        ------
        TypeError
            If the instance is a class, or if type validation fails.
        ValueError
            If the alias is invalid or already registered, or if the contract is
            already registered and override is False.
        """

    @abstractmethod
    def transient(
        self,
        abstract: type[Any] | None,
        concrete: type[Any],
        *,
        alias: str | None = None,
        override: bool = False,
    ) -> bool:
        """
        Register a transient service binding.

        Parameters
        ----------
        abstract : type[Any] | None
            The abstract contract type to bind, or None to use the concrete type.
        concrete : type[Any]
            The concrete implementation type to register.
        alias : str | None, optional
            An optional alias for the service.
        override : bool, optional
            Whether to override an existing registration.

        Returns
        -------
        bool
            True if the binding was registered successfully.
        """

    @abstractmethod
    def singleton(
        self,
        abstract: type[Any] | None,
        concrete: type[Any],
        *,
        alias: str | None = None,
        override: bool = False,
    ) -> bool:
        """
        Register a singleton service binding.

        Parameters
        ----------
        abstract : type[Any] | None
            The abstract contract type to bind, or None to use the concrete type.
        concrete : type[Any]
            The concrete implementation type to register.
        alias : str | None, optional
            An optional alias for the service.
        override : bool, optional
            Whether to override an existing registration.

        Returns
        -------
        bool
            True if the binding was registered successfully.
        """

    @abstractmethod
    def scoped(
        self,
        abstract: type[Any] | None,
        concrete: type[Any],
        *,
        alias: str | None = None,
        override: bool = False,
    ) -> bool:
        """
        Register a scoped service binding.

        Parameters
        ----------
        abstract : type[Any] | None
            The abstract contract type to bind, or None to use the concrete type.
        concrete : type[Any]
            The concrete implementation type to register.
        alias : str | None, optional
            An optional alias for the service.
        override : bool, optional
            Whether to override an existing registration.

        Returns
        -------
        bool
            True if the binding was registered successfully.
        """

    @abstractmethod
    def bound(
        self,
        key: type[Any] | str,
    ) -> bool:
        """
        Determine if a key is bound in the container or current scope.

        Parameters
        ----------
        key : type[Any] | str
            The abstract type or alias to check for binding.

        Returns
        -------
        bool
            True if the key is bound in the current scope or container,
            otherwise False.
        """

    @abstractmethod
    def beginScope(self) -> ScopeManager:
        """
        Begin a new scope context manager for scoped services.

        Parameters
        ----------
        self : Container
            The container instance.

        Returns
        -------
        ScopeManager
            Context manager for managing the lifecycle of scoped services.
        """

    @abstractmethod
    def getCurrentScope(self) -> dict[Any, Any] | None:
        """
        Get the current active scope context for scoped services.

        Parameters
        ----------
        self : Container
            The container instance.

        Returns
        -------
        dict[Any, Any] | None
            The current active scope context if available, otherwise None.
            The scope context is a dictionary-like object that contains
            instances of scoped services registered in the current scope.

        Notes
        -----
        Returns None if there is no active scope. Use `beginScope()` to create
        a new scope context before accessing scoped services.
        """

    @abstractmethod
    async def make(
        self,
        key: type[Any] | str,
        *args: tuple[Any, ...],
        **kwargs: dict[str, Any],
    ) -> Any:
        """
        Resolve and return a service instance by key.

        Parameters
        ----------
        key : type[Any] | str
            The abstract type or alias to resolve.
        *args : tuple[Any, ...]
            Positional arguments for instantiation.
        **kwargs : dict[str, Any]
            Keyword arguments for instantiation.

        Returns
        -------
        Any
            The resolved service instance.

        Raises
        ------
        ValueError
            If the service is not registered and cannot be auto-resolved.
        """

    @abstractmethod
    async def build(
        self,
        type_: Callable[..., Any],
        *args: tuple[Any, ...],
        **kwargs: dict[str, Any],
    ) -> Any:
        """
        Build and return an instance of the specified type.

        Parameters
        ----------
        type_ : Callable[..., Any]
            The class to instantiate.
        *args : tuple[Any, ...]
            Positional arguments for the constructor.
        **kwargs : dict[str, Any]
            Keyword arguments for the constructor.

        Returns
        -------
        Any
            Instantiated object of the specified type.

        Raises
        ------
        TypeError
            If the type cannot be auto-resolved by the container.

        Notes
        -----
        Resolves deferred providers before attempting instantiation.
        """

    @abstractmethod
    async def invoke(
        self,
        fn: Callable[..., Any],
        *args: tuple[Any, ...],
        **kwargs: dict[str, Any],
    ) -> Any:
        """
        Invoke a callable with automatic dependency injection.

        Parameters
        ----------
        fn : Callable[..., Any]
            The callable to invoke. Must not be a class or type.
        *args : tuple[Any, ...]
            Positional arguments for the callable.
        **kwargs : dict[str, Any]
            Keyword arguments for the callable.

        Returns
        -------
        Any
            The result of the callable execution with dependencies injected.

        Raises
        ------
        TypeError
            If `fn` is not a callable or is a class/type.
        """

    @abstractmethod
    async def call(
        self,
        instance: object,
        method_name: str,
        *args: tuple,
        **kwargs: dict,
    ) -> Any:
        """
        Invoke a method on an object instance with automatic dependency injection.

        Parameters
        ----------
        instance : object
            The object instance containing the method.
        method_name : str
            The name of the method to invoke.
        *args : tuple
            Positional arguments for the method.
        **kwargs : dict
            Keyword arguments for the method.

        Returns
        -------
        Any
            The result of the method invocation with dependencies resolved.

        Raises
        ------
        AttributeError
            If the method is not found on the instance.
        TypeError
            If the attribute is not callable.
        """
