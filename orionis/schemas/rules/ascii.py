# ruff: noqa: ARG002
# Keep rule interface parameter names compatible with keyword callers.
"""Ensure a string contains only 7-bit ASCII characters."""

from orionis.schemas.rule import Rule


class Ascii(Rule):
    """Ensure a string contains only 7-bit ASCII characters."""

    __slots__ = ()
    """Declare that this class introduces no additional instance slots."""

    __message__ = "Value must contain only 7-bit ASCII characters."
    """Error text for message: ``Value must contain only 7-bit ASCII characters.``."""
    __code__ = "ascii"
    """Code identifier: ``ascii``."""

    async def enforce(
        self,
        field: str,
        value: object,
        instance: object,
    ) -> bool:
        """
        Validate a field value as ASCII content.

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
        # Leave non-string values to the type layer, which already reports them.
        if not isinstance(value, str):
            return True

        return value.isascii()
