from orionis.schemas.rule import Rule

class DoesntEndWith(Rule):
    """Ensure a string does not end with any of the given suffixes."""

    # ruff: noqa: ARG002

    __slots__ = ("_suffixes",)

    __message__ = "Value must not end with any of the forbidden suffixes."
    __code__ = "doesnt_end_with"

    def __init__(self, *suffixes: str, message: str | None = None) -> None:
        """
        Initialize the rule with the forbidden suffixes.

        Parameters
        ----------
        *suffixes : str
            Suffixes the value must not end with. At least one is required.
        message : str | None, optional
            Override message used when validation fails.

        Returns
        -------
        None
            This method initializes the instance and returns None.

        Raises
        ------
        ValueError
            If no suffix is supplied.
        """
        super().__init__(message=message)
        if not suffixes:
            error_msg = "DoesntEndWith requires at least one suffix."
            raise ValueError(error_msg)
        self._suffixes: tuple[str, ...] = suffixes

    def enforce(
        self,
        field: str,
        value: object,
        instance: object,
    ) -> bool:
        """
        Validate a field value against the forbidden suffixes.

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

        return not value.endswith(self._suffixes)
