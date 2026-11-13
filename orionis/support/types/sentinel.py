"""Represent the absence of a value without conflating it with None."""


class _MissingType:
    """Represent the absence of a value without conflating it with None."""

    def __repr__(self) -> str:
        """
        Return a string representation of the sentinel.

        Returns
        -------
        str
            The string "<MISSING>" representing the sentinel.
        """
        return "<MISSING>"

    def __bool__(self) -> bool:
        """
        Return False to indicate the sentinel is falsy.

        Returns
        -------
        bool
            Always returns False.
        """
        return False

    def __copy__(self) -> _MissingType:
        """
        Preserve this immutable marker when copied.

        Returns
        -------
        _MissingType
            The same marker instance.
        """
        return self

    def __deepcopy__(self, memo: dict[int, object]) -> _MissingType:
        """
        Preserve this immutable marker when copying an object graph.

        Parameters
        ----------
        memo : dict[int, object]
            Standard deepcopy memo, unused for an immutable marker.

        Returns
        -------
        _MissingType
            The same marker instance.
        """
        return self

    def __reduce__(self) -> str | tuple:
        """
        Resolve the canonical marker by its module global during unpickling.

        Returns
        -------
        str or tuple
            The canonical global name, or a constructor for a private instance.
        """
        return "MISSING" if self is MISSING else (type(self), ())


_MISSING_TYPE = _MissingType
"""Compatibility alias for the private marker constructor."""

# Instance representing a missing value sentinel.
MISSING = _MissingType()
"""Instance representing a missing value sentinel."""
