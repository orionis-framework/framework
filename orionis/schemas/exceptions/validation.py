from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

    from orionis.schemas.entities.failure import ValidationFailure

# Fallback used when the exception is built without any failure.
_DEFAULT_MESSAGE = "The given data was invalid."

class ValidationException(Exception):

    def __init__(
        self,
        failures: ValidationFailure | Sequence[ValidationFailure],
        message: str | None = None,
    ) -> None:
        """
        Initialize the exception with one or more validation failures.

        Parameters
        ----------
        failures : ValidationFailure | Sequence[ValidationFailure]
            Provide a single failure or every failure collected for a payload.
        message : str | None, optional
            Override the summary message reported to the client.

        Returns
        -------
        None
            Return ``None`` after grouping the failures by field name.
        """
        # Accept a single failure for convenience without importing the entity.
        collected: tuple[ValidationFailure, ...] = (
            tuple(failures) if isinstance(failures, (list, tuple)) else (failures,)
        )

        # Group every message under its own field.
        errors: dict[str, list[str]] = {}
        for failure in collected:
            bucket = errors.get(failure.field)
            if bucket is None:
                errors[failure.field] = [failure.message]
            else:
                bucket.append(failure.message)

        self.failures = collected
        self.failure = collected[0] if collected else None
        self.errors = errors
        self.message = message or self._summary(collected)

        super().__init__(self.message)

    @staticmethod
    def _summary(failures: tuple[ValidationFailure, ...]) -> str:
        """
        Build the summary message reported alongside the field errors.

        Parameters
        ----------
        failures : tuple[ValidationFailure, ...]
            Every failure collected for the payload.

        Returns
        -------
        str
            First failure message, suffixed with the remaining error count.
        """
        if not failures:
            return _DEFAULT_MESSAGE

        remaining = len(failures) - 1
        if not remaining:
            return failures[0].message

        plural = "s" if remaining > 1 else ""
        return f"{failures[0].message} (and {remaining} more error{plural})"

    def error(self) -> dict:
        """
        Return the validation failures as a serializable dictionary.

        Returns
        -------
        dict
            Mapping with a ``message`` summary and an ``errors`` object
            indexing every message by field name.
        """
        return {
            "message": self.message,
            "errors": self.errors,
        }
