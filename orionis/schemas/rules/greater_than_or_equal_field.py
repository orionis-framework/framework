from orionis.schemas.rules.measure import measure
from orionis.schemas.rule import Rule

class GreaterThanOrEqualField(Rule):
    """
    Ensure a value is greater than or equal to a sibling field.

    Both values are compared using the same size semantics: numbers by
    magnitude, strings and collections by length, and uploaded files by
    their size in kilobytes.
    """

    # ruff: noqa: ARG002

    __slots__ = ("_other_field",)

    __message__ = "Value must be greater than or equal to the compared field."
    __code__ = "gte"

    def __init__(self, other_field: str, *, message: str | None = None) -> None:
        """
        Initialize the rule with the field to compare against.

        Parameters
        ----------
        other_field : str
            Name of the sibling field holding the lower bound.
        message : str | None, optional
            Override message used when validation fails.

        Returns
        -------
        None
            This method initializes the instance and returns None.
        """
        super().__init__(message=message)
        self._other_field: str = other_field

    def enforce(
        self,
        field: str,
        value: object,
        instance: object,
    ) -> bool:
        """
        Validate a field value against the compared field.

        Parameters
        ----------
        field : str
            Field name associated with the value.
        value : object
            Value to validate.
        instance : object
            Schema instance holding the compared field.

        Returns
        -------
        bool
            Return ``True`` when the value passes validation.
        """
        size = measure(value)
        bound = measure(getattr(instance, self._other_field, None))

        # Leave unmeasurable values to the type layer, which reports them.
        if size is None or bound is None:
            return True

        return size >= bound
