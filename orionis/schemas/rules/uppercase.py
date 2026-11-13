# ruff: noqa: ARG002
# Keep rule interface parameter names compatible with keyword callers.
"""Ensure a string contains no lowercase characters."""

from orionis.schemas.rule import Rule


class Uppercase(Rule):
    """Ensure a string contains no lowercase characters."""

    __slots__ = ()
    """Declare that this class introduces no additional instance slots."""

    __message__ = "Value must be uppercase."
    """Error text for message: ``Value must be uppercase.``."""
    __code__ = "uppercase"
    """Code identifier: ``uppercase``."""

    async def enforce(
        self,
        field: str,
        value: object,
        instance: object,
    ) -> bool:
        """
        Validate a field value as uppercase content.

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

        # Compare against the folded form so caseless characters still pass.
        return value == value.upper()
