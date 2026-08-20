from orionis.schemas.rule import Rule

class MaxDigits(Rule):
    """
    Ensure an integer is written with at most a given number of digits.

    The sign is ignored, so ``-1234`` counts as four digits.
    """

    # ruff: noqa: ARG002

    __slots__ = ("_maximum",)

    __message__ = "Value must not exceed the allowed number of digits."
    __code__ = "max_digits"

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
            This method initializes the instance and returns None.

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

    def enforce(
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
            digits = len(str(abs(value)))
        elif isinstance(value, str):
            digits = len(value.removeprefix("-").removeprefix("+"))
            if not value or digits == 0:
                return False
        else:
            return False

        return digits <= self._maximum
