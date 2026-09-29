from __future__ import annotations
import inspect
import keyword
from typing import TYPE_CHECKING, NamedTuple
from orionis.introspection.abstract.contracts.reflection import (
    IReflectionAbstract,
)
from orionis.introspection.dependencies.reflection import ReflectDependencies

if TYPE_CHECKING:
    from collections.abc import Callable
    from orionis.introspection.dependencies.entities.signature import (
        Signature,
    )

# Module-level coroutine-check callable to avoid repeated attribute lookups
_ISCORO: Callable[..., bool] = inspect.iscoroutinefunction

# Dunder attributes built into the language, excluded from user-defined detection
_EXCLUDED_DUNDER_ATTRS: frozenset[str] = frozenset({
    "__class__", "__delattr__", "__dir__", "__doc__", "__eq__", "__format__",
    "__ge__", "__getattribute__", "__gt__", "__hash__", "__init__",
    "__init_subclass__", "__le__", "__lt__", "__module__", "__ne__", "__new__",
    "__reduce__", "__reduce_ex__", "__repr__", "__setattr__", "__sizeof__",
    "__str__", "__subclasshook__", "__firstlineno__", "__annotations__",
    "__static_attributes__", "__dict__", "__weakref__", "__slots__", "__mro__",
    "__subclasses__", "__bases__", "__base__", "__flags__",
    "__abstractmethods__", "__code__", "__defaults__",
    "__kwdefaults__", "__closure__",
})

class _Flags(NamedTuple):
    """
    Represent visibility classification flags for a class member.

    Attributes
    ----------
    is_dunder : bool
        Indicate whether the member name is a double-underscore name.
    is_private : bool
        Indicate whether the member name is private.
    is_prot : bool
        Indicate whether the member name is protected.
    is_pub : bool
        Indicate whether the member name is public.
    """

    is_dunder: bool
    is_private: bool
    is_prot: bool
    is_pub: bool

class ReflectionAbstract(IReflectionAbstract):

    __slots__ = (
        "_abstract",
        "_abstract_module",
        "_abstract_name",
        "_cache",
        "_private_prefix",
        "_scanned",
    )

    def __init__(self, abstract: type) -> None:
        """
        Initialize the reflector for an abstract base class.

        Parameters
        ----------
        abstract : type
            Provide the abstract base class to inspect.

        Raises
        ------
        TypeError
            If ``abstract`` is not an abstract base class.
        """
        # Validate that the provided class is indeed an abstract base class
        if not inspect.isabstract(abstract):
            msg = f"The class '{abstract.__name__}' is not an abstract base class."
            raise TypeError(msg)

        # Capture frequently accessed class metadata into slots at construction time
        self._abstract: type = abstract
        abstract_name: str = abstract.__name__
        self._abstract_name: str = abstract_name
        self._abstract_module: str = abstract.__module__
        # Python strips the leading underscores of the class name when it
        # mangles private members, so the prefix must be built the same way.
        self._private_prefix: str = f"_{abstract_name.lstrip('_')}"
        self._cache: dict = {}
        self._scanned: bool = False

    def __getitem__(self, key: str) -> object | None:
        """
        Return the cached value for a key.

        Parameters
        ----------
        key : str
            Specify the cache key to look up.

        Returns
        -------
        object or None
            Return the cached value, or ``None`` if the key is not present.
        """
        return self._cache.get(key)

    def __setitem__(self, key: str, value: object) -> None:
        """
        Store a value in the cache.

        Parameters
        ----------
        key : str
            Specify the cache key to assign.
        value : object
            Provide the value to store.
        """
        self._cache[key] = value

    def __contains__(self, key: str) -> bool:
        """
        Return whether a cache key exists.

        Parameters
        ----------
        key : str
            Specify the cache key to test.

        Returns
        -------
        bool
            Return ``True`` if the key exists; otherwise return ``False``.
        """
        return key in self._cache

    def __delitem__(self, key: str) -> None:
        """
        Remove a key from the cache.

        Parameters
        ----------
        key : str
            Specify the cache key to remove.

        Notes
        -----
        Ignore missing keys without raising an exception.
        """
        self._cache.pop(key, None)

    def _ensureScanned(self) -> None:
        """
        Ensure class members are scanned once before member access.

        Notes
        -----
        Run a full single-pass class-dictionary scan only when no prior
        scan has been completed.
        """
        # Trigger a full single-pass class dict scan on the first member query
        if not self._scanned:
            self._scanClass()
            self._scanned = True

    def _invalidateMembers(self) -> None:
        """
        Invalidate cached member classifications.

        Notes
        -----
        Remove all cache entries derived from scanned class members and mark
        the scanner state as stale so the next member access triggers a
        full re-scan.
        """
        # Drop every member-related cache entry after a mutation, forcing a re-scan
        cache = self._cache
        for key in (
            "attributes", "public_attributes", "protected_attributes",
            "private_attributes", "dunder_attributes",
            "methods", "public_methods", "protected_methods", "private_methods",
            "public_sync_methods", "public_async_methods",
            "protected_sync_methods", "protected_async_methods",
            "private_sync_methods", "private_async_methods",
            "public_class_methods", "protected_class_methods", "private_class_methods",
            "public_class_sync_methods", "public_class_async_methods",
            "protected_class_sync_methods", "protected_class_async_methods",
            "private_class_sync_methods", "private_class_async_methods",
            "public_static_methods", "protected_static_methods",
            "private_static_methods",
            "public_static_sync_methods", "public_static_async_methods",
            "protected_static_sync_methods", "protected_static_async_methods",
            "private_static_sync_methods", "private_static_async_methods",
            "dunder_methods",
            "properties", "public_properties",
            "protected_properties", "private_properties",
        ):
            cache.pop(key, None)
        self._scanned = False

    def _makeBuckets(self, prefix_len: int) -> dict:
        """
        Create mutable classification containers for a scan pass.

        Parameters
        ----------
        prefix_len : int
            Length of the class-private name-mangling prefix used to unmask
            private member names.

        Returns
        -------
        dict
            Mapping of pre-initialized buckets for attributes, methods,
            properties, and sync/async method variants by visibility.
        """
        return {
            "_n": prefix_len,
            "pub_attrs": {}, "prot_attrs": {}, "priv_attrs": {}, "dund_attrs": {},
            "pub_methods": [], "pub_sync": [], "pub_async": [],
            "prot_methods": [], "prot_sync": [], "prot_async": [],
            "priv_methods": [], "priv_sync": [], "priv_async": [],
            "pub_cm": [], "pub_cm_sync": [], "pub_cm_async": [],
            "prot_cm": [], "prot_cm_sync": [], "prot_cm_async": [],
            "priv_cm": [], "priv_cm_sync": [], "priv_cm_async": [],
            "pub_sm": [], "pub_sm_sync": [], "pub_sm_async": [],
            "prot_sm": [], "prot_sm_sync": [], "prot_sm_async": [],
            "priv_sm": [], "priv_sm_sync": [], "priv_sm_async": [],
            "dund_methods": [],
            "props_all": [], "pub_props": [], "prot_props": [], "priv_props": [],
        }

    def _classifyProperty(self, attr: str, flags: _Flags, b: dict) -> None:
        """
        Classify a property name into visibility-specific buckets.

        Parameters
        ----------
        attr : str
            Raw attribute name as exposed by class introspection.
        flags : _Flags
            Precomputed visibility flags for ``attr``.
        b : dict
            Mutable bucket mapping populated during reflection.

        Returns
        -------
        None
            Update ``b`` in place with normalized property names.
        """
        n = b["_n"]
        if flags.is_private:
            clean = attr[n:]
            b["props_all"].append(clean)
            b["priv_props"].append(clean)
        elif flags.is_prot:
            b["props_all"].append(attr)
            b["prot_props"].append(attr)
        elif flags.is_pub:
            b["props_all"].append(attr)
            b["pub_props"].append(attr)

    def _classifyStatic(
        self, attr: str, value: staticmethod, flags: _Flags, b: dict,
    ) -> None:
        """
        Classify a static method by visibility and coroutine status.

        Parameters
        ----------
        attr : str
            Raw attribute name produced by class introspection.
        value : staticmethod
            Static method descriptor to classify.
        flags : _Flags
            Precomputed visibility and dunder flags for ``attr``.
        b : dict
            Mutable reflection bucket updated in place.

        Returns
        -------
        None
            Update ``b`` with normalized static method names.
        """
        # Route the static method into visibility and sync/async buckets.
        n = b["_n"]
        if flags.is_private:
            is_coro = _ISCORO(value.__func__)
            clean = attr[n:]
            b["priv_sm"].append(clean)
            (b["priv_sm_async"] if is_coro else b["priv_sm_sync"]).append(clean)
        elif flags.is_prot:
            is_coro = _ISCORO(value.__func__)
            b["prot_sm"].append(attr)
            (b["prot_sm_async"] if is_coro else b["prot_sm_sync"]).append(attr)
        elif flags.is_pub and not flags.is_dunder:
            is_coro = _ISCORO(value.__func__)
            b["pub_sm"].append(attr)
            (b["pub_sm_async"] if is_coro else b["pub_sm_sync"]).append(attr)

    def _classifyClassMethod(
        self, attr: str, value: classmethod, flags: _Flags, b: dict,
    ) -> None:
        """
        Classify a class method into reflection buckets.

        Parameters
        ----------
        attr : str
            Method attribute name as declared on the class.
        value : classmethod
            Bound ``classmethod`` descriptor to inspect.
        flags : _Flags
            Precomputed visibility and dunder flags for ``attr``.
        b : dict
            Mutable reflection bucket updated in place.

        Returns
        -------
        None
            Update ``b`` with normalized class method names.
        """
        # Route the class method into the correct visibility and sync/async buckets.
        n = b["_n"]
        if flags.is_private:
            is_coro = _ISCORO(value.__func__)
            clean = attr[n:]
            b["priv_cm"].append(clean)
            (b["priv_cm_async"] if is_coro else b["priv_cm_sync"]).append(clean)
        elif flags.is_prot:
            is_coro = _ISCORO(value.__func__)
            b["prot_cm"].append(attr)
            (b["prot_cm_async"] if is_coro else b["prot_cm_sync"]).append(attr)
        elif flags.is_pub and not flags.is_dunder:
            is_coro = _ISCORO(value.__func__)
            b["pub_cm"].append(attr)
            (b["pub_cm_async"] if is_coro else b["pub_cm_sync"]).append(attr)

    def _classifyCallable(
            self, attr: str, value: object, flags: _Flags, b: dict[str, object],
    ) -> None:
        """
        Classify a regular callable by visibility and coroutine type.

        Parameters
        ----------
        attr : str
            Raw attribute name from the inspected class namespace.
        value : object
            Callable object bound to ``attr``.
        flags : _Flags
            Precomputed visibility and dunder-state flags for ``attr``.
        b : dict[str, object]
            Mutable classification bucket updated in place.

        Returns
        -------
        None
            Update method name buckets for visibility and sync/async groups.
        """
        n = b["_n"]
        if flags.is_dunder:
            b["dund_methods"].append(attr)
        elif flags.is_private:
            is_coro = _ISCORO(value)  # type: ignore[arg-type]
            clean = attr[n:]
            b["priv_methods"].append(clean)
            (b["priv_async"] if is_coro else b["priv_sync"]).append(clean)
        elif flags.is_prot:
            is_coro = _ISCORO(value)  # type: ignore[arg-type]
            b["prot_methods"].append(attr)
            (b["prot_async"] if is_coro else b["prot_sync"]).append(attr)
        elif flags.is_pub:
            is_coro = _ISCORO(value)  # type: ignore[arg-type]
            b["pub_methods"].append(attr)
            (b["pub_async"] if is_coro else b["pub_sync"]).append(attr)

    def _classifyDataAttr(
            self, attr: str, value: object, flags: _Flags, b: dict[str, object],
    ) -> None:
        """
        Classify a non-callable attribute into visibility buckets.

        Parameters
        ----------
        attr : str
            Attribute name to classify.
        value : object
            Attribute value to store in the target bucket.
        flags : _Flags
            Precomputed visibility flags for ``attr``.
        b : dict[str, object]
            Mutable classification bucket updated in place.

        Returns
        -------
        None
            Update attribute name/value buckets by visibility.
        """
        # Route the data attribute into the appropriate visibility bucket.
        n = b["_n"]
        if flags.is_dunder:
            if attr not in _EXCLUDED_DUNDER_ATTRS:
                b["dund_attrs"][attr] = value
        elif flags.is_private:
            b["priv_attrs"][attr[n:]] = value
        elif flags.is_prot:
            if not attr.startswith("_abc_"):
                b["prot_attrs"][attr] = value
        elif flags.is_pub:
            b["pub_attrs"][attr] = value

    def _commitAttrBuckets(self, b: dict[str, dict[str, object]]) -> None:
        """
        Persist classified attribute buckets into the instance cache.

        Parameters
        ----------
        b : dict[str, dict[str, object]]
            Attribute buckets keyed by classifier names (public, protected,
            private, and dunder).

        Returns
        -------
        None
            Update cached attribute views in place.
        """
        # Write all classified attribute buckets into the instance cache.
        cache = self._cache
        pub_attrs = b["pub_attrs"]
        prot_attrs = b["prot_attrs"]
        priv_attrs = b["priv_attrs"]
        dund_attrs = b["dund_attrs"]
        cache["public_attributes"] = pub_attrs
        cache["protected_attributes"] = prot_attrs
        cache["private_attributes"] = priv_attrs
        cache["dunder_attributes"] = dund_attrs
        cache["attributes"] = {**pub_attrs, **prot_attrs, **priv_attrs, **dund_attrs}

    def _commitMethodBuckets(self, b: dict) -> None:
        """
        Persist classified method and property buckets into the instance cache.

        Parameters
        ----------
        b : dict
            Method and property buckets keyed by classifier names (public, protected,
            private, and dunder).

        Returns
        -------
        None
            Update cached method and property views in place.
        """
        # Write all classified method and property buckets into the instance cache
        cache = self._cache
        pub_m = b["pub_methods"]
        prot_m = b["prot_methods"]
        priv_m = b["priv_methods"]
        pub_cm = b["pub_cm"]
        prot_cm = b["prot_cm"]
        priv_cm = b["priv_cm"]
        pub_sm = b["pub_sm"]
        prot_sm = b["prot_sm"]
        priv_sm = b["priv_sm"]
        cache["public_methods"] = pub_m
        cache["public_sync_methods"] = b["pub_sync"]
        cache["public_async_methods"] = b["pub_async"]
        cache["protected_methods"] = prot_m
        cache["protected_sync_methods"] = b["prot_sync"]
        cache["protected_async_methods"] = b["prot_async"]
        cache["private_methods"] = priv_m
        cache["private_sync_methods"] = b["priv_sync"]
        cache["private_async_methods"] = b["priv_async"]
        cache["public_class_methods"] = pub_cm
        cache["public_class_sync_methods"] = b["pub_cm_sync"]
        cache["public_class_async_methods"] = b["pub_cm_async"]
        cache["protected_class_methods"] = prot_cm
        cache["protected_class_sync_methods"] = b["prot_cm_sync"]
        cache["protected_class_async_methods"] = b["prot_cm_async"]
        cache["private_class_methods"] = priv_cm
        cache["private_class_sync_methods"] = b["priv_cm_sync"]
        cache["private_class_async_methods"] = b["priv_cm_async"]
        cache["public_static_methods"] = pub_sm
        cache["public_static_sync_methods"] = b["pub_sm_sync"]
        cache["public_static_async_methods"] = b["pub_sm_async"]
        cache["protected_static_methods"] = prot_sm
        cache["protected_static_sync_methods"] = b["prot_sm_sync"]
        cache["protected_static_async_methods"] = b["prot_sm_async"]
        cache["private_static_methods"] = priv_sm
        cache["private_static_sync_methods"] = b["priv_sm_sync"]
        cache["private_static_async_methods"] = b["priv_sm_async"]
        cache["dunder_methods"] = b["dund_methods"]
        cache["properties"] = b["props_all"]
        cache["public_properties"] = b["pub_props"]
        cache["protected_properties"] = b["prot_props"]
        cache["private_properties"] = b["priv_props"]
        cache["methods"] = [
            *pub_m, *prot_m, *priv_m,
            *pub_cm, *prot_cm, *priv_cm,
            *pub_sm, *prot_sm, *priv_sm,
        ]

    def _scanClass(self) -> None:
        """
        Classify class members and commit cached reflection buckets.

        Performs a single pass over ``__dict__`` to categorize properties,
        methods, and data attributes by visibility and execution type.

        Returns
        -------
        None
            Update internal cache buckets in place.
        """
        private_prefix = self._private_prefix
        class_dict: dict = self._abstract.__dict__
        b = self._makeBuckets(len(private_prefix))

        for attr, value in class_dict.items():
            is_dunder = attr.startswith("__") and attr.endswith("__")
            is_private = not is_dunder and attr.startswith(private_prefix)
            is_prot = not is_dunder and not is_private and attr.startswith("_")
            flags = _Flags(is_dunder, is_private, is_prot, not attr.startswith("_"))

            if isinstance(value, property):
                self._classifyProperty(attr, flags, b)
            elif isinstance(value, staticmethod):
                self._classifyStatic(attr, value, flags, b)
            elif isinstance(value, classmethod):
                self._classifyClassMethod(attr, value, flags, b)
            elif callable(value):
                self._classifyCallable(attr, value, flags, b)
            else:
                self._classifyDataAttr(attr, value, flags, b)

        self._commitAttrBuckets(b)
        self._commitMethodBuckets(b)

    def getClass(self) -> type:
        """
        Return the class type associated with this reflection instance.

        Returns
        -------
        Type
            The abstract base class type provided during initialization.
        """
        return self._abstract

    def getClassName(self) -> str:
        """
        Return the name of the reflected abstract class.

        Returns
        -------
        str
            The name of the abstract class provided during initialization.
        """
        return self._abstract_name

    def getModuleName(self) -> str:
        """
        Return the module name of the reflected abstract class.

        Returns
        -------
        str
            The fully qualified module name containing the abstract class.
        """
        return self._abstract_module

    def getModuleWithClassName(self) -> str:
        """
        Return the fully qualified name of the abstract class.

        Returns
        -------
        str
            The module path and class name separated by a dot, such as
            'module.submodule.ClassName'.
        """
        return f"{self._abstract_module}.{self._abstract_name}"

    def getDocstring(self) -> str | None:
        """
        Retrieve the docstring for the reflected abstract class.

        Returns
        -------
        str or None
            The docstring of the abstract class, or None if not available.
        """
        return self._abstract.__doc__ or None

    def getBaseClasses(self) -> list[type]:
        """
        Return the direct base classes of the reflected abstract class.

        Returns
        -------
        list of type
            List of direct base classes for the abstract class.
        """
        cache = self._cache
        if (v := cache.get("base_classes")) is not None:
            return v
            # Normalize to list for a consistent, mutable return type.
        result: list[type] = list(self._abstract.__bases__)
        cache["base_classes"] = result
        return result

    def getSourceCode(self) -> str:
        """
        Retrieve the source code of the reflected abstract class.

        Parameters
        ----------
        None

        Returns
        -------
        str
            The complete source code of the abstract class as a string.

        Raises
        ------
        ValueError
            If the source code cannot be retrieved because the class has no
            reachable definition or no importable module file.
        """
        cache = self._cache
        if (v := cache.get("source_code")) is not None:
            return v
        # Attempt to retrieve source code and cache it; handle common errors gracefully
        try:
            result: str = inspect.getsource(self._abstract)
        except (OSError, TypeError) as e:
            msg = f"Could not retrieve source code for '{self._abstract_name}': {e}"
            raise ValueError(msg) from e
        cache["source_code"] = result
        return result

    def getFile(self) -> str:
        """
        Retrieve the absolute file path of the reflected abstract class.

        Parameters
        ----------
        None

        Returns
        -------
        str
            The absolute file path containing the abstract class definition.

        Raises
        ------
        ValueError
            If the file path cannot be retrieved because the class does not
            belong to an importable module file.
        """
        cache = self._cache
        if (v := cache.get("file_path")) is not None:
            return v
        try:
            result: str = inspect.getfile(self._abstract)
        except TypeError as e:
            msg = f"Could not retrieve file for '{self._abstract_name}': {e}"
            raise ValueError(msg) from e
        cache["file_path"] = result
        return result

    def getAnnotations(self) -> dict:
        """
        Retrieve type annotations for class attributes.

        Returns
        -------
        dict
            Dictionary mapping attribute names to their annotated types.
            Private attribute names are normalized by removing name mangling
            prefixes.
        """
        cache = self._cache
        if (v := cache.get("annotations")) is not None:
            return v
        private_prefix = self._private_prefix
        annotations: dict = {}
        # Normalize private attribute name mangling in a single loop
        for k, v in getattr(self._abstract, "__annotations__", {}).items():
            annotations[k.replace(private_prefix, "") if private_prefix in k else k] = v
        cache["annotations"] = annotations
        return annotations

    def hasAttribute(self, attribute: str) -> bool:
        """
        Check if the class has a specific attribute.

        Parameters
        ----------
        attribute : str
            The name of the attribute to check.

        Returns
        -------
        bool
            True if the attribute exists, False otherwise.
        """
        # Trigger scan if needed, then test membership directly against the dict
        self._ensureScanned()
        return attribute in self._cache["attributes"]

    def getAttribute(self, attribute: str) -> object | None:
        """
        Retrieve the value of a class attribute.

        Parameters
        ----------
        attribute : str
            Name of the attribute to retrieve.

        Returns
        -------
        object or None
            Value of the specified class attribute, or None if not found.

        Raises
        ------
        ValueError
            If the attribute does not exist or is inaccessible.
        """
        # Trigger scan if needed, then look up directly in the aggregated dict
        self._ensureScanned()
        return self._cache["attributes"].get(attribute)

    def setAttribute(self, name: str, value: object) -> bool:
        """
        Set the value of a class attribute.

        Parameters
        ----------
        name : str
            Name of the attribute to set. Must be a valid Python identifier and
            not a reserved keyword.
        value : object
            Value to assign to the attribute. Must not be callable.

        Returns
        -------
        bool
            True if the attribute was successfully set.

        Raises
        ------
        ValueError
            If the attribute name is invalid, is a Python keyword, or if the
            value is callable.
        """
        if (
            not isinstance(name, str)
            or not name.isidentifier()
            or keyword.iskeyword(name)
        ):
            msg = (
                f"Invalid attribute name '{name}'. Must be a valid Python identifier "
                "and not a keyword."
            )
            raise ValueError(msg)
        # Prevent callable values from being stored as plain attributes
        if callable(value):
            msg = f"Cannot set attribute '{name}' to a callable. Use setMethod instead."
            raise TypeError(msg)
        # Apply private-name mangling for double-underscore attributes.
        if name.startswith("__") and not name.endswith("__"):
            name = f"{self._private_prefix}{name}"
        setattr(self._abstract, name, value)
        # Refresh member views after mutation.
        self._invalidateMembers()
        return True

    def removeAttribute(self, name: str) -> bool:
        """
        Remove an attribute from the reflected abstract class.

        Parameters
        ----------
        name : str
            Name of the attribute to remove.

        Returns
        -------
        bool
            True if the attribute was successfully removed.

        Raises
        ------
        ValueError
            If the attribute does not exist or cannot be removed.
        """
        # Guard against removing attributes that do not exist
        if not self.hasAttribute(name):
            msg = f"Attribute '{name}' does not exist in class '{self._abstract_name}'."
            raise ValueError(msg)
        # Reconstruct the mangled name for private attributes
        if name.startswith("__") and not name.endswith("__"):
            name = f"{self._private_prefix}{name}"
        delattr(self._abstract, name)
        # Invalidate all member caches after removal
        self._invalidateMembers()
        return True

    def getAttributes(self) -> dict:
        """
        Aggregate all class-level attributes.

        Combines public, protected, private, and dunder attributes into a single
        dictionary. Excludes callable objects, static/class methods, and properties.

        Returns
        -------
        dict
            Dictionary mapping attribute names to their values.
        """
        self._ensureScanned()
        return self._cache["attributes"]

    def getPublicAttributes(self) -> dict:
        """
        Retrieve all public class-level attributes.

        Parameters
        ----------
        None

        Returns
        -------
        dict
            Dictionary mapping public attribute names to their values. Only includes
            attributes that do not start with underscores and are not callable,
            static methods, class methods, or properties.
        """
        self._ensureScanned()
        return self._cache["public_attributes"]

    def getProtectedAttributes(self) -> dict:
        """
        Retrieve all protected class-level attributes.

        Parameters
        ----------
        None

        Returns
        -------
        dict
            Dictionary mapping protected attribute names to their values. Only
            attributes that start with a single underscore, are not dunder,
            private, callable, static/class methods, or properties.
        """
        self._ensureScanned()
        return self._cache["protected_attributes"]

    def getPrivateAttributes(self) -> dict:
        """
        Retrieve all private class-level attributes.

        Parameters
        ----------
        None

        Returns
        -------
        dict
            Dictionary mapping private attribute names (with name mangling
            removed) to their values. Only includes attributes starting with
            _ClassName that are not callable, static methods, class methods,
            or properties.
        """
        self._ensureScanned()
        return self._cache["private_attributes"]

    def getDunderAttributes(self) -> dict:
        """
        Retrieve dunder (double underscore) class-level attributes.

        Returns
        -------
        dict
            Dictionary mapping dunder attribute names to their values. Only
            includes attributes that start and end with double underscores,
            are not callable, static methods, class methods, or properties,
            and are not in the excluded built-in list.
        """
        self._ensureScanned()
        return self._cache["dunder_attributes"]

    def getMagicAttributes(self) -> dict:
        """
        Return a dictionary of magic (dunder) class attributes.

        Returns
        -------
        dict
            Dictionary mapping magic attribute names to their values. Only includes
            attributes that start with double underscores and are not callable,
            static methods, class methods, or properties.
        """
        return self.getDunderAttributes()

    def hasMethod(self, name: str) -> bool:
        """
        Determine if the abstract class contains a method with the given name.

        Parameters
        ----------
        name : str
            The name of the method to check.

        Returns
        -------
        bool
            True if the method exists in the class, otherwise False.
        """
        self._ensureScanned()
        return name in self._cache["methods"]

    def removeMethod(self, name: str) -> bool:
        """
        Remove a method from the abstract class.

        Parameters
        ----------
        name : str
            Name of the method to remove.

        Returns
        -------
        bool
            True if the method was successfully removed.

        Raises
        ------
        ValueError
            If the method does not exist or cannot be removed.
        """
        # Guard against removing non-existent methods
        if not self.hasMethod(name):
            msg = f"Method '{name}' does not exist in class '{self._abstract_name}'."
            raise ValueError(msg)
        # Reconstruct the mangled name for private methods before deletion
        if name.startswith("__") and not name.endswith("__"):
            name = f"{self._private_prefix}{name}"
        delattr(self._abstract, name)
        # Invalidate all member caches after removal
        self._invalidateMembers()
        return True

    def getMethodSignature(self, name: str) -> inspect.Signature:
        """
        Retrieve the signature of a method in the abstract class.

        Parameters
        ----------
        name : str
            Name of the method to retrieve the signature for.

        Returns
        -------
        inspect.Signature
            Signature object of the specified method.

        Raises
        ------
        ValueError
            If the method does not exist or is not callable.
        """
        cache = self._cache
        cache_key = f"{name}_signature"
        if (v := cache.get(cache_key)) is not None:
            return v
        if not self.hasMethod(name):
            msg = f"Method '{name}' does not exist in class '{self._abstract_name}'."
            raise ValueError(msg)
        # Reconstruct the mangled name for private methods before lookup
        resolved = name
        if name.startswith("__") and not name.endswith("__"):
            resolved = f"{self._private_prefix}{name}"
        # getattr correctly resolves descriptors for signature inspection
        method = getattr(self._abstract, resolved, None)
        if not callable(method):
            msg = f"'{name}' is not callable in class '{self._abstract_name}'."
            raise TypeError(msg)
        # Compute and cache the signature object
        result: inspect.Signature = inspect.signature(method)
        cache[cache_key] = result
        return result

    def getMethods(self) -> list[str]:
        """
        Return all method names defined in the abstract class.

        Returns
        -------
        list of str
            List of all method names, including public, protected, private,
            static, and class methods.
        """
        self._ensureScanned()
        return self._cache["methods"]

    def getPublicMethods(self) -> list[str]:
        """
        Return all public instance method names.

        Returns
        -------
        list of str
            List of public instance method names. Excludes dunder, protected,
            private methods, static methods, class methods, and properties.
        """
        self._ensureScanned()
        return self._cache["public_methods"]

    def getPublicSyncMethods(self) -> list[str]:
        """
        Return all public synchronous method names from the abstract class.

        Returns
        -------
        list of str
            List of public synchronous method names. Excludes asynchronous methods.
        """
        self._ensureScanned()
        return self._cache["public_sync_methods"]

    def getPublicAsyncMethods(self) -> list[str]:
        """
        Return all public asynchronous method names.

        Returns
        -------
        list of str
            List of public asynchronous method names. Only coroutine functions
            are included.
        """
        self._ensureScanned()
        return self._cache["public_async_methods"]

    def getProtectedMethods(self) -> list[str]:
        """
        Return all protected instance method names.

        Parameters
        ----------
        None

        Returns
        -------
        list of str
            List of protected instance method names. Includes only methods that
            start with a single underscore, are not dunder, private, static,
            class methods, or properties.
        """
        self._ensureScanned()
        return self._cache["protected_methods"]

    def getProtectedSyncMethods(self) -> list[str]:
        """
        Return all protected synchronous method names.

        Returns
        -------
        list of str
            List of protected synchronous method names. Only includes protected
            methods that are not coroutine functions.
        """
        self._ensureScanned()
        return self._cache["protected_sync_methods"]

    def getProtectedAsyncMethods(self) -> list[str]:
        """
        Return all protected asynchronous method names.

        Parameters
        ----------
        None

        Returns
        -------
        list of str
            List of protected asynchronous method names. Only includes protected
            methods that are coroutine functions.
        """
        self._ensureScanned()
        return self._cache["protected_async_methods"]

    def getPrivateMethods(self) -> list[str]:
        """
        Return all private instance method names.

        Private methods are those with name-mangling (start with _ClassName).
        Excludes static methods, class methods, properties, and dunder methods.

        Returns
        -------
        list of str
            List of private instance method names with class name prefixes removed.
        """
        self._ensureScanned()
        return self._cache["private_methods"]

    def getPrivateSyncMethods(self) -> list[str]:
        """
        Return all private synchronous method names.

        Returns
        -------
        list of str
            List of private synchronous method names. Only includes private methods
            that are not coroutine functions.
        """
        self._ensureScanned()
        return self._cache["private_sync_methods"]

    def getPrivateAsyncMethods(self) -> list[str]:
        """
        Retrieve private asynchronous method names.

        Parameters
        ----------
        self : ReflectionAbstract
            The reflection instance.

        Returns
        -------
        list of str
            List of private asynchronous method names. Only includes private
            methods that are coroutine functions.
        """
        self._ensureScanned()
        return self._cache["private_async_methods"]

    def getPublicClassMethods(self) -> list[str]:
        """
        Return all public class method names.

        Returns
        -------
        list of str
            List of public class method names. Only includes methods decorated
            with @classmethod that do not start with underscores.
        """
        self._ensureScanned()
        return self._cache["public_class_methods"]

    def getPublicClassSyncMethods(self) -> list[str]:
        """
        Return all public synchronous class method names.

        Returns
        -------
        list of str
            List of public synchronous class method names. Only includes methods
            that are not coroutine functions.
        """
        self._ensureScanned()
        return self._cache["public_class_sync_methods"]

    def getPublicClassAsyncMethods(self) -> list[str]:
        """
        Return all public asynchronous class method names.

        Returns
        -------
        list of str
            List of public asynchronous class method names. Only includes methods
            decorated with @classmethod that are coroutine functions and do not
            start with underscores.
        """
        self._ensureScanned()
        return self._cache["public_class_async_methods"]

    def getProtectedClassMethods(self) -> list[str]:
        """
        Return a list of protected class methods.

        Parameters
        ----------
        self : ReflectionAbstract
            The reflection instance.

        Returns
        -------
        list of str
            Names of protected class methods (not instance methods).
        """
        self._ensureScanned()
        return self._cache["protected_class_methods"]

    def getProtectedClassSyncMethods(self) -> list[str]:
        """
        Return all protected synchronous class method names.

        Parameters
        ----------
        self : ReflectionAbstract

        Returns
        -------
        list of str
            List of protected synchronous class method names. Only includes
            protected class methods that are not coroutine functions.
        """
        self._ensureScanned()
        return self._cache["protected_class_sync_methods"]

    def getProtectedClassAsyncMethods(self) -> list[str]:
        """
        Return all protected asynchronous class method names.

        Parameters
        ----------
        self : ReflectionAbstract

        Returns
        -------
        list of str
            List of protected asynchronous class method names. Only includes
            protected class methods that are coroutine functions.
        """
        self._ensureScanned()
        return self._cache["protected_class_async_methods"]

    def getPrivateClassMethods(self) -> list[str]:
        """
        Return a list of private class methods.

        Parameters
        ----------
        self : ReflectionAbstract

        Returns
        -------
        list of str
            List of private class method names with class name prefixes removed.
        """
        self._ensureScanned()
        return self._cache["private_class_methods"]

    def getPrivateClassSyncMethods(self) -> list[str]:
        """
        Return all private synchronous class method names.

        Parameters
        ----------
        self : ReflectionAbstract

        Returns
        -------
        list of str
            List of private synchronous class method names. Only includes private
            class methods that are not coroutine functions.
        """
        self._ensureScanned()
        return self._cache["private_class_sync_methods"]

    def getPrivateClassAsyncMethods(self) -> list[str]:
        """
        Return all private asynchronous class method names.

        Finds private class methods (name-mangled) that are coroutine functions.

        Returns
        -------
        list of str
            List of private asynchronous class method names with class name
            prefixes removed.
        """
        self._ensureScanned()
        return self._cache["private_class_async_methods"]

    def getPublicStaticMethods(self) -> list[str]:
        """
        Return all public static method names.

        Returns
        -------
        list of str
            List of public static method names. Only includes methods decorated
            with @staticmethod that do not start with underscores.
        """
        self._ensureScanned()
        return self._cache["public_static_methods"]

    def getPublicStaticSyncMethods(self) -> list[str]:
        """
        Return all public synchronous static method names.

        Parameters
        ----------
        self : ReflectionAbstract

        Returns
        -------
        list of str
            List of public static method names that are synchronous (not coroutine
            functions).
        """
        self._ensureScanned()
        return self._cache["public_static_sync_methods"]

    def getPublicStaticAsyncMethods(self) -> list[str]:
        """
        Return all public asynchronous static method names.

        Parameters
        ----------
        self : ReflectionAbstract

        Returns
        -------
        list of str
            List of public static method names that are coroutine functions.
        """
        self._ensureScanned()
        return self._cache["public_static_async_methods"]

    def getProtectedStaticMethods(self) -> list[str]:
        """
        Return a list of protected static method names.

        Parameters
        ----------
        self : ReflectionAbstract

        Returns
        -------
        list of str
            List of protected static method names. Only includes methods decorated
            with @staticmethod that start with a single underscore, are not dunder,
            and are not name-mangled private methods.
        """
        self._ensureScanned()
        return self._cache["protected_static_methods"]

    def getProtectedStaticSyncMethods(self) -> list[str]:
        """
        Return all protected synchronous static method names.

        Parameters
        ----------
        self : ReflectionAbstract

        Returns
        -------
        list of str
            List of protected static method names that are synchronous (not
            coroutine functions).
        """
        self._ensureScanned()
        return self._cache["protected_static_sync_methods"]

    def getProtectedStaticAsyncMethods(self) -> list[str]:
        """
        Return all protected asynchronous static method names.

        Parameters
        ----------
        self : ReflectionAbstract

        Returns
        -------
        list of str
            List of protected static method names that are coroutine functions.
        """
        self._ensureScanned()
        return self._cache["protected_static_async_methods"]

    def getPrivateStaticMethods(self) -> list[str]:
        """
        Return a list of private static method names.

        Parameters
        ----------
        self : ReflectionAbstract

        Returns
        -------
        list of str
            List of private static method names with class name prefixes removed.
        """
        self._ensureScanned()
        return self._cache["private_static_methods"]

    def getPrivateStaticSyncMethods(self) -> list[str]:
        """
        Return all private synchronous static method names.

        Parameters
        ----------
        self : ReflectionAbstract

        Returns
        -------
        list of str
            List of private static method names that are synchronous (not coroutine
            functions).
        """
        self._ensureScanned()
        return self._cache["private_static_sync_methods"]

    def getPrivateStaticAsyncMethods(self) -> list[str]:
        """
        Return all private asynchronous static method names.

        Parameters
        ----------
        self : ReflectionAbstract

        Returns
        -------
        list of str
            List of private static method names that are coroutine functions.
        """
        self._ensureScanned()
        return self._cache["private_static_async_methods"]

    def getDunderMethods(self) -> list[str]:
        """
        Return all dunder (double underscore) method names in the abstract class.

        Returns
        -------
        list of str
            List of dunder method names. Only includes methods that start and end
            with double underscores, are callable, and are not static, class
            methods, or properties.
        """
        self._ensureScanned()
        return self._cache["dunder_methods"]

    def getMagicMethods(self) -> list[str]:
        """
        Return all magic (dunder) methods from the abstract class.

        Returns
        -------
        list of str
            List of magic method names. This is an alias for getDunderMethods().
        """
        return self.getDunderMethods()

    def getProperties(self) -> list[str]:
        """
        Retrieve all property names from the abstract class.

        Returns
        -------
        List[str]
            List of property names with name mangling prefixes removed for clarity.
        """
        # Single-pass scan fills this aggregated list; return it directly
        self._ensureScanned()
        return self._cache["properties"]

    def getPublicProperties(self) -> list[str]:
        """
        Return all public property names from the abstract class.

        Parameters
        ----------
        self : ReflectionAbstract

        Returns
        -------
        list of str
            List of public property names with name mangling prefixes removed.
            Only properties that do not start with underscores are included.
        """
        # Single-pass scan fills this bucket; return it directly
        self._ensureScanned()
        return self._cache["public_properties"]

    def getProtectedProperties(self) -> list[str]:
        """
        Retrieve all protected properties from the abstract class.

        Parameters
        ----------
        self : ReflectionAbstract

        Returns
        -------
        list of str
            List of protected property names. Only includes properties that start
            with a single underscore, are not dunder, and are not name-mangled
            private properties.
        """
        # Single-pass scan fills this bucket; return it directly
        self._ensureScanned()
        return self._cache["protected_properties"]

    def getPrivateProperties(self) -> list[str]:
        """
        Retrieve all private properties from the abstract class.

        Parameters
        ----------
        self : ReflectionAbstract

        Returns
        -------
        list of str
            List of private property names with class name prefixes removed.
            Only includes name-mangled properties that start with _ClassName.
        """
        # Single-pass scan fills this bucket; return it directly
        self._ensureScanned()
        return self._cache["private_properties"]

    def getPropertySignature(self, name: str) -> inspect.Signature:
        """
        Retrieve the signature of a property's getter method.

        Parameters
        ----------
        name : str
            Name of the property to inspect.

        Returns
        -------
        inspect.Signature
            Signature object of the property's getter method.

        Raises
        ------
        ValueError
            If the property does not exist or is not accessible.
        """
        cache = self._cache
        cache_key = f"{name}_property_signature"
        if (v := cache.get(cache_key)) is not None:
            return v
        abstract = self._abstract
        # Apply Python name-mangling for private (dunder-prefixed) attributes
        if name.startswith("__") and not name.endswith("__"):
            name = f"{self._private_prefix}{name}"
        if not hasattr(abstract, name):
            msg = f"Property '{name}' does not exist in class '{self._abstract_name}'."
            raise ValueError(msg)
        prop = getattr(abstract, name)
        if not isinstance(prop, property):
            msg = f"'{name}' is not a property in class '{self._abstract_name}'."
            raise TypeError(msg)
        result: inspect.Signature = inspect.signature(prop.fget)
        cache[cache_key] = result
        return result

    def getPropertyDocstring(self, name: str) -> str | None:
        """
        Retrieve the docstring of a property's getter method.

        Parameters
        ----------
        name : str
            The name of the property.

        Returns
        -------
        str or None
            The docstring of the property's getter method, or None if unavailable.

        Raises
        ------
        ValueError
            If the property does not exist or is not accessible.
        """
        cache = self._cache
        cache_key = f"{name}_property_docstring"
        # Use 'in' check because a cached value of None is valid
        if cache_key in cache:
            return cache[cache_key]
        abstract = self._abstract
        # Apply name-mangling for private (dunder-prefixed) attributes
        if name.startswith("__") and not name.endswith("__"):
            name = f"{self._private_prefix}{name}"
        if not hasattr(abstract, name):
            msg = f"Property '{name}' does not exist in class '{self._abstract_name}'."
            raise ValueError(msg)
        prop = getattr(abstract, name)
        if not isinstance(prop, property):
            msg = f"'{name}' is not a property in class '{self._abstract_name}'."
            raise TypeError(msg)
        result: str | None = prop.fget.__doc__ if prop.fget else None
        cache[cache_key] = result
        return result

    def constructorSignature(self) -> Signature:
        """
        Retrieve constructor dependencies for the reflected class.

        Returns
        -------
        Signature
            Structured representation of constructor dependencies, including
            resolved (names and values) and unresolved (parameter names without
            default values or annotations).
        """
        cache = self._cache
        if (v := cache.get("dependencies_constructor")) is not None:
            return v
        # Delegate inspection to ReflectDependencies and cache the result
        result: Signature = ReflectDependencies(self._abstract).constructorSignature()
        cache["dependencies_constructor"] = result
        return result

    def methodSignature(self, method_name: str) -> Signature:
        """
        Retrieve resolved and unresolved dependencies for a method.

        Parameters
        ----------
        method_name : str
            Name of the method to inspect.

        Returns
        -------
        Signature
            Structured representation of method dependencies, including resolved
            and unresolved dependencies.

        Raises
        ------
        AttributeError
            If the method does not exist on the abstract class.
        """
        cache = self._cache
        cache_key = f"{method_name}_dependencies_signature"
        if (v := cache.get(cache_key)) is not None:
            return v
        if not self.hasMethod(method_name):
            msg = f"Method '{method_name}' does not exist on '{self._abstract_name}'."
            raise AttributeError(msg)
        # Apply Python name-mangling for private (non-dunder) method names
        if method_name.startswith("__") and not method_name.endswith("__"):
            method_name = f"{self._private_prefix}{method_name}"
        result: Signature = (
            ReflectDependencies(self._abstract).methodSignature(method_name)
        )
        cache[cache_key] = result
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
        # Wipe all cached entries and reset the scan flag so next
        # access triggers a full re-inspection of the abstract class.
        self._cache.clear()
        self._scanned = False
