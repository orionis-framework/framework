# ruff: noqa: ARG002
# Keep rule interface parameter names compatible with keyword callers.
"""Ensure an integer is written with at most a given number of digits."""

from orionis.schemas.rule import Rule


class MaxDigits(Rule):
    """
    Ensure an integer is written with at most a given number of digits.

    The sign is ignored, so ``-1234`` counts as four digits.
    """

    __slots__ = ("_maximum",)
    """Declare the instance attribute slots reserved by this class."""

    __message__ = "Value must not exceed the allowed number of digits."
    """
    Error text for message: ``Value must not exceed the allowed number of digits.``.
    """
    __code__ = "max_digits"
    """Code identifier: ``max_digits``."""

    def __init__(self, maximum: int, *, message: str | None = None) -> None:
        """
        Initialize the rule with the maximum number of digits.

        Parameters
        ----------
        maximum : int
            Highest accepted number of digits.
        message : str | None, optional
            Override message used when validation fails.

        Returns
        -------
        None
            No return value.

        Raises
        ------
        ValueError
            If ``maximum`` is not strictly positive.
        """
        super().__init__(message=message)
        if maximum < 1:
            error_msg = (
                f"Invalid 'MaxDigits' value: {maximum!r}. "
                "The digit count must be strictly positive (>= 1)."
            )
            raise ValueError(error_msg)
        self._maximum: int = maximum
        """Highest accepted number of digits."""

    async def enforce(
        self,
        field: str,
        value: object,
        instance: object,
    ) -> bool:
        """
        Validate a field value against the allowed number of digits.

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
        # Booleans are integers in Python but are never valid numeric input.
        if isinstance(value, bool):
            return False

        if isinstance(value, int):
            magnitude = abs(value)
            if self._maximum >= magnitude.bit_length():
                return True
            return magnitude < 10**self._maximum
        if isinstance(value, str):
            text = value[1:] if value.startswith(("-", "+")) else value
            if not text.isdecimal():
                return False
            digits = len(text)
        else:
            return False

        return digits <= self._maximum
