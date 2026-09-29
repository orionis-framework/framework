from __future__ import annotations
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from orionis.introspection.dependencies.entities.signature import (
        Signature,
    )

class IReflectDependencies(ABC):
    """
    Define the contract for dependency-reflection implementations.

    Subclasses must implement all abstract methods to inspect callables
    and extract categorized parameter dependency signatures.
    """

    __slots__ = ()

    @abstractmethod
    def constructorSignature(self) -> Signature:
        """
        Inspect the constructor (__init__) and categorize parameter dependencies.

        Returns
        -------
        Signature
            Contains resolved and unresolved parameter dependencies.

        Raises
        ------
        ReflectionValueError
            If the constructor signature cannot be inspected.
        """

    @abstractmethod
    def methodSignature(self, method_name: str) -> Signature:
        """
        Inspect a named method and categorize its parameter dependencies.

        Parameters
        ----------
        method_name : str
            Name of the method to inspect.

        Returns
        -------
        Signature
            Categorized resolved and unresolved parameter dependencies.

        Raises
        ------
        ReflectionValueError
            If the method does not exist or its signature cannot be inspected.
        """

    @abstractmethod
    def callableSignature(self) -> Signature:
        """
        Inspect the callable target and categorize its parameter dependencies.

        Returns
        -------
        Signature
            Contains resolved and unresolved parameter dependencies.

        Raises
        ------
        ReflectionValueError
            If the target is not callable or its signature cannot be inspected.
        """
