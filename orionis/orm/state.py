from __future__ import annotations
from typing import Any

# Sentinel distinguishing "attribute absent from the original snapshot"
# from any legitimate stored value, including None, in a single lookup.
_UNSET: Any = object()

class StateMixin:
    """
    Attribute state tracking behavior shared by every model.

    Tracks the original attribute snapshot taken at hydration or after
    the last successful save, the current attribute values, and the
    changes applied by the most recent save operation.
    """

    __slots__ = ()

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
            if original.get(key, _UNSET) != value
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
                key in current and original.get(key, _UNSET) != current[key]
                for key in attributes
            )
        return any(
            original.get(key, _UNSET) != value
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
        return dict(self._changes)

    def getOriginal(
        self,
        key: str | None = None,
        default: Any = None,  # noqa: ANN401
    ) -> Any:  # noqa: ANN401
        """
        Return the original attribute snapshot or a single original value.

        Parameters
        ----------
        key : str or None, optional
            Attribute name, or ``None`` for the whole snapshot.
        default : Any, optional
            Value returned when the attribute is absent.

        Returns
        -------
        Any
            Original snapshot dictionary, or the original value for
            the requested key.
        """
        if key is None:
            return dict(self._original)
        return self._original.get(key, default)

    def syncOriginal(self) -> Any:  # noqa: ANN401
        """
        Snapshot the current attributes as the new original state.

        Returns
        -------
        Model
            The same instance, enabling fluent chaining.
        """
        # Mutate the snapshot in place: the mixin declares no slots,
        # so rebinding the attribute is left to the owning model.
        self._original.clear()
        self._original.update(self._attributes)
        return self
