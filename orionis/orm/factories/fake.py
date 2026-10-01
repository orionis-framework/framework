from functools import lru_cache
from types import MappingProxyType
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable
    from random import Random

def _camel_case(name: str) -> str:
    """Normalize a provider method while retaining its original word casing.

    Parameters
    ----------
    name : str
        Public method name declared by the backend.

    Returns
    -------
    str
        Orionis camelCase method name.
    """
    if "_" not in name:
        return name
    first, *rest = name.split("_")
    return first + "".join(word[:1].upper() + word[1:] for word in rest)

@lru_cache(maxsize=128)
def _provider_aliases(names: tuple[str, ...]) -> MappingProxyType[str, str]:
    """Compile immutable aliases for one set of backend member names.

    Parameters
    ----------
    names : tuple of str
        Sorted public and private names reported by the backend.

    Returns
    -------
    MappingProxyType of str to str
        Shared camelCase aliases containing no bound provider methods.
    """
    aliases: dict[str, str] = {}
    for name in names:
        if name.startswith("_") or name == "seed":
            continue
        alias = _camel_case(name)
        if alias not in aliases or name == alias:
            aliases[alias] = name
    return MappingProxyType(aliases)

class _ProviderState:

    __slots__ = ("aliases", "backend", "revision")

    def __init__(self, backend: object) -> None:
        """Initialize provider names and cache revision for one instance.

        Parameters
        ----------
        backend : object
            Instance-local data generator.

        Returns
        -------
        None
            Apply the described operation.
        """
        self.backend: Any = backend
        self.revision = 0
        self.refresh()

    def refresh(self) -> None:
        """
        Publish aliases and invalidate views after backend registration.

        Returns
        -------
        None
            Replace the immutable name table and advance this instance's revision.
        """
        self.aliases = _provider_aliases(tuple(dir(self.backend)))
        self.revision += 1

class _ProviderView:

    __slots__ = ("_backend", "_cache", "_revision", "_state")

    def __init__(self, backend: object, state: _ProviderState) -> None:
        """Bind a normal, unique, or optional provider view.

        Parameters
        ----------
        backend : object
            Backend object dispatching this view's calls.
        state : _ProviderState
            Names and revision shared by views of the same generator.

        Returns
        -------
        None
            Apply the described operation.
        """
        self._backend: Any = backend
        self._state = state
        self._revision = state.revision
        self._cache: dict[str, Callable[..., Any]] = {}

    def __getattr__(self, name: str) -> Any:  # noqa: ANN401
        """
        Return a bound camelCase provider method.

        Parameters
        ----------
        name : str
            Public Orionis method name.

        Returns
        -------
        Any
            Bound callable, including dynamically registered providers.

        Raises
        ------
        AttributeError
            If the name is unknown, private, snake_case, or a raw property.
        """
        if "_" in name or name == "seed":
            error_msg = f"Use camelCase provider methods; {name!r} is unavailable."
            raise AttributeError(error_msg)
        if self._revision != self._state.revision:
            self._cache.clear()
            self._revision = self._state.revision
        method = self._cache.get(name)
        if method is not None:
            return method
        original = self._state.aliases.get(name)
        if original is not None:
            method = getattr(self._backend, original)
            if callable(method):
                self._cache[name] = method
                return method
        error_msg = f"{type(self).__name__} has no provider method {name!r}."
        raise AttributeError(error_msg)

    def __dir__(self) -> list[str]:
        """
        List camelCase provider methods available for the selected locale.

        Returns
        -------
        list of str
            Public facade members and callable provider aliases.
        """
        methods = {
            alias for alias, name in self._state.aliases.items()
            if callable(getattr(self._state.backend, name))
        }
        methods.update(name for name in super().__dir__() if "_" not in name)
        return sorted(methods)

class UniqueFake(_ProviderView):

    __slots__ = ()

    def clear(self) -> None:
        """
        Clear values tracked by this backend's unique view.

        Returns
        -------
        None
            Previously generated values become eligible for reuse.
        """
        self._backend.clear()

    def excludeTypes(self, types: list[type]) -> UniqueFake:
        """
        Exclude selected result types from uniqueness checks.

        Parameters
        ----------
        types : list of type
            Result types for which repeated values are allowed.

        Returns
        -------
        UniqueFake
            View sharing the backend's unique pool and dispatch lifecycle.
        """
        return UniqueFake(self._backend.exclude_types(types), self._state)

    def __getitem__(self, locale: str) -> UniqueFake:
        """
        Select the configured locale without exposing a native proxy.

        Parameters
        ----------
        locale : str
            Locale already configured on the backend.

        Returns
        -------
        UniqueFake
            Locale-specific uniqueness view.
        """
        return UniqueFake(self._backend[locale], self._state)

class OptionalFake(_ProviderView):

    __slots__ = ()

class Fake(_ProviderView):

    __slots__ = ("_optional", "_unique")

    def __init__(self, backend: object) -> None:
        """Wrap an independently configured backend without changing its seed.

        Parameters
        ----------
        backend : object
            Faker-compatible provider instance created by factory infrastructure.

        Returns
        -------
        None
            Apply the described operation.
        """
        super().__init__(backend, _ProviderState(backend))
        self._unique: UniqueFake | None = None
        self._optional: OptionalFake | None = None

    @property
    def unique(self) -> UniqueFake:
        """
        Return the typed camelCase uniqueness view.

        Returns
        -------
        UniqueFake
            Stable view retaining the instance's unique history.
        """
        view = self._unique
        if view is None:
            view = self._unique = UniqueFake(self._backend.unique, self._state)
        return view

    @property
    def optional(self) -> OptionalFake:
        """
        Return the typed camelCase optional-value view.

        Returns
        -------
        OptionalFake
            Stable view accepting a ``prob`` keyword on provider calls.
        """
        view = self._optional
        if view is None:
            view = self._optional = OptionalFake(self._backend.optional, self._state)
        return view

    @property
    def locales(self) -> list[str]:
        """
        Return the configured backend locales.

        Returns
        -------
        list of str
            Detached list of configured locales.
        """
        return list(self._backend.locales)

    @property
    def random(self) -> Random:
        """
        Return the instance's independent standard-library random generator.

        Returns
        -------
        Random
            Random generator owned by this backend instance.
        """
        return self._backend.random

    def __getitem__(self, locale: str) -> Fake:
        """
        Select a configured locale without exposing the native generator.

        Parameters
        ----------
        locale : str
            Locale already configured on this instance.

        Returns
        -------
        Fake
            This facade when its single configured locale is selected.
        """
        backend = self._backend[locale]
        return self if backend is self._backend else Fake(backend)

    def addProvider(self, provider: object) -> None:
        """Register a custom provider and invalidate cached bound methods.

        Parameters
        ----------
        provider : object
            Provider class or instance accepted by the data backend.

        Returns
        -------
        None
            Apply the described operation.
        """
        self._backend.add_provider(provider)
        self._state.refresh()

    def seedInstance(self, seed: int | None = None) -> None:
        """Reseed this generator without touching other factory instances.

        Parameters
        ----------
        seed : int or None, optional
            Deterministic integer seed or system entropy.

        Returns
        -------
        None
            Apply the described operation.
        """
        self._backend.seed_instance(seed)

    def seedLocale(self, locale: str, seed: int | None = None) -> None:
        """Reseed a configured locale's independent generator.

        Parameters
        ----------
        locale : str
            Configured locale to reseed.
        seed : int or None, optional
            Deterministic integer seed or system entropy.

        Returns
        -------
        None
            Apply the described operation.
        """
        self._backend.seed_locale(locale, seed)

    def getFormatter(self, name: str) -> Callable[..., Any]:
        """
        Resolve a provider callable using its public camelCase name.

        Parameters
        ----------
        name : str
            Public provider name.

        Returns
        -------
        Callable
            Bound provider callable.
        """
        return self.__getattr__(name)

    def setFormatter(self, name: str, formatter: Callable[..., Any]) -> None:
        """Install a formatter under its public camelCase provider name.

        Parameters
        ----------
        name : str
            Public camelCase name, with no underscores.
        formatter : Callable
            Callable accepting the desired provider arguments.

        Raises
        ------
        ValueError
            If the name is not a public camelCase identifier.
        TypeError
            If formatter is not callable.

        Returns
        -------
        None
            Apply the described operation.
        """
        if not name.isidentifier() or "_" in name or name == "seed":
            error_msg = "Formatter names must be public camelCase identifiers."
            raise ValueError(error_msg)
        if not callable(formatter):
            error_msg = "A formatter must be callable."
            raise TypeError(error_msg)
        original = self._state.aliases.get(name, name)
        self._backend.set_formatter(original, formatter)
        self._state.refresh()

    def format(
        self,
        formatter: str,
        *args: Any,  # noqa: ANN401
        **kwargs: Any,  # noqa: ANN401
    ) -> Any:  # noqa: ANN401
        """
        Generate a value from a named camelCase formatter.

        Parameters
        ----------
        formatter : str
            Public provider method name.
        *args : Any
            Positional provider arguments.
        **kwargs : Any
            Provider keyword arguments, retaining snake_case names.

        Returns
        -------
        Any
            Value produced by the requested provider method.
        """
        return self.getFormatter(formatter)(*args, **kwargs)
