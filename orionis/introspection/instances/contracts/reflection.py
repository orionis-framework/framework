from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import inspect
    from collections.abc import Callable
    from orionis.introspection.dependencies.entities.signature import (
        Signature,
    )

class IReflectionInstance(ABC):

    # ruff :noqa: ANN401

    @abstractmethod
    def getInstance(self) -> Any:
        """
        Return the reflected object instance.

        Returns
        -------
        Any
            The object instance being reflected upon.
        """

    @abstractmethod
    def getClass(self) -> type:
        """
        Return the class of the instance.

        Returns
        -------
        type
            The class object of the instance.
        """

    @abstractmethod
    def getClassName(self) -> str:
        """
        Return the name of the instance's class.

        Returns
        -------
        str
            The name of the class.
        """

    @abstractmethod
    def getModuleName(self) -> str:
        """
        Return the name of the module where the class is defined.

        Returns
        -------
        str
            The module name where the class is defined.
        """

    @abstractmethod
    def getModuleWithClassName(self) -> str:
        """
        Return the module and class name as a single string.

        Returns
        -------
        str
            The module name and class name in the format 'module.ClassName'.
        """

    @abstractmethod
    def getDocstring(self) -> str | None:
        """
        Return the docstring of the instance's class.

        Returns
        -------
        str or None
            The docstring of the class, or None if not available.
        """

    @abstractmethod
    def getBaseClasses(self) -> tuple[type, ...]:
        """
        Return the base classes of the instance's class.

        Returns
        -------
        tuple of type
            Tuple containing the base classes of the class.
        """

    @abstractmethod
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

    @abstractmethod
    def getFile(self) -> str | None:
        """
        Return the file path where the class is defined.

        Returns
        -------
        str or None
            The file path of the class definition, or None if unavailable.
        """

    @abstractmethod
    def getAnnotations(self) -> dict[str, type]:
        """
        Retrieve type annotations of the class.

        Returns
        -------
        dict[str, type]
            Dictionary mapping attribute names to their type annotations.
        """

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
    def getMagicAttributes(self) -> dict[str, Any]:
        """
        Return all magic attributes of the instance.

        Returns
        -------
        dict[str, Any]
            Dictionary mapping magic attribute names to their values.
        """

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
    def getPublicSyncMethods(self) -> list[str]:
        """
        Return all public synchronous method names of the instance.

        Returns
        -------
        list of str
            List of public synchronous method names.
        """

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
    def getPrivateSyncMethods(self) -> list[str]:
        """
        Retrieve all private synchronous method names of the instance.

        Returns
        -------
        list of str
            List of private synchronous method names (unmangled).
        """

    @abstractmethod
    def getPrivateAsyncMethods(self) -> list[str]:
        """
        Retrieve all private asynchronous method names of the instance.

        Returns
        -------
        list of str
            List of private asynchronous method names (unmangled).
        """

    @abstractmethod
    def getPublicClassMethods(self) -> list[str]:
        """
        Return all public class method names of the instance.

        Returns
        -------
        list of str
            List of public class method names.
        """

    @abstractmethod
    def getPublicClassSyncMethods(self) -> list[str]:
        """
        Return all public synchronous class method names of the instance.

        Returns
        -------
        list of str
            List of public synchronous class method names.
        """

    @abstractmethod
    def getPublicClassAsyncMethods(self) -> list[str]:
        """
        Return all public asynchronous class method names of the instance.

        Returns
        -------
        list of str
            List of public asynchronous class method names.
        """

    @abstractmethod
    def getProtectedClassMethods(self) -> list[str]:
        """
        Return all protected class method names of the instance.

        Returns
        -------
        list of str
            List of protected class method names.
        """

    @abstractmethod
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

    @abstractmethod
    def getProtectedClassAsyncMethods(self) -> list[str]:
        """
        Retrieve all protected asynchronous class method names of the instance.

        Returns
        -------
        list of str
            List of protected asynchronous class method names.
        """

    @abstractmethod
    def getPrivateClassMethods(self) -> list[str]:
        """
        Return all private class method names of the instance.

        Returns
        -------
        list of str
            List of private class method names (unmangled).
        """

    @abstractmethod
    def getPrivateClassSyncMethods(self) -> list[str]:
        """
        Retrieve all private synchronous class method names of the instance.

        Returns
        -------
        list of str
            List of private synchronous class method names.
        """

    @abstractmethod
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

    @abstractmethod
    def getPublicStaticMethods(self) -> list[str]:
        """
        Return the names of all public static methods of the instance's class.

        Returns
        -------
        list of str
            List of public static method names defined on the class.
        """

    @abstractmethod
    def getPublicStaticSyncMethods(self) -> list[str]:
        """
        Return all public synchronous static method names of the instance.

        Returns
        -------
        list of str
            List of public synchronous static method names defined on the class.
        """

    @abstractmethod
    def getPublicStaticAsyncMethods(self) -> list[str]:
        """
        Retrieve all public asynchronous static method names of the instance.

        Returns
        -------
        list of str
            List of public asynchronous static method names defined on the class.
        """

    @abstractmethod
    def getProtectedStaticMethods(self) -> list[str]:
        """
        Return all protected static method names of the instance.

        Returns
        -------
        list of str
            List of protected static method names defined on the class.
        """

    @abstractmethod
    def getProtectedStaticSyncMethods(self) -> list[str]:
        """
        Retrieve all protected synchronous static method names.

        Returns
        -------
        list of str
            List of protected synchronous static method names defined on the class.
        """

    @abstractmethod
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

    @abstractmethod
    def getPrivateStaticMethods(self) -> list[str]:
        """
        Return all private static method names of the instance.

        Returns
        -------
        list of str
            List of private static method names defined on the class.
        """

    @abstractmethod
    def getPrivateStaticSyncMethods(self) -> list[str]:
        """
        Retrieve all private synchronous static method names of the instance.

        Returns
        -------
        list of str
            List of private synchronous static method names defined on the class.
        """

    @abstractmethod
    def getPrivateStaticAsyncMethods(self) -> list[str]:
        """
        Retrieve all private asynchronous static method names of the instance.

        Returns
        -------
        list of str
            List of private asynchronous static method names defined on the class.
        """

    @abstractmethod
    def getDunderMethods(self) -> list[str]:
        """
        Return all dunder (double underscore) method names of the instance.

        Returns
        -------
        list of str
            List of dunder method names defined on the instance.
        """

    @abstractmethod
    def getMagicMethods(self) -> list[str]:
        """
        Return all magic method names of the instance.

        Returns
        -------
        list of str
            List of magic (dunder) method names defined on the instance.
        """

    @abstractmethod
    def getProperties(self) -> list[str]:
        """
        Return all property names of the instance.

        Returns
        -------
        list of str
            List of property names defined as properties on the class.
        """

    @abstractmethod
    def getPublicProperties(self) -> list:
        """
        Return all public properties of the instance.

        Returns
        -------
        list
            List of public property names.
        """

    @abstractmethod
    def getProtectedProperties(self) -> list:
        """
        Retrieve all protected properties of the instance.

        Returns
        -------
        list
            List of protected property names (unmangled).
        """

    @abstractmethod
    def getPrivateProperties(self) -> list:
        """
        Retrieve all private properties of the instance.

        Returns
        -------
        list
            List of private property names (unmangled).
        """

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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
