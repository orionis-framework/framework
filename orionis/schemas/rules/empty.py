# ruff: noqa: ARG002
# Keep rule interface parameter names compatible with keyword callers.
"""Ensure a field contains an empty value."""

from orionis.schemas.rule import Rule
from orionis.schemas.rules.measure import is_empty


class Empty(Rule):
    """
    Accept None, blank strings, zero, False and zero-length values.

    Uploaded files are empty when their byte size is zero. Unsized iterables
    are not consumed and are considered present.
    """

    __slots__ = ()
    """Declare that this class introduces no additional instance slots."""

    __code__ = "empty"
    """Code identifier: ``empty``."""
    __message__ = "Value must be empty."
    """Default message reported for a non-empty value."""

    async def enforce(
        self,
        field: str,
        value: object,
        instance: object,
    ) -> bool:
        """
        Check that a field value is empty.

        Parameters
        ----------
        field : str
            Field path accepted for rule interface compatibility.
        value : object
            Value to inspect without consuming or changing it.
        instance : object
            Owner accepted for rule interface compatibility.

        Returns
        -------
        bool
            Whether the field value is empty.
        """
        return is_empty(value)
