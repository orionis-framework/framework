from orionis.schemas.contracts.constraint import IRule
from orionis.schemas.entities.failure import ValidationFailure

class Rule(IRule):

    # Use __slots__ to optimize memory usage
    # by preventing the creation of __dict__ for each instance.
    __slots__ = ("_code", "_message")

    def __init__(self, *, message: str | None = None) -> None:
        """
        Initialize the rule with an optional custom failure message.

        Parameters
        ----------
        message : str | None, optional
            Override message used when validation fails.

        Returns
        -------
        None
            Return ``None`` after resolving the code and message to report.
        """
        # Resolve class-level attributes once at construction time, so the
        # failure path only reads two slots.
        klass = type(self)
        self._code: str = getattr(klass, "__code__", klass.__name__.lower())
        self._message: str | None = (
            message if message is not None else getattr(klass, "__message__", None)
        )

    def enforce(
        self,
        field: str,
        value: object,
        instance: object,
    ) -> bool:
        """
        Evaluate whether the current value satisfies this rule.

        Parameters
        ----------
        field : str
            Field name associated with ``value``.
        value : object
            Current field value to validate.
        instance : object
            Schema instance that owns the field value.

        Returns
        -------
        bool
            Return ``True`` when the value passes validation.
        """
        error_msg = "Subclasses must implement the enforce method."
        raise NotImplementedError(error_msg)

    def validate(
        self,
        field: str,
        value: object,
        instance: object,
    ) -> ValidationFailure | None:
        """
        Validate the field value and return a failure when invalid.

        Parameters
        ----------
        field : str
            Field name associated with ``value``.
        value : object
            Current field value to validate.
        instance : object
            Schema instance that owns the field value.

        Returns
        -------
        ValidationFailure | None
            Failure details when validation fails; otherwise ``None``.
        """
        # Call the enforce method to check if the value satisfies the rule.
        if not self.enforce(field, value, instance):
            return ValidationFailure(
                field=field,
                rule=self._code,
                message=self._message,
            )

        # If validation passes, return None to indicate success.
        return None
