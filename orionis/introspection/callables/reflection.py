from __future__ import annotations
import inspect
import types
from typing import TYPE_CHECKING
from orionis.introspection.callables.contracts.reflection import (
    IReflectionCallable,
)
from orionis.introspection.dependencies.reflection import ReflectDependencies

if TYPE_CHECKING:
    from orionis.introspection.dependencies.entities.signature import (
        Signature,
    )

# Global sentinel: distinguishes "not yet cached" from None as a legitimate cached value
_UNSET: object = object()

class ReflectionCallable(IReflectionCallable):

    # Explicit slots remove the per-instance __dict__ and speed up attribute access
    __slots__ = ("_cache", "_docstring", "_function", "_module", "_name")

    def __init__(self, fn: callable) -> None:
        """
        Initialize the reflection wrapper with a callable object.

        Parameters
        ----------
        fn : callable
            The function, method, or lambda to be wrapped.

        Raises
        ------
        TypeError
            If `fn` is not a function, method, or lambda.

        Returns
        -------
        None
            This method does not return a value.
        """
        # Validate using concrete types; faster than inspect.isfunction/ismethod
        if not (
            isinstance(fn, (types.FunctionType, types.MethodType))
            or (callable(fn) and hasattr(fn, "__code__"))
        ):
            error_msg = (
                f"Expected a function, method, or lambda, got {type(fn).__name__}"
            )
            raise TypeError(error_msg)
        # Store the callable and pre-compute its immutable read-only properties
        self._function = fn
        self._name: str = fn.__name__
        self._module: str = fn.__module__
        self._docstring: str = fn.__doc__ or ""
        # Shared dict for deferred computation results and the external cache protocol
        self._cache: dict[str, object] = {}

    def __getitem__(self, key: str) -> object | None:
        """
        Retrieve a cached value by key.

        Parameters
        ----------
        key : str
            The key to look up in the cache.

        Returns
        -------
        object or None
            The cached value if found, otherwise None.
        """
        # Read directly from the cache dict without extra indirection
        return self._cache.get(key)

    def __setitem__(self, key: str, value: object) -> None:
        """
        Store a value in the cache with the specified key.

        Parameters
        ----------
        key : str
            The key under which to store the value.
        value : object
            The value to store in the cache.

        Returns
        -------
        None
            This method does not return a value.
        """
        # Write the value directly into the cache dict
        self._cache[key] = value

    def __contains__(self, key: str) -> bool:
        """
        Check if the cache contains the specified key.

        Parameters
        ----------
        key : str
            The key to check for existence in the cache.

        Returns
        -------
        bool
            True if the key exists in the cache, False otherwise.
        """
        # Check key existence directly in the cache dict
        return key in self._cache

    def __delitem__(self, key: str) -> None:
        """
        Remove an item from the memory cache by key.

        Parameters
        ----------
        key : str
            The key to remove from the cache.

        Returns
        -------
        None
            This method does not return a value.
        """
        # Silent removal: does not raise if the key is absent
        self._cache.pop(key, None)

    def getCallable(self) -> callable:
        """
        Return the callable function associated with this instance.

        Returns
        -------
        callable
            The function object encapsulated by this instance.
        """
        return self._function

    def getName(self) -> str:
        """
        Return the name of the callable.

        Returns
        -------
        str
            Name of the function as defined in its declaration.
        """
        # Return the name pre-computed at construction time from the dedicated slot
        return self._name

    def getModuleName(self) -> str:
        """
        Return the module name where the callable is defined.

        Returns
        -------
        str
            The name of the module in which the function was declared.
        """
        # Return the module pre-computed at construction time from the dedicated slot
        return self._module

    def getModuleWithCallableName(self) -> str:
        """
        Return the fully qualified name of the callable.

        Combines the module name and callable name to create a complete identifier.

        Returns
        -------
        str
            The module and callable name separated by a dot.
        """
        # Build the qualified name from pre-computed slots without method dispatches
        return f"{self._module}.{self._name}"

    def getDocstring(self) -> str:
        """
        Return the docstring of the callable.

        Returns
        -------
        str
            The docstring of the function, or an empty string if not present.
        """
        # Return the docstring pre-computed at construction time from the dedicated slot
        return self._docstring

    def getSourceCode(self) -> str:
        """
        Retrieve the source code of the wrapped callable.

        Uses Python's inspect module to extract the complete source code of the
        callable function from its definition file.

        Returns
        -------
        str
            The source code of the callable function as a string.

        Raises
        ------
        AttributeError
            If the source code cannot be obtained due to an OSError or if the
            callable is built-in without accessible source.
        """
        # Single-lookup cache read with sentinel; avoids a second dict access on hit
        _cache = self._cache
        cached = _cache.get("source_code", _UNSET)
        if cached is not _UNSET:
            return cached  # type: ignore[return-value]
        try:
            result: str = inspect.getsource(self._function)
        except OSError as e:
            error_msg = f"Could not retrieve source code: {e}"
            raise AttributeError(error_msg) from e
        _cache["source_code"] = result
        return result

    def getFile(self) -> str:
        """
        Retrieve the absolute path to the source file of the callable.

        Returns
        -------
        str
            Absolute path to the file containing the callable.

        Raises
        ------
        TypeError
            If the callable is built-in or its file cannot be determined.
        """
        # Single-lookup cache read with sentinel; avoids a second dict access on hit
        _cache = self._cache
        cached = _cache.get("file", _UNSET)
        if cached is not _UNSET:
            return cached  # type: ignore[return-value]
        result: str = inspect.getfile(self._function)
        _cache["file"] = result
        return result

    def getSignature(self) -> inspect.Signature:
        """
        Return the signature of the callable.

        Returns
        -------
        inspect.Signature
            The signature object representing the callable's parameters,
            default values, and type annotations.
        """
        # Single-lookup cache read with sentinel; avoids a second dict access on hit
        _cache = self._cache
        cached = _cache.get("signature", _UNSET)
        if cached is not _UNSET:
            return cached  # type: ignore[return-value]
        result = inspect.signature(self._function)
        _cache["signature"] = result
        return result

    def getDependencies(self) -> Signature:
        """
        Analyze and return the dependency signature of the wrapped callable.

        Delegates to ReflectDependencies to inspect each parameter and resolve
        its type annotation into a dependency descriptor. The result is stored
        in the shared cache so that repeated calls skip reanalysis.

        Returns
        -------
        Signature
            A structure that holds the resolved and unresolved dependencies
            derived from the callable's parameter annotations.
        """
        # Single-lookup cache read with sentinel; avoids a second dict access on hit
        _cache = self._cache
        cached = _cache.get("dependencies", _UNSET)
        if cached is not _UNSET:
            return cached  # type: ignore[return-value]
        result = ReflectDependencies(self._function).callableSignature()
        _cache["dependencies"] = result
        return result

    def clearCache(self) -> None:
        """
        Clear all cached reflection data.

        Removes all cached entries stored in the reflection instance. Forces
        fresh computation on subsequent method calls.

        Returns
        -------
        None
            This method does not return a value.
        """
        # Evict all entries, including any keys stored externally via the cache protocol
        self._cache.clear()
