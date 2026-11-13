# ruff: noqa: TC001
# Public annotations remain available to runtime inspection.
"""Define the contract for dependency-reflection implementations."""

from __future__ import annotations
from abc import ABC, abstractmethod

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
    """Declare that this class introduces no additional instance slots."""

    @abstractmethod
    def constructorSignature(self) -> Signature:
        """
        Inspect the constructor (__init__) and categorize parameter dependencies.

        Returns
        -------
        orionis.introspection.dependencies.entities.signature.Signature
            Contains resolved and unresolved parameter dependencies.

        Raises
        ------
        ValueError
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
        orionis.introspection.dependencies.entities.signature.Signature
            Categorized resolved and unresolved parameter dependencies.

        Raises
        ------
        AttributeError
            If the target has no method with the requested name.
        ValueError
            If the method's signature cannot be inspected.
        """

    @abstractmethod
    def callableSignature(self) -> Signature:
        """
        Inspect the callable target and categorize its parameter dependencies.

        Returns
        -------
        orionis.introspection.dependencies.entities.signature.Signature
            Contains resolved and unresolved parameter dependencies.

        Raises
        ------
        TypeError
            If the target is not callable.
        ValueError
            If the target's signature cannot be inspected.
        """
