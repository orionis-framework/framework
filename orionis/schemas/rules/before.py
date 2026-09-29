from orionis.schemas.rules.temporal import resolve_moment, to_datetime
from orionis.schemas.rule import Rule

class Before(Rule):
    """
    Ensure a date comes strictly before a reference moment.

    The reference may be a sibling field name, a parsable date string, a
    ``datetime``/``date`` value, or ``None`` to compare against the current
    moment.
    """

    # ruff: noqa: ARG002

    __slots__ = ("_reference",)

    __message__ = "Value must be a date before the reference moment."
    __code__ = "before"

    def __init__(
        self,
        reference: object = None,
        *,
        message: str | None = None,
    ) -> None:
        """
        Initialize the rule with the reference moment.

        Parameters
        ----------
        reference : object, optional
            Sibling field name, date string or datetime to compare against.
            Defaults to the current moment.
        message : str | None, optional
            Override message used when validation fails.

        Returns
        -------
        None
            This method initializes the instance and returns None.
        """
        super().__init__(message=message)
        self._reference: object = reference

    def enforce(
        self,
        field: str,
        value: object,
        instance: object,
    ) -> bool:
        """
        Validate a field value against the reference moment.

        Parameters
        ----------
        field : str
            Field name associated with the value.
        value : object
            Value to validate.
        instance : object
            Schema instance used to resolve sibling field references.

        Returns
        -------
        bool
            Return ``True`` when the value passes validation.
        """
        moment = to_datetime(value)

        # Leave non-date values to the type layer, which already reports them.
        if moment is None:
            return True

        reference = resolve_moment(self._reference, instance)
        if reference is None:
            return False

        return moment < reference
