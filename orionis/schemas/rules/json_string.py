# ruff: noqa: ARG002
# Keep rule interface parameter names compatible with keyword callers.
"""Ensure a string holds a syntactically valid JSON document."""

import msgspec
from orionis.schemas.rule import Rule


class Json(Rule):
    """Ensure a string holds a syntactically valid JSON document."""

    __slots__ = ()
    """Declare that this class introduces no additional instance slots."""

    __message__ = "Value must be a valid JSON string."
    """Error text for message: ``Value must be a valid JSON string.``."""
    __code__ = "json"
    """Code identifier: ``json``."""

    async def enforce(
        self,
        field: str,
        value: object,
        instance: object,
    ) -> bool:
        """
        Validate a field value as a JSON document.

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

        try:
            msgspec.json.decode(value)
        except msgspec.DecodeError, UnicodeEncodeError:
            return False

        return True
