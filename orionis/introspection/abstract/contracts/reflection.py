from __future__ import annotations
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import inspect
    from orionis.introspection.dependencies.entities.signature import (
        Signature,
    )

class IReflectionAbstract(ABC):

    @abstractmethod
    def getClass(self) -> type:
        """
        Return the class type associated with this reflection instance.

        Returns
        -------
        Type
            The abstract base class type provided during initialization.
        """

    @abstractmethod
    def getClassName(self) -> str:
        """
        Return the name of the reflected abstract class.

        Returns
        -------
        str
            The name of the abstract class provided during initialization.
        """

    @abstractmethod
    def getModuleName(self) -> str:
        """
        Return the module name of the reflected abstract class.

        Returns
        -------
        str
            The fully qualified module name containing the abstract class.
        """

    @abstractmethod
    def getModuleWithClassName(self) -> str:
        """
        Return the fully qualified name of the abstract class.

        Returns
        -------
        str
            The module path and class name separated by a dot, such as
            'module.submodule.ClassName'.
        """

    @abstractmethod
    def getDocstring(self) -> str | None:
        """
        Retrieve the docstring for the reflected abstract class.

        Returns
        -------
        str or None
            The docstring of the abstract class, or None if not available.
        """

    @abstractmethod
    def getBaseClasses(self) -> list[type]:
        """
        Return the direct base classes of the reflected abstract class.

        Returns
        -------
        list of type
            List of direct base classes for the abstract class.
        """

    @abstractmethod
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
            If the source code cannot be retrieved due to file system errors or
            other unexpected exceptions.
        """

    @abstractmethod
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
            If the file path cannot be retrieved due to type errors or other
            unexpected exceptions.
        """

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
    def getMethods(self) -> list[str]:
        """
        Return all method names defined in the abstract class.

        Returns
        -------
        list of str
            List of all method names, including public, protected, private,
            static, and class methods.
        """

    @abstractmethod
    def getPublicMethods(self) -> list[str]:
        """
        Return all public instance method names.

        Returns
        -------
        list of str
            List of public instance method names. Excludes dunder, protected,
            private methods, static methods, class methods, and properties.
        """

    @abstractmethod
    def getPublicSyncMethods(self) -> list[str]:
        """
        Return all public synchronous method names from the abstract class.

        Returns
        -------
        list of str
            List of public synchronous method names. Excludes asynchronous methods.
        """

    @abstractmethod
    def getPublicAsyncMethods(self) -> list[str]:
        """
        Return all public asynchronous method names.

        Returns
        -------
        list of str
            List of public asynchronous method names. Only coroutine functions
            are included.
        """

    @abstractmethod
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

    @abstractmethod
    def getProtectedSyncMethods(self) -> list[str]:
        """
        Return all protected synchronous method names.

        Returns
        -------
        list of str
            List of protected synchronous method names. Only includes protected
            methods that are not coroutine functions.
        """

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
    def getPrivateSyncMethods(self) -> list[str]:
        """
        Return all private synchronous method names.

        Returns
        -------
        list of str
            List of private synchronous method names. Only includes private methods
            that are not coroutine functions.
        """

    @abstractmethod
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

    @abstractmethod
    def getPublicClassMethods(self) -> list[str]:
        """
        Return all public class method names.

        Returns
        -------
        list of str
            List of public class method names. Only includes methods decorated
            with @classmethod that do not start with underscores.
        """

    @abstractmethod
    def getPublicClassSyncMethods(self) -> list[str]:
        """
        Return all public synchronous class method names.

        Returns
        -------
        list of str
            List of public synchronous class method names. Only includes methods
            that are not coroutine functions.
        """

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
    def getPublicStaticMethods(self) -> list[str]:
        """
        Return all public static method names.

        Returns
        -------
        list of str
            List of public static method names. Only includes methods decorated
            with @staticmethod that do not start with underscores.
        """

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
    def getMagicMethods(self) -> list[str]:
        """
        Return all magic (dunder) methods from the abstract class.

        Returns
        -------
        list of str
            List of magic method names. This is an alias for getDunderMethods().
        """

    @abstractmethod
    def getProperties(self) -> list[str]:
        """
        Retrieve all property names from the abstract class.

        Returns
        -------
        List[str]
            List of property names with name mangling prefixes removed for clarity.
        """

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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
