from orionis.schemas.rule import Rule

# Sentinel telling apart "field absent" from "field present but None".
_MISSING: object = object()

class ConfirmPassword(Rule):
    """
    Ensure a value matches the password supplied in a sibling field.

    The rule is applied to the confirmation field and compares its value
    against the field holding the original password.
    """

    # ruff: noqa: ARG002

    __slots__ = ("_other_field",)

    __message__ = "Value must match the password field."
    __code__ = "confirm_password"

    def __init__(
        self,
        other_field: str = "password",
        *,
        message: str | None = None,
    ) -> None:
        """
        Initialize the rule with the field holding the original password.

        Parameters
        ----------
        other_field : str, optional
            Name of the sibling field holding the password to match.
        message : str | None, optional
            Override message used when validation fails.

        Returns
        -------
        None
            This method initializes the instance and returns None.

        Raises
        ------
        ValueError
            If ``other_field`` is empty.
        """
        super().__init__(message=message)
        if not other_field:
            error_msg = "ConfirmPassword requires the name of the password field."
            raise ValueError(error_msg)
        self._other_field: str = other_field

    def enforce(
        self,
        field: str,
        value: object,
        instance: object,
    ) -> bool:
        """
        Validate a field value against the referenced password field.

        Parameters
        ----------
        field : str
            Field name associated with the value.
        value : object
            Value to validate.
        instance : object
            Schema instance holding the referenced password field.

        Returns
        -------
        bool
            Return ``True`` when the value passes validation.
        """
        password = getattr(instance, self._other_field, _MISSING)

        # Leave a missing password to the type layer, which already reports it.
        if password is _MISSING:
            return True

        return value == password
