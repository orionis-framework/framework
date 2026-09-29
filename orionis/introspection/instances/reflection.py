from __future__ import annotations
import inspect
import keyword
import types
from typing import TYPE_CHECKING, Any
from orionis.introspection.dependencies.reflection import ReflectDependencies
from orionis.introspection.instances.contracts.reflection import (
    IReflectionInstance,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from orionis.introspection.dependencies.entities.signature import (
        Signature,
    )

class ReflectionInstance(IReflectionInstance):

    # ruff: noqa : ANN401

    def __init__(self, instance: Any) -> None:
        """
        Initialize the ReflectionInstance with the given object instance.

        Parameters
        ----------
        instance : Any
            The object instance to reflect.

        Raises
        ------
        TypeError
            If the provided instance is not a valid object instance or is of a
            built-in/abstract base class.
        ValueError
            If the instance is from '__main__'.

        Returns
        -------
        None
            This method does not return a value.
        """
        # Ensure input is an object instance, not a class
        if isinstance(instance, type):
            error_msg = (
                "The provided instance must be an object instance, not a class."
            )
            raise TypeError(error_msg)

        # Retrieve the class once to avoid repeated attribute chain traversal
        cls = instance.__class__
        module: str = cls.__module__

        # Exclude built-in or abstract base class instances
        if module in {"builtins", "abc"}:
            error_msg = (
                "Cannot reflect on instances of built-in or abstract base classes."
            )
            raise TypeError(error_msg)

        # Prevent reflection on instances from '__main__'
        if module == "__main__":
            error_msg = "Cannot reflect on instances from '__main__'."
            raise ValueError(error_msg)

        # Store instance and pre-computed class metadata for fast repeated access
        self._instance: Any = instance
        self._cls: type = cls
        self._class_name: str = cls.__name__
        self._module_name: str = module
        # Python strips the leading underscores of the class name when it
        # mangles private members, so the prefix must be built the same way.
        self._private_prefix: str = f"_{self._class_name.lstrip('_')}"
        self._memory_cache: dict[str, Any] = {}

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
        # Return the value from the memory cache for the given key
        return self._memory_cache.get(key, None)

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
        # Set the value in the memory cache for the given key
        self._memory_cache[key] = value

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
        # Return True if the key is present in the memory cache
        return key in self._memory_cache

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
        # Remove the key from the cache if present
        self._memory_cache.pop(key, None)

    def _scanInstanceVars(self) -> None:
        """
        Categorize instance variables into visibility groups in a single traversal.

        Populates the cache with public, protected, private, dunder,
        and combined attribute dictionaries derived from the reflected instance.

        Returns
        -------
        None
            This method does not return a value.
        """
        private_prefix = self._private_prefix
        prefix_len = len(private_prefix)
        cache = self._memory_cache
        public: dict[str, Any] = {}
        protected: dict[str, Any] = {}
        private: dict[str, Any] = {}
        dunder: dict[str, Any] = {}

        # Classify each instance variable by its name prefix in a single pass
        for attr, value in vars(self._instance).items():
            if attr.startswith("__") and attr.endswith("__"):
                dunder[attr] = value
            elif attr.startswith(private_prefix):
                private[attr[prefix_len:]] = value
            elif attr.startswith("_"):
                protected[attr] = value
            else:
                public[attr] = value

        # Populate all attribute cache entries at once
        cache["public_attributes"] = public
        cache["protected_attributes"] = protected
        cache["private_attributes"] = private
        cache["dunder_attributes"] = dunder
        cache["attributes"] = {**public, **protected, **private, **dunder}

    def _scanPropertyEntries(
        self,
        cls: type,
    ) -> tuple[list[str], list[str], list[str], list[str]]:
        """
        Scan the class dict for property descriptors and sort by visibility.

        Parameters
        ----------
        cls : type
            The class whose __dict__ is traversed.

        Returns
        -------
        tuple[list[str], list[str], list[str], list[str]]
            Four lists: all properties, public, protected, and private.
        """
        private_prefix = self._private_prefix
        prefix_len = len(private_prefix)
        all_props: list[str] = []
        pub_props: list[str] = []
        prot_props: list[str] = []
        priv_props: list[str] = []

        # Walk the class __dict__ directly to exclude inherited properties
        for pname, pattr in cls.__dict__.items():
            if not isinstance(pattr, property):
                continue
            if pname.startswith(private_prefix):
                unmangled = pname[prefix_len:]
                all_props.append(unmangled)
                priv_props.append(unmangled)
            elif pname.startswith("__") and pname.endswith("__"):
                continue
            elif pname.startswith("_"):
                all_props.append(pname)
                prot_props.append(pname)
            else:
                all_props.append(pname)
                pub_props.append(pname)

        return all_props, pub_props, prot_props, priv_props

    def _classifyStaticEntry(
        self,
        name: str,
        attr: Any,
        acc: dict[str, list[str]],
    ) -> None:
        """
        Categorize a static method by visibility and append to the accumulator.

        Parameters
        ----------
        name : str
            The member name as returned by dir().
        attr : Any
            The staticmethod descriptor.
        acc : dict[str, list[str]]
            Shared accumulator dict keyed by category name.

        Returns
        -------
        None
            This method does not return a value.
        """
        private_prefix = self._private_prefix
        is_async = inspect.iscoroutinefunction(attr.__func__)

        # Append to the matching visibility bucket for static methods
        if name.startswith(private_prefix):
            unmangled = name[len(private_prefix):]
            acc["priv_sta_m"].append(unmangled)
            if is_async:
                acc["priv_sta_m_async"].append(unmangled)
            else:
                acc["priv_sta_m_sync"].append(unmangled)
        elif name.startswith("_"):
            acc["prot_sta_m"].append(name)
            if is_async:
                acc["prot_sta_m_async"].append(name)
            else:
                acc["prot_sta_m_sync"].append(name)
        else:
            acc["pub_sta_m"].append(name)
            (acc["pub_sta_m_async"] if is_async else acc["pub_sta_m_sync"]).append(name)

    def _classifyClassEntry(
        self,
        name: str,
        attr: Any,
        acc: dict[str, list[str]],
    ) -> None:
        """
        Categorize a class method by visibility and append to the accumulator.

        Parameters
        ----------
        name : str
            The member name as returned by dir().
        attr : Any
            The classmethod descriptor.
        acc : dict[str, list[str]]
            Shared accumulator dict keyed by category name.

        Returns
        -------
        None
            This method does not return a value.
        """
        private_prefix = self._private_prefix
        is_async = inspect.iscoroutinefunction(attr.__func__)

        # Append to the matching visibility bucket for class methods
        if name.startswith(private_prefix):
            unmangled = name[len(private_prefix):]
            acc["priv_cls_m"].append(unmangled)
            if is_async:
                acc["priv_cls_m_async"].append(unmangled)
            else:
                acc["priv_cls_m_sync"].append(unmangled)
        elif name.startswith("_"):
            acc["prot_cls_m"].append(name)
            if is_async:
                acc["prot_cls_m_async"].append(name)
            else:
                acc["prot_cls_m_sync"].append(name)
        else:
            acc["pub_cls_m"].append(name)
            (acc["pub_cls_m_async"] if is_async else acc["pub_cls_m_sync"]).append(name)

    def _classifyFunctionEntry(
        self,
        name: str,
        attr: Any,
        acc: dict[str, list[str]],
    ) -> None:
        """
        Categorize an instance method by visibility and append to the accumulator.

        Parameters
        ----------
        name : str
            The member name as returned by dir().
        attr : Any
            The function object.
        acc : dict[str, list[str]]
            Shared accumulator dict keyed by category name.

        Returns
        -------
        None
            This method does not return a value.
        """
        private_prefix = self._private_prefix
        is_async = inspect.iscoroutinefunction(attr)

        # Append to the matching visibility bucket for instance methods
        if name.startswith(private_prefix):
            unmangled = name[len(private_prefix):]
            acc["priv_m"].append(unmangled)
            (acc["priv_m_async"] if is_async else acc["priv_m_sync"]).append(unmangled)
        elif name.startswith("_"):
            acc["prot_m"].append(name)
            (acc["prot_m_async"] if is_async else acc["prot_m_sync"]).append(name)
        else:
            acc["pub_m"].append(name)
            (acc["pub_m_async"] if is_async else acc["pub_m_sync"]).append(name)

    def _scanClassMembers(self) -> None:  # noqa: PLR0915
        """
        Discover and categorize all class members in a single traversal.

        Walks the class dict for properties and dir() for methods, building all
        method and property category lists and populating the cache in one pass.

        Returns
        -------
        None
            This method does not return a value.
        """
        cls = self._cls
        cache = self._memory_cache

        # Initialize accumulators for each method visibility and type category
        acc: dict[str, list[str]] = {
            "pub_m": [], "pub_m_sync": [], "pub_m_async": [],
            "prot_m": [], "prot_m_sync": [], "prot_m_async": [],
            "priv_m": [], "priv_m_sync": [], "priv_m_async": [],
            "pub_cls_m": [], "pub_cls_m_sync": [], "pub_cls_m_async": [],
            "prot_cls_m": [], "prot_cls_m_sync": [], "prot_cls_m_async": [],
            "priv_cls_m": [], "priv_cls_m_sync": [], "priv_cls_m_async": [],
            "pub_sta_m": [], "pub_sta_m_sync": [], "pub_sta_m_async": [],
            "prot_sta_m": [], "prot_sta_m_sync": [], "prot_sta_m_async": [],
            "priv_sta_m": [], "priv_sta_m_sync": [], "priv_sta_m_async": [],
        }
        dunder_m: list[str] = []

        # Scan class dict for properties and categorize by visibility
        all_props, pub_props, prot_props, priv_props = self._scanPropertyEntries(cls)

        # Walk all accessible names (including inherited) to categorize methods
        for name in dir(cls):
            attr = inspect.getattr_static(cls, name)
            if name.startswith("__") and name.endswith("__"):
                dunder_m.append(name)
                continue
            if isinstance(attr, staticmethod):
                self._classifyStaticEntry(name, attr, acc)
            elif isinstance(attr, classmethod):
                self._classifyClassEntry(name, attr, acc)
            elif isinstance(attr, types.FunctionType):
                self._classifyFunctionEntry(name, attr, acc)

        # Build the combined method list and fast-lookup set
        all_methods: list[str] = [
            *acc["pub_m"], *acc["prot_m"], *acc["priv_m"],
            *acc["pub_cls_m"], *acc["prot_cls_m"], *acc["priv_cls_m"],
            *acc["pub_sta_m"], *acc["prot_sta_m"], *acc["priv_sta_m"],
        ]

        # Populate all method and property cache entries in a single operation
        cache["public_methods"] = acc["pub_m"]
        cache["public_sync_methods"] = acc["pub_m_sync"]
        cache["public_async_methods"] = acc["pub_m_async"]
        cache["protected_methods"] = acc["prot_m"]
        cache["protected_sync_methods"] = acc["prot_m_sync"]
        cache["protected_async_methods"] = acc["prot_m_async"]
        cache["private_methods"] = acc["priv_m"]
        cache["private_sync_methods"] = acc["priv_m_sync"]
        cache["private_async_methods"] = acc["priv_m_async"]
        cache["dunder_methods"] = dunder_m
        cache["public_class_methods"] = acc["pub_cls_m"]
        cache["public_class_sync_methods"] = acc["pub_cls_m_sync"]
        cache["public_class_async_methods"] = acc["pub_cls_m_async"]
        cache["protected_class_methods"] = acc["prot_cls_m"]
        cache["protected_class_sync_methods"] = acc["prot_cls_m_sync"]
        cache["protected_class_async_methods"] = acc["prot_cls_m_async"]
        cache["private_class_methods"] = acc["priv_cls_m"]
        cache["private_class_sync_methods"] = acc["priv_cls_m_sync"]
        cache["private_class_async_methods"] = acc["priv_cls_m_async"]
        cache["public_static_methods"] = acc["pub_sta_m"]
        cache["public_static_sync_methods"] = acc["pub_sta_m_sync"]
        cache["public_static_async_methods"] = acc["pub_sta_m_async"]
        cache["protected_static_methods"] = acc["prot_sta_m"]
        cache["protected_static_sync_methods"] = acc["prot_sta_m_sync"]
        cache["protected_static_async_methods"] = acc["prot_sta_m_async"]
        cache["private_static_methods"] = acc["priv_sta_m"]
        cache["private_static_sync_methods"] = acc["priv_sta_m_sync"]
        cache["private_static_async_methods"] = acc["priv_sta_m_async"]
        cache["properties"] = all_props
        cache["public_properties"] = pub_props
        cache["protected_properties"] = prot_props
        cache["private_properties"] = priv_props
        cache["methods"] = all_methods
        cache["_methods_set"] = frozenset(all_methods)

    def getInstance(self) -> Any:
        """
        Return the reflected object instance.

        Returns
        -------
        Any
            The object instance being reflected upon.
        """
        return self._instance

    def getClass(self) -> type:
        """
        Return the class of the instance.

        Returns
        -------
        type
            The class object of the instance.
        """
        # Return the pre-computed class reference
        return self._cls

    def getClassName(self) -> str:
        """
        Return the name of the instance's class.

        Returns
        -------
        str
            The name of the class.
        """
        # Return the pre-computed class name string
        return self._class_name

    def getModuleName(self) -> str:
        """
        Return the name of the module where the class is defined.

        Returns
        -------
        str
            The module name where the class is defined.
        """
        # Return the pre-computed module name string
        return self._module_name

    def getModuleWithClassName(self) -> str:
        """
        Return the module and class name as a single string.

        Returns
        -------
        str
            The module name and class name in the format 'module.ClassName'.
        """
        # Build the qualified name from pre-computed metadata fields
        return f"{self._module_name}.{self._class_name}"

    def getDocstring(self) -> str | None:
        """
        Return the docstring of the instance's class.

        Returns
        -------
        str or None
            The docstring of the class, or None if not available.
        """
        # Access the docstring directly from the pre-computed class reference
        return self._cls.__doc__

    def getBaseClasses(self) -> tuple[type, ...]:
        """
        Return the base classes of the instance's class.

        Returns
        -------
        tuple of type
            Tuple containing the base classes of the class.
        """
        # Return the direct base classes from the pre-computed class reference
        return self._cls.__bases__

    def getSourceCode(self, method: str | None = None) -> str | None:
        """
        Retrieve the source code for the class or a specific method.

        Parameters
        ----------
        method : str or None, optional
            Name of the method to retrieve source code for. If None, retrieves
            the source code of the class.

        Returns
        -------
        str or None
            The source code as a string if available, otherwise None.

        Notes
        -----
        Handles name mangling for private methods. Returns None if the source
        code cannot be retrieved (e.g., for built-in or dynamically generated
        objects).
        """
        try:
            cache = self._memory_cache

            # Return cached class source code if available
            if not method:
                if "source_code" in cache:
                    return cache["source_code"]
                cache["source_code"] = inspect.getsource(self._cls)
                return cache["source_code"]

            # Return cached method source code if available (pre-mangle key)
            pre_key = f"{method}_source_code"
            if pre_key in cache:
                return cache[pre_key]

            # Verify the method exists before retrieving source; hasMethod()
            # indexes the demangled names produced by the member scan
            if not self.hasMethod(method):
                return None

            # Apply name mangling for private method attribute lookup
            resolved = method
            if method.startswith("__") and not method.endswith("__"):
                resolved = f"{self._private_prefix}{method}"

            # Retrieve and cache the source code of the specified method
            cache[pre_key] = inspect.getsource(getattr(self._cls, resolved))
            return cache[pre_key]

        except (TypeError, OSError):
            # Return None if the source code cannot be retrieved
            return None

    def getFile(self) -> str | None:
        """
        Return the file path where the class is defined.

        Returns
        -------
        str or None
            The file path of the class definition, or None if unavailable.
        """
        cache = self._memory_cache

        # Return cached file path if available
        if "file" in cache:
            return cache["file"]
        try:
            # Retrieve and cache the file path of the class definition
            cache["file"] = inspect.getfile(self._cls)
            return cache["file"]
        except (TypeError, OSError):
            # Return None if the file path cannot be determined
            return None

    def getAnnotations(self) -> dict[str, type]:
        """
        Retrieve type annotations of the class.

        Returns
        -------
        dict[str, type]
            Dictionary mapping attribute names to their type annotations.
        """
        cache = self._memory_cache

        # Return cached annotations if available
        if "annotations" in cache:
            return cache["annotations"]

        # Collect and unmangle class annotations using the pre-computed prefix
        private_prefix = self._private_prefix
        prefix_len = len(private_prefix)
        annotations: dict[str, type] = {}
        class_annotations = getattr(self._cls, "__annotations__", {})

        # Unmangle private annotation names and build the annotations dict
        for k, v in class_annotations.items():
            if k.startswith(private_prefix):
                annotations[k[prefix_len:]] = v
            else:
                annotations[k] = v

        cache["annotations"] = annotations
        return annotations

    def hasAttribute(self, name: str) -> bool:
        """
        Check if the instance has a specific attribute.

        Parameters
        ----------
        name : str
            Attribute name to check.

        Returns
        -------
        bool
            True if the attribute exists, False otherwise.
        """
        # Check attribute existence in both instance variables and accessible attrs
        return name in self.getAttributes() or hasattr(self._instance, name)

    def getAttribute(self, name: str, default: Any = None) -> Any:
        """
        Retrieve the value of an attribute by name from the instance.

        Parameters
        ----------
        name : str
            Name of the attribute to retrieve.
        default : Any, optional
            Value to return if the attribute does not exist. Defaults to None.

        Returns
        -------
        Any
            Value of the specified attribute if it exists, otherwise the provided
            `default` value.

        Raises
        ------
        AttributeError
            If the attribute does not exist and no default value is provided.

        Notes
        -----
        This method first checks the instance's attributes dictionary for the
        given name. If not found, it attempts to retrieve the attribute directly
        from the instance using `getattr`. If the attribute is still not found,
        the `default` value is returned.
        """
        # Retrieve all attributes and fall back to getattr for computed/property attrs
        return self.getAttributes().get(name, getattr(self._instance, name, default))

    def setAttribute(self, name: str, value: Any) -> bool:
        """
        Set the value of an attribute on the instance.

        Parameters
        ----------
        name : str
            Name of the attribute to set.
        value : Any
            Value to assign to the attribute.

        Returns
        -------
        bool
            True if the attribute was set successfully.

        Raises
        ------
        AttributeError
            If the attribute name is invalid, is a keyword, or the value is callable.
        """
        # Validate attribute name: must be a valid identifier and not a keyword
        if (
            not isinstance(name, str)
            or not name.isidentifier()
            or keyword.iskeyword(name)
        ):
            error_msg = (
                f"Invalid method name '{name}'. Must be a valid Python identifier "
                "and not a keyword."
            )
            raise AttributeError(error_msg)

        # Prevent setting callable values as attributes
        if callable(value):
            error_msg = (
                f"Cannot set attribute '{name}' to a callable. Use setMethod instead."
            )
            raise TypeError(error_msg)

        # Apply name mangling for private attribute assignment
        if name.startswith("__") and not name.endswith("__"):
            name = f"{self._private_prefix}{name}"

        # Set the attribute value on the instance
        setattr(self._instance, name, value)

        # Invalidate the entire attribute cache after mutation
        self._memory_cache.clear()

        # Return True to indicate the attribute was set successfully
        return True

    def removeAttribute(self, name: str) -> bool:
        """
        Remove an attribute from the instance.

        Parameters
        ----------
        name : str
            Name of the attribute to remove.

        Returns
        -------
        bool
            True if the attribute was removed successfully.

        Raises
        ------
        AttributeError
            If the attribute does not exist or is read-only.

        Notes
        -----
        Clears the memory cache after removal.
        """
        # Check if the attribute exists before attempting removal
        if self.getAttribute(name) is None:
            error_msg = (
                f"'{self._class_name}' object has no attribute '{name}'."
            )
            raise AttributeError(error_msg)

        # Apply name mangling for private attribute removal
        if name.startswith("__") and not name.endswith("__"):
            name = f"{self._private_prefix}{name}"

        # Remove the attribute from the instance
        delattr(self._instance, name)

        # Invalidate the entire attribute cache after mutation
        self._memory_cache.clear()

        # Return True to indicate the attribute was removed successfully
        return True

    def getAttributeDocstring(self, name: str) -> str | None:
        """
        Retrieve the docstring of a specific attribute.

        Parameters
        ----------
        name : str
            Name of the attribute.

        Returns
        -------
        str or None
            The docstring of the attribute, or None if not available.

        Raises
        ------
        AttributeError
            If the attribute does not exist on the instance.
        """
        # Apply name mangling for private attribute lookup
        if name.startswith("__") and not name.endswith("__"):
            name = f"{self._private_prefix}{name}"

        # Verify the attribute exists on the instance
        if not self.hasAttribute(name):
            error_msg = (
                f"'{self._class_name}' object has no attribute '{name}'."
            )
            raise AttributeError(error_msg)

        # Return the docstring of the attribute value if one exists
        attr_value = getattr(self._instance, name)
        return attr_value.__doc__ if hasattr(attr_value, "__doc__") else None

    def getAttributes(self) -> dict[str, Any]:
        """
        Aggregate all attributes of the instance.

        Combines public, protected, private, and dunder attributes into a single
        dictionary. Private attribute names are unmangled. The result is cached
        for performance.

        Returns
        -------
        dict[str, Any]
            Dictionary mapping attribute names to their values for all visibility
            levels.
        """
        cache = self._memory_cache

        # Return cached combined attributes if available
        if "attributes" in cache:
            return cache["attributes"]

        # Trigger a single-pass scan to populate all attribute categories
        self._scanInstanceVars()
        return cache["attributes"]

    def getPublicAttributes(self) -> dict[str, Any]:
        """
        Return all public attributes of the instance.

        Parameters
        ----------
        self : ReflectionInstance

        Returns
        -------
        dict[str, Any]
            Dictionary mapping public attribute names to their values. Excludes
            dunder, protected, and private attributes.
        """
        cache = self._memory_cache

        # Trigger scan if public attributes have not been cached yet
        if "public_attributes" not in cache:
            self._scanInstanceVars()
        return cache["public_attributes"]

    def getProtectedAttributes(self) -> dict[str, Any]:
        """
        Return all protected attributes of the instance.

        Parameters
        ----------
        self : ReflectionInstance

        Returns
        -------
        dict[str, Any]
            Dictionary containing protected attribute names and their values.
            Protected attributes start with a single underscore, are not dunder,
            and are not private (do not start with the class name).
        """
        cache = self._memory_cache

        # Trigger scan if protected attributes have not been cached yet
        if "protected_attributes" not in cache:
            self._scanInstanceVars()
        return cache["protected_attributes"]

    def getPrivateAttributes(self) -> dict[str, Any]:
        """
        Retrieve all private attributes of the instance.

        Parameters
        ----------
        self : ReflectionInstance

        Returns
        -------
        dict[str, Any]
            Dictionary mapping unmangled private attribute names to their values.
        """
        cache = self._memory_cache

        # Trigger scan if private attributes have not been cached yet
        if "private_attributes" not in cache:
            self._scanInstanceVars()
        return cache["private_attributes"]

    def getDunderAttributes(self) -> dict[str, Any]:
        """
        Retrieve all dunder (double underscore) attributes of the instance.

        Parameters
        ----------
        self : ReflectionInstance

        Returns
        -------
        dict[str, Any]
            Dictionary mapping dunder attribute names to their values.
        """
        cache = self._memory_cache

        # Trigger scan if dunder attributes have not been cached yet
        if "dunder_attributes" not in cache:
            self._scanInstanceVars()
        return cache["dunder_attributes"]

    def getMagicAttributes(self) -> dict[str, Any]:
        """
        Return all magic attributes of the instance.

        Returns
        -------
        dict[str, Any]
            Dictionary mapping magic attribute names to their values.
        """
        # Magic attributes are equivalent to dunder attributes in Python
        return self.getDunderAttributes()

    def hasMethod(self, name: str) -> bool:
        """
        Determine if the instance has a specific method.

        Parameters
        ----------
        name : str
            Name of the method to check.

        Returns
        -------
        bool
            True if the method exists, otherwise False.

        Notes
        -----
        Checks the presence of the method in the aggregated method list.
        """
        cache = self._memory_cache

        # Trigger scan to build the frozenset if it has not been cached yet
        if "_methods_set" not in cache:
            self._scanClassMembers()

        # Use the frozenset for O(1) membership testing
        return name in cache["_methods_set"]

    def setMethod(self, name: str, method: Callable) -> bool:
        """
        Set a callable attribute as a method.

        Parameters
        ----------
        name : str
            Name of the method to set.
        method : Callable
            Callable object to assign as the method.

        Returns
        -------
        bool
            True if the method was set successfully.

        Raises
        ------
        AttributeError
            If the name is not a valid identifier, is a keyword, or the method
            is not callable.
        """
        # Validate method name: must be a valid identifier and not a keyword
        if (
            not isinstance(name, str)
            or not name.isidentifier()
            or keyword.iskeyword(name)
        ):
            error_msg = (
                f"Invalid method name '{name}'. Must be a valid Python identifier "
                "and not a keyword."
            )
            raise AttributeError(error_msg)

        # Ensure the method is callable
        if not callable(method):
            error_msg = (
                f"Cannot set attribute '{name}' to a non-callable value."
            )
            raise TypeError(error_msg)

        # Apply name mangling for private method assignment
        if name.startswith("__") and not name.endswith("__"):
            name = f"{self._private_prefix}{name}"

        # Assign the callable to the instance
        setattr(self._instance, name, method)

        # Invalidate the entire cache after mutating the instance
        self._memory_cache.clear()
        return True

    def removeMethod(self, name: str) -> None:
        """
        Remove a method from the instance.

        Parameters
        ----------
        name : str
            Name of the method to remove.

        Returns
        -------
        None
            This method does not return a value.

        Raises
        ------
        AttributeError
            If the method does not exist or is not callable.
        """
        # Verify the method exists before attempting removal
        if not self.hasMethod(name):
            error_msg = (
                f"Method '{name}' does not exist on '{self._class_name}'."
            )
            raise AttributeError(error_msg)

        # Remove the method from the class definition
        delattr(self._instance.__class__, name)

        # Invalidate the entire cache after mutating the class
        self._memory_cache.clear()

    def getMethodSignature(self, name: str) -> inspect.Signature:
        """
        Retrieve the signature of a method.

        Parameters
        ----------
        name : str
            Name of the method.

        Returns
        -------
        inspect.Signature
            Signature object representing the method's parameters and return type.

        Raises
        ------
        AttributeError
            If the method does not exist or is not callable.
        """
        cache = self._memory_cache

        # Return cached signature if available
        cache_key = f"{name}_method_signature"
        if cache_key in cache:
            return cache[cache_key]

        # Apply name mangling for private method lookup
        lookup = name
        if name.startswith("__") and not name.endswith("__"):
            lookup = f"{self._private_prefix}{name}"

        # Retrieve the method and inspect its signature
        resolved = getattr(self._cls, lookup, None)
        if callable(resolved):
            cache[cache_key] = inspect.signature(resolved)
            return cache[cache_key]

        error_msg = (
            f"Method '{name}' is not callable on '{self._class_name}'."
        )
        raise AttributeError(error_msg)

    def getMethodDocstring(self, name: str) -> str | None:
        """
        Retrieve the docstring of a method.

        Parameters
        ----------
        name : str
            Name of the method.

        Returns
        -------
        str | None
            The docstring of the method, or None if not available.

        Raises
        ------
        AttributeError
            If the method does not exist on the class.
        """
        cache = self._memory_cache

        # Return cached docstring if available
        cache_key = f"{name}_docstring"
        if cache_key in cache:
            return cache[cache_key]

        # Apply name mangling for private method lookup
        lookup = name
        if name.startswith("__") and not name.endswith("__"):
            lookup = f"{self._private_prefix}{name}"

        # Retrieve the method and cache its docstring
        resolved = getattr(self._cls, lookup, None)
        if callable(resolved):
            cache[cache_key] = resolved.__doc__
            return cache[cache_key]

        error_msg = (
            f"Method '{name}' does not exist on '{self._class_name}'."
        )
        raise AttributeError(error_msg)

    def getMethods(self) -> list[str]:
        """
        Retrieve all method names associated with the instance.

        Aggregates method names from public, protected, private, class, and static
        categories by calling their respective getter methods. The result is cached
        for performance.

        Returns
        -------
        list of str
            List of all method names (instance, class, static) defined on the
            instance's class, including public, protected, and private methods.
        """
        cache = self._memory_cache

        # Trigger scan to populate all method lists if not yet cached
        if "methods" not in cache:
            self._scanClassMembers()
        return cache["methods"]

    def getPublicMethods(self) -> list[str]:
        """
        Return all public method names of the instance.

        Parameters
        ----------
        self : ReflectionInstance
            The ReflectionInstance object.

        Returns
        -------
        list of str
            List of public method names. Public methods are not static, class,
            private, protected, or magic methods.
        """
        cache = self._memory_cache

        # Trigger scan to populate method lists if not yet cached
        if "public_methods" not in cache:
            self._scanClassMembers()
        return cache["public_methods"]

    def getPublicSyncMethods(self) -> list[str]:
        """
        Return all public synchronous method names of the instance.

        Returns
        -------
        list of str
            List of public synchronous method names.
        """
        cache = self._memory_cache

        # Trigger scan to populate method lists if not yet cached
        if "public_sync_methods" not in cache:
            self._scanClassMembers()
        return cache["public_sync_methods"]

    def getPublicAsyncMethods(self) -> list[str]:
        """
        Return all public asynchronous method names of the instance.

        Parameters
        ----------
        self : ReflectionInstance
            The ReflectionInstance object.

        Returns
        -------
        list of str
            List of public asynchronous method names.
        """
        cache = self._memory_cache

        # Trigger scan to populate method lists if not yet cached
        if "public_async_methods" not in cache:
            self._scanClassMembers()
        return cache["public_async_methods"]

    def getProtectedMethods(self) -> list[str]:
        """
        Return all protected method names of the instance.

        Parameters
        ----------
        self : ReflectionInstance
            The ReflectionInstance object.

        Returns
        -------
        list of str
            List of protected method names. Protected methods start with a single
            underscore, are not private (do not start with the class name), and
            are not dunder methods.
        """
        cache = self._memory_cache

        # Trigger scan to populate method lists if not yet cached
        if "protected_methods" not in cache:
            self._scanClassMembers()
        return cache["protected_methods"]

    def getProtectedSyncMethods(self) -> list[str]:
        """
        Return all protected synchronous method names of the instance.

        Parameters
        ----------
        self : ReflectionInstance
            The ReflectionInstance object.

        Returns
        -------
        list of str
            List of protected synchronous method names.
        """
        cache = self._memory_cache

        # Trigger scan to populate method lists if not yet cached
        if "protected_sync_methods" not in cache:
            self._scanClassMembers()
        return cache["protected_sync_methods"]

    def getProtectedAsyncMethods(self) -> list[str]:
        """
        Retrieve all protected asynchronous method names of the instance.

        Parameters
        ----------
        self : ReflectionInstance
            The ReflectionInstance object.

        Returns
        -------
        list of str
            List of protected asynchronous method names.

        Notes
        -----
        Protected asynchronous methods start with a single underscore, are not private,
        and are coroutine functions.
        """
        cache = self._memory_cache

        # Trigger scan to populate method lists if not yet cached
        if "protected_async_methods" not in cache:
            self._scanClassMembers()
        return cache["protected_async_methods"]

    def getPrivateMethods(self) -> list[str]:
        """
        Return all private method names of the instance.

        Private methods are those whose names start with the class name prefix
        (name-mangled), but do not start with double underscores.

        Returns
        -------
        list of str
            List of private method names, unmangled (without class name prefix).
        """
        cache = self._memory_cache

        # Trigger scan to populate method lists if not yet cached
        if "private_methods" not in cache:
            self._scanClassMembers()
        return cache["private_methods"]

    def getPrivateSyncMethods(self) -> list[str]:
        """
        Retrieve all private synchronous method names of the instance.

        Returns
        -------
        list of str
            List of private synchronous method names (unmangled).
        """
        cache = self._memory_cache

        # Trigger scan to populate method lists if not yet cached
        if "private_sync_methods" not in cache:
            self._scanClassMembers()
        return cache["private_sync_methods"]

    def getPrivateAsyncMethods(self) -> list[str]:
        """
        Retrieve all private asynchronous method names of the instance.

        Returns
        -------
        list of str
            List of private asynchronous method names (unmangled).
        """
        cache = self._memory_cache

        # Trigger scan to populate method lists if not yet cached
        if "private_async_methods" not in cache:
            self._scanClassMembers()
        return cache["private_async_methods"]

    def getPublicClassMethods(self) -> list[str]:
        """
        Return all public class method names of the instance.

        Returns
        -------
        list of str
            List of public class method names.
        """
        cache = self._memory_cache

        # Trigger scan to populate method lists if not yet cached
        if "public_class_methods" not in cache:
            self._scanClassMembers()
        return cache["public_class_methods"]

    def getPublicClassSyncMethods(self) -> list[str]:
        """
        Return all public synchronous class method names of the instance.

        Returns
        -------
        list of str
            List of public synchronous class method names.
        """
        cache = self._memory_cache

        # Trigger scan to populate method lists if not yet cached
        if "public_class_sync_methods" not in cache:
            self._scanClassMembers()
        return cache["public_class_sync_methods"]

    def getPublicClassAsyncMethods(self) -> list[str]:
        """
        Return all public asynchronous class method names of the instance.

        Returns
        -------
        list of str
            List of public asynchronous class method names.
        """
        cache = self._memory_cache

        # Trigger scan to populate method lists if not yet cached
        if "public_class_async_methods" not in cache:
            self._scanClassMembers()
        return cache["public_class_async_methods"]

    def getProtectedClassMethods(self) -> list[str]:
        """
        Return all protected class method names of the instance.

        Returns
        -------
        list of str
            List of protected class method names.
        """
        cache = self._memory_cache

        # Trigger scan to populate method lists if not yet cached
        if "protected_class_methods" not in cache:
            self._scanClassMembers()
        return cache["protected_class_methods"]

    def getProtectedClassSyncMethods(self) -> list[str]:
        """
        Return all protected synchronous class method names of the instance.

        Parameters
        ----------
        self : ReflectionInstance
            The ReflectionInstance object.

        Returns
        -------
        list of str
            List of protected synchronous class method names.
        """
        cache = self._memory_cache

        # Trigger scan to populate method lists if not yet cached
        if "protected_class_sync_methods" not in cache:
            self._scanClassMembers()
        return cache["protected_class_sync_methods"]

    def getProtectedClassAsyncMethods(self) -> list[str]:
        """
        Retrieve all protected asynchronous class method names of the instance.

        Returns
        -------
        list of str
            List of protected asynchronous class method names.
        """
        cache = self._memory_cache

        # Trigger scan to populate method lists if not yet cached
        if "protected_class_async_methods" not in cache:
            self._scanClassMembers()
        return cache["protected_class_async_methods"]

    def getPrivateClassMethods(self) -> list[str]:
        """
        Return all private class method names of the instance.

        Returns
        -------
        list of str
            List of private class method names (unmangled).
        """
        cache = self._memory_cache

        # Trigger scan to populate method lists if not yet cached
        if "private_class_methods" not in cache:
            self._scanClassMembers()
        return cache["private_class_methods"]

    def getPrivateClassSyncMethods(self) -> list[str]:
        """
        Retrieve all private synchronous class method names of the instance.

        Returns
        -------
        list of str
            List of private synchronous class method names.
        """
        cache = self._memory_cache

        # Trigger scan to populate method lists if not yet cached
        if "private_class_sync_methods" not in cache:
            self._scanClassMembers()
        return cache["private_class_sync_methods"]

    def getPrivateClassAsyncMethods(self) -> list[str]:
        """
        Retrieve all private asynchronous class method names of the instance.

        Parameters
        ----------
        self : ReflectionInstance
            The ReflectionInstance object.

        Returns
        -------
        list of str
            List of private asynchronous class method names.
        """
        cache = self._memory_cache

        # Trigger scan to populate method lists if not yet cached
        if "private_class_async_methods" not in cache:
            self._scanClassMembers()
        return cache["private_class_async_methods"]

    def getPublicStaticMethods(self) -> list[str]:
        """
        Return the names of all public static methods of the instance's class.

        Returns
        -------
        list of str
            List of public static method names defined on the class.
        """
        cache = self._memory_cache

        # Trigger scan to populate method lists if not yet cached
        if "public_static_methods" not in cache:
            self._scanClassMembers()
        return cache["public_static_methods"]

    def getPublicStaticSyncMethods(self) -> list[str]:
        """
        Return all public synchronous static method names of the instance.

        Returns
        -------
        list of str
            List of public synchronous static method names defined on the class.
        """
        cache = self._memory_cache

        # Trigger scan to populate method lists if not yet cached
        if "public_static_sync_methods" not in cache:
            self._scanClassMembers()
        return cache["public_static_sync_methods"]

    def getPublicStaticAsyncMethods(self) -> list[str]:
        """
        Retrieve all public asynchronous static method names of the instance.

        Returns
        -------
        list of str
            List of public asynchronous static method names defined on the class.
        """
        cache = self._memory_cache

        # Trigger scan to populate method lists if not yet cached
        if "public_static_async_methods" not in cache:
            self._scanClassMembers()
        return cache["public_static_async_methods"]

    def getProtectedStaticMethods(self) -> list[str]:
        """
        Return all protected static method names of the instance.

        Returns
        -------
        list of str
            List of protected static method names defined on the class.
        """
        cache = self._memory_cache

        # Trigger scan to populate method lists if not yet cached
        if "protected_static_methods" not in cache:
            self._scanClassMembers()
        return cache["protected_static_methods"]

    def getProtectedStaticSyncMethods(self) -> list[str]:
        """
        Retrieve all protected synchronous static method names.

        Returns
        -------
        list of str
            List of protected synchronous static method names defined on the class.
        """
        cache = self._memory_cache

        # Trigger scan to populate method lists if not yet cached
        if "protected_static_sync_methods" not in cache:
            self._scanClassMembers()
        return cache["protected_static_sync_methods"]

    def getProtectedStaticAsyncMethods(self) -> list[str]:
        """
        Retrieve all protected asynchronous static method names.

        Parameters
        ----------
        None

        Returns
        -------
        list of str
            List of protected asynchronous static method names defined on the class.
        """
        cache = self._memory_cache

        # Trigger scan to populate method lists if not yet cached
        if "protected_static_async_methods" not in cache:
            self._scanClassMembers()
        return cache["protected_static_async_methods"]

    def getPrivateStaticMethods(self) -> list[str]:
        """
        Return all private static method names of the instance.

        Returns
        -------
        list of str
            List of private static method names defined on the class.
        """
        cache = self._memory_cache

        # Trigger scan to populate method lists if not yet cached
        if "private_static_methods" not in cache:
            self._scanClassMembers()
        return cache["private_static_methods"]

    def getPrivateStaticSyncMethods(self) -> list[str]:
        """
        Retrieve all private synchronous static method names of the instance.

        Returns
        -------
        list of str
            List of private synchronous static method names defined on the class.
        """
        cache = self._memory_cache

        # Trigger scan to populate method lists if not yet cached
        if "private_static_sync_methods" not in cache:
            self._scanClassMembers()
        return cache["private_static_sync_methods"]

    def getPrivateStaticAsyncMethods(self) -> list[str]:
        """
        Retrieve all private asynchronous static method names of the instance.

        Returns
        -------
        list of str
            List of private asynchronous static method names defined on the class.
        """
        cache = self._memory_cache

        # Trigger scan to populate method lists if not yet cached
        if "private_static_async_methods" not in cache:
            self._scanClassMembers()
        return cache["private_static_async_methods"]

    def getDunderMethods(self) -> list[str]:
        """
        Return all dunder (double underscore) method names of the instance.

        Returns
        -------
        list of str
            List of dunder method names defined on the instance.
        """
        cache = self._memory_cache

        # Trigger scan to populate dunder method list if not yet cached
        if "dunder_methods" not in cache:
            self._scanClassMembers()
        return cache["dunder_methods"]

    def getMagicMethods(self) -> list[str]:
        """
        Return all magic method names of the instance.

        Returns
        -------
        list of str
            List of magic (dunder) method names defined on the instance.
        """
        # Magic methods are equivalent to dunder methods in Python
        return self.getDunderMethods()

    def getProperties(self) -> list[str]:
        """
        Return all property names of the instance.

        Returns
        -------
        list of str
            List of property names defined as properties on the class.
        """
        cache = self._memory_cache

        # Trigger scan to populate property lists if not yet cached
        if "properties" not in cache:
            self._scanClassMembers()
        return cache["properties"]

    def getPublicProperties(self) -> list:
        """
        Return all public properties of the instance.

        Returns
        -------
        list
            List of public property names.
        """
        cache = self._memory_cache

        # Trigger scan to populate property lists if not yet cached
        if "public_properties" not in cache:
            self._scanClassMembers()
        return cache["public_properties"]

    def getProtectedProperties(self) -> list:
        """
        Retrieve all protected properties of the instance.

        Returns
        -------
        list
            List of protected property names (unmangled).
        """
        cache = self._memory_cache

        # Trigger scan to populate property lists if not yet cached
        if "protected_properties" not in cache:
            self._scanClassMembers()
        return cache["protected_properties"]

    def getPrivateProperties(self) -> list:
        """
        Retrieve all private properties of the instance.

        Returns
        -------
        list
            List of private property names (unmangled).
        """
        cache = self._memory_cache

        # Trigger scan to populate property lists if not yet cached
        if "private_properties" not in cache:
            self._scanClassMembers()
        return cache["private_properties"]

    def getProperty(self, name: str) -> Any:
        """
        Retrieve the value of a property from the instance.

        Parameters
        ----------
        name : str
            Name of the property to retrieve.

        Returns
        -------
        Any
            Value of the specified property.

        Raises
        ------
        AttributeError
            If the property does not exist or is not accessible.
        """
        # Verify the property exists before accessing it
        if name in self.getProperties():
            # Apply name mangling for private property access
            if name.startswith("__") and not name.endswith("__"):
                name = f"{self._private_prefix}{name}"
            return getattr(self._instance, name, None)

        error_msg = (
            f"Property '{name}' does not exist on '{self._class_name}'."
        )
        raise AttributeError(error_msg)

    def getPropertySignature(self, name: str) -> inspect.Signature:
        """
        Return the signature of a property getter.

        Parameters
        ----------
        name : str
            Name of the property.

        Returns
        -------
        inspect.Signature
            Signature of the property's getter method.

        Raises
        ------
        AttributeError
            If the property does not exist on the class.
        """
        cache = self._memory_cache

        # Return cached property signature if available
        cache_key = f"property_signature_{name}"
        if cache_key in cache:
            return cache[cache_key]

        # Apply name mangling for private property lookup
        original_name = name
        if name.startswith("__") and not name.endswith("__"):
            name = f"{self._private_prefix}{name}"

        # Retrieve the property descriptor and inspect the getter signature
        prop = getattr(self._cls, name, None)
        if isinstance(prop, property):
            cache[cache_key] = inspect.signature(prop.fget)
            return cache[cache_key]

        error_msg = (
            f"Property '{original_name}' does not exist on '{self._class_name}'."
        )
        raise AttributeError(error_msg)

    def getPropertyDocstring(self, name: str) -> str:
        """
        Retrieve the docstring for a property.

        Parameters
        ----------
        name : str
            Name of the property.

        Returns
        -------
        str
            The docstring of the property, or an empty string if not present.

        Raises
        ------
        AttributeError
            If the property does not exist on the class.
        """
        cache = self._memory_cache

        # Return cached property docstring if available
        cache_key = f"property_docstring_{name}"
        if cache_key in cache:
            return cache[cache_key]

        # Apply name mangling for private property lookup
        original_name = name
        if name.startswith("__") and not name.endswith("__"):
            name = f"{self._private_prefix}{name}"

        # Retrieve the property descriptor and cache its getter docstring
        prop = getattr(self._cls, name, None)
        if isinstance(prop, property):
            result = prop.fget.__doc__ or ""
            cache[cache_key] = result
            return result

        error_msg = (
            f"Property '{original_name}' does not exist on '{self._class_name}'."
        )
        raise AttributeError(error_msg)

    def constructorSignature(self) -> Signature:
        """
        Analyze and return constructor dependencies of the instance's class.

        Returns
        -------
        Signature
            Structured representation of the constructor dependencies. Contains:
            - resolved : dict
                Dictionary of resolved dependencies with names and values.
            - unresolved : list
                List of unresolved dependencies (parameter names without default
                values or annotations).
        """
        cache = self._memory_cache

        # Return cached constructor signature if available
        if "constructor_signature" in cache:
            return cache["constructor_signature"]

        # Analyze the constructor dependencies using the pre-computed class reference
        cache["constructor_signature"] = ReflectDependencies(
            self._cls,
        ).constructorSignature()
        return cache["constructor_signature"]

    def methodSignature(self, method_name: str) -> Signature:
        """
        Analyze and return dependencies for a method of the instance's class.

        Parameters
        ----------
        method_name : str
            Name of the method to inspect.

        Returns
        -------
        Signature
            Structured representation of the method dependencies, including:
            - resolved: dict of resolved dependencies with names and values.
            - unresolved: list of unresolved dependencies (parameter names
              without default values or annotations).

        Raises
        ------
        AttributeError
            If the method does not exist on the class.
        """
        cache = self._memory_cache

        # Return cached method signature if available
        cache_key = f"method_signature_{method_name}"
        if cache_key in cache:
            return cache[cache_key]

        # Verify the method exists before analyzing its signature
        if not self.hasMethod(method_name):
            error_msg = (
                f"Method '{method_name}' does not exist on '{self._class_name}'."
            )
            raise AttributeError(error_msg)

        # Apply name mangling for private method lookup
        if method_name.startswith("__") and not method_name.endswith("__"):
            method_name = f"{self._private_prefix}{method_name}"

        # Analyze method dependencies and cache the result
        cache[cache_key] = ReflectDependencies(
            self._instance,
        ).methodSignature(method_name)
        return cache[cache_key]

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
        # Clear the internal memory cache for reflection results
        self._memory_cache.clear()
