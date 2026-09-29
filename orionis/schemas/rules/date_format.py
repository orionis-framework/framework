from orionis.support.facades.datetime import DateTime
from orionis.schemas.rule import Rule

class DateFormat(Rule):
    """
    Ensure a date string matches one of the accepted formats.

    Formats use the tokens understood by the ``DateTime`` facade, such as
    ``"YYYY-MM-DD"`` or ``"DD/MM/YYYY HH:mm"``.
    """

    # ruff: noqa: ARG002

    __slots__ = ("_formats",)

    __message__ = "Value must match one of the accepted date formats."
    __code__ = "date_format"

    def __init__(self, *formats: str, message: str | None = None) -> None:
        """
        Initialize the rule with the accepted date formats.

        Parameters
        ----------
        *formats : str
            Format strings the value may match. At least one is required.
        message : str | None, optional
            Override message used when validation fails.

        Returns
        -------
        None
            This method initializes the instance and returns None.

        Raises
        ------
        ValueError
            If no format is supplied.
        """
        super().__init__(message=message)
        if not formats:
            error_msg = "DateFormat requires at least one format."
            raise ValueError(error_msg)
        self._formats: tuple[str, ...] = formats

    def enforce(
        self,
        field: str,
        value: object,
        instance: object,
    ) -> bool:
        """
        Validate a field value against the accepted date formats.

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

        for fmt in self._formats:
            try:
                DateTime.fromFormat(value, fmt)
            except (ValueError, TypeError):
                continue
            return True

        return False
