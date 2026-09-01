from __future__ import annotations
import asyncio
import contextvars
import importlib
import inspect
import threading
from collections import deque
from typing import TYPE_CHECKING, Any, ClassVar, Self
from orionis.container.context.manager import ScopeManager
from orionis.container.context.scope import get_current_scope
from orionis.container.contracts.container import IContainer
from orionis.container.entities.binding import Binding
from orionis.container.enums.lifetimes import Lifetime
from orionis.container.exceptions import CircularDependencyException
from orionis.http.request import Request
from orionis.schemas.validator import Schema
from orionis.introspection.callables.reflection import ReflectionCallable
from orionis.introspection.concretes.reflection import ReflectionConcrete

if TYPE_CHECKING:
    import msgspec
    from collections.abc import Callable
    from orionis.container.contracts.service_provider import IServiceProvider
    from orionis.http.contracts.request import IRequest
    from orionis.introspection.dependencies.entities.argument import Argument
    from orionis.introspection.dependencies.entities.signature import Signature

# Context variable to track the resolution stack for circular dependency detection.
_resolution_stack: contextvars.ContextVar[frozenset[str]] = contextvars.ContextVar(
    "x-orionis-resolution-stack", default=frozenset(),
)

# Sentinel value for empty parameters in inspect signatures,
# used for clarity and to avoid magic numbers.
_INSPECT_EMPTY = inspect.Parameter.empty

class Container(IContainer):
    """
    Resolve services from contracts, aliases and constructor signatures.

    Concurrency
    -----------
    ``__new__`` is thread-safe: concurrent construction of the same subclass
    always yields a single instance, guarded by ``_lock``.

    Inside one event loop, the one-shot work behind ``Lifetime.SINGLETON``,
    ``Lifetime.SCOPED`` and deferred providers is serialised per key, so
    concurrent tasks share a single construction instead of duplicating it.

    No other guarantee is provided: registration methods mutate plain
    dictionaries without locks, and containers shared between distinct event
    loops fall back to per-loop serialisation only.
    """

    # ruff: noqa: ANN401, FBT001, ANN002, ANN003, ARG004, C901

    # Dictionary to hold singleton instances for each class
    # This allows proper inheritance of the singleton pattern
    _instances: ClassVar[dict] = {}

    # Lock for thread-safe singleton instantiation and access
    # This lock ensures that only one thread can create or access instances at a time
    _lock: ClassVar[threading.RLock] = threading.RLock()

    def __new__(cls, *args, **kwargs) -> Self:
        """
        Create and return a singleton instance for each class in the hierarchy.

        Ensures thread-safe singleton instantiation for each subclass of Container.
        Uses double-checked locking to avoid race conditions and optimize performance.

        Returns
        -------
        Self
            The singleton instance of the calling class.
        """
        # Fast path: check if instance already exists for the class
        instance = cls._instances.get(cls)
        if instance is not None:
            return instance

        # Slow path: acquire lock to ensure thread safety
        with cls._lock:

            # Double-check if instance was created while waiting for the lock
            instance = cls._instances.get(cls)
            if instance is not None:
                return instance

            # Create a new instance using the superclass's __new__ method
            instance = super().__new__(cls)

            # Store the instance in the class-specific dictionary
            cls._instances[cls] = instance

            # Return the newly created singleton instance
            return instance

    def __init__(self) -> None:
        """
        Initialize the internal state of the container.

        Sets up internal data structures for dependency injection and ensures
        single initialization per instance.

        Returns
        -------
        None
            This method does not return a value.
        """
        # Prevent multiple initializations for singleton instances
        if "_Container__initialized" not in self.__dict__:

            # Deferred providers for lazy loading
            self._deferred_providers: dict[str, dict[str, str]] = {}

            # Cache for singleton instances
            self.__singleton_cache: dict[str, Any] = {}

            # Aliases mapping for service resolution
            self.__aliases: dict[str, type] = {}

            # Registered bindings for services
            self.__bindings: dict[Any, Binding] = {}

            # Tracks resolved deferred providers
            self.__cache_resolve_deferred_providers: set[Any] = set()

            # Per-key locks serialising one-shot construction, paired with the
            # loop they were created on so a second loop never awaits a foreign lock.
            self.__creation_locks: dict[
                Any, tuple[asyncio.AbstractEventLoop, asyncio.Lock],
            ] = {}

            # Mark as initialized to prevent re-initialization
            self._Container__initialized = True

    def __creationLock(
        self,
        key: Any,
    ) -> asyncio.Lock:
        """
        Return the creation lock for a key, bound to the running loop.

        Parameters
        ----------
        key : Any
            Contract or deferred provider key whose construction is guarded.

        Returns
        -------
        asyncio.Lock
            Lock owned by the running loop for this key. A new lock replaces
            any entry created on a different loop.
        """
        loop = asyncio.get_running_loop()
        entry = self.__creation_locks.get(key)
        if entry is not None and entry[0] is loop:
            return entry[1]

        lock = asyncio.Lock()
        self.__creation_locks[key] = (loop, lock)
        return lock

    @staticmethod
    def __isBeingResolved(
        concrete: type[Any],
    ) -> bool:
        """
        Determine whether a concrete type is already resolving in this task.

        Parameters
        ----------
        concrete : type[Any]
            Concrete class about to be constructed.

        Returns
        -------
        bool
            True when the type is already on the current resolution stack,
            which means the caller must skip the creation lock it already owns.
        """
        return (
            f"{concrete.__module__}.{concrete.__name__}"
            in _resolution_stack.get()
        )

    def __aliasService(
        self,
        alias: str | None,
    ) -> str | None:
        """
        Validate and normalize a service alias string.

        Parameters
        ----------
        alias : str | None
            The alias string to validate and normalize.

        Returns
        -------
        str | None
            The validated and normalized alias string, or None if not provided.

        Raises
        ------
        TypeError
            If the alias is not a string.
        ValueError
            If the alias is empty after stripping.
        """
        # Return None if alias is not provided
        if alias is None:
            return None

        # Ensure alias is a string
        if not isinstance(alias, str):
            error_msg = "alias must be a string."
            raise TypeError(error_msg)

        # Strip leading and trailing whitespace from the alias
        alias = alias.strip()

        # Ensure alias is not empty after stripping
        if not alias:
            error_msg = "Alias cannot be empty."
            raise ValueError(error_msg)

        return alias

    def __ensureCanOverrideScope(
        self,
        override: bool,
        abstract: type[Any],
        scope: dict[Any, Any],
    ) -> None:
        """
        Ensure that a service can be overridden in the current scope.

        Parameters
        ----------
        override : bool
            Whether to allow overriding existing registrations.
        abstract : type[Any]
            The abstract contract type to check.
        scope : dict[Any, Any]
            The current scope dictionary.

        Returns
        -------
        None
            This method does not return a value.

        Raises
        ------
        ValueError
            If the service already exists in the current scope and
            override is False.
        """
        # Allow override if specified
        if override:
            return

        # Raise if the abstract contract already exists in the scope
        if abstract in scope:
            error_msg = "Service already exists in current scope."
            raise ValueError(error_msg)

    def __ensureCanOverrideGlobal(
        self,
        override: bool,
        abstract: type[Any],
        alias: str | None,
    ) -> None:
        """
        Ensure that a service or alias can be overridden globally.

        Parameters
        ----------
        override : bool
            Whether to allow overriding existing registrations.
        abstract : type[Any]
            The abstract contract type to check.
        alias : str | None
            The alias to check for conflicts.

        Returns
        -------
        None
            This method does not return a value.

        Raises
        ------
        ValueError
            If the service or alias already exists globally and override is False.
        """
        # Allow override if specified
        if override:
            return

        # Raise if the abstract contract already exists in global bindings
        if abstract in self.__bindings:
            error_msg = "Service already registered for this contract."
            raise ValueError(error_msg)

        # Raise if the alias already exists in global aliases
        if alias is not None and alias in self.__aliases:
            error_msg = "Service already registered for this alias."
            raise ValueError(error_msg)

    def __ensureInstanceImplements(
        self,
        abstract: type[Any],
        instance: object,
    ) -> None:
        """
        Ensure that an instance implements the specified abstract class.

        Parameters
        ----------
        abstract : type[Any]
            The abstract class type to check against.
        instance : object
            The object instance to validate.

        Returns
        -------
        None
            This method does not return a value.

        Raises
        ------
        TypeError
            If `abstract` is not a class type or `instance` does not implement it.
        """
        # Check that the abstract argument is a class type
        if not isinstance(abstract, type):
            error_msg = "abstract must be a class type."
            raise TypeError(error_msg)

        # Ensure the instance implements the abstract class
        if not isinstance(instance, abstract):
            error_msg = (
                f"{type(instance).__name__} must implement {abstract.__name__}"
            )
            raise TypeError(error_msg)

    def __ensureConcreteImplements(
        self,
        abstract: type[Any],
        concrete: type[Any],
    ) -> None:
        """
        Ensure that a concrete class implements the specified abstract class.

        Parameters
        ----------
        abstract : type[Any]
            The abstract class type to check against.
        concrete : type[Any]
            The concrete class type to validate.

        Returns
        -------
        None
            This method does not return a value.

        Raises
        ------
        TypeError
            If `abstract` or `concrete` is not a class type, or if `concrete`
            does not implement `abstract`.
        """
        # Validate that abstract is a class type
        if not isinstance(abstract, type):
            error_msg = "abstract must be a class type."
            raise TypeError(error_msg)

        # Validate that concrete is a class type
        if not isinstance(concrete, type):
            error_msg = "concrete must be a class type."
            raise TypeError(error_msg)

        # Ensure concrete implements abstract
        if not issubclass(concrete, abstract):
            error_msg = (
                f"{concrete.__name__} must implement {abstract.__name__}"
            )
            raise TypeError(error_msg)

    def __bind(
        self,
        lifetime: Lifetime,
        abstract: type[Any] | None,
        concrete: type[Any],
        *,
        alias: str | None,
        override: bool,
    ) -> bool:
        """
        Bind a concrete implementation to an abstract contract with a given lifetime.

        Parameters
        ----------
        lifetime : Lifetime
            The lifetime of the binding (singleton, scoped, or transient).
        abstract : type[Any] | None
            The abstract contract class to associate with the concrete class,
            or None to use the concrete class as the contract.
        concrete : type[Any]
            The concrete class to register.
        alias : str | None
            An optional alias for the registration.
        override : bool
            If True, override any existing registration.

        Returns
        -------
        bool
            True if the binding was registered successfully.

        Raises
        ------
        TypeError
            If the concrete is not a class type or type validation fails.
        ValueError
            If the alias is invalid or already registered, or if the contract is
            already registered and override is False.
        """
        # Validate the contract if provided
        if abstract is not None:
            self.__ensureConcreteImplements(abstract, concrete)
        else:
            if not isinstance(concrete, type):
                error_msg = "concrete must be a class type."
                raise TypeError(error_msg)
            abstract = concrete

        # Validate the alias; a missing alias passes through untouched
        alias = self.__aliasService(alias)

        # Enforce override rules for service registration
        self.__ensureCanOverrideGlobal(override, abstract, alias)

        # Register the binding in the container
        binding = Binding(
            contract=abstract,
            concrete=concrete,
            lifetime=lifetime,
            alias=alias,
        )
        self.__bindings[abstract] = binding
        if alias is not None:
            self.__aliases[alias] = abstract

        # Registration successful
        return True

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
        # Ensure the provided instance is not a class type
        if isinstance(instance, type):
            error_msg = "instance() expects an initialized object, not a class."
            raise TypeError(error_msg)

        # Validate the contract if provided
        if abstract is not None:
            self.__ensureInstanceImplements(abstract, instance)
        else:
            abstract = type(instance)

        # Validate the alias; a missing alias passes through untouched
        alias = self.__aliasService(alias)

        # Get the current scope for registration
        scope: dict[Any, Any] | None = self.getCurrentScope()

        # Enforce override rules for service registration
        if scope is not None:
            self.__ensureCanOverrideScope(override, abstract, scope)
        else:
            self.__ensureCanOverrideGlobal(override, abstract, alias)

        if scope is not None:
            if alias is not None:
                msg_error = "Alias registration is only allowed globally."
                raise ValueError(msg_error)
            # Register instance in the current scope
            scope[abstract] = instance
        else:
            # Register as singleton in the container
            binding = Binding(
                contract=abstract,
                concrete=type(instance),
                lifetime=Lifetime.SINGLETON,
                alias=alias,
            )
            self.__bindings[abstract] = binding
            self.__singleton_cache[abstract] = instance
            if alias is not None:
                self.__aliases[alias] = abstract

        # Registration successful
        return True

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
        # Register the binding with transient lifetime
        return self.__bind(
            lifetime=Lifetime.TRANSIENT,
            abstract=abstract,
            concrete=concrete,
            alias=alias,
            override=override,
        )

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
        # Register the binding with singleton lifetime
        return self.__bind(
            lifetime=Lifetime.SINGLETON,
            abstract=abstract,
            concrete=concrete,
            alias=alias,
            override=override,
        )

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
        # Register the binding with scoped lifetime
        return self.__bind(
            lifetime=Lifetime.SCOPED,
            abstract=abstract,
            concrete=concrete,
            alias=alias,
            override=override,
        )

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
        # Resolve alias to abstract type if key is a string
        if isinstance(key, str):
            abstract = self.__aliases.get(key)
            if abstract is None:
                return False
        else:
            abstract = key

        # Check if the abstract type is present in the current scope
        scope: dict[Any, Any] | None = self.getCurrentScope()
        if scope is not None and abstract in scope:
            return True

        # Check if the abstract type is registered in the container bindings
        return (
            abstract in self.__bindings or
            abstract in self.__singleton_cache
        )

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
        # Instantiate and return a new ScopeManager for scoped service management
        return ScopeManager()

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
        # Return the current active scope context from ScopedContext
        return get_current_scope()

    async def __resolveDeferredProvider(
        self,
        key: type[Any] | str,
    ) -> None:
        """
        Resolve and register a deferred service provider for a given service.

        Parameters
        ----------
        key : type[Any] | str
            The service type or fully qualified class name for which to find the
            deferred provider.

        Returns
        -------
        None
            This method does not return a value. Registers the deferred service
            provider in the application container if found.

        Notes
        -----
        Loads and registers a deferred provider for the specified service.
        Returns early if the provider is already resolved or is a built-in.
        """
        # Return early if there are no deferred providers to resolve
        if not self._deferred_providers:
            return

        # Convert class type to fully qualified class name string if necessary
        if isinstance(key, type):
            key = f"{key.__module__}.{key.__name__}"

        # Check existence in the provider registry BEFORE the resolved-cache.
        # Most types are not deferred providers, so this exits in one lookup
        # without ever touching __cache_resolve_deferred_providers.
        if key not in self._deferred_providers:
            return

        # Already resolved — no work needed
        if key in self.__cache_resolve_deferred_providers:
            return

        # Serialise the bootstrap: registering and booting a provider spans
        # several await points, so without this lock concurrent tasks would run
        # the same provider twice and its register() would raise on the second.
        async with self.__creationLock(key):

            # Another task may have completed the bootstrap while waiting
            if key in self.__cache_resolve_deferred_providers:
                return

            # Retrieve provider metadata for the given key
            provider_metadata = self._deferred_providers.get(key)

            # Import the module declaring the provider class
            module = importlib.import_module(provider_metadata["module"])
            provider_class = getattr(module, provider_metadata["class"], None)

            # Build and register the provider instance
            instance: IServiceProvider = await self.build(provider_class)
            instance.register()

            # Boot the provider instance, supporting async and sync methods
            if inspect.iscoroutinefunction(instance.boot):
                await instance.boot()
            else:
                instance.boot()

            # Cache the resolved service to prevent redundant resolution
            self.__cache_resolve_deferred_providers.add(key)

    async def __resolveKey(
        self,
        key: type[Any] | str,
    ) -> type[Any]:
        """
        Resolve a service key to its abstract type.

        Parameters
        ----------
        key : type[Any] | str
            Service identifier as an abstract type or alias string.

        Returns
        -------
        type[Any]
            The resolved abstract service type.

        Raises
        ------
        ValueError
            If a string alias is not registered after deferred resolution.
        """
        # If the key is a string.
        if isinstance(key, str):

            # First check if it's an alias registered in the container.
            abstract = self.__aliases.get(key)

            # If not found, attempt to resolve a deferred provider
            # that may register this alias.
            if abstract is None:
                await self.__resolveDeferredProvider(key)
                abstract = self.__aliases.get(key)
                if abstract is None:
                    error_msg = f"Service '{key}' is not registered."
                    raise ValueError(error_msg)

            # At this point, abstract is guaranteed to be a type due to
            # the way aliases are registered.
            return abstract

        # If the key is already a type, return it directly (fast path).
        return key

    async def __resolveOrBuild(
        self,
        abstract: type[Any],
        key: type[Any] | str,
        *args: tuple[Any, ...],
        **kwargs: dict[str, Any],
    ) -> Any:
        """
        Resolve a binding for an abstract service or build it when unbound.

        Parameters
        ----------
        abstract : type[Any]
            Abstract service type to resolve.
        key : type[Any] | str
            Original service key used for resolution and error messages.
        *args : tuple[Any, ...]
            Positional arguments passed to the resolver or builder.
        **kwargs : dict[str, Any]
            Keyword arguments passed to the resolver or builder.

        Returns
        -------
        Any
            Resolved service instance.

        Raises
        ------
        ValueError
            If no binding exists and the service cannot be resolved.
        """
        # Lookup the binding for the abstract type. This is a single lookup that
        binding = self.__bindings.get(abstract)

        # If no binding exists, attempt to resolve a deferred provider
        # that may register this service, then check again for the binding.
        if binding is None:
            await self.__resolveDeferredProvider(abstract)
            binding = self.__bindings.get(abstract)
            if binding is None:
                if isinstance(abstract, type):
                    return await self.build(abstract, *args, **kwargs)
                error_msg = f"Service '{key}' is not registered."
                raise ValueError(error_msg)

        # At this point, we have a binding and can resolve it according to its lifetime.
        return await self.__resolve(binding, *args, **kwargs)

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
        # If key is a type and already has a singleton instance, return it immediately.
        if not isinstance(key, str):
            _cached = self.__singleton_cache.get(key)
            if _cached is not None:
                return _cached

        # Resolve the key to an abstract type, handling aliases and deferred providers.
        abstract = await self.__resolveKey(key)

        # If the abstract type has a cached singleton instance, return it immediately.
        _cached = self.__singleton_cache.get(abstract)
        if _cached is not None:
            return _cached

        # Check if the abstract type is present in the current
        # scope and return it if found.
        scope: dict[Any, Any] | None = get_current_scope()
        if scope is not None and abstract in scope:
            return scope[abstract]

        # Finally, resolve or build the service instance according to
        # its binding or auto-resolve it if unbound.
        return await self.__resolveOrBuild(abstract, key, *args, **kwargs)

    async def __resolve(
        self,
        binding: Binding,
        *args: tuple[Any, ...],
        **kwargs: dict[str, Any],
    ) -> Any:
        """
        Resolve an instance from a binding according to its lifetime.

        Parameters
        ----------
        binding : Binding
            The binding to resolve.
        *args : tuple[Any, ...]
            Positional arguments for the constructor.
        **kwargs : dict[str, Any]
            Keyword arguments for the constructor.

        Returns
        -------
        Any
            The resolved instance according to the binding's lifetime.

        Raises
        ------
        RuntimeError
            If there is no active scope for scoped services.
        """
        lt = binding.lifetime

        # Handle singleton lifetime: return cached instance or create and cache it
        if lt is Lifetime.SINGLETON:
            cached = self.__singleton_cache.get(binding.contract)
            if cached is not None:
                return cached
            return await self.__createSingleton(binding, *args, **kwargs)

        # Handle transient lifetime: always create a new instance
        if lt is Lifetime.TRANSIENT:
            return await self.__autoResolveClass(binding.concrete, *args, **kwargs)

        # Handle scoped lifetime: store instance in the current scope
        if lt is Lifetime.SCOPED:
            scope: dict[Any, Any] | None = get_current_scope()
            if scope is None:
                error_msg = (
                    "No active scope for scoped service. "
                    "Use 'beginScope()' to create a scope."
                )
                raise RuntimeError(error_msg)

            if binding.contract in scope:
                return scope[binding.contract]

            return await self.__createScoped(binding, scope, *args, **kwargs)

        # This line should never be reached due to the enum handling
        return None

    async def __createSingleton(
        self,
        binding: Binding,
        *args: tuple[Any, ...],
        **kwargs: dict[str, Any],
    ) -> Any:
        """
        Build and cache the single instance backing a singleton binding.

        Parameters
        ----------
        binding : Binding
            The singleton binding to materialize.
        *args : tuple[Any, ...]
            Positional arguments for the constructor.
        **kwargs : dict[str, Any]
            Keyword arguments for the constructor.

        Returns
        -------
        Any
            The cached instance, built by this call or by the task that won
            the creation lock.
        """
        concrete = binding.concrete

        # A nested resolution of the same concrete type already owns the lock;
        # going through it again would deadlock instead of reporting the cycle.
        if self.__isBeingResolved(concrete):
            return await self.__autoResolveClass(concrete, *args, **kwargs)

        async with self.__creationLock(binding.contract):

            # Another task may have finished the construction while waiting
            cached = self.__singleton_cache.get(binding.contract)
            if cached is not None:
                return cached

            instance = await self.__autoResolveClass(concrete, *args, **kwargs)
            self.__singleton_cache[binding.contract] = instance
            return instance

    async def __createScoped(
        self,
        binding: Binding,
        scope: dict[Any, Any],
        *args: tuple[Any, ...],
        **kwargs: dict[str, Any],
    ) -> Any:
        """
        Build and store the instance backing a scoped binding.

        Parameters
        ----------
        binding : Binding
            The scoped binding to materialize.
        scope : dict[Any, Any]
            The active scope that owns the resulting instance.
        *args : tuple[Any, ...]
            Positional arguments for the constructor.
        **kwargs : dict[str, Any]
            Keyword arguments for the constructor.

        Returns
        -------
        Any
            The scoped instance, built by this call or by the task that won
            the creation lock.
        """
        concrete = binding.concrete

        # A nested resolution of the same concrete type already owns the lock;
        # going through it again would deadlock instead of reporting the cycle.
        if self.__isBeingResolved(concrete):
            return await self.__autoResolveClass(concrete, *args, **kwargs)

        async with self.__creationLock(binding.contract):

            # Another task may have finished the construction while waiting
            if binding.contract in scope:
                return scope[binding.contract]

            instance = await self.__autoResolveClass(concrete, *args, **kwargs)
            scope[binding.contract] = instance
            return instance

    async def __autoResolveClass(
        self,
        type_: Callable[..., Any],
        *args: tuple[Any, ...],
        **kwargs: dict[str, Any],
    ) -> Any:
        """
        Automatically instantiate a class with injected dependencies.

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
            The instantiated object with dependencies resolved.

        Raises
        ------
        CircularDependencyException
            If a circular dependency is detected.
        Exception
            If the type cannot be auto-resolved.
        """
        # Build a unique key for this type to track within the current task's stack
        type_key = f"{type_.__module__}.{type_.__name__}"

        # Detect circular dependencies using the per-task ContextVar stack.
        # This is safe under async concurrency: each asyncio Task has its own
        # context, so concurrent resolutions of the same type never collide.
        stack = _resolution_stack.get()
        if type_key in stack:
            error_msg = (
                f"Circular dependency detected while resolving argument '{type_key}'."
            )
            raise CircularDependencyException(error_msg)

        # Push type onto the per-task stack; token allows precise rollback
        token = _resolution_stack.set(stack | {type_key})
        try:
            # Get constructor dependencies using reflection
            signature = ReflectionConcrete(type_).constructorSignature()

            # If no dependencies, instantiate directly
            if not signature.hasParameters():
                return type_(*args, **kwargs)

            # Resolve dependencies recursively
            final_args, final_kwargs = await self.__resolveSignature(
                signature, *args, **kwargs,
            )

            # Instantiate with resolved arguments
            return type_(*final_args, **final_kwargs)

        finally:
            # Restore the previous stack state for this task
            _resolution_stack.reset(token)

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
        # Resolve deferred providers for the given type if not already bound
        if not self.bound(type_):
            await self.__resolveDeferredProvider(type_)

        # Ensure the provided type is a class
        if not isinstance(type_, type):
            error_msg = "build() expects a class type to instantiate."
            raise TypeError(error_msg)

        # Auto-resolve and instantiate the class with provided arguments
        return await self.__autoResolveClass(type_, *args, **kwargs)

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
        # Ensure the provided function is callable and not a class/type
        if not callable(fn) or isinstance(fn, type):
            error_msg = "invoke() expects a non-class callable as the first argument."
            raise TypeError(error_msg)

        # Resolve dependencies and execute the callable
        return await self.__autoResolveCallable(fn, *args, **kwargs)

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
        # Retrieve the method from the instance by name
        method = getattr(instance, method_name, None)

        # Check if the method exists
        if method is None:
            error_msg = (
                f"Method '{method_name}' not found on instance of type "
                f"'{type(instance).__name__}'."
            )
            raise AttributeError(error_msg)

        # Ensure the attribute is callable
        if not callable(method):
            error_msg = (
                f"Attribute '{method_name}' on instance of type "
                f"'{type(instance).__name__}' is not callable."
            )
            raise TypeError(error_msg)

        # Invoke the method with automatic dependency resolution
        return await self.__autoResolveCallable(method, *args, **kwargs)

    async def __autoResolveCallable(
        self,
        type_: Callable[..., Any],
        *args: tuple,
        **kwargs: dict,
    ) -> type[Any]:
        """
        Resolve and invoke a callable, injecting dependencies.

        Parameters
        ----------
        type_ : Callable[..., Any]
            The callable to invoke.
        *args : tuple
            Positional arguments for the callable.
        **kwargs : dict
            Keyword arguments for the callable.

        Returns
        -------
        Any
            The result of the callable invocation.

        Raises
        ------
        OrionisContainerCircularDependencyException
            If a circular dependency is detected.
        Exception
            If the callable cannot be auto-resolved.
        """
        # Get callable dependencies using reflection
        signature = ReflectionCallable(type_).getDependencies()

        # If no dependencies, invoke directly
        if not signature.hasParameters():
            if inspect.iscoroutinefunction(type_):
                return await type_(*args, **kwargs)
            return type_(*args, **kwargs)

        # Resolve dependencies recursively
        final_args, final_kwargs = await self.__resolveSignature(
            signature, *args, **kwargs,
        )

        # Invoke the callable with resolved arguments
        if inspect.iscoroutinefunction(type_):
            return await type_(*final_args, **final_kwargs)
        return type_(*final_args, **final_kwargs)

    async def __resolveSignature( # NOSONAR
        self,
        signature: Signature,
        *args: tuple[Any, ...],
        **kwargs: dict[str, Any],
    ) -> tuple[list[Any], dict[str, Any]]:
        """
        Resolve arguments for a callable signature using dependency injection.

        Parameters
        ----------
        signature : Signature
            The signature object containing argument metadata.
        *args : tuple[Any, ...]
            Positional arguments to pass to the callable.
        **kwargs : dict[str, Any]
            Keyword arguments to pass to the callable.

        Returns
        -------
        tuple[list[Any], dict[str, Any]]
            A tuple containing the resolved positional and keyword arguments.
        """
        # Copy kwargs to avoid mutating the original dictionary
        remaining_kwargs: dict[str, Any] = dict(kwargs) if kwargs else {}

        # Use a deque for efficient popping of positional arguments from the left
        positional: deque[Any] = deque(args) if args else deque()

        # Prepare containers for resolved arguments
        final_args: list[Any] = []
        final_kwargs: dict[str, Any] = {}

        # Pre-check if there are any deferred providers to resolve,
        # to optimize the loop.
        _has_deferred = bool(self._deferred_providers)

        # Cache references to container bindings and singletons for
        # faster access within the loop.
        _bindings       = self.__bindings
        _singleton      = self.__singleton_cache

        # Iterate over arguments in definition order
        for name, argument in signature.arguments():

            # Resolve deferred provider for this argument's type if applicable.
            if _has_deferred and argument.full_class_path in self._deferred_providers:
                await self.__resolveDeferredProvider(argument.full_class_path)

            # Determine if the argument is keyword-only
            is_keyword_only = argument.is_keyword_only

            # Handle positional or positional-or-keyword arguments
            if not is_keyword_only:

                # Special handling for msgspec.Struct subclasses with default value
                if argument.is_schema:
                    final_args.append(await self.__resolveSchemaArgument(argument))
                    continue

                # Optimize resolution for arguments that are bound in
                # the container by type.
                arg_type = argument.type
                is_bound = arg_type in _bindings or arg_type in _singleton
                if is_bound and name not in remaining_kwargs:
                    resolved = await self.make(arg_type)
                    final_args.append(resolved)
                    continue

                # Use next positional argument if available
                if positional:
                    value = positional.popleft()
                    final_args.append(value)
                    continue

                # Use provided keyword argument if available
                if name in remaining_kwargs:
                    final_args.append(remaining_kwargs[name])
                    del remaining_kwargs[name]
                    continue

                # Fallback to automatic resolution if no explicit value
                resolved = await self.__resolveArgument(argument)
                final_args.append(resolved)

            else:

                # Special handling for msgspec.Struct subclasses with default value
                if argument.is_schema:
                    final_kwargs[name] = await self.__resolveSchemaArgument(argument)
                    continue

                # Use provided keyword argument if available
                if name in remaining_kwargs:
                    final_kwargs[name] = remaining_kwargs[name]
                    del remaining_kwargs[name]
                    continue

                # Optimize resolution for keyword-only arguments that are bound in
                # the container by type.
                arg_type = argument.type
                if arg_type in _bindings or arg_type in _singleton:
                    resolved = await self.make(arg_type)
                    final_kwargs[name] = resolved
                    continue

                # Fallback to automatic resolution for keyword-only argument
                resolved = await self.__resolveArgument(argument)
                final_kwargs[name] = resolved

        # Append any remaining positional arguments
        final_args.extend(positional)

        # Add any remaining unused keyword arguments
        final_kwargs.update(remaining_kwargs)

        # Return resolved positional and keyword arguments
        return final_args, final_kwargs

    async def __resolveSchemaArgument(
        self,
        argument: Argument,
    ) -> msgspec.Struct:
        """
        Resolve an argument that is a subclass of msgspec.Struct.

        Parameters
        ----------
        argument : Argument
            The argument metadata to resolve.

        Returns
        -------
        msgspec.Struct
            The resolved value for the msgspec.Struct argument.

        Raises
        ------
        Exception
            If there is an error during resolution of the msgspec.Struct argument.
        """
        # Create a request instance to access the request data
        request: IRequest = await self.make(Request)

        # Retrieve the raw data from the request body
        data = await request.data()

        # Validate and deserialize the data using the specified schema
        return Schema.validate(data, argument.type)

    async def __resolveArgument(
        self,
        argument: Argument,
    ) -> Any:
        """
        Resolve a single argument for dependency injection.

        Parameters
        ----------
        argument : Argument
            The argument metadata to resolve.

        Returns
        -------
        Any
            The resolved value for the argument.

        Raises
        ------
        TypeError
            If the argument cannot be resolved or is a built-in type.
        """
        if not argument.resolved:

            # Do not auto-resolve built-in or typing types
            if argument.module_name in ("builtins", "typing"):
                error_msg = (
                    f"Cannot auto-resolve built-in type '{argument.type.__name__}' "
                    f"for parameter '{argument.name}'. Provide a default value."
                )
                raise TypeError(error_msg)

            # If the argument is not bound in the container, raise an error
            error_msg = (
                f"Cannot resolve parameter '{argument.name}'. "
                "Provide a default value or register the dependency."
            )
            raise TypeError(error_msg)

        # Prefer the default value if it exists
        if argument.default is not _INSPECT_EMPTY:
            return argument.default

        # Resolve from container or auto-resolve
        return await self.make(argument.type)
