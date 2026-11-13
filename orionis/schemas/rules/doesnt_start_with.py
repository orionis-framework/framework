# ruff: noqa: ARG002
# Keep rule interface parameter names compatible with keyword callers.
"""Ensure a string does not start with any of the given prefixes."""

from orionis.schemas.rule import Rule


class DoesntStartWith(Rule):
    """Ensure a string does not start with any of the given prefixes."""

    __slots__ = ("_prefixes",)
    """Declare the instance attribute slots reserved by this class."""

    __message__ = "Value must not start with any of the forbidden prefixes."
    """
    Error text for message: ``Value must not start with any of the forbidden
    prefixes.``.
    """
    __code__ = "doesnt_start_with"
    """Code identifier: ``doesnt_start_with``."""

    def __init__(self, *prefixes: str, message: str | None = None) -> None:
        """
        Initialize the rule with the forbidden prefixes.

        Parameters
        ----------
        *prefixes : str
            Prefixes the value must not start with. At least one is required.
        message : str | None, optional
            Override message used when validation fails.

        Returns
        -------
        None
            No return value.

        Raises
        ------
        ValueError
            If no prefix is supplied.
        """
        super().__init__(message=message)
        if not prefixes:
            error_msg = "DoesntStartWith requires at least one prefix."
            raise ValueError(error_msg)
        self._prefixes: tuple[str, ...] = prefixes
        """Prefixes the value must not start with. At least one is required."""

    async def enforce(
        self,
        field: str,
        value: object,
        instance: object,
    ) -> bool:
        """
        Validate a field value against the forbidden prefixes.

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

        return not value.startswith(self._prefixes)
