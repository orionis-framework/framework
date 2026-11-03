"""Ensure a field contains a non-empty value."""

from orionis.schemas.rule import Rule
from orionis.schemas.rules.measure import is_empty

class NoEmpty(Rule):
    """
    Reject exactly the values accepted by Empty.

    None, blank strings, zero, False and zero-length values are rejected.
    Uploaded files require a non-zero byte size; unsized iterables are not
    consumed and are considered present.
    """

    __slots__ = ()
    """Declare that this class introduces no additional instance slots."""

    __code__ = "no_empty"
    """Code identifier: ``no_empty``."""
    __message__ = "Value must not be empty."
    """Default message reported for an empty value."""

    async def enforce(
        self,
        field: str,  # noqa: ARG002
        value: object,
        instance: object,  # noqa: ARG002
    ) -> bool:
        """
        Check that a field value is not empty.

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
            Whether the field value is not empty.
        """
        return not is_empty(value)
