from orionis.schemas.rules.measure import measure
from orionis.schemas.rule import Rule

class Between(Rule):
    """
    Ensure a value's size falls within an inclusive range.

    Numbers are compared by magnitude, strings and collections by length,
    and uploaded files by their size in kilobytes.
    """

    # ruff: noqa: ARG002

    __slots__ = ("_maximum", "_minimum")

    __message__ = "Value must be between the configured bounds."
    __code__ = "between"

    def __init__(
        self,
        minimum: float,
        maximum: float,
        *,
        message: str | None = None,
    ) -> None:
        """
        Initialize the rule with the inclusive bounds.

        Parameters
        ----------
        minimum : int | float
            Lowest accepted size.
        maximum : int | float
            Highest accepted size.
        message : str | None, optional
            Override message used when validation fails.

        Returns
        -------
        None
            This method initializes the instance and returns None.

        Raises
        ------
        ValueError
            If ``minimum`` is greater than ``maximum``.
        """
        super().__init__(message=message)
        if minimum > maximum:
            error_msg = (
                f"Impossible range: minimum {minimum!r} is greater than "
                f"maximum {maximum!r}."
            )
            raise ValueError(error_msg)
        self._minimum: float = minimum
        self._maximum: float = maximum

    def enforce(
        self,
        field: str,
        value: object,
        instance: object,
    ) -> bool:
        """
        Validate a field value against the configured range.

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
        size = measure(value)

        # Leave unmeasurable values to the type layer, which reports them.
        if size is None:
            return True

        return self._minimum <= size <= self._maximum
