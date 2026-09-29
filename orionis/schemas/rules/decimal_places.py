from decimal import Decimal, InvalidOperation
from orionis.schemas.rule import Rule

class DecimalPlaces(Rule):
    """
    Ensure a numeric value carries a given number of decimal places.

    A single bound requires an exact number of places, while supplying
    ``maximum`` accepts any count within the inclusive range.
    """

    # ruff: noqa: ARG002

    __slots__ = ("_maximum", "_minimum")

    __message__ = "Value must have the required number of decimal places."
    __code__ = "decimal"

    def __init__(
        self,
        minimum: int,
        maximum: int | None = None,
        *,
        message: str | None = None,
    ) -> None:
        """
        Initialize the rule with the accepted number of decimal places.

        Parameters
        ----------
        minimum : int
            Lowest accepted number of decimal places.
        maximum : int | None, optional
            Highest accepted number of decimal places. Defaults to
            ``minimum``, which requires an exact count.
        message : str | None, optional
            Override message used when validation fails.

        Returns
        -------
        None
            This method initializes the instance and returns None.

        Raises
        ------
        ValueError
            If the bounds are negative or produce an empty range.
        """
        super().__init__(message=message)
        upper = minimum if maximum is None else maximum
        if minimum < 0 or upper < minimum:
            error_msg = (
                f"Invalid decimal range: ({minimum!r}, {upper!r}). "
                "Bounds must be non-negative and ordered."
            )
            raise ValueError(error_msg)
        self._minimum: int = minimum
        self._maximum: int = upper

    def enforce(
        self,
        field: str,
        value: object,
        instance: object,
    ) -> bool:
        """
        Validate a field value against the accepted decimal places.

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
        # Booleans are integers in Python but never carry decimal places.
        if isinstance(value, bool):
            return False

        if not isinstance(value, int | float | str | Decimal):
            return False

        try:
            # The textual form is used so trailing zeros are preserved.
            number = Decimal(str(value))
        except (InvalidOperation, ValueError):
            return False

        exponent = number.as_tuple().exponent

        # Infinite and NaN values expose a string exponent instead of an int.
        if not isinstance(exponent, int):
            return False

        places = -exponent if exponent < 0 else 0
        return self._minimum <= places <= self._maximum
