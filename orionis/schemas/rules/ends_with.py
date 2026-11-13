# ruff: noqa: ARG002
# Keep rule interface parameter names compatible with keyword callers.
"""Ensure a string ends with one of the given suffixes."""

from orionis.schemas.rule import Rule


class EndsWith(Rule):
    """Ensure a string ends with one of the given suffixes."""

    __slots__ = ("_suffixes",)
    """Declare the instance attribute slots reserved by this class."""

    __message__ = "Value must end with one of the allowed suffixes."
    """Error text for message: ``Value must end with one of the allowed suffixes.``."""
    __code__ = "ends_with"
    """Code identifier: ``ends_with``."""

    def __init__(self, *suffixes: str, message: str | None = None) -> None:
        """
        Initialize the rule with the accepted suffixes.

        Parameters
        ----------
        *suffixes : str
            Suffixes the value may end with. At least one is required.
        message : str | None, optional
            Override message used when validation fails.

        Returns
        -------
        None
            No return value.

        Raises
        ------
        ValueError
            If no suffix is supplied.
        """
        super().__init__(message=message)
        if not suffixes:
            error_msg = "EndsWith requires at least one suffix."
            raise ValueError(error_msg)
        self._suffixes: tuple[str, ...] = suffixes
        """Suffixes the value may end with. At least one is required."""

    async def enforce(
        self,
        field: str,
        value: object,
        instance: object,
    ) -> bool:
        """
        Validate a field value against the accepted suffixes.

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

        return value.endswith(self._suffixes)
