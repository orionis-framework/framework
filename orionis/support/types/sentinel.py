"""Represent the absence of a value without conflating it with None."""

class _MISSING_TYPE: # NOSONAR

    # ruff: noqa: N801
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

# Instance representing a missing value sentinel.
MISSING = _MISSING_TYPE()
"""Instance representing a missing value sentinel."""
