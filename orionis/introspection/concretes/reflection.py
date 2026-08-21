from __future__ import annotations
import inspect
import keyword
from typing import TYPE_CHECKING, Any
from orionis.introspection.concretes.contracts.reflection import (
    IReflectionConcrete,
)
from orionis.introspection.dependencies.reflection import ReflectDependencies
from orionis.introspection.reflection import Reflection as _Reflection

if TYPE_CHECKING:
    from collections.abc import Callable
    from orionis.introspection.dependencies.entities.signature import (
        Signature,
    )

# Standard dunder names excluded from non-callable attribute introspection results
_DUNDER_ATTR_EXCLUDE: frozenset[str] = frozenset({
    "__class__", "__delattr__", "__dir__", "__doc__", "__eq__", "__format__",
    "__ge__", "__getattribute__", "__gt__", "__hash__", "__init__",
    "__init_subclass__", "__le__", "__lt__", "__module__", "__ne__", "__new__",
    "__reduce__", "__reduce_ex__", "__repr__", "__setattr__", "__sizeof__",
    "__str__", "__subclasshook__", "__firstlineno__", "__annotations__",
    "__static_attributes__", "__dict__", "__weakref__", "__slots__", "__mro__",
    "__subclasses__", "__bases__", "__base__", "__flags__",
    "__abstractmethods__", "__code__", "__defaults__", "__kwdefaults__",
    "__closure__",
})

class _ScanBuffers:
    """
    Collect mutable scan buckets for ReflectionConcrete._scanClass.

    Store all classification buckets in one object so type-specific
    routing helpers can run from a flat loop without passing many
    separate containers. ``__slots__`` avoids per-instance ``__dict__``
    allocations and keeps attribute access fast.
    """

    __slots__ = (
        "all_props",
        "dunder_attrs",
        "dunder_m",
        "priv_async_cm",
        "priv_async_m",
        "priv_async_sm",
        "priv_attrs",
        "priv_cm",
        "priv_m",
        "priv_props",
        "priv_sm",
        "priv_sync_cm",
        "priv_sync_m",
        "priv_sync_sm",
        "prot_async_cm",
        "prot_async_m",
        "prot_async_sm",
        "prot_attrs",
        "prot_cm",
        "prot_m",
        "prot_props",
        "prot_sm",
        "prot_sync_cm",
        "prot_sync_m",
        "prot_sync_sm",
        "pub_async_cm",
        "pub_async_m",
        "pub_async_sm",
        "pub_attrs",
        "pub_cm",
        "pub_m",
        "pub_props",
        "pub_sm",
        "pub_sync_cm",
        "pub_sync_m",
        "pub_sync_sm",
    )

    def __init__(self) -> None:
        """
        Initialize all classification buckets with empty containers.

        Returns
        -------
        None
            Return ``None`` after initializing mutable scan buffers.
        """
        # Initialize all mutable buckets used during class scanning.
        # Attribute buckets partitioned by visibility
        self.pub_attrs: dict = {}
        self.prot_attrs: dict = {}
        self.priv_attrs: dict = {}
        self.dunder_attrs: dict = {}
        # Instance method buckets partitioned by visibility and sync/async
        self.pub_m: list[str] = []
        self.pub_sync_m: list[str] = []
        self.pub_async_m: list[str] = []
        self.prot_m: list[str] = []
        self.prot_sync_m: list[str] = []
        self.prot_async_m: list[str] = []
        self.priv_m: list[str] = []
        self.priv_sync_m: list[str] = []
        self.priv_async_m: list[str] = []
        self.dunder_m: list[str] = []
        # Class method buckets partitioned by visibility and sync/async
        self.pub_cm: list[str] = []
        self.pub_sync_cm: list[str] = []
        self.pub_async_cm: list[str] = []
        self.prot_cm: list[str] = []
        self.prot_sync_cm: list[str] = []
        self.prot_async_cm: list[str] = []
        self.priv_cm: list[str] = []
        self.priv_sync_cm: list[str] = []
        self.priv_async_cm: list[str] = []
        # Static method buckets partitioned by visibility and sync/async
        self.pub_sm: list[str] = []
        self.pub_sync_sm: list[str] = []
        self.pub_async_sm: list[str] = []
        self.prot_sm: list[str] = []
        self.prot_sync_sm: list[str] = []
        self.prot_async_sm: list[str] = []
        self.priv_sm: list[str] = []
        self.priv_sync_sm: list[str] = []
        self.priv_async_sm: list[str] = []
        # Property buckets partitioned by visibility
        self.all_props: list[str] = []
        self.pub_props: list[str] = []
        self.prot_props: list[str] = []
        self.priv_props: list[str] = []

class ReflectionConcrete(IReflectionConcrete):

    # ruff: noqa: ANN401

    def __init__(self, concrete: type) -> None:
        """
        Initialize the reflection concrete with a validated class type.

        Parameters
        ----------
        concrete : Type
            The class type to reflect.

        Raises
        ------
        TypeError
            If the argument is not a class type.
        ValueError
            If the class is built-in, primitive, abstract, or an interface.

        Returns
        -------
        None
            This method does not return a value.
        """
        # Validate that the provided type is a concrete class
        if not _Reflection.isConcreteClass(concrete):
            error_msg = (
                f"Argument 'concrete' must be a class type, got "
                f"'{type(concrete).__name__}' instead."
            )
            raise TypeError(error_msg)

        # Store the class and precompute string constants reused across methods
        self._concrete = concrete
        self._class_name: str = concrete.__name__
        # Python strips the leading underscores of the class name when it
        # mangles private members, so the prefix must be built the same way.
        self._private_prefix: str = f"_{self._class_name.lstrip('_')}"
        self._private_prefix_len: int = len(self._private_prefix)
        self._cache: dict = {}

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
        # Return the value from the cache for the given key
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
        # Set the value in the cache for the given key
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
        # Return True if the key is present in the cache
        return key in self._cache

    def __delitem__(self, key: str) -> None:
        """
        Remove an item from the cache by key.

        Parameters
        ----------
        key : str
            The key to remove from the cache.

        Returns
        -------
        None
            This method does not return a value.
        """
        # Remove the key from the cache if present
        self._cache.pop(key, None)

    @staticmethod
    def _routeStaticMethod(
        attr: str,
        value: staticmethod,
        prefix: str,
        prefix_len: int,
        buf: _ScanBuffers,
    ) -> None:
        """
        Route a static method into the correct visibility and async bucket.

        Determines coroutine status from the wrapped ``__func__`` and
        appends the attribute name to the appropriate ``_ScanBuffers``
        lists for private, protected, or public static methods.

        Parameters
        ----------
        attr : str
            Raw attribute name from the class ``__dict__``.
        value : staticmethod
            The ``staticmethod`` descriptor to classify.
        prefix : str
            Private name-mangling prefix (e.g. ``_ClassName``).
        prefix_len : int
            Pre-computed length of ``prefix`` for efficient slicing.
        buf : _ScanBuffers
            Mutable accumulator that collects all classification results.

        Returns
        -------
        None
            Results are written into ``buf`` in place.
        """
        # Detect coroutine status from the underlying wrapped function
        is_coro = inspect.iscoroutinefunction(value.__func__)
        # Private: strip name-mangling prefix before appending
        if attr.startswith(prefix):
            clean = attr[prefix_len:]
            buf.priv_sm.append(clean)
            (buf.priv_async_sm if is_coro else buf.priv_sync_sm).append(clean)
        elif not attr.startswith("__"):
            if attr.startswith("_"):
                # Protected: single underscore prefix
                buf.prot_sm.append(attr)
                (buf.prot_async_sm if is_coro else buf.prot_sync_sm).append(attr)
            else:
                # Public: no underscore prefix
                buf.pub_sm.append(attr)
                (buf.pub_async_sm if is_coro else buf.pub_sync_sm).append(attr)

    @staticmethod
    def _routeClassMethod(
        attr: str,
        value: classmethod,
        prefix: str,
        prefix_len: int,
        buf: _ScanBuffers,
    ) -> None:
        """
        Route a class method into the correct visibility and async bucket.

        Determines coroutine status from the wrapped ``__func__`` and
        appends the attribute name to the appropriate ``_ScanBuffers``
        lists for private, protected, or public class methods.

        Parameters
        ----------
        attr : str
            Raw attribute name from the class ``__dict__``.
        value : classmethod
            The ``classmethod`` descriptor to classify.
        prefix : str
            Private name-mangling prefix (e.g. ``_ClassName``).
        prefix_len : int
            Pre-computed length of ``prefix`` for efficient slicing.
        buf : _ScanBuffers
            Mutable accumulator that collects all classification results.

        Returns
        -------
        None
            Results are written into ``buf`` in place.
        """
        # Detect coroutine status from the underlying wrapped function
        is_coro = inspect.iscoroutinefunction(value.__func__)
        # Private: strip name-mangling prefix before appending
        if attr.startswith(prefix):
            clean = attr[prefix_len:]
            buf.priv_cm.append(clean)
            (buf.priv_async_cm if is_coro else buf.priv_sync_cm).append(clean)
        elif not attr.startswith("__"):
            if attr.startswith("_"):
                # Protected: single underscore prefix
                buf.prot_cm.append(attr)
                (buf.prot_async_cm if is_coro else buf.prot_sync_cm).append(attr)
            else:
                # Public: no underscore prefix
                buf.pub_cm.append(attr)
                (buf.pub_async_cm if is_coro else buf.pub_sync_cm).append(attr)

    @staticmethod
    def _routeProperty(
        attr: str,
        prefix: str,
        prefix_len: int,
        buf: _ScanBuffers,
    ) -> None:
        """
        Route a property descriptor into the correct visibility bucket.

        Appends the property name (with name mangling resolved) to the
        ``_ScanBuffers`` lists for private, protected, or public
        properties, and always to the global ``all_props`` list.

        Parameters
        ----------
        attr : str
            Raw attribute name from the class ``__dict__``.
        prefix : str
            Private name-mangling prefix (e.g. ``_ClassName``).
        prefix_len : int
            Pre-computed length of ``prefix`` for efficient slicing.
        buf : _ScanBuffers
            Mutable accumulator that collects all classification results.

        Returns
        -------
        None
            Results are written into ``buf`` in place.
        """
        # Private property: strip name-mangling prefix
        if attr.startswith(prefix):
            clean = attr[prefix_len:]
            buf.priv_props.append(clean)
            buf.all_props.append(clean)
        elif not attr.startswith("__"):
            buf.all_props.append(attr)
            if attr.startswith("_"):
                # Protected property: single underscore prefix
                buf.prot_props.append(attr)
            else:
                # Public property: no underscore prefix
                buf.pub_props.append(attr)

    @staticmethod
    def _routeMethod(
        attr: str,
        value: object,
        prefix: str,
        prefix_len: int,
        buf: _ScanBuffers,
    ) -> None:
        """
        Route a plain callable into the correct instance method buckets.

        Classifies the attribute as private, dunder, protected, or public
        and further separates sync from async variants within each group.

        Parameters
        ----------
        attr : str
            Raw attribute name from the class ``__dict__``.
        value : object
            The callable object to classify.
        prefix : str
            Private name-mangling prefix (e.g. ``_ClassName``).
        prefix_len : int
            Pre-computed length of ``prefix`` for efficient slicing.
        buf : _ScanBuffers
            Mutable accumulator that collects all classification results.

        Returns
        -------
        None
            Results are written into ``buf`` in place.
        """
        # Detect async vs sync before branching on visibility
        is_coro = inspect.iscoroutinefunction(value)
        # Private: strip name-mangling prefix before appending
        if attr.startswith(prefix):
            clean = attr[prefix_len:]
            buf.priv_m.append(clean)
            (buf.priv_async_m if is_coro else buf.priv_sync_m).append(clean)
        elif attr.startswith("__") and attr.endswith("__"):
            # Dunder method: double underscore on both sides
            buf.dunder_m.append(attr)
        elif attr.startswith("_"):
            # Protected: single underscore prefix
            buf.prot_m.append(attr)
            (buf.prot_async_m if is_coro else buf.prot_sync_m).append(attr)
        else:
            # Public: no underscore prefix
            buf.pub_m.append(attr)
            (buf.pub_async_m if is_coro else buf.pub_sync_m).append(attr)

    @staticmethod
    def _routeAttribute(
        attr: str,
        value: object,
        prefix: str,
        prefix_len: int,
        buf: _ScanBuffers,
    ) -> None:
        """
        Route a non-callable member into the correct attribute bucket.

        Classifies the attribute as private, dunder, protected, or public
        and stores the value in the corresponding dictionary within
        ``_ScanBuffers``. Standard dunder attributes listed in
        ``_DUNDER_ATTR_EXCLUDE`` are silently skipped.

        Parameters
        ----------
        attr : str
            Raw attribute name from the class ``__dict__``.
        value : object
            The non-callable value to classify.
        prefix : str
            Private name-mangling prefix (e.g. ``_ClassName``).
        prefix_len : int
            Pre-computed length of ``prefix`` for efficient slicing.
        buf : _ScanBuffers
            Mutable accumulator that collects all classification results.

        Returns
        -------
        None
            Results are written into ``buf`` in place.
        """
        # Private attribute: strip name-mangling prefix
        if attr.startswith(prefix):
            buf.priv_attrs[attr[prefix_len:]] = value
        elif attr.startswith("__") and attr.endswith("__"):
            # Only include dunder attributes not in the exclusion set
            if attr not in _DUNDER_ATTR_EXCLUDE:
                buf.dunder_attrs[attr] = value
        elif attr.startswith("_"):
            # Protected attribute: single underscore prefix
            buf.prot_attrs[attr] = value
        else:
            # Public attribute: no underscore prefix
            buf.pub_attrs[attr] = value

    def _scanClass(self) -> None:
        """
        Perform a single-pass classification of all members in the class __dict__.

        Partitions every entry in the class dictionary into its respective
        category: public/protected/private/dunder for attributes, instance
        methods, class methods, static methods, and properties. Sync/async
        variants are determined in the same pass using the raw function objects,
        avoiding repeated getattr calls. All results are stored atomically in
        the instance cache via a single dict.update call.

        Returns
        -------
        None
            All classification results are stored atomically in the
            instance cache via a single ``dict.update`` call.
        """
        # Initialize the accumulator and bind local constants for the loop
        buf = _ScanBuffers()
        prefix = self._private_prefix
        prefix_len = self._private_prefix_len

        # Dispatch each class member to its type-specific routing helper
        for attr, value in self._concrete.__dict__.items():
            if isinstance(value, staticmethod):
                self._routeStaticMethod(attr, value, prefix, prefix_len, buf)
            elif isinstance(value, classmethod):
                self._routeClassMethod(attr, value, prefix, prefix_len, buf)
            elif isinstance(value, property):
                self._routeProperty(attr, prefix, prefix_len, buf)
            elif callable(value):
                self._routeMethod(attr, value, prefix, prefix_len, buf)
            else:
                self._routeAttribute(attr, value, prefix, prefix_len, buf)

        # Aggregate cross-category collections before caching
        all_attrs: dict = {
            **buf.pub_attrs, **buf.prot_attrs,
            **buf.priv_attrs, **buf.dunder_attrs,
        }
        all_methods: list[str] = [
            *buf.pub_m, *buf.prot_m, *buf.priv_m,
            *buf.pub_cm, *buf.prot_cm, *buf.priv_cm,
            *buf.pub_sm, *buf.prot_sm, *buf.priv_sm,
        ]

        # Store all classification results atomically via a single dict update
        self._cache.update({
            "public_attributes":             buf.pub_attrs,
            "protected_attributes":          buf.prot_attrs,
            "private_attributes":            buf.priv_attrs,
            "dunder_attributes":             buf.dunder_attrs,
            "attributes":                    all_attrs,
            "public_methods":                buf.pub_m,
            "public_sync_methods":           buf.pub_sync_m,
            "public_async_methods":          buf.pub_async_m,
            "protected_methods":             buf.prot_m,
            "protected_sync_methods":        buf.prot_sync_m,
            "protected_async_methods":       buf.prot_async_m,
            "private_methods":               buf.priv_m,
            "private_sync_methods":          buf.priv_sync_m,
            "private_async_methods":         buf.priv_async_m,
            "dunder_methods":                buf.dunder_m,
            "public_class_methods":          buf.pub_cm,
            "public_class_sync_methods":     buf.pub_sync_cm,
            "public_class_async_methods":    buf.pub_async_cm,
            "protected_class_methods":       buf.prot_cm,
            "protected_class_sync_methods":  buf.prot_sync_cm,
            "protected_class_async_methods": buf.prot_async_cm,
            "private_class_methods":         buf.priv_cm,
            "private_class_sync_methods":    buf.priv_sync_cm,
            "private_class_async_methods":   buf.priv_async_cm,
            "public_static_methods":         buf.pub_sm,
            "public_static_sync_methods":    buf.pub_sync_sm,
            "public_static_async_methods":   buf.pub_async_sm,
            "protected_static_methods":         buf.prot_sm,
            "protected_static_sync_methods":    buf.prot_sync_sm,
            "protected_static_async_methods":   buf.prot_async_sm,
            "private_static_methods":        buf.priv_sm,
            "private_static_sync_methods":   buf.priv_sync_sm,
            "private_static_async_methods":  buf.priv_async_sm,
            "properties":                    buf.all_props,
            "public_properties":             buf.pub_props,
            "protected_properties":          buf.prot_props,
            "private_properties":            buf.priv_props,
            "methods":                       all_methods,
            "methods_set":                   frozenset(all_methods),
        })

    def getClass(self) -> type:
        """
        Return the class type being reflected.

        Returns
        -------
        Type
            The class type provided during initialization.
        """
        return self._concrete

    def getClassName(self) -> str:
        """
        Return the name of the reflected class.

        Returns
        -------
        str
            The simple name of the class without module qualification.
        """
        return self._class_name

    def getModuleName(self) -> str:
        """
        Return the module name where the reflected class is defined.

        Returns
        -------
        str
            The fully qualified module name containing the class.
        """
        return self._concrete.__module__

    def getModuleWithClassName(self) -> str:
        """
        Return the fully qualified class name with module path.

        Returns
        -------
        str
            The module name concatenated with the class name, separated by a dot.
        """
        # Return cached result to avoid repeated string concatenation on each call
        _cache = self._cache
        if "module_with_class_name" in _cache:
            return _cache["module_with_class_name"]
        result = f"{self._concrete.__module__}.{self._class_name}"
        _cache["module_with_class_name"] = result
        return result

    def getDocstring(self) -> str | None:
        """
        Return the docstring of the reflected class.

        Returns
        -------
        str or None
            The docstring of the class if defined, otherwise None.
        """
        # Return the class docstring if available
        return self._concrete.__doc__ or None

    def getBaseClasses(self) -> list[type]:
        """
        Return all base classes of the reflected class.

        Returns
        -------
        list of type
            A list containing all base classes in the method resolution order.
        """
        # Return the immediate base classes of the reflected class
        return list(self._concrete.__bases__)

    def getSourceCode(self, method: str | None = None) -> str | None:
        """
        Retrieve the source code for the class or a specific method.

        Parameters
        ----------
        method : str or None, optional
            Name of the method to retrieve source code for. If None, returns
            the source code of the entire class.

        Returns
        -------
        str or None
            Source code as a string if available, otherwise None.
        """
        _cache = self._cache
        try:
            if not method:
                # Return cached class source if already retrieved
                cached = _cache.get("source_code")
                if cached is not None:
                    return cached
                src = inspect.getsource(self._concrete)
                _cache["source_code"] = src
                return src

            # Compute cache key once to avoid redundant f-string construction
            cache_key = f"source_code_{method}"
            cached = _cache.get(cache_key)
            if cached is not None:
                return cached

            # Resolve private method name mangling before attribute access;
            # hasMethod() indexes the demangled names produced by the scan.
            resolved = method
            if method.startswith("__") and not method.endswith("__"):
                resolved = self._private_prefix + method

            if not self.hasMethod(method):
                return None

            src = inspect.getsource(getattr(self._concrete, resolved))
            _cache[cache_key] = src
            return src

        except (TypeError, OSError):
            # Return None if source code cannot be retrieved
            return None

    def getFile(self) -> str:
        """
        Return the absolute file path of the reflected class.

        Returns
        -------
        str
            The absolute file path containing the class definition.

        Raises
        ------
        ValueError
            If the file path cannot be determined.
        """
        # Return cached file path if available
        _cache = self._cache
        if "file_path" in _cache:
            return _cache["file_path"]
        try:
            # Retrieve and cache the file path of the class
            file_path = inspect.getfile(self._concrete)
            _cache["file_path"] = file_path
            return file_path
        except TypeError as e:
            error_msg = (
                f"Could not retrieve file for '{self._class_name}': {e}"
            )
            raise ValueError(error_msg) from e

    def getAnnotations(self) -> dict:
        """
        Retrieve type annotations defined on the reflected class.

        Resolves name mangling for private attributes and returns a dictionary
        mapping attribute names to their type annotations.

        Returns
        -------
        dict
            Dictionary of attribute names and their type annotations.
        """
        # Return cached annotations if available
        _cache = self._cache
        if "annotations" in _cache:
            return _cache["annotations"]

        # Read raw annotations using getattr to support Python 3.14+ (PEP 649)
        private_prefix = self._private_prefix
        prefix_len = self._private_prefix_len
        raw: dict = getattr(self._concrete, "__annotations__", {})
        # Strip private name-mangling prefix using a slice instead of str.replace
        annotations = {
            (k[prefix_len:] if k.startswith(private_prefix) else k): v
            for k, v in raw.items()
        }
        _cache["annotations"] = annotations
        return annotations

    def hasAttribute(self, attribute: str) -> bool:
        """
        Determine if the reflected class has a specific attribute.

        Parameters
        ----------
        attribute : str
            Name of the attribute to check.

        Returns
        -------
        bool
            True if the attribute exists in the class, otherwise False.
        """
        # Trigger the single-pass scan if attributes are not yet classified
        _cache = self._cache
        if "attributes" not in _cache:
            self._scanClass()
        return attribute in _cache["attributes"]

    def getAttribute(self, name: str, default: Any = None) -> Any:
        """
        Retrieve the value of a class attribute.

        Parameters
        ----------
        name : str
            Name of the attribute to retrieve.
        default : Any, optional
            Value to return if the attribute is not found. Defaults to None.

        Returns
        -------
        Any
            Value of the attribute if found, otherwise the default value.
        """
        # Fetch from classified attributes, falling back to direct getattr
        _cache = self._cache
        if "attributes" not in _cache:
            self._scanClass()
        attrs = _cache["attributes"]
        return attrs.get(name, getattr(self._concrete, name, default))

    def setAttribute(self, name: str, value: object) -> bool:
        """
        Set a class attribute to the specified value.

        Parameters
        ----------
        name : str
            Name of the attribute to set.
        value : object
            Value to assign to the attribute.

        Returns
        -------
        bool
            True if the attribute was set successfully.

        Raises
        ------
        ValueError
            If the attribute name is invalid or the value is callable.
        """
        # Validate attribute name: must be a valid identifier and not a keyword
        if (
            not isinstance(name, str)
            or not name.isidentifier()
            or keyword.iskeyword(name)
        ):
            error_msg = (
                f"Invalid attribute name '{name}'. Must be a valid Python identifier "
                "and not a keyword."
            )
            raise ValueError(error_msg)

        # Prevent setting callables as attributes; suggest setMethod instead
        if callable(value):
            error_msg = (
                f"Cannot set attribute '{name}' to a callable. Use setMethod instead."
            )
            raise TypeError(error_msg)

        # Handle name mangling for private attributes
        if name.startswith("__") and not name.endswith("__"):
            name = self._private_prefix + name

        # Mutate the class and invalidate the entire cache
        setattr(self._concrete, name, value)
        self._cache.clear()
        return True

    def removeAttribute(self, name: str) -> bool:
        """
        Remove an attribute from the reflected class.

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
        # Verify the attribute exists before attempting removal
        if not self.hasAttribute(name):
            error_msg = (
                f"Attribute '{name}' does not exist in class '{self._class_name}'."
            )
            raise ValueError(error_msg)

        # Handle name mangling for private attributes
        if name.startswith("__") and not name.endswith("__"):
            name = self._private_prefix + name

        # Remove the attribute and invalidate the entire cache
        delattr(self._concrete, name)
        self._cache.clear()
        return True

    def getAttributes(self) -> dict:
        """
        Aggregate all class attributes of all visibility levels.

        Returns
        -------
        dict
            Dictionary mapping attribute names (str) to their values. Includes
            public, protected, private (with name mangling removed), and dunder
            attributes. Excludes methods and properties. The result is cached.
        """
        # Trigger the single-pass scan if not yet populated
        _cache = self._cache
        if "attributes" not in _cache:
            self._scanClass()
        return _cache["attributes"]

    def getPublicAttributes(self) -> dict:
        """
        Retrieve all public class attributes.

        Public attributes are those that do not start with an underscore and are
        not callables, static methods, class methods, or properties.

        Returns
        -------
        dict
            Dictionary mapping public attribute names to their values. Excludes
            dunder, protected, and private attributes.
        """
        # Trigger the single-pass scan if not yet populated
        _cache = self._cache
        if "public_attributes" not in _cache:
            self._scanClass()
        return _cache["public_attributes"]

    def getProtectedAttributes(self) -> dict:
        """
        Retrieve all protected class attributes.

        Protected attributes are those that start with a single underscore,
        excluding dunder, public, and private attributes.

        Returns
        -------
        dict
            Dictionary mapping protected attribute names to their values.
        """
        # Trigger the single-pass scan if not yet populated
        _cache = self._cache
        if "protected_attributes" not in _cache:
            self._scanClass()
        return _cache["protected_attributes"]

    def getPrivateAttributes(self) -> dict:
        """
        Retrieve all private class attributes.

        Private attributes use Python's name mangling convention (double
        underscore prefix). Excludes methods, static methods, class methods,
        and properties.

        Returns
        -------
        dict
            Dictionary mapping private attribute names (with mangling removed)
            to their values.
        """
        # Trigger the single-pass scan if not yet populated
        _cache = self._cache
        if "private_attributes" not in _cache:
            self._scanClass()
        return _cache["private_attributes"]

    def getDunderAttributes(self) -> dict:
        """
        Retrieve all dunder (magic) class attributes.

        Dunder attributes are those with names that start and end with double
        underscores, excluding standard Python dunder attributes.

        Returns
        -------
        dict
            Dictionary mapping dunder attribute names to their values, excluding
            standard Python dunder attributes.
        """
        # Trigger the single-pass scan if not yet populated
        _cache = self._cache
        if "dunder_attributes" not in _cache:
            self._scanClass()
        return _cache["dunder_attributes"]

    def getMagicAttributes(self) -> dict:
        """
        Return all magic (dunder) class attributes.

        This method is an alias for `getDunderAttributes()` and provides access
        to double underscore attributes.

        Returns
        -------
        dict
            Dictionary mapping magic attribute names to their values.
        """
        return self.getDunderAttributes()

    def hasMethod(self, name: str) -> bool:
        """
        Determine if the class defines a method with the given name.

        Parameters
        ----------
        name : str
            Name of the method to check.

        Returns
        -------
        bool
            True if the method exists in the class, otherwise False.
        """
        # Use a frozenset for O(1) membership test instead of an O(n) list scan
        _cache = self._cache
        if "methods_set" not in _cache:
            self._scanClass()
        return name in _cache["methods_set"]

    def setMethod(self, name: str, method: Callable) -> bool:
        """
        Add a method to the reflected class.

        Validates the method name and callable before adding it to the class.
        Handles private method name mangling automatically.

        Parameters
        ----------
        name : str
            Name for the new method.
        method : Callable
            Callable object to set as a method.

        Returns
        -------
        bool
            True if the method was successfully added.

        Raises
        ------
        ValueError
            If the method name already exists, is invalid, or the object is not
            callable.
        """
        # Reject duplicate method names before any further validation
        if self.hasMethod(name):
            error_msg = (
                f"Method '{name}' already exists in class '{self._class_name}'. "
                "Use a different name or remove the existing method first."
            )
            raise ValueError(error_msg)

        # Ensure the name is a valid Python identifier and not a keyword
        if (
            not isinstance(name, str)
            or not name.isidentifier()
            or keyword.iskeyword(name)
        ):
            error_msg = (
                f"Invalid method name '{name}'. Must be a valid Python identifier "
                "and not a keyword."
            )
            raise ValueError(error_msg)

        # Ensure the supplied value is callable
        if not callable(method):
            error_msg = (
                f"Cannot set method '{name}' to a non-callable value."
            )
            raise TypeError(error_msg)

        # Handle private method name mangling
        if name.startswith("__") and not name.endswith("__"):
            name = self._private_prefix + name

        # Mutate the class and invalidate the entire cache
        setattr(self._concrete, name, method)
        self._cache.clear()
        return True

    def removeMethod(self, name: str) -> bool:
        """
        Remove a method from the reflected class.

        Handles private method name mangling before removal.

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
        # Verify the method exists before attempting removal
        if not self.hasMethod(name):
            error_msg = (
                f"Method '{name}' does not exist in class '{self._class_name}'."
            )
            raise ValueError(error_msg)

        # Handle name mangling for private methods
        if name.startswith("__") and not name.endswith("__"):
            name = self._private_prefix + name

        # Remove the method and invalidate the entire cache
        delattr(self._concrete, name)
        self._cache.clear()
        return True

    def getMethodSignature(self, name: str) -> inspect.Signature:
        """
        Retrieve the signature of a specific method.

        Parameters
        ----------
        name : str
            Name of the method to inspect.

        Returns
        -------
        inspect.Signature
            Signature object containing parameter and return information.

        Raises
        ------
        ValueError
            If the method does not exist or is not callable.
        """
        # Compute cache key once; reuse for both read and write operations
        cache_key = f"method_signature_{name}"
        _cache = self._cache
        if cache_key in _cache:
            return _cache[cache_key]

        # Validate method existence before inspection
        if not self.hasMethod(name):
            error_msg = (
                f"Method '{name}' does not exist in class '{self._class_name}'."
            )
            raise ValueError(error_msg)

        # Resolve private method name mangling before attribute access
        resolved = name
        if name.startswith("__") and not name.endswith("__"):
            resolved = self._private_prefix + name

        method = getattr(self._concrete, resolved, None)

        # Ensure the retrieved attribute is callable
        if not callable(method):
            error_msg = f"'{name}' is not callable in class '{self._class_name}'."
            raise TypeError(error_msg)

        # Cache and return the method signature
        sig = inspect.signature(method)
        _cache[cache_key] = sig
        return sig

    def getMethods(self) -> list[str]:
        """
        Retrieve all method names defined in the reflected class.

        Aggregates method names from all visibility levels (public, protected,
        private) and method types (instance, class, static). The result is
        cached after the first call for efficiency.

        Returns
        -------
        list of str
            List of all method names (instance, class, and static) defined in
            the class, including public, protected, and private methods.
        """
        # Trigger the single-pass scan if not yet populated
        _cache = self._cache
        if "methods" not in _cache:
            self._scanClass()
        return _cache["methods"]

    def getPublicMethods(self) -> list[str]:
        """
        Return all public instance method names of the reflected class.

        Retrieves method names that are callable, not static or class methods,
        not properties, and do not start with underscores.

        Returns
        -------
        list of str
            List of public instance method names.
        """
        # Trigger the single-pass scan if not yet populated
        _cache = self._cache
        if "public_methods" not in _cache:
            self._scanClass()
        return _cache["public_methods"]

    def getPublicSyncMethods(self) -> list[str]:
        """
        Return all public synchronous method names of the reflected class.

        Filters public methods to include only those that are not coroutine
        functions.

        Returns
        -------
        list of str
            List of public synchronous method names.
        """
        # Trigger the single-pass scan if not yet populated
        _cache = self._cache
        if "public_sync_methods" not in _cache:
            self._scanClass()
        return _cache["public_sync_methods"]

    def getPublicAsyncMethods(self) -> list[str]:
        """
        Return all public asynchronous method names of the reflected class.

        Filters public methods to include only coroutine functions.

        Returns
        -------
        list of str
            List of public asynchronous method names.
        """
        # Trigger the single-pass scan if not yet populated
        _cache = self._cache
        if "public_async_methods" not in _cache:
            self._scanClass()
        return _cache["public_async_methods"]

    def getProtectedMethods(self) -> list[str]:
        """
        Return all protected instance method names.

        Protected methods start with a single underscore, are not dunder,
        and are not private (name-mangled). Excludes static, class methods,
        and properties.

        Returns
        -------
        list of str
            List of protected instance method names.
        """
        # Trigger the single-pass scan if not yet populated
        _cache = self._cache
        if "protected_methods" not in _cache:
            self._scanClass()
        return _cache["protected_methods"]

    def getProtectedSyncMethods(self) -> list[str]:
        """
        Return all protected synchronous method names.

        Filters protected methods to include only those that are not coroutine
        functions.

        Returns
        -------
        list of str
            List of protected synchronous method names.
        """
        # Trigger the single-pass scan if not yet populated
        _cache = self._cache
        if "protected_sync_methods" not in _cache:
            self._scanClass()
        return _cache["protected_sync_methods"]

    def getProtectedAsyncMethods(self) -> list[str]:
        """
        Retrieve all protected asynchronous method names.

        Filters protected methods to include only those that are coroutine
        functions.

        Returns
        -------
        list of str
            List of protected asynchronous method names.
        """
        # Trigger the single-pass scan if not yet populated
        _cache = self._cache
        if "protected_async_methods" not in _cache:
            self._scanClass()
        return _cache["protected_async_methods"]

    def getPrivateMethods(self) -> list[str]:
        """
        Retrieve all private instance method names.

        Private methods are those using Python's name mangling convention
        (class name prefix). Name mangling is resolved in the returned names.

        Returns
        -------
        list of str
            List of private instance method names with mangling removed.
        """
        # Trigger the single-pass scan if not yet populated
        _cache = self._cache
        if "private_methods" not in _cache:
            self._scanClass()
        return _cache["private_methods"]

    def getPrivateSyncMethods(self) -> list[str]:
        """
        Return all private synchronous method names of the class.

        Returns
        -------
        list of str
            List of private synchronous method names.
        """
        # Trigger the single-pass scan if not yet populated
        _cache = self._cache
        if "private_sync_methods" not in _cache:
            self._scanClass()
        return _cache["private_sync_methods"]

    def getPrivateAsyncMethods(self) -> list[str]:
        """
        Return all private asynchronous method names of the class.

        Finds private methods (using name mangling) that are coroutine functions.

        Returns
        -------
        list of str
            List of private asynchronous method names.
        """
        # Trigger the single-pass scan if not yet populated
        _cache = self._cache
        if "private_async_methods" not in _cache:
            self._scanClass()
        return _cache["private_async_methods"]

    def getPublicClassMethods(self) -> list[str]:
        """
        Return a list of public class method names.

        Public class methods are those that do not start with an underscore,
        are not dunder, and are not private (name-mangled).

        Returns
        -------
        list of str
            List of public class method names.
        """
        # Trigger the single-pass scan if not yet populated
        _cache = self._cache
        if "public_class_methods" not in _cache:
            self._scanClass()
        return _cache["public_class_methods"]

    def getPublicClassSyncMethods(self) -> list[str]:
        """
        Return all public synchronous class method names.

        Returns
        -------
        list of str
            List of public synchronous class method names.
        """
        # Trigger the single-pass scan if not yet populated
        _cache = self._cache
        if "public_class_sync_methods" not in _cache:
            self._scanClass()
        return _cache["public_class_sync_methods"]

    def getPublicClassAsyncMethods(self) -> list[str]:
        """
        Return all public asynchronous class method names.

        Returns
        -------
        list of str
            List of public asynchronous class method names.
        """
        # Trigger the single-pass scan if not yet populated
        _cache = self._cache
        if "public_class_async_methods" not in _cache:
            self._scanClass()
        return _cache["public_class_async_methods"]

    def getProtectedClassMethods(self) -> list[str]:
        """
        Return a list of protected class method names.

        Protected class methods start with a single underscore, are not dunder,
        and are not private (name-mangled).

        Returns
        -------
        list of str
            List of protected class method names.
        """
        # Trigger the single-pass scan if not yet populated
        _cache = self._cache
        if "protected_class_methods" not in _cache:
            self._scanClass()
        return _cache["protected_class_methods"]

    def getProtectedClassSyncMethods(self) -> list[str]:
        """
        Return all protected synchronous class method names.

        Returns
        -------
        list of str
            List of protected synchronous class method names.
        """
        # Trigger the single-pass scan if not yet populated
        _cache = self._cache
        if "protected_class_sync_methods" not in _cache:
            self._scanClass()
        return _cache["protected_class_sync_methods"]

    def getProtectedClassAsyncMethods(self) -> list[str]:
        """
        Return all protected asynchronous class method names.

        Returns
        -------
        list of str
            List of protected asynchronous class method names.
        """
        # Trigger the single-pass scan if not yet populated
        _cache = self._cache
        if "protected_class_async_methods" not in _cache:
            self._scanClass()
        return _cache["protected_class_async_methods"]

    def getPrivateClassMethods(self) -> list[str]:
        """
        Return a list of private class method names.

        Private class methods use Python's name mangling convention and are
        defined with a double underscore prefix.

        Returns
        -------
        list of str
            List of private class method names with name mangling removed.
        """
        # Trigger the single-pass scan if not yet populated
        _cache = self._cache
        if "private_class_methods" not in _cache:
            self._scanClass()
        return _cache["private_class_methods"]

    def getPrivateClassSyncMethods(self) -> list[str]:
        """
        Return all private synchronous class method names.

        Returns
        -------
        list of str
            List of private synchronous class method names.
        """
        # Trigger the single-pass scan if not yet populated
        _cache = self._cache
        if "private_class_sync_methods" not in _cache:
            self._scanClass()
        return _cache["private_class_sync_methods"]

    def getPrivateClassAsyncMethods(self) -> list[str]:
        """
        Return all private asynchronous class method names.

        Finds private class methods (using name mangling) that are coroutine
        functions.

        Returns
        -------
        list of str
            List of private asynchronous class method names.
        """
        # Trigger the single-pass scan if not yet populated
        _cache = self._cache
        if "private_class_async_methods" not in _cache:
            self._scanClass()
        return _cache["private_class_async_methods"]

    def getPublicStaticMethods(self) -> list[str]:
        """
        Return a list of public static method names.

        Scans the class dictionary for static methods that are public, i.e.,
        do not start with underscores or use name mangling.

        Returns
        -------
        list of str
            List of public static method names.
        """
        # Trigger the single-pass scan if not yet populated
        _cache = self._cache
        if "public_static_methods" not in _cache:
            self._scanClass()
        return _cache["public_static_methods"]

    def getPublicStaticSyncMethods(self) -> list[str]:
        """
        Return all public synchronous static method names of the class.

        Returns
        -------
        list of str
            List of public synchronous static method names.
        """
        # Trigger the single-pass scan if not yet populated
        _cache = self._cache
        if "public_static_sync_methods" not in _cache:
            self._scanClass()
        return _cache["public_static_sync_methods"]

    def getPublicStaticAsyncMethods(self) -> list[str]:
        """
        Return all public asynchronous static method names of the class.

        Returns
        -------
        list of str
            List of public asynchronous static method names.
        """
        # Trigger the single-pass scan if not yet populated
        _cache = self._cache
        if "public_static_async_methods" not in _cache:
            self._scanClass()
        return _cache["public_static_async_methods"]

    def getProtectedStaticMethods(self) -> list[str]:
        """
        Return a list of protected static method names.

        Protected static methods start with a single underscore, are not dunder,
        and are not private (name-mangled).

        Returns
        -------
        list of str
            List of protected static method names.
        """
        # Trigger the single-pass scan if not yet populated
        _cache = self._cache
        if "protected_static_methods" not in _cache:
            self._scanClass()
        return _cache["protected_static_methods"]

    def getProtectedStaticSyncMethods(self) -> list[str]:
        """
        Return all protected synchronous static method names of the class.

        Returns
        -------
        list of str
            List of protected synchronous static method names.
        """
        # Trigger the single-pass scan if not yet populated
        _cache = self._cache
        if "protected_static_sync_methods" not in _cache:
            self._scanClass()
        return _cache["protected_static_sync_methods"]

    def getProtectedStaticAsyncMethods(self) -> list[str]:
        """
        Retrieve all protected asynchronous static method names.

        Returns
        -------
        list of str
            List of protected asynchronous static method names.
        """
        # Trigger the single-pass scan if not yet populated
        _cache = self._cache
        if "protected_static_async_methods" not in _cache:
            self._scanClass()
        return _cache["protected_static_async_methods"]

    def getPrivateStaticMethods(self) -> list[str]:
        """
        Return the names of all private static methods of the class.

        Private static methods are those using Python's name mangling
        convention (class name prefix).

        Returns
        -------
        list of str
            List of private static method names with name mangling removed.
        """
        # Trigger the single-pass scan if not yet populated
        _cache = self._cache
        if "private_static_methods" not in _cache:
            self._scanClass()
        return _cache["private_static_methods"]

    def getPrivateStaticSyncMethods(self) -> list[str]:
        """
        Return all private synchronous static method names of the class.

        Returns
        -------
        list of str
            List of private synchronous static method names.
        """
        # Trigger the single-pass scan if not yet populated
        _cache = self._cache
        if "private_static_sync_methods" not in _cache:
            self._scanClass()
        return _cache["private_static_sync_methods"]

    def getPrivateStaticAsyncMethods(self) -> list[str]:
        """
        Retrieve all private asynchronous static method names of the class.

        Returns
        -------
        list of str
            List of private asynchronous static method names.
        """
        # Trigger the single-pass scan if not yet populated
        _cache = self._cache
        if "private_static_async_methods" not in _cache:
            self._scanClass()
        return _cache["private_static_async_methods"]

    def getDunderMethods(self) -> list[str]:
        """
        Retrieve all dunder (magic) method names from the reflected class.

        Finds callable attributes that follow the double underscore naming
        convention, excluding static, class methods, and properties.

        Returns
        -------
        list of str
            List of dunder method names available in the class.
        """
        # Trigger the single-pass scan if not yet populated
        _cache = self._cache
        if "dunder_methods" not in _cache:
            self._scanClass()
        return _cache["dunder_methods"]

    def getMagicMethods(self) -> list[str]:
        """
        Return all magic (dunder) method names from the reflected class.

        This is an alias for ``getDunderMethods()``, providing alternative
        naming for accessing double underscore methods.

        Returns
        -------
        list of str
            List of magic method names available in the class.
        """
        return self.getDunderMethods()

    def getProperties(self) -> list[str]:
        """
        Return all property names defined in the reflected class.

        Scans the class dictionary for property objects and returns their names
        with private attribute name mangling resolved.

        Returns
        -------
        list of str
            List of all property names in the class, with name mangling removed.
        """
        # Trigger the single-pass scan if not yet populated
        _cache = self._cache
        if "properties" not in _cache:
            self._scanClass()
        return _cache["properties"]

    def getPublicProperties(self) -> list[str]:
        """
        Return all public property names of the reflected class.

        Properties are considered public if their names do not start with
        underscores or the class name (for name-mangled attributes).

        Returns
        -------
        list of str
            List of public property names with name mangling resolved.
        """
        # Trigger the single-pass scan if not yet populated
        _cache = self._cache
        if "public_properties" not in _cache:
            self._scanClass()
        return _cache["public_properties"]

    def getProtectedProperties(self) -> list[str]:
        """
        Retrieve all protected property names from the reflected class.

        Protected properties are those that start with a single underscore,
        are not private (name-mangled), and are not dunder attributes.

        Returns
        -------
        list of str
            List of protected property names.
        """
        # Trigger the single-pass scan if not yet populated
        _cache = self._cache
        if "protected_properties" not in _cache:
            self._scanClass()
        return _cache["protected_properties"]

    def getPrivateProperties(self) -> list[str]:
        """
        Return all private property names of the reflected class.

        Private properties use Python's name mangling convention (class name
        prefix). The returned names have name mangling removed.

        Returns
        -------
        list of str
            List of private property names with name mangling removed.
        """
        # Trigger the single-pass scan if not yet populated
        _cache = self._cache
        if "private_properties" not in _cache:
            self._scanClass()
        return _cache["private_properties"]

    def getProperty(self, name: str) -> Any:
        """
        Retrieve the value of a property from the reflected class.

        Handles private property name mangling and validates that the requested
        attribute is a property object.

        Parameters
        ----------
        name : str
            Name of the property to retrieve.

        Returns
        -------
        Any
            The current value of the property.

        Raises
        ------
        ValueError
            If the property does not exist or is not accessible.
        """
        # Resolve private property name mangling for double underscore properties
        if name.startswith("__") and not name.endswith("__"):
            name = self._private_prefix + name

        if not hasattr(self._concrete, name):
            error_msg = (
                f"Property '{name}' does not exist in class '{self._class_name}'."
            )
            raise ValueError(error_msg)

        prop = getattr(self._concrete, name)
        if not isinstance(prop, property):
            error_msg = (
                f"'{name}' is not a property in class '{self._class_name}'."
            )
            raise TypeError(error_msg)

        # Invoke the property getter with the class as the receiver
        return prop.fget(self._concrete)

    def getPropertySignature(self, name: str) -> inspect.Signature:
        """
        Return the signature of a property's getter method.

        Parameters
        ----------
        name : str
            Name of the property to inspect.

        Returns
        -------
        inspect.Signature
            The signature object of the property's getter function.

        Raises
        ------
        ValueError
            If the property does not exist or is not accessible.
        """
        # Compute cache key once; reuse for both read and write operations
        cache_key = f"property_signature_{name}"
        _cache = self._cache
        if cache_key in _cache:
            return _cache[cache_key]

        # Resolve private property name mangling for double underscore properties
        if name.startswith("__") and not name.endswith("__"):
            name = self._private_prefix + name

        if not hasattr(self._concrete, name):
            error_msg = (
                f"Property '{name}' does not exist in class "
                f"'{self._class_name}'."
            )
            raise ValueError(error_msg)

        prop = getattr(self._concrete, name)
        if not isinstance(prop, property):
            error_msg = (
                f"'{name}' is not a property in class '{self._class_name}'."
            )
            raise TypeError(error_msg)

        # Cache and return the signature of the property getter
        sig = inspect.signature(prop.fget)
        _cache[cache_key] = sig
        return sig

    def getPropertyDocstring(self, name: str) -> str | None:
        """
        Retrieve the docstring of a property's getter method.

        Parameters
        ----------
        name : str
            Name of the property to inspect.

        Returns
        -------
        str or None
            The docstring of the property's getter function, or None if not defined.

        Raises
        ------
        ValueError
            If the property does not exist or is not accessible.
        """
        # Compute cache key once; reuse for both read and write operations
        cache_key = f"property_docstring_{name}"
        _cache = self._cache
        if cache_key in _cache:
            return _cache[cache_key]

        # Resolve private property name mangling
        if name.startswith("__") and not name.endswith("__"):
            name = self._private_prefix + name

        if not hasattr(self._concrete, name):
            error_msg = (
                f"Property '{name}' does not exist in class '{self._class_name}'."
            )
            raise ValueError(error_msg)

        prop = getattr(self._concrete, name)
        if not isinstance(prop, property):
            error_msg = (
                f"'{name}' is not a property in class '{self._class_name}'."
            )
            raise TypeError(error_msg)

        # Cache and return the docstring of the property getter
        docstring = prop.fget.__doc__ if prop.fget else None
        _cache[cache_key] = docstring
        return docstring

    def getConstructorSignature(self) -> inspect.Signature:
        """
        Return the signature of the class constructor.

        Returns
        -------
        inspect.Signature
            Signature object for the __init__ method, containing parameter
            information.
        """
        # Return cached constructor signature if available
        _cache = self._cache
        if "constructor_signature" in _cache:
            return _cache["constructor_signature"]
        sig = inspect.signature(self._concrete.__init__)
        _cache["constructor_signature"] = sig
        return sig

    def constructorSignature(self) -> Signature:
        """
        Analyze the constructor's dependencies.

        Analyzes the constructor parameters to identify resolved and unresolved
        dependencies using type annotations and default values.

        Returns
        -------
        Signature
            Structured representation of resolved and unresolved dependencies.
        """
        # Return cached dependency analysis if available
        _cache = self._cache
        if "constructor_signature_analysis" in _cache:
            return _cache["constructor_signature_analysis"]
        result = ReflectDependencies(self._concrete).constructorSignature()
        _cache["constructor_signature_analysis"] = result
        return result

    def methodSignature(self, method_name: str) -> Signature:
        """
        Analyze the dependencies of a specific method.

        Parameters
        ----------
        method_name : str
            Name of the method to analyze.

        Returns
        -------
        Signature
            Structured representation of resolved and unresolved dependencies.

        Raises
        ------
        AttributeError
            If the method does not exist in the class.
        """
        # Compute cache key once; reuse for both read and write operations
        cache_key = f"method_signature_analysis_{method_name}"
        _cache = self._cache
        if cache_key in _cache:
            return _cache[cache_key]

        # Validate method existence before analysis
        if not self.hasMethod(method_name):
            error_msg = (
                f"Method '{method_name}' does not exist on '{self._class_name}'."
            )
            raise AttributeError(error_msg)

        # Handle name mangling for private methods before delegation
        if method_name.startswith("__") and not method_name.endswith("__"):
            method_name = self._private_prefix + method_name

        # Analyze method dependencies and cache the result
        result = ReflectDependencies(self._concrete).methodSignature(method_name)
        _cache[cache_key] = result
        return result

    def clearCache(self) -> None:
        """
        Clear the internal memory cache.

        Removes all cached entries stored in the reflection instance. Subsequent
        method calls will recompute and cache results.

        Returns
        -------
        None
            This method does not return a value.
        """
        # Invalidate all cached reflection results
        self._cache.clear()
