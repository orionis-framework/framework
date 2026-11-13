# ruff: noqa: TC001, TC003
# Entity fields and return annotations must resolve at runtime.
"""Represent the categorized dependency signature of a callable."""

from __future__ import annotations
from dataclasses import dataclass
from collections.abc import ItemsView
from orionis.support.entities.base import BaseEntity

from orionis.introspection.dependencies.entities.argument import Argument


@dataclass(frozen=True, kw_only=True)
class Signature(BaseEntity):
    """
    Represent the categorized dependency signature of a callable.

    Groups parameter dependencies into resolved, unresolved, and ordered
    buckets that downstream IoC logic can consume directly.

    Attributes
    ----------
    resolved : dict[str, orionis.introspection.dependencies.entities.argument.Argument]
        Parameters whose types or defaults are fully known.
    unresolved : dict[str, Argument]
        Parameters that lack sufficient type or default information.
    ordered : dict[str, orionis.introspection.dependencies.entities.argument.Argument]
        All parameters in their original declaration order.
    """

    resolved: dict[str, Argument]
    unresolved: dict[str, Argument]
    ordered: dict[str, Argument]

    def __post_init__(self) -> None:
        """
        Validate that all three bucket fields are dictionaries.

        Returns
        -------
        None
            No return value.

        Raises
        ------
        TypeError
            If ``resolved``, ``unresolved``, or ``ordered`` is not a dict.
        """
        if not isinstance(self.resolved, dict):
            msg = f"resolved must be a dict, got {type(self.resolved).__name__!r}"
            raise TypeError(msg)
        if not isinstance(self.unresolved, dict):
            msg = f"unresolved must be a dict, got {type(self.unresolved).__name__!r}"
            raise TypeError(msg)
        if not isinstance(self.ordered, dict):
            msg = f"ordered must be a dict, got {type(self.ordered).__name__!r}"
            raise TypeError(msg)

    # ------------------------------------------------------------------
    # Predicate helpers
    # ------------------------------------------------------------------

    def hasParameters(self) -> bool:
        """
        Determine whether the callable defines any parameters.

        Returns
        -------
        bool
            True if at least one parameter is defined; otherwise False.
        """
        return bool(self.ordered)

    def noArgumentsRequired(self) -> bool:
        """
        Determine whether the callable requires no arguments.

        Returns
        -------
        bool
            True when the ordered parameter map is empty.
        """
        return not bool(self.ordered)

    def hasUnresolvedArguments(self) -> bool:
        """
        Determine whether any unresolved parameters exist.

        Returns
        -------
        bool
            True when the unresolved map is non-empty.
        """
        return bool(self.unresolved)

    # ------------------------------------------------------------------
    # Accessor helpers
    # ------------------------------------------------------------------

    def getResolved(self) -> dict[str, Argument]:
        """
        Return the resolved parameter dictionary.

        Returns
        -------
        dict[str, orionis.introspection.dependencies.entities.argument.Argument]
            Mapping of parameter names to resolved Argument objects.
        """
        return self.resolved

    def getUnresolved(self) -> dict[str, Argument]:
        """
        Return the unresolved parameter dictionary.

        Returns
        -------
        dict[str, orionis.introspection.dependencies.entities.argument.Argument]
            Mapping of parameter names to unresolved Argument objects.
        """
        return self.unresolved

    def getAllOrdered(self) -> dict[str, Argument]:
        """
        Return all parameters in their original declaration order.

        Returns
        -------
        dict[str, orionis.introspection.dependencies.entities.argument.Argument]
            Mapping of all parameter names to their Argument objects.
        """
        return self.ordered

    def getPositionalOnly(self) -> dict[str, Argument]:
        """
        Return parameters that are not keyword-only.

        Returns
        -------
        dict[str, orionis.introspection.dependencies.entities.argument.Argument]
            Subset of ordered containing only positional arguments.
        """
        return {k: v for k, v in self.ordered.items() if not v.is_keyword_only}

    def getKeywordOnly(self) -> dict[str, Argument]:
        """
        Return parameters that are keyword-only.

        Returns
        -------
        dict[str, orionis.introspection.dependencies.entities.argument.Argument]
            Subset of ordered containing only keyword-only arguments.
        """
        return {k: v for k, v in self.ordered.items() if v.is_keyword_only}

    # ------------------------------------------------------------------
    # Conversion helpers
    # ------------------------------------------------------------------

    def toDict(self) -> dict[str, Argument]:
        """
        Return the ordered parameters as a plain dictionary.

        Returns
        -------
        dict[str, orionis.introspection.dependencies.entities.argument.Argument]
            A new dict with the same contents as ordered.
        """
        return dict(self.ordered)

    def resolvedToDict(self) -> dict[str, Argument]:
        """
        Return the resolved parameters as a plain dictionary.

        Returns
        -------
        dict[str, orionis.introspection.dependencies.entities.argument.Argument]
            A new dict with the same contents as resolved.
        """
        return dict(self.resolved)

    def unresolvedToDict(self) -> dict[str, Argument]:
        """
        Return the unresolved parameters as a plain dictionary.

        Returns
        -------
        dict[str, orionis.introspection.dependencies.entities.argument.Argument]
            A new dict with the same contents as unresolved.
        """
        return dict(self.unresolved)

    # ------------------------------------------------------------------
    # Iteration helpers
    # ------------------------------------------------------------------

    def arguments(self) -> ItemsView[str, Argument]:
        """
        Return an iterable view of all parameters in declaration order.

        Returns
        -------
        collections.abc.ItemsView[str, Argument]
            Iterable of (name, Argument) pairs from ``ordered``.
        """
        return self.ordered.items()
