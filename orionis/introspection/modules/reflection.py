from __future__ import annotations
import importlib
import inspect
import keyword
from pathlib import Path
from types import FunctionType as _FunctionType, ModuleType as _ModuleType
from orionis.introspection.modules.contracts.reflection import (
    IReflectionModule,
)

class ReflectionModule(IReflectionModule):

    def __init__(self, module: str) -> None:
        """
        Initialize the ReflectionModule by importing the specified module.

        Parameters
        ----------
        module : str
            Name of the module to import and reflect upon.

        Raises
        ------
        TypeError
            If `module` is not a non-empty string or cannot be imported.

        Returns
        -------
        None
            This method does not return a value.
        """
        # Validate module name and import the module
        if not isinstance(module, str) or not module.strip():
            error_msg = f"Module name must be a non-empty string, got {module!r}"
            raise TypeError(error_msg)
        try:
            self.__module = importlib.import_module(module)
        except Exception as e:
            error_msg = f"Failed to import module '{module}': {e}"
            raise TypeError(error_msg) from e
        # Initialize memory cache for storing values
        self.__memory_cache: dict = {}

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
        return self.__memory_cache.get(key, None)

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
        self.__memory_cache[key] = value

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
        return key in self.__memory_cache

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
        self.__memory_cache.pop(key, None)

    def getModule(self) -> object:
        """
        Return the imported module object.

        Returns
        -------
        object
            The imported module object.
        """
        return self.__module

    def hasClass(self, class_name: str) -> bool:
        """
        Check if a class with the specified name exists in the module.

        Parameters
        ----------
        class_name : str
            Name of the class to check.

        Returns
        -------
        bool
            True if the class exists in the module, otherwise False.
        """
        # Check for class existence in the module's class dictionary
        return class_name in self.getClasses()

    def getClass(self, class_name: str) -> type | None:
        """
        Retrieve a class object by its name from the module.

        Parameters
        ----------
        class_name : str
            Name of the class to retrieve.

        Returns
        -------
        type or None
            The class object if found, otherwise None.
        """
        # Get all classes from the module and return the one matching class_name
        classes = self.getClasses()
        if class_name in classes:
            return classes[class_name]
        return None

    def setClass(self, class_name: str, cls: type) -> bool:
        """
        Set a class in the module.

        Parameters
        ----------
        class_name : str
            Name of the class to set.
        cls : type
            Class object to set.

        Raises
        ------
        ValueError
            If `cls` is not a class type, if `class_name` is not a valid identifier,
            or if `class_name` is a reserved keyword.

        Returns
        -------
        bool
            True if the class was set successfully.
        """
        # Validate that cls is a class type
        if not isinstance(cls, type):
            error_msg = f"Expected a class type, got {type(cls)}"
            raise TypeError(error_msg)
        # Validate that class_name is a valid identifier
        if not class_name.isidentifier():
            error_msg = f"Invalid class name '{class_name}'. Must be a valid identifier"
            raise ValueError(error_msg)
        # Validate that class_name is not a reserved keyword
        if keyword.iskeyword(class_name):
            error_msg = f"Class name '{class_name}' is a reserved keyword."
            raise ValueError(error_msg)
        # Set the class in the module and invalidate the classes cache
        setattr(self.__module, class_name, cls)
        del self["classes"]
        return True

    def removeClass(self, class_name: str) -> bool:
        """
        Remove a class from the module.

        Parameters
        ----------
        class_name : str
            Name of the class to remove.

        Raises
        ------
        ValueError
            If `class_name` is not a valid identifier or if the class does not exist.

        Returns
        -------
        bool
            True if the class was removed successfully.
        """
        # Check if the class exists in the module
        if class_name not in self.getClasses():
            error_msg = (
                f"Class '{class_name}' does not exist "
                f"in module '{self.__module.__name__}'"
            )
            raise ValueError(error_msg)
        # Remove the class attribute from the module and invalidate cache
        delattr(self.__module, class_name)
        del self["classes"]
        return True

    def getClasses(self) -> dict:
        """
        Return a dictionary of classes defined in the module.

        Parameters
        ----------
        None

        Returns
        -------
        dict
            Dictionary with class names as keys and class objects as values.
        """
        # Return cached result using a single dict lookup instead of two dunder calls
        _cache = self.__memory_cache
        _cached = _cache.get("classes")
        if _cached is not None:
            return _cached
        # Collect all type objects from the module namespace
        classes = {
            k: v
            for k, v in self.__module.__dict__.items()
            if isinstance(v, type)
        }
        _cache["classes"] = classes
        return classes

    def getPublicClasses(self) -> dict:
        """
        Return a dictionary of public classes defined in the module.

        Parameters
        ----------
        None

        Returns
        -------
        dict
            Dictionary with class names as keys and class objects as values.
        """
        # Return cached result using a single dict lookup instead of two dunder calls
        _cache = self.__memory_cache
        _cached = _cache.get("public_classes")
        if _cached is not None:
            return _cached
        # Collect classes whose names do not start with an underscore
        public_classes = {
            k: v for k, v in self.getClasses().items() if not k.startswith("_")
        }
        _cache["public_classes"] = public_classes
        return public_classes

    def getProtectedClasses(self) -> dict:
        """
        Return a dictionary of protected classes defined in the module.

        Parameters
        ----------
        None

        Returns
        -------
        dict
            Dictionary with class names as keys and class objects as values.
        """
        # Return cached result using a single dict lookup instead of two dunder calls
        _cache = self.__memory_cache
        _cached = _cache.get("protected_classes")
        if _cached is not None:
            return _cached
        # Collect classes whose names start with exactly one underscore
        protected_classes = {
            k: v for k, v in self.getClasses().items()
            if k.startswith("_") and not k.startswith("__")
        }
        _cache["protected_classes"] = protected_classes
        return protected_classes

    def getPrivateClasses(self) -> dict:
        """
        Return a dictionary of private classes defined in the module.

        Parameters
        ----------
        None

        Returns
        -------
        dict
            Dictionary with class names as keys and class objects as values.
        """
        # Return cached result using a single dict lookup instead of two dunder calls
        _cache = self.__memory_cache
        _cached = _cache.get("private_classes")
        if _cached is not None:
            return _cached
        # Collect classes with double-underscore prefix that are not dunder names
        private_classes = {
            k: v for k, v in self.getClasses().items()
            if k.startswith("__") and not k.endswith("__")
        }
        _cache["private_classes"] = private_classes
        return private_classes

    def getConstant(self, constant_name: str) -> object | None:
        """
        Retrieve a constant value by name from the module.

        Parameters
        ----------
        constant_name : str
            Name of the constant to retrieve.

        Returns
        -------
        object or None
            Value of the constant if found, otherwise None.
        """
        # Get all constants and return the value for the given name if present
        constants = self.getConstants()
        if constant_name in constants:
            return constants[constant_name]
        return None

    def getConstants(self) -> dict:
        """
        Retrieve constants defined in the module.

        Parameters
        ----------
        None

        Returns
        -------
        dict
            Dictionary with constant names as keys and their values as values.
        """
        # Return cached result using a single dict lookup instead of two dunder calls
        _cache = self.__memory_cache
        _cached = _cache.get("constants")
        if _cached is not None:
            return _cached
        # Collect non-callable all-uppercase attributes; keywords are always lowercase
        # so the isupper() check already excludes them, making iskeyword() redundant
        constants = {
            k: v for k, v in self.__module.__dict__.items()
            if k.isupper() and not callable(v)
        }
        _cache["constants"] = constants
        return constants

    def getPublicConstants(self) -> dict:
        """
        Retrieve public constants defined in the module.

        Parameters
        ----------
        None

        Returns
        -------
        dict
            Dictionary with constant names as keys and their values as values.
        """
        # Return cached result using a single dict lookup instead of two dunder calls
        _cache = self.__memory_cache
        _cached = _cache.get("public_constants")
        if _cached is not None:
            return _cached
        # Collect constants whose names do not start with an underscore
        public_constants = {
            k: v for k, v in self.getConstants().items() if not k.startswith("_")
        }
        _cache["public_constants"] = public_constants
        return public_constants

    def getProtectedConstants(self) -> dict:
        """
        Return protected constants defined in the module.

        Parameters
        ----------
        None

        Returns
        -------
        dict
            Dictionary with constant names as keys and their values as values.
        """
        # Return cached result using a single dict lookup instead of two dunder calls
        _cache = self.__memory_cache
        _cached = _cache.get("protected_constants")
        if _cached is not None:
            return _cached
        # Collect constants whose names start with exactly one underscore
        protected_constants = {
            k: v for k, v in self.getConstants().items()
            if k.startswith("_") and not k.startswith("__")
        }
        _cache["protected_constants"] = protected_constants
        return protected_constants

    def getPrivateConstants(self) -> dict:
        """
        Retrieve private constants defined in the module.

        Parameters
        ----------
        None

        Returns
        -------
        dict
            Dictionary with constant names as keys and their values as values.
        """
        # Return cached result using a single dict lookup instead of two dunder calls
        _cache = self.__memory_cache
        _cached = _cache.get("private_constants")
        if _cached is not None:
            return _cached
        # Collect constants with double-underscore prefix that are not dunder names
        private_constants = {
            k: v for k, v in self.getConstants().items()
            if k.startswith("__") and not k.endswith("__")
        }
        _cache["private_constants"] = private_constants
        return private_constants

    def getFunctions(self) -> dict:
        """
        Return a dictionary of functions defined in the module.

        Parameters
        ----------
        None

        Returns
        -------
        dict
            Dictionary with function names as keys and function objects as values.
        """
        # Return cached result using a single dict lookup instead of two dunder calls
        _cache = self.__memory_cache
        _cached = _cache.get("functions")
        if _cached is not None:
            return _cached
        # Use an exact type check to identify Python functions; this covers both
        # synchronous and asynchronous def-defined callables, excluding built-ins
        functions = {
            k: v
            for k, v in self.__module.__dict__.items()
            if isinstance(v, _FunctionType)
        }
        _cache["functions"] = functions
        return functions

    def getPublicFunctions(self) -> dict:
        """
        Return a dictionary of public functions defined in the module.

        Parameters
        ----------
        None

        Returns
        -------
        dict
            Dictionary mapping function names to function objects.
        """
        # Return cached result using a single dict lookup instead of two dunder calls
        _cache = self.__memory_cache
        _cached = _cache.get("public_functions")
        if _cached is not None:
            return _cached
        # Collect functions whose names do not start with an underscore
        public_functions = {
            k: v for k, v in self.getFunctions().items() if not k.startswith("_")
        }
        _cache["public_functions"] = public_functions
        return public_functions

    def getPublicSyncFunctions(self) -> dict:
        """
        Return a dictionary of public synchronous functions in the module.

        Parameters
        ----------
        None

        Returns
        -------
        dict
            Dictionary mapping function names to function objects.
        """
        # Return cached result using a single dict lookup instead of two dunder calls
        _cache = self.__memory_cache
        _cached = _cache.get("public_sync_functions")
        if _cached is not None:
            return _cached
        # Collect public functions that are not coroutine functions
        sync_functions = {
            k: v for k, v in self.getPublicFunctions().items()
            if not inspect.iscoroutinefunction(v)
        }
        _cache["public_sync_functions"] = sync_functions
        return sync_functions

    def getPublicAsyncFunctions(self) -> dict:
        """
        Return a dictionary of public asynchronous functions in the module.

        Parameters
        ----------
        None

        Returns
        -------
        dict
            Dictionary mapping function names to function objects.
        """
        # Return cached result using a single dict lookup instead of two dunder calls
        _cache = self.__memory_cache
        _cached = _cache.get("public_async_functions")
        if _cached is not None:
            return _cached
        # Collect public functions that are coroutine functions
        async_functions = {
            k: v for k, v in self.getPublicFunctions().items()
            if inspect.iscoroutinefunction(v)
        }
        _cache["public_async_functions"] = async_functions
        return async_functions

    def getProtectedFunctions(self) -> dict:
        """
        Return a dictionary of protected functions defined in the module.

        Parameters
        ----------
        None

        Returns
        -------
        dict
            Dictionary mapping protected function names to function objects.
        """
        # Return cached result using a single dict lookup instead of two dunder calls
        _cache = self.__memory_cache
        _cached = _cache.get("protected_functions")
        if _cached is not None:
            return _cached
        # Collect functions whose names start with exactly one underscore
        protected_functions = {
            k: v for k, v in self.getFunctions().items()
            if k.startswith("_") and not k.startswith("__")
        }
        _cache["protected_functions"] = protected_functions
        return protected_functions

    def getProtectedSyncFunctions(self) -> dict:
        """
        Return protected synchronous functions defined in the module.

        Parameters
        ----------
        None

        Returns
        -------
        dict
            Dictionary mapping function names to function objects.
        """
        # Return cached result using a single dict lookup instead of two dunder calls
        _cache = self.__memory_cache
        _cached = _cache.get("protected_sync_functions")
        if _cached is not None:
            return _cached
        # Collect protected functions that are not coroutine functions
        sync_functions = {
            k: v for k, v in self.getProtectedFunctions().items()
            if not inspect.iscoroutinefunction(v)
        }
        _cache["protected_sync_functions"] = sync_functions
        return sync_functions

    def getProtectedAsyncFunctions(self) -> dict:
        """
        Return protected asynchronous functions defined in the module.

        Parameters
        ----------
        None

        Returns
        -------
        dict
            Dictionary mapping function names to function objects.
        """
        # Return cached result using a single dict lookup instead of two dunder calls
        _cache = self.__memory_cache
        _cached = _cache.get("protected_async_functions")
        if _cached is not None:
            return _cached
        # Collect protected functions that are coroutine functions
        async_functions = {
            k: v for k, v in self.getProtectedFunctions().items()
            if inspect.iscoroutinefunction(v)
        }
        _cache["protected_async_functions"] = async_functions
        return async_functions

    def getPrivateFunctions(self) -> dict:
        """
        Return private functions defined in the module.

        Parameters
        ----------
        None

        Returns
        -------
        dict
            Dictionary mapping function names to function objects.
        """
        # Return cached result using a single dict lookup instead of two dunder calls
        _cache = self.__memory_cache
        _cached = _cache.get("private_functions")
        if _cached is not None:
            return _cached
        # Collect functions with double-underscore prefix that are not dunder names
        private_functions = {
            k: v for k, v in self.getFunctions().items()
            if k.startswith("__") and not k.endswith("__")
        }
        _cache["private_functions"] = private_functions
        return private_functions

    def getPrivateSyncFunctions(self) -> dict:
        """
        Return private synchronous functions defined in the module.

        Parameters
        ----------
        None

        Returns
        -------
        dict
            Dictionary with function names as keys and function objects as values.
        """
        # Return cached result using a single dict lookup instead of two dunder calls
        _cache = self.__memory_cache
        _cached = _cache.get("private_sync_functions")
        if _cached is not None:
            return _cached
        # Collect private functions that are not coroutine functions
        sync_functions = {
            k: v for k, v in self.getPrivateFunctions().items()
            if not inspect.iscoroutinefunction(v)
        }
        _cache["private_sync_functions"] = sync_functions
        return sync_functions

    def getPrivateAsyncFunctions(self) -> dict:
        """
        Return private asynchronous functions defined in the module.

        Returns
        -------
        dict
            Dictionary with function names as keys and function objects as values.
        """
        # Return cached result using a single dict lookup instead of two dunder calls
        _cache = self.__memory_cache
        _cached = _cache.get("private_async_functions")
        if _cached is not None:
            return _cached
        # Collect private functions that are coroutine functions
        async_functions = {
            k: v for k, v in self.getPrivateFunctions().items()
            if inspect.iscoroutinefunction(v)
        }
        _cache["private_async_functions"] = async_functions
        return async_functions

    def getImports(self) -> dict:
        """
        Retrieve imported modules from the module.

        Returns
        -------
        dict
            Dictionary mapping import names to module objects.
        """
        # Return cached result using a single dict lookup instead of two dunder calls
        _cache = self.__memory_cache
        _cached = _cache.get("imports")
        if _cached is not None:
            return _cached
        # Use the module-level _ModuleType constant to identify module attributes
        imports = {
            k: v
            for k, v in self.__module.__dict__.items()
            if isinstance(v, _ModuleType)
        }
        _cache["imports"] = imports
        return imports

    def getFile(self) -> str:
        """
        Return the file path of the module.

        Returns
        -------
        str
            The absolute file path of the module.
        """
        # Return cached path to avoid repeated inspect.getfile() introspection calls
        _cache = self.__memory_cache
        _cached = _cache.get("_file")
        if _cached is not None:
            return _cached
        file_path = inspect.getfile(self.__module)
        _cache["_file"] = file_path
        return file_path

    def getSourceCode(self) -> str:
        """
        Retrieve the source code of the module.

        Returns
        -------
        str
            The source code of the module as a string.

        Raises
        ------
        ValueError
            If the source code cannot be read from the module file.
        """
        # Return cached source code to skip re-reading the file on repeated calls
        _cache = self.__memory_cache
        _cached = _cache.get("source_code")
        if _cached is not None:
            return _cached

        try:
            # Read the module source file from its resolved path
            with Path.open(self.getFile(), encoding="utf-8") as file:
                source = file.read()
            _cache["source_code"] = source
            return source
        except Exception as e:
            error_msg = (
                f"Failed to read source code for module '{self.__module.__name__}': {e}"
            )
            raise ValueError(error_msg) from e

    def clearCache(self) -> None:
        """
        Clear all cached reflection data.

        Removes all cached entries stored in the reflection instance. Forces
        fresh computation on subsequent method calls.

        Parameters
        ----------
        None

        Returns
        -------
        None
            This method does not return a value.
        """
        # Clear the internal memory cache for reflection results
        self.__memory_cache.clear()
