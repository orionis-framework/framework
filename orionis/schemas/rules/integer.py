# ruff: noqa: ARG002
# Keep rule interface parameter names compatible with keyword callers.
"""Ensure a value represents a whole number."""

import re
from orionis.schemas.rule import Rule

# Optionally signed sequence of digits, matching a whole number in text form.
_INTEGER_PATTERN = re.compile(r"^[+-]?\d+$")
"""Optionally signed sequence of digits, matching a whole number in text form."""


class Integer(Rule):
    """
    Ensure a value represents a whole number.

    Integers pass directly, floats only when they carry no fractional part,
    and strings when they hold an optionally signed sequence of digits.
    """

    __slots__ = ()
    """Declare that this class introduces no additional instance slots."""

    __message__ = "Value must be an integer."
    """Error text for message: ``Value must be an integer.``."""
    __code__ = "integer"
    """Code identifier: ``integer``."""

    async def enforce(
        self,
        field: str,
        value: object,
        instance: object,
    ) -> bool:
        """
        Validate a field value as a whole number.

        Parameters
        ----------
        field : str
            Field name associated with the value.
        value : object
            Value to validate.
        instance : object
            Owning object instance. This argument is accepted for
            interface compatibility.

        Returns
        -------
        bool
            Return ``True`` when the value passes validation.
        """
        # Booleans are integers in Python but are never valid numeric input.
        if isinstance(value, bool):
            return False

        if isinstance(value, int):
            return True

        if isinstance(value, float):
            return value.is_integer()

        if isinstance(value, str):
            return _INTEGER_PATTERN.fullmatch(value) is not None

        return False
