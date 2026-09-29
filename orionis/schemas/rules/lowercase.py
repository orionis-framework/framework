from orionis.schemas.rule import Rule

class Lowercase(Rule):
    """Ensure a string contains no uppercase characters."""

    # ruff: noqa: ARG002

    __slots__ = ()

    __message__ = "Value must be lowercase."
    __code__ = "lowercase"

    def enforce(
        self,
        field: str,
        value: object,
        instance: object,
    ) -> bool:
        """
        Validate a field value as lowercase content.

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
        return value == value.lower()
