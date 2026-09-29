from orionis.schemas.rule import Rule

class StartsWith(Rule):
    """Ensure a string starts with one of the given prefixes."""

    # ruff: noqa: ARG002

    __slots__ = ("_prefixes",)

    __message__ = "Value must start with one of the allowed prefixes."
    __code__ = "starts_with"

    def __init__(self, *prefixes: str, message: str | None = None) -> None:
        """
        Initialize the rule with the accepted prefixes.

        Parameters
        ----------
        *prefixes : str
            Prefixes the value may start with. At least one is required.
        message : str | None, optional
            Override message used when validation fails.

        Returns
        -------
        None
            This method initializes the instance and returns None.

        Raises
        ------
        ValueError
            If no prefix is supplied.
        """
        super().__init__(message=message)
        if not prefixes:
            error_msg = "StartsWith requires at least one prefix."
            raise ValueError(error_msg)
        self._prefixes: tuple[str, ...] = prefixes

    def enforce(
        self,
        field: str,
        value: object,
        instance: object,
    ) -> bool:
        """
        Validate a field value against the accepted prefixes.

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

        return value.startswith(self._prefixes)
