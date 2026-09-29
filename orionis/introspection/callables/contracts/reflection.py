from __future__ import annotations
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import inspect
    from orionis.introspection.dependencies.entities.signature import (
        Signature,
    )

class IReflectionCallable(ABC):

    # Empty slots so subclasses can define __slots__ without inheriting __dict__
    __slots__ = ()

    @abstractmethod
    def getCallable(self) -> callable:
        """
        Return the callable function associated with this instance.

        Returns
        -------
        callable
            The function object encapsulated by this instance.
        """

    @abstractmethod
    def getName(self) -> str:
        """
        Return the name of the callable.

        Returns
        -------
        str
            Name of the function as defined in its declaration.
        """

    @abstractmethod
    def getModuleName(self) -> str:
        """
        Return the module name where the callable is defined.

        Returns
        -------
        str
            The name of the module in which the function was declared.
        """

    @abstractmethod
    def getModuleWithCallableName(self) -> str:
        """
        Return the fully qualified name of the callable.

        Combines the module name and callable name to create a complete identifier.

        Returns
        -------
        str
            The module and callable name separated by a dot.
        """

    @abstractmethod
    def getDocstring(self) -> str:
        """
        Return the docstring of the callable.

        Returns
        -------
        str
            The docstring of the function, or an empty string if not present.
        """

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
    def getSignature(self) -> inspect.Signature:
        """
        Return the signature of the callable.

        Returns
        -------
        inspect.Signature
            The signature object representing the callable's parameters,
            default values, and type annotations.
        """

    @abstractmethod
    def getDependencies(self) -> Signature:
        """
        Analyze and return the dependency signature of the wrapped callable.

        Inspects the callable's parameters and resolves each one into a typed
        dependency descriptor. The result is cached so that repeated calls do
        not re-run the analysis.

        Returns
        -------
        Signature
            A structure that holds the resolved and unresolved dependencies
            derived from the callable's parameter annotations.
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
