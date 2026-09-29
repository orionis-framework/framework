from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    import inspect
    from collections.abc import Callable
    from orionis.introspection.dependencies.entities.signature import (
        Signature,
    )

class IReflectionConcrete(ABC):

    # ruff: noqa: ANN401

    @abstractmethod
    def getClass(self) -> type:
        """
        Return the class type being reflected.

        Returns
        -------
        Type
            The class type provided during initialization.
        """

    @abstractmethod
    def getClassName(self) -> str:
        """
        Return the name of the reflected class.

        Returns
        -------
        str
            The simple name of the class without module qualification.
        """

    @abstractmethod
    def getModuleName(self) -> str:
        """
        Return the module name where the reflected class is defined.

        Returns
        -------
        str
            The fully qualified module name containing the class.
        """

    @abstractmethod
    def getModuleWithClassName(self) -> str:
        """
        Return the fully qualified class name with module path.

        Returns
        -------
        str
            The module name concatenated with the class name, separated by a dot.
        """

    @abstractmethod
    def getDocstring(self) -> str | None:
        """
        Return the docstring of the reflected class.

        Returns
        -------
        str or None
            The docstring of the class if defined, otherwise None.
        """

    @abstractmethod
    def getBaseClasses(self) -> list[type]:
        """
        Return all base classes of the reflected class.

        Returns
        -------
        list of type
            A list containing all base classes in the method resolution order.
        """

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
    def getPublicAsyncMethods(self) -> list[str]:
        """
        Return all public asynchronous method names of the reflected class.

        Filters public methods to include only coroutine functions.

        Returns
        -------
        list of str
            List of public asynchronous method names.
        """

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
    def getPrivateSyncMethods(self) -> list[str]:
        """
        Return all private synchronous method names of the class.

        Returns
        -------
        list of str
            List of private synchronous method names.
        """

    @abstractmethod
    def getPrivateAsyncMethods(self) -> list[str]:
        """
        Return all private asynchronous method names of the class.

        Finds private methods (using name mangling) that are coroutine functions.

        Returns
        -------
        list of str
            List of private asynchronous method names.
        """

    @abstractmethod
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

    @abstractmethod
    def getPublicClassSyncMethods(self) -> list[str]:
        """
        Return all public synchronous class method names.

        Returns
        -------
        list of str
            List of public synchronous class method names.
        """

    @abstractmethod
    def getPublicClassAsyncMethods(self) -> list[str]:
        """
        Return all public asynchronous class method names.

        Returns
        -------
        list of str
            List of public asynchronous class method names.
        """

    @abstractmethod
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

    @abstractmethod
    def getProtectedClassSyncMethods(self) -> list[str]:
        """
        Return all protected synchronous class method names.

        Returns
        -------
        list of str
            List of protected synchronous class method names.
        """

    @abstractmethod
    def getProtectedClassAsyncMethods(self) -> list[str]:
        """
        Return all protected asynchronous class method names.

        Returns
        -------
        list of str
            List of protected asynchronous class method names.
        """

    @abstractmethod
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

    @abstractmethod
    def getPrivateClassSyncMethods(self) -> list[str]:
        """
        Return all private synchronous class method names.

        Returns
        -------
        list of str
            List of private synchronous class method names.
        """

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
    def getPublicStaticSyncMethods(self) -> list[str]:
        """
        Return all public synchronous static method names of the class.

        Returns
        -------
        list of str
            List of public synchronous static method names.
        """

    @abstractmethod
    def getPublicStaticAsyncMethods(self) -> list[str]:
        """
        Return all public asynchronous static method names of the class.

        Returns
        -------
        list of str
            List of public asynchronous static method names.
        """

    @abstractmethod
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

    @abstractmethod
    def getProtectedStaticSyncMethods(self) -> list[str]:
        """
        Return all protected synchronous static method names of the class.

        Returns
        -------
        list of str
            List of protected synchronous static method names.
        """

    @abstractmethod
    def getProtectedStaticAsyncMethods(self) -> list[str]:
        """
        Retrieve all protected asynchronous static method names.

        Returns
        -------
        list of str
            List of protected asynchronous static method names.
        """

    @abstractmethod
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

    @abstractmethod
    def getPrivateStaticSyncMethods(self) -> list[str]:
        """
        Return all private synchronous static method names of the class.

        Returns
        -------
        list of str
            List of private synchronous static method names.
        """

    @abstractmethod
    def getPrivateStaticAsyncMethods(self) -> list[str]:
        """
        Retrieve all private asynchronous static method names of the class.

        Returns
        -------
        list of str
            List of private asynchronous static method names.
        """

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
    def getConstructorSignature(self) -> inspect.Signature:
        """
        Return the signature of the class constructor.

        Returns
        -------
        inspect.Signature
            Signature object for the __init__ method, containing parameter
            information.
        """

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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
