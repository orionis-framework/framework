import asyncio
from orionis.schemas.contracts.constraint import IRule
from orionis.schemas.entities.failure import ValidationFailure

class Rule(IRule):

    # Restrict rule instances to their declared attributes.
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

    async def enforceAsync(
        self,
        field: str,
        value: object,
        instance: object,
    ) -> bool:
        """
        Run an explicitly asynchronous rule check without blocking the loop.

        Parameters
        ----------
        field : str
            Field name associated with the value.
        value : object
            Current field value to validate.
        instance : object
            Schema instance owning the field value.

        Returns
        -------
        bool
            Whether the synchronous rule accepts the value in a worker thread.

        Notes
        -----
        Rules with native asynchronous I/O should override this method. Schema
        plans call ordinary synchronous rules directly, without using a worker.
        """
        return await asyncio.to_thread(self.enforce, field, value, instance)

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

    async def validateAsync(
        self,
        field: str,
        value: object,
        instance: object,
    ) -> ValidationFailure | None:
        """Await the rule and describe an invalid field value.

        Parameters
        ----------
        field : str
            Field name associated with the value.
        value : object
            Current field value to validate.
        instance : object
            Schema instance owning the field value.

        Returns
        -------
        ValidationFailure | None
            Failure details when validation fails, otherwise None.
        """
        if not await self.enforceAsync(field, value, instance):
            return ValidationFailure(
                field=field, rule=self._code, message=self._message,
            )
        return None
