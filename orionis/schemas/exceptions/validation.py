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
        Initialize field errors and a summary from validation failures.

        Parameters
        ----------
        failures : ValidationFailure | Sequence[ValidationFailure]
            Single failure or collected payload failures in reporting order.
        message : str | None, optional
            Override the summary message reported to the client.

        Returns
        -------
        None
            Store failures, group rule codes and messages, and set the summary.
        """
        # Accept a single failure for convenience without importing the entity.
        collected: tuple[ValidationFailure, ...] = (
            tuple(failures) if isinstance(failures, (list, tuple)) else (failures,)
        )

        # Preserve the public rule code alongside every field message.
        errors: dict[str, list[dict[str, str]]] = {}
        for failure in collected:
            detail = {"rule": failure.rule, "message": failure.message}
            bucket = errors.get(failure.field)
            if bucket is None:
                errors[failure.field] = [detail]
            else:
                bucket.append(detail)

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
        Return the summary and structured field errors as a dictionary.

        Returns
        -------
        dict
            ``message`` summary and ``errors`` mapping each field to a list
            of ``{rule, message}`` objects.
        """
        return {
            "message": self.message,
            "errors": self.errors,
        }
