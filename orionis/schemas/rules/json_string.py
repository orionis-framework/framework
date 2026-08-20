import msgspec
from orionis.schemas.rule import Rule

class Json(Rule):
    """Ensure a string holds a syntactically valid JSON document."""

    # ruff: noqa: ARG002

    __slots__ = ()

    __message__ = "Value must be a valid JSON string."
    __code__ = "json"

    def enforce(
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
        except msgspec.DecodeError:
            return False

        return True
