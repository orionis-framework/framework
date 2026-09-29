from orionis.schemas.rules.measure import measure
from orionis.schemas.rule import Rule

class Size(Rule):
    """
    Ensure a value has an exact size.

    Numbers are compared by magnitude, strings and collections by length,
    and uploaded files by their size in kilobytes.
    """

    # ruff: noqa: ARG002

    __slots__ = ("_size",)

    __message__ = "Value must have the required size."
    __code__ = "size"

    def __init__(self, size: float, *, message: str | None = None) -> None:
        """
        Initialize the rule with the required size.

        Parameters
        ----------
        size : int | float
            Exact size the value must have.
        message : str | None, optional
            Override message used when validation fails.

        Returns
        -------
        None
            This method initializes the instance and returns None.

        Raises
        ------
        ValueError
            If ``size`` is negative.
        """
        super().__init__(message=message)
        if size < 0:
            error_msg = (
                f"Invalid 'Size' value: {size!r}. The size must be "
                "non-negative (>= 0)."
            )
            raise ValueError(error_msg)
        self._size: float = size

    def enforce(
        self,
        field: str,
        value: object,
        instance: object,
    ) -> bool:
        """
        Validate a field value against the required size.

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

        return size == self._size
