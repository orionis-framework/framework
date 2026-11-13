# ruff: noqa: ARG002
# Keep rule interface parameter names compatible with keyword callers.
"""Ensure a value differs from every value supplied to the rule."""

from orionis.schemas.rule import Rule


class Different(Rule):
    """Ensure a value differs from every value supplied to the rule."""

    __slots__ = ("_forbidden",)
    """Declare the instance attribute slots reserved by this class."""

    __message__ = "Value must be different from the forbidden values."
    """
    Error text for message: ``Value must be different from the forbidden values.``.
    """
    __code__ = "different"
    """Code identifier: ``different``."""

    def __init__(self, *values: object, message: str | None = None) -> None:
        """
        Initialize the rule with the forbidden values.

        Parameters
        ----------
        *values : object
            Values the field must not be equal to. At least one is required.
        message : str | None, optional
            Override message used when validation fails.

        Returns
        -------
        None
            No return value.

        Raises
        ------
        ValueError
            If no value is supplied.
        """
        super().__init__(message=message)
        if not values:
            error_msg = "Different requires at least one value."
            raise ValueError(error_msg)
        self._forbidden: tuple[object, ...] = values
        """Values the field must not be equal to. At least one is required."""

    async def enforce(
        self,
        field: str,
        value: object,
        instance: object,
    ) -> bool:
        """
        Validate a field value against the forbidden values.

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
        # Equality is used instead of membership so unhashable values work.
        return all(value != forbidden for forbidden in self._forbidden)
