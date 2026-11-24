# ruff: noqa: ANN401
# Retain runtime annotations and dynamic attribute values.
"""Attribute state tracking behavior shared by every model."""

from __future__ import annotations
from copy import deepcopy
from datetime import UTC, datetime
from typing import Any, Self


def _changed(previous: Any, current: Any) -> bool:
    """
    Compare aware datetimes by instant, including both sides of a DST fold.

    Parameters
    ----------
    previous : typing.Any
        Original value recorded by the model.
    current : typing.Any
        Currently assigned value.

    Returns
    -------
    bool
        Whether the current value differs from the snapshot.
    """
    if (
        isinstance(previous, datetime)
        and isinstance(current, datetime)
        and previous.utcoffset() is not None
        and current.utcoffset() is not None
    ):
        return previous.astimezone(UTC) != current.astimezone(UTC)
    return previous != current


class StateMixin:
    """
    Track model attributes against their last persisted snapshot.

    Tracks the original attribute snapshot taken at hydration or after
    the last successful save, the current attribute values, and the
    changes applied by the most recent save operation.
    """

    __slots__ = ()
    """Declare that this class introduces no additional instance slots."""

    def getDirty(self) -> dict[str, Any]:
        """
        Return the attributes modified since the last sync.

        Returns
        -------
        dict
            Changed attribute values keyed by name.
        """
        original = self._original
        return {
            key: value
            for key, value in self._attributes.items()
            if key not in original or _changed(original[key], value)
        }

    def isDirty(self, *attributes: str) -> bool:
        """
        Report whether any attribute changed since the last sync.

        Parameters
        ----------
        *attributes : str
            Restrict the check to these attribute names when provided.

        Returns
        -------
        bool
            ``True`` when at least one tracked attribute changed.
        """
        current = self._attributes
        original = self._original
        if attributes:
            return any(
                key in current
                and (key not in original or _changed(original[key], current[key]))
                for key in attributes
            )
        return any(
            key not in original or _changed(original[key], value)
            for key, value in current.items()
        )

    def isClean(self, *attributes: str) -> bool:
        """
        Report whether no attribute changed since the last sync.

        Parameters
        ----------
        *attributes : str
            Restrict the check to these attribute names when provided.

        Returns
        -------
        bool
            ``True`` when no tracked attribute changed.
        """
        return not self.isDirty(*attributes)

    def wasChanged(self, *attributes: str) -> bool:
        """
        Report whether the last save operation changed any attribute.

        Parameters
        ----------
        *attributes : str
            Restrict the check to these attribute names when provided.

        Returns
        -------
        bool
            ``True`` when the last save persisted at least one change.
        """
        changes = self._changes
        if not attributes:
            return bool(changes)
        return any(key in changes for key in attributes)

    def getChanges(self) -> dict[str, Any]:
        """
        Return the attributes persisted by the last save operation.

        Returns
        -------
        dict
            Attribute values written by the last save.
        """
        return deepcopy(self._changes)

    def getOriginal(
        self,
        key: str | None = None,
        default: Any = None,
    ) -> Any:
        """
        Return the original attribute snapshot or a single original value.

        Parameters
        ----------
        key : str or None, optional
            Attribute name, or ``None`` for the whole snapshot.
        default : typing.Any, optional
            Value returned when the attribute is absent.

        Returns
        -------
        typing.Any
            Original snapshot dictionary, or the original value for
            the requested key.
        """
        if key is None:
            return deepcopy(self._original)
        return deepcopy(self._original[key]) if key in self._original else default

    def syncOriginal(self) -> Self:
        """
        Snapshot the current attributes as the new original state.

        Returns
        -------
        orionis.orm.Model
            The same instance, enabling fluent chaining.
        """
        # Mutate the snapshot in place: the mixin declares no slots,
        # so rebinding the attribute is left to the owning model.
        snapshot = deepcopy(self._attributes)
        self._original.clear()
        self._original.update(snapshot)
        return self
